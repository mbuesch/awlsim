# -*- coding: utf-8 -*-
#
# AWL simulator - PLC core server
#
# Copyright 2013-2017 Michael Buesch <m@bues.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim.common.compat import *

from awlsim.common.subprocess_wrapper import *
from awlsim.common.cpuspecs import * #+cimport
from awlsim.common.cpuconfig import *
from awlsim.common.sources import *
from awlsim.common.net import *
from awlsim.common.env import *
from awlsim.common.util import *
from awlsim.common.exceptions import *

from awlsim.core.main import * #+cimport
from awlsim.core.symbolparser import *

from awlsim.awlcompiler import *

from awlsim.coreserver.messages import *
from awlsim.coreserver.memarea import *

from awlsim.fupcompiler import *

import sys
import os
import select
import signal
import socket
import errno
import time


class AwlSimClientInfo(object):
	"""Client information."""

	def __init__(self, sock, peerInfoString):
		# Socket
		self.socket = sock
		self.transceiver = AwlSimMessageTransceiver(sock, peerInfoString)

		# Broken-flag. Set, if connection breaks.
		self.broken = False

		# CPU-dump
		self.dumpInterval = 0
		self.nextDump = 0

		# Instruction state dump: Enabled lines.
		# dict key: AWL source ID number.
		# dict values: range() of AWL line numbers.
		self.insnStateDump_enabledLines = {}

		# Memory read requests
		self.memReadRequestMsg = None
		self.repetitionPeriod = 0.0
		self.nextRepTime = monotonic_time()

class AwlSimServer(object): #+cdef
	"""Awlsim coreserver server API.
	"""

	DEFAULT_HOST		= "localhost"
	DEFAULT_PORT		= 4151

	ENV_MAGIC		= "AWLSIM_CORESERVER_MAGIC"

	EnumGen.start
	_STATE_INIT		= EnumGen.item # CPU not runnable, yet.
	STATE_STOP		= EnumGen.item # CPU runnable, but stopped.
	STATE_RUN		= EnumGen.item # CPU running.
	STATE_MAINTENANCE	= EnumGen.item # CPU maintenance (stopped).
	STATE_EXIT		= EnumGen.item # CPU exiting (stopped).
	EnumGen.end

	# Command mask bits
	CMDMSK_SHUTDOWN	= (1 << 0) # Allow shutdown command

	@classmethod
	def getaddrinfo(cls, host, port, family = None):
		socktype = socket.SOCK_STREAM
		if osIsPosix and\
		   family is None and\
		   host in {"localhost", "127.0.0.1", "::1"} and\
		   False: #XXX disabled, for now
			# We are on posix OS. Instead of AF_INET on localhost,
			# we use Unix domain sockets.
			family = AF_UNIX
			sockaddr = "/tmp/awlsim-server-%d.socket" % port
		else:
			if family in {None, socket.AF_UNSPEC}:
				# First try IPv4
				try:
					family, socktype, proto, canonname, sockaddr =\
						socket.getaddrinfo(host, port,
								   socket.AF_INET,
								   socktype)[0]
				except socket.gaierror as e:
					if e.errno == socket.EAI_ADDRFAMILY:
						# Also try IPv6
						family, socktype, proto, canonname, sockaddr =\
							socket.getaddrinfo(host, port,
									   socket.AF_INET6,
									   socktype)[0]
					else:
						raise e
			else:
				family, socktype, proto, canonname, sockaddr =\
					socket.getaddrinfo(host, port,
							   family,
							   socktype)[0]
		return (family, socktype, sockaddr)

	@classmethod
	def portIsUnused(cls, host, port):
		sock = None
		result = True
		try:
			family, socktype, sockaddr = AwlSimServer.getaddrinfo(host, port)
			if family == AF_UNIX:
				if fileExists(sockaddr) == False:
					return True
				return False
			sock = socket.socket(family, socktype)
			sock.bind(sockaddr)
			sock.close()
		except SocketErrors as e:
			result = False
		if sock:
			with suppressAllExc:
				sock.shutdown(socket.SHUT_RDWR)
			with suppressAllExc:
				sock.close()
		return result

	@classmethod
	def start(cls, listenHost, listenPort,
		  listenFamily=None,
		  forkInterpreter=None,
		  forkServerProcess=None,
		  commandMask=CMDMSK_SHUTDOWN,
		  projectFile=None,
		  projectWriteBack=False):
		"""Start a new server.
		If 'forkInterpreter' or 'forkServerProcess' are not None, spawn a subprocess.
		If 'forkInterpreter' and 'forkServerProcess' are None, run the server in this process."""

		if listenFamily is None:
			listenFamily = ""
		else:
			listenFamily = int(listenFamily)

		# Prepare the environment for the server process.
		# Inherit from the starter and add awlsim specific variables.
		env = AwlSimEnv.getEnv()
		env[AwlSimServer.ENV_MAGIC]		= AwlSimServer.ENV_MAGIC
		env["AWLSIM_CORESERVER_HOST"]		= str(listenHost)
		env["AWLSIM_CORESERVER_PORT"]		= str(int(listenPort))
		env["AWLSIM_CORESERVER_FAM"]		= str(listenFamily)
		env["AWLSIM_CORESERVER_LOGLEVEL"]	= str(Logging.loglevel)
		env["AWLSIM_CORESERVER_CMDMSK"]		= str(int(commandMask))
		env["AWLSIM_CORESERVER_PROJECT"]	= str(projectFile or "")
		env["AWLSIM_CORESERVER_PROJECTRW"]	= str(int(bool(projectWriteBack)))

		if forkServerProcess:
			# Fork a new server process.
			proc = findExecutable(forkServerProcess)
			printInfo("Forking server process '%s'" % proc)
			if not proc:
				raise AwlSimError("Failed to find executable '%s'" %\
						  forkServerProcess)
			try:
				serverProcess = PopenWrapper([proc],
							     env = env)
			except OSError as e:
				raise AwlSimError("Failed to run executable '%s': %s" %(
						  forkServerProcess, str(e)))
			return serverProcess
		elif forkInterpreter:
			# Fork a new interpreter process and run server.py as module.
			interp = findExecutable(forkInterpreter)
			printInfo("Forking awlsim core server with interpreter '%s'" % interp)
			if not interp:
				raise AwlSimError("Failed to find interpreter "
						  "executable '%s'" % forkInterpreter)
			try:
				serverProcess = PopenWrapper(
					[interp, "-m", "awlsim.coreserver.run"],
					env = env)
			except OSError as e:
				raise AwlSimError("Failed to run interpreter '%s': %s" %(
						  forkInterpreter, str(e)))
			return serverProcess
		else:
			# Do not fork. Just run the server in this process.
			return cls._execute(env)

	@classmethod
	def _execute(cls, env=None):
		"""Execute the server process.
		Returns the exit() return value."""

		server, retval = None, ExitCodes.EXIT_OK
		try:
			server = AwlSimServer()
			for sig in (signal.SIGTERM, ):
				signal.signal(sig, server.signalHandler)
			server.runFromEnvironment(env)
		except AwlSimError as e:
			print(e.getReport())
			retval = ExitCodes.EXIT_ERR_SIM
		except MaintenanceRequest as e:
			print("AwlSimServer: Unhandled MaintenanceRequest:\n%s" %\
			      str(e))
			retval = ExitCodes.EXIT_ERR_SIM
		except KeyboardInterrupt:
			print("AwlSimServer: Interrupted.")
		finally:
			if server:
				server.shutdown()
		return retval

	def __init__(self):
		self.__emptyList = []
		self.__startupDone = False
		self.__state = -1
		self.__needOB10x = True
		self.__projectFile = None
		self.__projectWriteBack = False
		self.setRunState(self._STATE_INIT)

		self.__nextStats = 0
		self.__commandMask = 0
		self.__handleExceptionServerside = False
		self.__handleMaintenanceServerside = False
		self.__haveAnyMemReadReq = False

		self.__socket = None
		self.__unixSockPath = None
		self.__clients = []
		self.__sock2client = {}

		self.__sim = AwlSim()
		self.setCycleExitHook(None)

		# Container of loaded and managed AwlSource()s
		self.awlSourceContainer = SourceContainer()
		# Container of loaded and managed SymTabSource()s
		self.symTabSourceContainer = SourceContainer()
		# List of tuples of loaded hardware modules (HwmodDescriptor instances)
		self.loadedHwModules = []
		# List of loaded AwlLibEntrySelection()s
		self.loadedLibSelections = []

		self.__resetSources()

	def runFromEnvironment(self, env=None):
		"""Run the server.
		Configuration is passed via environment variables in 'env'.
		If 'env' is not passed, the current environment is used."""

		if not env:
			env = AwlSimEnv.getEnv()

		try:
			loglevel = int(env.get("AWLSIM_CORESERVER_LOGLEVEL"))
		except (TypeError, ValueError) as e:
			raise AwlSimError("AwlSimServer: No loglevel specified")
		Logging.setPrefix("AwlSimServer: ")
		Logging.setLoglevel(loglevel)

		if self.__socket:
			raise AwlSimError("AwlSimServer: Already running")

		if env.get(self.ENV_MAGIC) != self.ENV_MAGIC:
			raise AwlSimError("AwlSimServer: Missing magic value")

		host = env.get("AWLSIM_CORESERVER_HOST")
		if host is None:
			raise AwlSimError("AwlSimServer: No listen host specified")
		try:
			port = int(env.get("AWLSIM_CORESERVER_PORT"))
		except (TypeError, ValueError) as e:
			raise AwlSimError("AwlSimServer: No listen port specified")
		try:
			fam = env.get("AWLSIM_CORESERVER_FAM")
			if fam and fam.strip():
				fam = int(fam)
			else:
				fam = None
		except (TypeError, ValueError) as e:
			raise AwlSimError("AwlSimServer: Invalid family specified")

		try:
			commandMask = int(env.get("AWLSIM_CORESERVER_CMDMSK"))
		except (TypeError, ValueError) as e:
			raise AwlSimError("AwlSimServer: No command mask specified")

		projectFile = env.get("AWLSIM_CORESERVER_PROJECT")
		try:
			projectWriteBack = bool(int(env.get("AWLSIM_CORESERVER_PROJECTRW")))
		except (TypeError, ValueError) as e:
			projectWriteBack = True

		self.startup(host = host,
			     port = port,
			     family = fam,
			     commandMask = commandMask,
			     project = projectFile,
			     projectWriteBack = projectWriteBack)
		self.run()

	def getRunState(self):
		return self.__state

	def setRunState(self, runstate):
		if self.__state == runstate:
			# Already in that state.
			return
		if self.__state == self.STATE_EXIT:
			# We are exiting. Cannot set another state.
			return

		if runstate == self.STATE_RUN or\
		   runstate == self.STATE_STOP:
			# Reset instruction dump serial number
			self.__insnSerial = 0

		if runstate == self._STATE_INIT:
			# We just entered initialization state.
			printVerbose("Putting CPU into INIT state.")
			self.__needOB10x = True
		elif runstate == self.STATE_RUN:
			# We just entered RUN state.
			if self.__needOB10x:
				printVerbose("CPU startup (OB 10x).")
				self.__sim.startup()
				self.__needOB10x = False
			printVerbose("Putting CPU into RUN state.")
		elif runstate == self.STATE_STOP:
			# We just entered STOP state.
			printVerbose("Putting CPU into STOP state.")
		elif runstate == self.STATE_MAINTENANCE:
			# We just entered MAINTENANCE state.
			printVerbose("Putting CPU into MAINTENANCE state.")
			self.__needOB10x = True

		self.__state = runstate
		# Make a shortcut variable for RUN
		self.__running = bool(runstate == self.STATE_RUN)

	def __getMnemonics(self):
		return self.__sim.cpu.getConf().getMnemonics()

	def __rebuildSelectReadList(self):
		rlist = [ self.__socket ]
		rlist.extend(client.transceiver.sock for client in self.__clients)
		self.__selectRlist = rlist

	def __sendCpuDump(self, constrained=True):
		dumpText = self.__sim.cpu.dump(withTime=self.__running)
		if not dumpText:
			return
		msg = AwlSimMessage_CPUDUMP(dumpText)
		now = self.__sim.cpu.now
		broken = False
		for client in self.__clients:
			if client.dumpInterval and\
			   (now >= client.nextDump or not constrained):
				client.nextDump = now + client.dumpInterval / 1000.0
				try:
					client.transceiver.send(msg)
				except TransferError as e:
					client.broken = broken = True
		if broken:
			self.__removeBrokenClients()

	def __cpuBlockExitCallback(self, userData):
		now = self.__sim.cpu.now
		if any(c.dumpInterval and now >= c.nextDump for c in self.__clients):
			self.__sendCpuDump()

	def __cpuPostInsnCallback(self, callStackElement, userData):
		try:
			insn = callStackElement.insns[callStackElement.ip]
		except IndexError:
			return
		cpu, sourceId, lineNr, msg =\
			self.__sim.cpu, insn.getSourceId(), insn.getLineNr(), None
		broken = False
		for client in self.__clients:
			try:
				if lineNr not in client.insnStateDump_enabledLines[sourceId]:
					continue
			except KeyError:
				continue
			if not msg:
				msg = AwlSimMessage_INSNSTATE(
					sourceId,
					lineNr & 0xFFFFFFFF,
					self.__insnSerial,
					0,
					cpu.statusWord.getWord(),
					cpu.accu1.get(),
					cpu.accu2.get(),
					cpu.accu3.get(),
					cpu.accu4.get(),
					cpu.ar1.get(),
					cpu.ar2.get(),
					cpu.dbRegister.index & 0xFFFF,
					cpu.diRegister.index & 0xFFFF)
			try:
				client.transceiver.send(msg)
			except TransferError as e:
				client.broken = broken = True
		if broken:
			self.__removeBrokenClients()
		self.__insnSerial += 1

	def __printCpuStats(self):
		cpu = self.__sim.cpu
		if cpu.insnPerSecond:
			usPerInsn = "%.03f" % ((1.0 / cpu.insnPerSecond) * 1000000)
		else:
			usPerInsn = "-/-"
		printVerbose("[CPU] "
			"%d stmt/s (= %s us/stmt); %.01f stmt/cycle" %\
			(int(round(cpu.insnPerSecond)),
			 usPerInsn,
			 cpu.avgInsnPerCycle))

	def __cpuCycleExitCallback(self, userData):
		# Reset instruction dump serial number
		self.__insnSerial = 0

		# Print CPU stats, if requested.
		if Logging.loglevel >= Logging.LOG_VERBOSE:
			now = self.__sim.cpu.now
			if now >= self.__nextStats:
				self.__nextStats = now + 1.0
				self.__printCpuStats()

		# Call the cycle exit hook, if any.
		if self.__cycleExitHook:
			self.__cycleExitHook(self.__cycleExitHookData)

	def __updateCpuBlockExitCallback(self):
		if any(c.dumpInterval for c in self.__clients):
			self.__sim.cpu.setBlockExitCallback(self.__cpuBlockExitCallback, None)
		else:
			self.__sim.cpu.setBlockExitCallback(None)

	def __updateCpuPostInsnCallback(self):
		if any(c.insnStateDump_enabledLines for c in self.__clients):
			self.__sim.cpu.setPostInsnCallback(self.__cpuPostInsnCallback, None)
		else:
			self.__sim.cpu.setPostInsnCallback(None)

	def __updateCpuCycleExitCallback(self):
		if any(c.insnStateDump_enabledLines for c in self.__clients) or\
		   Logging.loglevel >= Logging.LOG_VERBOSE or\
		   self.__cycleExitHook:
			self.__sim.cpu.setCycleExitCallback(self.__cpuCycleExitCallback, None)
		else:
			self.__sim.cpu.setCycleExitCallback(None)

	def __updateCpuCallbacks(self):
		self.__updateCpuBlockExitCallback()
		self.__updateCpuPostInsnCallback()
		self.__updateCpuCycleExitCallback()

	def __generateProject(self):
		cpu = self.__sim.getCPU()
		awlSources = self.awlSourceContainer.getSources()
		fupSources = [] #TODO
		kopSources = [] #TODO
		symTabSources = self.symTabSourceContainer.getSources()
		libSelections = self.loadedLibSelections[:]
		cpuSpecs = cpu.getSpecs() # (Note: not a deep-copy)
		cpuConf = cpu.getConf() # (Note: not a deep-copy)
		hwmodSettings = HwmodSettings(
			loadedModules = self.loadedHwModules[:]
		)
		project = Project(
			projectFile = None,
			awlSources = awlSources,
			fupSources = fupSources,
			kopSources = kopSources,
			symTabSources = symTabSources,
			libSelections = libSelections,
			cpuSpecs = cpuSpecs,
			cpuConf = cpuConf,
			obTempPresetsEn = cpu.obTempPresetsEnabled(),
			extInsnsEn = cpu.extendedInsnsEnabled(),
			guiSettings = None,
			coreLinkSettings = None,
			hwmodSettings = hwmodSettings,
		)
		return project

	def __updateProjectFile(self):
		if not self.__projectWriteBack or\
		   not self.__projectFile:
			return
		printDebug("Updating project file '%s'" % self.__projectFile)
		project = self.__generateProject()
		project.toFile(self.__projectFile)

	def __resetSources(self):
		self.awlSourceContainer.clear()
		self.symTabSourceContainer.clear()
		self.loadedHwModules = []
		self.loadedLibSelections = []
		# Schedule a CPU restart/rebuild.
		self.__needOB10x = True

		self.__updateProjectFile()

	def __resetAll(self):
		self.setRunState(self.STATE_STOP)
		self.__sim.reset()
		self.__resetSources()

	def removeSource(self, identHash):
		ret = True
		srcMgr = self.awlSourceContainer.getSourceManagerByIdent(identHash)
		tabMgr = self.symTabSourceContainer.getSourceManagerByIdent(identHash)
		try:
			if srcMgr:
				# Remove all blocks that were created from this source.
				for block in srcMgr.getBlocks():
					if not isinstance(block, CodeBlock):
						# This is not a compiled block.
						continue
					blockInfo = block.getBlockInfo()
					if not blockInfo:
						continue
					self.__sim.removeBlock(blockInfo,
							       sanityChecks = False)
				# Remove the source, if it's not gone already.
				self.awlSourceContainer.removeByIdent(identHash)
				# Run static sanity checks now to ensure
				# the CPU is still runnable.
				self.__sim.staticSanityChecks()
			elif tabMgr:
				pass#TODO
				ret = False
		finally:
			if ret:
				self.__updateProjectFile()
		return ret

	def loadAwlSource(self, awlSource):
		parser = AwlParser()
		parser.parseSource(awlSource)

		srcManager = SourceManager(awlSource)

		if awlSource.enabled:
			needRebuild = False
			if self.__state == self.STATE_RUN or\
			   (self.__state == self.STATE_STOP and\
			    not self.__needOB10x):
				needRebuild = True
			self.__sim.load(parser.getParseTree(), needRebuild, srcManager)

		self.awlSourceContainer.addManager(srcManager)
		self.__updateProjectFile()

	def loadFupSource(self, fupSource):
		#TODO src manager
		#TODO do not add to awlSourceContainer
		if fupSource.enabled:
			compiler = FupCompiler()
			#FIXME mnemonics auto detection might cause mismatching mnemonics w.r.t. the main blocks.
			symSrcs = self.symTabSourceContainer.getSources()
			awlSource = compiler.compile(fupSource=fupSource,
						     symTabSources=symSrcs,
						     mnemonics=self.__getMnemonics())
			self.loadAwlSource(awlSource)

	def loadKopSource(self, kopSource):
		if kopSource.enabled:
			pass#TODO

	def loadSymTabSource(self, symTabSource):
		srcManager = SourceManager(symTabSource)

		if symTabSource.enabled:
			symbolTable = SymTabParser.parseSource(symTabSource,
						autodetectFormat=True,
						mnemonics=self.__getMnemonics())

			self.setRunState(self.STATE_STOP)
			self.__sim.loadSymbolTable(symbolTable)

		self.symTabSourceContainer.addManager(srcManager)
		self.__updateProjectFile()

	def loadHardwareModule(self, hwmodDesc):
		hwmodName = hwmodDesc.getModuleName()
		printInfo("Loading hardware module '%s'..." % hwmodName)

		hwClass = self.__sim.loadHardwareModule(hwmodDesc.getModuleName())
		self.__sim.registerHardwareClass(hwClass = hwClass,
						 parameters = hwmodDesc.getParameters())

		self.loadedHwModules.append(hwmodDesc)
		self.__updateProjectFile()

		printInfo("Hardware module '%s' loaded." % hwmodName)

	def loadLibraryBlock(self, libSelection):
		self.setRunState(self.STATE_STOP)
		self.__sim.loadLibraryBlock(libSelection)

		self.loadedLibSelections.append(libSelection)
		self.__updateProjectFile()

	def cpuEnableObTempPresets(self, en):
		self.__sim.cpu.enableObTempPresets(en)
		self.__updateProjectFile()

	def cpuEnableExtendedInsns(self, en):
		self.__sim.cpu.enableExtendedInsns(en)
		self.__updateProjectFile()

	def cpuSetCycleTimeLimit(self, limitSeconds):
		self.__sim.cpu.setCycleTimeLimit(limitSeconds)
		self.__updateProjectFile()

	def cpuSetRunTimeLimit(self, limitSeconds):
		self.__sim.cpu.setRunTimeLimit(limitSeconds)
		self.__updateProjectFile()

	def cpuSetSpecs(self, cpuSpecs):
		self.__sim.cpu.getSpecs().assignFrom(cpuSpecs)
		self.__updateProjectFile()

	def cpuSetConf(self, cpuConf):
		self.__sim.cpu.getConf().assignFrom(cpuConf)
		self.__updateProjectFile()

	def setCycleExitHook(self, hook, hookData = None):
		self.__cycleExitHook = hook
		self.__cycleExitHookData = hookData
		self.__updateCpuCallbacks()

	def __rx_PING(self, client, msg):
		printDebug("Received message: PING")
		client.transceiver.send(AwlSimMessage_PONG())

	def __rx_PONG(self, client, msg):
		printInfo("Received message: PONG")

	def __rx_RESET(self, client, msg):
		printVerbose("Resetting CPU.")
		status = AwlSimMessage_REPLY.STAT_OK
		self.__resetAll()
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_SHUTDOWN(self, client, msg):
		printDebug("Received message: SHUTDOWN")
		status = AwlSimMessage_REPLY.STAT_FAIL
		if self.__commandMask & AwlSimServer.CMDMSK_SHUTDOWN:
			printInfo("Exiting due to shutdown command")
			self.setRunState(self.STATE_EXIT)
			status = AwlSimMessage_REPLY.STAT_OK
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_RUNSTATE(self, client, msg):
		printDebug("Received message: RUNSTATE %d" % msg.runState)
		status = AwlSimMessage_REPLY.STAT_OK
		if msg.runState == msg.STATE_STOP:
			self.setRunState(self.STATE_STOP)
		elif msg.runState == msg.STATE_RUN:
			if self.__state == self.STATE_RUN:
				pass
			elif self.__state == self.STATE_STOP or\
			     self.__state == self.STATE_MAINTENANCE:
				self.setRunState(self.STATE_RUN)
			else:
				status = AwlSimMessage_REPLY.STAT_FAIL
		else:
			status = AwlSimMessage_REPLY.STAT_FAIL
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_GET_RUNSTATE(self, client, msg):
		printDebug("Received message: GET_RUNSTATE")
		reply = AwlSimMessage_RUNSTATE(
			AwlSimMessage_RUNSTATE.STATE_RUN\
			if self.__state == self.STATE_RUN else\
			AwlSimMessage_RUNSTATE.STATE_STOP
		)
		client.transceiver.send(reply)

	def __rx_GET_AWLSRC(self, client, msg):
		printDebug("Received message: GET_AWLSRC")
		awlSource = self.awlSourceContainer.getSourceByIdent(msg.identHash)
		reply = AwlSimMessage_AWLSRC(awlSource)
		client.transceiver.send(reply)

	def __rx_AWLSRC(self, client, msg):
		printDebug("Received message: AWLSRC")
		status = AwlSimMessage_REPLY.STAT_OK
		self.loadAwlSource(msg.source)
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_GET_SYMTABSRC(self, client, msg):
		printDebug("Received message: GET_SYMTABSRC")
		symTabSource = self.symTabSourceContainer.getSourceByIdent(msg.identHash)
		reply = AwlSimMessage_SYMTABSRC(symTabSource)
		client.transceiver.send(reply)

	def __rx_SYMTABSRC(self, client, msg):
		printDebug("Received message: SYMTABSRC")
		status = AwlSimMessage_REPLY.STAT_OK
		self.loadSymTabSource(msg.source)
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_HWMOD(self, client, msg):
		printDebug("Received message: HWMOD")
		status = AwlSimMessage_REPLY.STAT_OK
		self.loadHardwareModule(msg.hwmodDesc)
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_LIBSEL(self, client, msg):
		printDebug("Received message: LIBSEL")
		status = AwlSimMessage_REPLY.STAT_OK
		self.loadLibraryBlock(msg.libSelection)
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_FUPSRC(self, client, msg):
		printDebug("Received message: FUPSRC")
		status = AwlSimMessage_REPLY.STAT_OK
		self.loadFupSource(msg.source)
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_KOPSRC(self, client, msg):
		printDebug("Received message: KOPSRC")
		status = AwlSimMessage_REPLY.STAT_OK
		self.loadKopSource(msg.source)
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_BUILD(self, client, msg):
		printDebug("Received message: BUILD")
		status = AwlSimMessage_REPLY.STAT_OK
		self.__sim.build()
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_REMOVESRC(self, client, msg):
		printDebug("Received message: REMOVESRC")
		status = AwlSimMessage_REPLY.STAT_OK
		if not self.removeSource(msg.identHash):
			status = AwlSimMessage_REPLY.STAT_FAIL
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_REMOVEBLK(self, client, msg):
		printDebug("Received message: REMOVEBLK")
		status = AwlSimMessage_REPLY.STAT_OK
		self.__sim.removeBlock(msg.blockInfo)
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_OPT(self, client, msg):
		printDebug("Received message: OPT %s" % msg.name)
		status = AwlSimMessage_REPLY.STAT_OK

		if msg.name == "loglevel":
			Logging.setLoglevel(msg.getIntValue())
		elif msg.name == "ob_temp_presets":
			self.cpuEnableObTempPresets(msg.getBoolValue())
		elif msg.name == "extended_insns":
			self.cpuEnableExtendedInsns(msg.getBoolValue())
		elif msg.name == "periodic_dump_int":
			client.dumpInterval = msg.getIntValue()
			if client.dumpInterval:
				client.nextDump = self.__sim.cpu.now
			else:
				client.nextDump = None
			self.__updateCpuCallbacks()
		elif msg.name == "cycle_time_limit":
			self.cpuSetCycleTimeLimit(msg.getFloatValue())
		elif msg.name == "runtime_limit":
			self.cpuSetRunTimeLimit(msg.getFloatValue())
		else:
			status = AwlSimMessage_REPLY.STAT_FAIL

		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_GET_BLOCKINFO(self, client, msg):
		printDebug("Received message: GET_BLOCKINFO")

		blockInfos = self.__sim.cpu.getBlockInfos(
			getOBInfo = bool(msg.getFlags & msg.GET_OB_INFO),
			getFCInfo = bool(msg.getFlags & msg.GET_FC_INFO),
			getFBInfo = bool(msg.getFlags & msg.GET_FB_INFO),
			getDBInfo = bool(msg.getFlags & msg.GET_DB_INFO))
		reply = AwlSimMessage_BLOCKINFO(blockInfos)
		client.transceiver.send(reply)

	def __rx_GET_CPUSPECS(self, client, msg):
		printDebug("Received message: GET_CPUSPECS")
		reply = AwlSimMessage_CPUSPECS(self.__sim.cpu.getSpecs())
		client.transceiver.send(reply)

	def __rx_CPUSPECS(self, client, msg):
		printDebug("Received message: CPUSPECS")
		status = AwlSimMessage_REPLY.STAT_OK
		self.cpuSetSpecs(msg.cpuspecs)
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_GET_CPUCONF(self, client, msg):
		printDebug("Received message: GET_CPUCONF")
		reply = AwlSimMessage_CPUCONF(self.__sim.cpu.getConf())
		client.transceiver.send(reply)

	def __rx_CPUCONF(self, client, msg):
		printDebug("Received message: CPUCONF")
		status = AwlSimMessage_REPLY.STAT_OK
		self.cpuSetConf(msg.cpuconf)
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_REQ_MEMORY(self, client, msg):
		printDebug("Received message: REQ_MEMORY")
		client.memReadRequestMsg = AwlSimMessage_MEMORY(0, msg.memAreas)
		client.repetitionPeriod = msg.repetitionPeriod
		client.nextRepTime = monotonic_time()
		self.__updateMemReadReqFlag()
		if msg.flags & msg.FLG_SYNC:
			client.transceiver.send(AwlSimMessage_REPLY.make(
				msg, AwlSimMessage_REPLY.STAT_OK)
			)

	def __rx_MEMORY(self, client, msg):
		printDebug("Received message: MEMORY")
		cpu = self.__sim.cpu
		status = AwlSimMessage_REPLY.STAT_OK
		for memArea in msg.memAreas:
			try:
				memArea.writeToCpu(cpu)
			except AwlSimError as e:
				if memArea.flags & (MemoryArea.FLG_ERR_READ |\
						    MemoryArea.FLG_ERR_WRITE):
					# Just signal failure to the client.
					status = AwlSimMessage_REPLY.STAT_FAIL
				else:
					# This is a serious fault.
					# Re-raise the exception.
					raise
		if msg.flags & msg.FLG_SYNC:
			client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_INSNSTATE_CONFIG(self, client, msg):
		printDebug("Received message: INSNSTATE_CONFIG")
		status = AwlSimMessage_REPLY.STAT_OK
		if msg.flags & (msg.FLG_CLEAR | msg.FLG_CLEAR_ONLY):
			client.insnStateDump_enabledLines = {}
		if not (msg.flags & msg.FLG_CLEAR_ONLY):
			rnge = range(msg.fromLine, msg.toLine + 1)
			client.insnStateDump_enabledLines[msg.sourceId] = rnge
		self.__updateCpuCallbacks()
		if msg.flags & msg.FLG_SYNC:
			client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_GET_IDENTS(self, client, msg):
		printDebug("Received message: GET_IDENTS")
		awlSrcs = symSrcs = hwMods = libSels = fupSrcs = kopSrcs = ()
		if msg.getFlags & msg.GET_AWLSRCS:
			awlSrcs = self.awlSourceContainer.getSources()
		if msg.getFlags & msg.GET_SYMTABSRCS:
			symSrcs = self.symTabSourceContainer.getSources()
		if msg.getFlags & msg.GET_HWMODS:
			hwMods = self.loadedHwModules
		if msg.getFlags & msg.GET_LIBSELS:
			libSels = self.loadedLibSelections
		if msg.getFlags & msg.GET_FUPSRCS:
			pass#TODO
		if msg.getFlags & msg.GET_KOPSRCS:
			pass#TODO
		reply = AwlSimMessage_IDENTS(awlSrcs, symSrcs,
					     hwMods, libSels,
					     fupSrcs, kopSrcs)
		client.transceiver.send(reply)

	__msgRxHandlers = {
		AwlSimMessage.MSG_ID_PING		: __rx_PING,
		AwlSimMessage.MSG_ID_PONG		: __rx_PONG,
		AwlSimMessage.MSG_ID_RESET		: __rx_RESET,
		AwlSimMessage.MSG_ID_SHUTDOWN		: __rx_SHUTDOWN,
		AwlSimMessage.MSG_ID_RUNSTATE		: __rx_RUNSTATE,
		AwlSimMessage.MSG_ID_GET_RUNSTATE	: __rx_GET_RUNSTATE,
		AwlSimMessage.MSG_ID_GET_AWLSRC		: __rx_GET_AWLSRC,
		AwlSimMessage.MSG_ID_AWLSRC		: __rx_AWLSRC,
		AwlSimMessage.MSG_ID_GET_SYMTABSRC	: __rx_GET_SYMTABSRC,
		AwlSimMessage.MSG_ID_SYMTABSRC		: __rx_SYMTABSRC,
		AwlSimMessage.MSG_ID_HWMOD		: __rx_HWMOD,
		AwlSimMessage.MSG_ID_LIBSEL		: __rx_LIBSEL,
		AwlSimMessage.MSG_ID_FUPSRC		: __rx_FUPSRC,
#		AwlSimMessage.MSG_ID_KOPSRC		: __rx_KOPSRC,
		AwlSimMessage.MSG_ID_BUILD		: __rx_BUILD,
		AwlSimMessage.MSG_ID_REMOVESRC		: __rx_REMOVESRC,
		AwlSimMessage.MSG_ID_REMOVEBLK		: __rx_REMOVEBLK,
		AwlSimMessage.MSG_ID_OPT		: __rx_OPT,
		AwlSimMessage.MSG_ID_GET_BLOCKINFO	: __rx_GET_BLOCKINFO,
		AwlSimMessage.MSG_ID_GET_CPUSPECS	: __rx_GET_CPUSPECS,
		AwlSimMessage.MSG_ID_CPUSPECS		: __rx_CPUSPECS,
		AwlSimMessage.MSG_ID_GET_CPUCONF	: __rx_GET_CPUCONF,
		AwlSimMessage.MSG_ID_CPUCONF		: __rx_CPUCONF,
		AwlSimMessage.MSG_ID_REQ_MEMORY		: __rx_REQ_MEMORY,
		AwlSimMessage.MSG_ID_MEMORY		: __rx_MEMORY,
		AwlSimMessage.MSG_ID_INSNSTATE_CONFIG	: __rx_INSNSTATE_CONFIG,
		AwlSimMessage.MSG_ID_GET_IDENTS		: __rx_GET_IDENTS,
	}

	def __clientCommTransferError(self, exception, client):
		if exception.reason == exception.REASON_REMOTEDIED:
			printInfo("Client '%s' disconnected" %\
				  client.transceiver.peerInfoString)
		else:
			printInfo("Client '%s' data "
				"transfer error:\n%s" %\
				(client.transceiver.peerInfoString,
				 str(exception)))
		self.__clientRemove(client)

	def __handleClientComm(self, client): #+cdef
		try:
			msg = client.transceiver.receive(0.0)
		except TransferError as e:
			self.__clientCommTransferError(e, client)
			return
		if not msg:
			return
		try:
			handler = self.__msgRxHandlers[msg.msgId]
		except KeyError:
			printInfo("Received unsupported "
				"message 0x%02X" % msg.msgId)
			return
		try:
			handler(self, client, msg)
		except TransferError as e:
			self.__clientCommTransferError(e, client)
			return

	def __handleSocketComm(self, sockList): #@nocy
#@cy	cdef __handleSocketComm(self, list sockList):
		if self.__socket in sockList:
			sockList.remove(self.__socket)
			self.__accept()
		for sock in sockList:
			self.__handleClientComm(self.__sock2client[sock])

	def __selectException(self, exception):
		raise AwlSimError("AwlSimServer: Communication error. "
				  "'select' failed")

	def __handleCommunication(self, __select=select.select, __Exception=Exception): #@nocy
#@cy	cdef __handleCommunication(self, object __select=select.select, type __Exception=Exception):
#@cy		cdef list rlist
#@cy		cdef list wlist
#@cy		cdef list xlist

		try:
			rlist, wlist, xlist = __select(self.__selectRlist,
						       self.__emptyList,
						       self.__emptyList, 0.0)
			if not rlist:
				return
		except __Exception as e:
			self.__selectException(e)
		self.__handleSocketComm(rlist)

		# Check again to receive more data (with a small timeout).
		while True:
			try:
				rlist, wlist, xlist = __select(self.__selectRlist,
							       self.__emptyList,
							       self.__emptyList, 0.01)
				if not rlist:
					return
			except __Exception as e:
				self.__selectException(e)
			self.__handleSocketComm(rlist)

	def __handleCommunicationBlocking(self):
		try:
			select.select(self.__selectRlist, [], [], None)
		except Exception as e:
			self.__selectException(e)
		self.__handleCommunication()

	def __updateMemReadReqFlag(self):
		self.__haveAnyMemReadReq = bool(any(bool(c.memReadRequestMsg)
						    for c in self.__clients))

	def __handleMemReadReqs(self, constrained=True):
		broken = False
		for client in self.__clients:
			if not client.memReadRequestMsg:
				continue

			if client.repetitionPeriod < 0.0:
				# One shot mem read request.
				memReadRequestMsg = client.memReadRequestMsg
				self.memReadRequestMsg = None
			else:
				# Repetitive mem read request.
				now = monotonic_time()
				if now < client.nextRepTime and constrained:
					continue # Time constrained. Don't send, yet.
				client.nextRepTime = now + client.repetitionPeriod
				memReadRequestMsg = client.memReadRequestMsg

			cpu, memAreas = self.__sim.cpu, memReadRequestMsg.memAreas
			for memArea in memAreas:
				memArea.flags = 0
				try:
					memArea.readFromCpu(cpu)
				except AwlSimError as e:
					if memArea.flags & (MemoryArea.FLG_ERR_READ |\
							    MemoryArea.FLG_ERR_WRITE):
						# We do not forward this as an exception.
						# The client is supposed to check the error bits.
						# Just continue as usual.
						pass
					else:
						# This is a serious fault.
						# Re-raise the exception.
						raise e
			try:
				client.transceiver.send(memReadRequestMsg)
			except TransferError as e:
				client.broken = broken = True
		if broken:
			self.__removeBrokenClients()

	def __loadProject(self, project, writeBack):
		self.__projectFile = None
		self.__projectWriteBack = False
		if not project:
			return

		if isString(project):
			if fileExists(project) == False and writeBack:
				# The project file does not exist.
				# Create an empty one.
				printInfo("Creating empty project at '%s'" %\
					  project)
				empty = Project(project)
				empty.toFile()
			project = Project.fromProjectOrRawAwlFile(project)
		printDebug("Loading project '%s'" % str(project))

		self.__resetAll()

		for modDesc in project.getHwmodSettings().getLoadedModules():
			self.loadHardwareModule(modDesc)
		self.cpuEnableObTempPresets(project.getObTempPresetsEn())
		self.cpuEnableExtendedInsns(project.getExtInsnsEn())
		self.cpuSetSpecs(project.getCpuSpecs())
		#TODO set cycle time limit
		#TODO set run time limit

		for symSrc in project.getSymTabSources():
			self.loadSymTabSource(symSrc)
		for libSel in project.getLibSelections():
			self.loadLibraryBlock(libSel)
		for awlSrc in project.getAwlSources():
			self.loadAwlSource(awlSrc)
		for fupSrc in project.getFupSources():
			self.loadFupSource(fupSrc)
		for kopSrc in project.getKopSources():
			self.loadKopSource(kopSrc)

		self.__projectFile = project.getProjectFile()
		self.__projectWriteBack = writeBack

	def startup(self, host, port, family = None,
		    commandMask = 0,
		    handleExceptionServerside = False,
		    handleMaintenanceServerside = False,
		    project = None,
		    projectWriteBack = False):
		"""Start the server on 'host':'port'.
		family -> Address family. Either None or one of socket.AF_...
		commanMask -> Mask of allowed commands (CMDMSK_...).
		handleExceptionServerside -> Flag whether to raise AwlSimError()
		                             exceptions on the server only.
		handleMaintenanceServerside -> Flag whether to raise maintenance
		                               request exceptions on the server only.
		project -> If this is a .awlpro path string or Project(), it uses the data
		           from the specified project as an initial program.
		projectWriteBack -> If True, all data changes (e.g. source download)
		                    be written to the projectFile (if available).
		This must be called once before run()."""

		assert(not self.__startupDone)
		self.__commandMask = commandMask
		self.__handleExceptionServerside = handleExceptionServerside
		self.__handleMaintenanceServerside = handleMaintenanceServerside

		self.__loadProject(project, projectWriteBack)

		self.__listen(host, port, family)
		self.__rebuildSelectReadList()

		self.__nextStats = self.__sim.cpu.now
		self.__updateCpuCallbacks()

		self.__startupDone = True
		self.setRunState(self.STATE_STOP)

	def run(self):
		"""Run the main server event loop."""
#@cy		cdef AwlSim sim

		# Check whether startup() was called and
		# the CPU is in a runnable state.
		assert(self.__startupDone)
		assert(self.__state in (self.STATE_STOP,
					self.STATE_RUN,
					self.STATE_MAINTENANCE))

		# Main event loop.
		while self.__state != self.STATE_EXIT:
			try:
				sim = self.__sim

				if self.__state in {self.STATE_STOP,
						    self.STATE_MAINTENANCE}:
					while self.__state in {self.STATE_STOP,
							       self.STATE_MAINTENANCE}:
						self.__sendCpuDump(constrained=False)
						self.__handleMemReadReqs(constrained=False)
						self.__handleCommunicationBlocking()
					continue

				if self.__state == self.STATE_RUN:
					while self.__running:
						sim.runCycle()
						if self.__haveAnyMemReadReq:
							self.__handleMemReadReqs()
						self.__handleCommunication()
					continue

			except (AwlSimError, AwlParserError) as e:
				self.setRunState(self.STATE_STOP)
				# Schedule a CPU restart/rebuild.
				self.__needOB10x = True

				if self.__handleExceptionServerside:
					# Let the server handle the exception
					raise e
				else:
					# Send the exception to all clients.
					msg = AwlSimMessage_EXCEPTION(e)
					for client in self.__clients:
						try:
							client.transceiver.send(msg)
						except TransferError as e:
							printError("Failed to forward "
								   "exception to client.")
							client.broken = True
					self.__removeBrokenClients()
			except MaintenanceRequest as e:
				# Put the CPU into maintenance mode.
				# This will halt the CPU until a client
				# or the server sets it into RUN or STOP again.
				self.setRunState(self.STATE_MAINTENANCE)
				if self.__handleMaintenanceServerside:
					# Let the server handle the request.
					raise e
				else:
					# Send the maintenance message.
					with contextlib.suppress(TransferError):
						if self.__clients:
							# Forward it to the first client
							msg = AwlSimMessage_MAINTREQ(e)
							self.__clients[0].transceiver.send(msg)
			except TransferError as e:
				# This should be caught earlier.
				printError("Uncaught transfer error: " + str(e))

	def __listen(self, host, port, family):
		"""Listen on 'host':'port'."""

		if family is None or\
		   family not in {socket.AF_INET,
				  socket.AF_INET6,
				  AF_UNIX}:
			family = None # autodetect

		self.close()
		try:
			if host:
				family, socktype, sockaddr = netGetAddrInfo(
						host, port, family)
				if family == AF_UNIX:
					self.__unixSockPath = sockaddr
					readableSockaddr = sockaddr
				else:
					readableSockaddr = "[%s]:%d" % (sockaddr[0], sockaddr[1])
			else:
				if family is None:
					family = socket.AF_INET
				if family == AF_UNIX:
					raise AwlSimError("AwlSimServer: "
						"AF_UNIX can't be used with 'ANY' host.")
				assert(family in {socket.AF_INET, socket.AF_INET6})
				socktype = socket.SOCK_STREAM
				sockaddr = ("", # INADDR_ANY
					    port)
				readableSockaddr = "[all-interfaces-ipv%d]:%d" %\
						(4 if family == socket.AF_INET else 6,
						 port)
			printInfo("Listening on %s..." % readableSockaddr)
			sock = socket.socket(family, socktype)
			sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			sock.setblocking(False)
			sock.bind(sockaddr)
			sock.listen(5)
		except SocketErrors as e:
			raise AwlSimError("AwlSimServer: Failed to create server "
				"socket: " + str(e))
		self.__socket = sock

	def __accept(self):
		"""Accept a client connection.
		Returns the Client instance or None."""

		if not self.__socket:
			raise AwlSimError("AwlSimServer: No server socket")

		try:
			clientSock, addrInfo = self.__socket.accept()
			if self.__unixSockPath:
				peerInfoString = self.__unixSockPath
			else:
				peerInfoString = "[%s]:%d" % addrInfo[:2]
		except SocketErrors as e:
			transferError = TransferError(None, parentException = e)
			if transferError.reason == transferError.REASON_BLOCKING:
				return None
			raise AwlSimError("AwlSimServer: accept() failed: %s" % str(e))
		printInfo("Client '%s' connected" % peerInfoString)

		client = AwlSimClientInfo(clientSock, peerInfoString)
		self.__clientAdd(client)

		return client

	def __clientAdd(self, client):
		self.__clients.append(client)
		self.__sock2client[client.socket] = client
		self.__rebuildSelectReadList()

	def __clientRemove(self, client):
		self.__clients.remove(client)
		self.__sock2client.pop(client.socket)
		self.__rebuildSelectReadList()
		self.__updateCpuCallbacks()
		self.__updateMemReadReqFlag()

	def __removeBrokenClients(self):
		for client in [ c for c in self.__clients if c.broken ]:
			self.__clientRemove(client)
		self.__updateMemReadReqFlag()

	def close(self):
		"""Closes all client sockets and the main socket."""

		self.__startupDone = False

		for client in self.__clients:
			client.transceiver.shutdown()
			client.transceiver = None
			client.socket = None
		self.__clients = []

		if self.__socket:
			with suppressAllExc:
				self.__socket.shutdown(socket.SHUT_RDWR)
			with suppressAllExc:
				self.__socket.close()
			self.__socket = None
		if self.__unixSockPath:
			with contextlib.suppress(OSError):
				os.unlink(self.__unixSockPath)
			self.__unixSockPath = None

	def shutdown(self):
		printInfo("Shutting down.")
		self.close()
		self.__sim.shutdown()

	def signalHandler(self, sig, frame):
		printInfo("Received signal %d" % sig)
		if sig in (signal.SIGTERM, signal.SIGINT):
			self.setRunState(self.STATE_EXIT)

if __name__ == "__main__":
	# Run a server process.
	# Parameters are passed via environment.
	sys.exit(AwlSimServer._execute())

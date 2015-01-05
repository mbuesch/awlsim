# -*- coding: utf-8 -*-
#
# AWL simulator - PLC core server
#
# Copyright 2013-2014 Michael Buesch <m@bues.ch>
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

from awlsim.common.subprocess import *
from awlsim.common.cpuspecs import *

from awlsim.core.main import *
from awlsim.core.parser import *

from awlsim.coreserver.messages import *

import sys
import os
import select
import signal
import socket
import errno
import time

if hasattr(socket, "AF_UNIX"):
	AF_UNIX = socket.AF_UNIX
else:
	AF_UNIX = None


class AwlSimServer(object):
	DEFAULT_HOST	= "localhost"
	DEFAULT_PORT	= 4151

	ENV_MAGIC	= "AWLSIM_CORESERVER_MAGIC"

	EnumGen.start
	_STATE_INIT		= EnumGen.item # CPU not runnable, yet.
	STATE_STOP		= EnumGen.item # CPU runnable, but stopped.
	STATE_RUN		= EnumGen.item # CPU running.
	STATE_MAINTENANCE	= EnumGen.item # CPU maintenance (stopped).
	STATE_EXIT		= EnumGen.item # CPU exiting (stopped).
	EnumGen.end

	# Command mask bits
	CMDMSK_SHUTDOWN	= (1 << 0) # Allow shutdown command

	class Client(object):
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
			self.repetitionFactor = 0
			self.repetitionCount = 0

	@classmethod
	def getaddrinfo(cls, host, port):
		if osIsPosix and host == "localhost" and False: #XXX disabled, for now
			# We are on posix OS. Instead of AF_INET on localhost,
			# we use Unix domain sockets.
			family, socktype = AF_UNIX, socket.SOCK_STREAM
			sockaddr = "/tmp/awlsim-server-%d.socket" % port
		else:
			# First try IPv4
			family, socktype = socket.AF_INET, socket.SOCK_STREAM
			try:
				family, socktype, proto, canonname, sockaddr =\
					socket.getaddrinfo(host, port, family, socktype)[0]
			except socket.gaierror as e:
				if e.errno == socket.EAI_ADDRFAMILY:
					# Also try IPv6
					family, socktype = socket.AF_INET6, socket.SOCK_STREAM
					family, socktype, proto, canonname, sockaddr =\
						socket.getaddrinfo(host, port, family, socktype)[0]
				else:
					raise e
		return (family, socktype, sockaddr)

	@classmethod
	def portIsUnused(cls, host, port):
		sock = None
		result = True
		try:
			family, socktype, sockaddr = AwlSimServer.getaddrinfo(host, port)
			if family == AF_UNIX:
				try:
					os.stat(sockaddr)
				except OSError as e:
					if e.errno == errno.ENOENT:
						return True
				return False
			sock = socket.socket(family, socktype)
			sock.bind(sockaddr)
		except SocketErrors as e:
			result = False
		if sock:
			CALL_NOEX(sock.shutdown, socket.SHUT_RDWR)
			CALL_NOEX(sock.close)
		return result

	@classmethod
	def start(cls, listenHost, listenPort,
		  forkInterpreter=None,
		  forkServerProcess=None,
		  commandMask=CMDMSK_SHUTDOWN):
		"""Start a new server.
		If 'forkInterpreter' or 'forkServerProcess' are not None, spawn a subprocess.
		If 'forkInterpreter' and 'forkServerProcess' are None, run the server in this process."""

		# Prepare the environment for the server process.
		# Inherit from the starter and add awlsim specific variables.
		env = dict(os.environ)
		env[AwlSimServer.ENV_MAGIC]		= AwlSimServer.ENV_MAGIC
		env["AWLSIM_CORESERVER_HOST"]		= str(listenHost)
		env["AWLSIM_CORESERVER_PORT"]		= str(int(listenPort))
		env["AWLSIM_CORESERVER_LOGLEVEL"]	= str(Logging.loglevel)
		env["AWLSIM_CORESERVER_CMDMSK"]		= str(int(commandMask))

		if forkServerProcess:
			# Fork a new server process.
			proc = findExecutable(forkServerProcess)
			printInfo("Forking server process '%s'" % proc)
			if not proc:
				raise AwlSimError("Failed to run executable '%s'" %\
						  forkServerProcess)
			serverProcess = PopenWrapper([proc],
						     env = env)
			return serverProcess
		elif forkInterpreter:
			# Fork a new interpreter process and run server.py as module.
			interp = findExecutable(forkInterpreter)
			printInfo("Forking awlsim core server with interpreter '%s'" % interp)
			if not interp:
				raise AwlSimError("Failed to find interpreter "
						  "executable '%s'" % forkInterpreter)
			serverProcess = PopenWrapper([interp, "-m", "awlsim.coreserver.server"],
						     env = env)
			return serverProcess
		else:
			# Do not fork. Just run the server in this process.
			return cls._execute(env)

	@classmethod
	def _execute(cls, env=None):
		"""Execute the server process.
		Returns the exit() return value."""

		server, retval = None, 0
		try:
			server = AwlSimServer()
			for sig in (signal.SIGTERM, ):
				signal.signal(sig, server.signalHandler)
			server.runFromEnvironment(env)
		except AwlSimError as e:
			print(e.getReport())
			retval = 1
		except KeyboardInterrupt:
			print("AwlSimServer: Interrupted.")
		finally:
			if server:
				server.shutdown()
		return retval

	def __init__(self):
		self.__startupDone = False
		self.__state = -1
		self.setRunState(self._STATE_INIT)

		self.__nextStats = 0
		self.__commandMask = 0
		self.__handleExceptionServerside = False
		self.__handleMaintenanceServerside = False
		self.__socket = None
		self.__unixSockPath = None
		self.__clients = []

		self.__sim = AwlSim()
		self.setCycleExitHook(None)
		self.__resetSources()

	def runFromEnvironment(self, env=None):
		"""Run the server.
		Configuration is passed via environment variables in 'env'.
		If 'env' is not passed, os.environ is used."""

		if not env:
			env = dict(os.environ)

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
		if not host:
			raise AwlSimError("AwlSimServer: No listen host specified")
		try:
			port = int(env.get("AWLSIM_CORESERVER_PORT"))
		except (TypeError, ValueError) as e:
			raise AwlSimError("AwlSimServer: No listen port specified")

		try:
			commandMask = int(env.get("AWLSIM_CORESERVER_CMDMSK"))
		except (TypeError, ValueError) as e:
			raise AwlSimError("AwlSimServer: No command mask specified")

		self.startup(host = host,
			     port = port,
			     commandMask = commandMask)
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
		elif runstate == self.STATE_RUN:
			# We just entered RUN state.
			printVerbose("CPU startup (OB 10x).")
			self.__sim.startup()
			printVerbose("Putting CPU into RUN state.")
		elif runstate == self.STATE_STOP:
			# We just entered STOP state.
			printVerbose("Putting CPU into STOP state.")
		elif runstate == self.STATE_MAINTENANCE:
			# We just entered MAINTENANCE state.
			printVerbose("Putting CPU into MAINTENANCE state.")

		self.__state = runstate
		# Make a shortcut variable for RUN
		self.__running = bool(runstate == self.STATE_RUN)

	def __rebuildSelectReadList(self):
		rlist = [ self.__socket ]
		rlist.extend(client.transceiver.sock for client in self.__clients)
		self.__selectRlist = rlist

	def __cpuBlockExitCallback(self, userData):
		now = self.__sim.cpu.now
		if any(c.dumpInterval and now >= c.nextDump for c in self.__clients):
			msg = AwlSimMessage_CPUDUMP(str(self.__sim.cpu))
			broken = False
			for client in self.__clients:
				if client.dumpInterval and now >= client.nextDump:
					client.nextDump = now + client.dumpInterval / 1000.0
					try:
						client.transceiver.send(msg)
					except TransferError as e:
						client.broken = broken = True
			if broken:
				self.__removeBrokenClients()

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

	def __resetSources(self):
		# List of loaded AwlSource()s
		self.loadedAwlSources = []
		# List of loaded SymTabSource()s
		self.loadedSymTabSources = []
		# List of tuples of loaded hardware modules:
		#   (hwModName, parameterDict)
		self.loadedHwModules = []
		# List of loaded AwlLibEntrySelection()s
		self.loadedLibSelections = []

	def loadAwlSource(self, awlSource):
		parser = AwlParser()
		parser.parseSource(awlSource)
		self.setRunState(self.STATE_STOP)
		self.__sim.load(parser.getParseTree())
		self.loadedAwlSources.append(awlSource)

	def loadSymTabSource(self, symTabSource):
		symbolTable = SymTabParser.parseSource(symTabSource,
					autodetectFormat = True,
					mnemonics = self.__sim.cpu.getSpecs().getMnemonics())
		self.setRunState(self.STATE_STOP)
		self.__sim.loadSymbolTable(symbolTable)
		self.loadedSymTabSources.append(symTabSource)

	def loadHardwareModule(self, moduleName, paramDict):
		printInfo("Loading hardware module '%s'..." % moduleName)
		hwClass = self.__sim.loadHardwareModule(moduleName)
		self.__sim.registerHardwareClass(hwClass = hwClass,
					       parameters = paramDict)
		self.loadedHwModules.append( (moduleName, paramDict) )

	def loadLibraryBlock(self, libSelection):
		self.setRunState(self.STATE_STOP)
		self.__sim.loadLibraryBlock(libSelection)
		self.loadedLibSelections.append(libSelection)

	def cpuEnableObTempPresets(self, en):
		self.__sim.cpu.enableObTempPresets(en)

	def cpuEnableExtendedInsns(self, en):
		self.__sim.cpu.enableExtendedInsns(en)

	def cpuSetCycleTimeLimit(self, limitSeconds):
		self.__sim.cpu.setCycleTimeLimit(limitSeconds)

	def cpuSetRunTimeLimit(self, limitSeconds):
		self.__sim.cpu.setRunTimeLimit(limitSeconds)

	def cpuSetSpecs(self, cpuSpecs):
		self.__sim.cpu.getSpecs().assignFrom(cpuSpecs)

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
		self.setRunState(self.STATE_STOP)
		self.__sim.reset()
		self.__resetSources()
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

	def __rx_LOAD_CODE(self, client, msg):
		printDebug("Received message: LOAD_CODE")
		status = AwlSimMessage_REPLY.STAT_OK
		self.loadAwlSource(msg.source)
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_LOAD_SYMTAB(self, client, msg):
		printDebug("Received message: LOAD_SYMTAB")
		status = AwlSimMessage_REPLY.STAT_OK
		self.loadSymTabSource(msg.source)
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_LOAD_HW(self, client, msg):
		printDebug("Received message: LOAD_HW")
		status = AwlSimMessage_REPLY.STAT_OK
		self.loadHardwareModule(msg.name, msg.paramDict)
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_LOAD_LIB(self, client, msg):
		printDebug("Received message: LOAD_LIB")
		status = AwlSimMessage_REPLY.STAT_OK
		self.loadLibraryBlock(msg.libSelection)
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_SET_OPT(self, client, msg):
		printDebug("Received message: SET_OPT %s" % msg.name)
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

	def __rx_GET_CPUSPECS(self, client, msg):
		printDebug("Received message: GET_CPUSPECS")
		reply = AwlSimMessage_CPUSPECS(self.__sim.cpu.getSpecs())
		client.transceiver.send(reply)

	def __rx_CPUSPECS(self, client, msg):
		printDebug("Received message: CPUSPECS")
		status = AwlSimMessage_REPLY.STAT_OK
		self.cpuSetSpecs(msg.cpuspecs)
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_REQ_MEMORY(self, client, msg):
		printDebug("Received message: REQ_MEMORY")
		client.memReadRequestMsg = AwlSimMessage_MEMORY(0, msg.memAreas)
		client.repetitionFactor = msg.repetitionFactor
		client.repetitionCount = client.repetitionFactor
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
		awlSrcs = symSrcs = hwMods = libSels = ()
		if msg.getFlags & msg.GET_AWLSRCS:
			awlSrcs = self.loadedAwlSources
		if msg.getFlags & msg.GET_SYMTABSRCS:
			symSrcs = self.loadedSymTabSources
		if msg.getFlags & msg.GET_HWMODS:
			hwMods = self.loadedHwModules
		if msg.getFlags & msg.GET_LIBSELS:
			libSels = self.loadedLibSelections
		reply = AwlSimMessage_IDENTS(awlSrcs, symSrcs,
					     hwMods, libSels)
		client.transceiver.send(reply)

	__msgRxHandlers = {
		AwlSimMessage.MSG_ID_PING		: __rx_PING,
		AwlSimMessage.MSG_ID_PONG		: __rx_PONG,
		AwlSimMessage.MSG_ID_RESET		: __rx_RESET,
		AwlSimMessage.MSG_ID_SHUTDOWN		: __rx_SHUTDOWN,
		AwlSimMessage.MSG_ID_RUNSTATE		: __rx_RUNSTATE,
		AwlSimMessage.MSG_ID_GET_RUNSTATE	: __rx_GET_RUNSTATE,
		AwlSimMessage.MSG_ID_LOAD_CODE		: __rx_LOAD_CODE,
		AwlSimMessage.MSG_ID_LOAD_SYMTAB	: __rx_LOAD_SYMTAB,
		AwlSimMessage.MSG_ID_LOAD_HW		: __rx_LOAD_HW,
		AwlSimMessage.MSG_ID_LOAD_LIB		: __rx_LOAD_LIB,
		AwlSimMessage.MSG_ID_SET_OPT		: __rx_SET_OPT,
		AwlSimMessage.MSG_ID_GET_CPUSPECS	: __rx_GET_CPUSPECS,
		AwlSimMessage.MSG_ID_CPUSPECS		: __rx_CPUSPECS,
		AwlSimMessage.MSG_ID_REQ_MEMORY		: __rx_REQ_MEMORY,
		AwlSimMessage.MSG_ID_MEMORY		: __rx_MEMORY,
		AwlSimMessage.MSG_ID_INSNSTATE_CONFIG	: __rx_INSNSTATE_CONFIG,
		AwlSimMessage.MSG_ID_GET_IDENTS		: __rx_GET_IDENTS,
	}

	def __clientCommTransferError(self, exception, client):
		if exception.reason == exception.REASON_REMOTEDIED:
			printInfo("Client '%s' died" %\
				  client.transceiver.peerInfoString)
		else:
			printInfo("Client '%s' data "
				"transfer error:\n%s" %\
				(client.transceiver.peerInfoString,
				 str(exception)))
		self.__clientRemove(client)

	def __handleClientComm(self, client):
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

	def __handleCommunication(self):
		while 1:
			try:
				rlist, wlist, xlist = select.select(self.__selectRlist, [], [], 0)
			except Exception as e:
				raise AwlSimError("AwlSimServer: Communication error. "
					"'select' failed")
			if not rlist:
				break
			if self.__socket in rlist:
				rlist.remove(self.__socket)
				self.__accept()
			for sock in rlist:
				client = [ c for c in self.__clients if c.socket is sock ][0]
				self.__handleClientComm(client)

	def __handleMemReadReqs(self):
		broken = False
		for client in self.__clients:
			if not client.memReadRequestMsg:
				continue
			client.repetitionCount -= 1
			if client.repetitionCount <= 0:
				cpu, memAreas = self.__sim.cpu, client.memReadRequestMsg.memAreas
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
							raise
				try:
					client.transceiver.send(client.memReadRequestMsg)
				except TransferError as e:
					client.broken = broken = True
				client.repetitionCount = client.repetitionFactor
				if not client.repetitionFactor:
					self.memReadRequestMsg = None
		if broken:
			self.__removeBrokenClients()

	def startup(self, host, port, commandMask = 0,
		    handleExceptionServerside = False,
		    handleMaintenanceServerside = False):
		"""Start the server on 'host':'port'.
		commanMask -> Mask of allowed commands (CMDMSK_...).
		handleExceptionServerside -> Flag whether to raise AwlSimError()
		                             exceptions on the server only.
		handleMaintenanceServerside -> Flag whether to raise maintenance
		                               request exceptions on the server only.
		This must be called once before run()."""

		assert(not self.__startupDone)
		self.__commandMask = commandMask
		self.__handleExceptionServerside = handleExceptionServerside
		self.__handleMaintenanceServerside = handleMaintenanceServerside

		self.__listen(host, port)
		self.__rebuildSelectReadList()

		self.__nextStats = self.__sim.cpu.now
		self.__updateCpuCallbacks()

		self.__startupDone = True
		self.setRunState(self.STATE_STOP)

	def run(self):
		"""Run the main server event loop."""

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

				if self.__state in (self.STATE_STOP,
						    self.STATE_MAINTENANCE):
					while self.__state in (self.STATE_STOP,
							       self.STATE_MAINTENANCE):
						self.__handleCommunication()
						time.sleep(0.01)
					continue

				if self.__state == self.STATE_RUN:
					while self.__running:
						sim.runCycle()
						self.__handleMemReadReqs()
						self.__handleCommunication()
					continue

			except (AwlSimError, AwlParserError) as e:
				self.setRunState(self.STATE_STOP)
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
					try:
						if self.__clients:
							# Forward it to the first client
							msg = AwlSimMessage_MAINTREQ(e)
							self.__clients[0].transceiver.send(msg)
					except TransferError as e:
						pass
			except TransferError as e:
				# This should be caught earlier.
				printError("Uncaught transfer error: " + str(e))

	def __listen(self, host, port):
		"""Listen on 'host':'port'."""

		self.close()
		try:
			family, socktype, sockaddr = AwlSimServer.getaddrinfo(host, port)
			if family == AF_UNIX:
				self.__unixSockPath = sockaddr
				readableSockaddr = sockaddr
			else:
				readableSockaddr = "%s:%d" % (sockaddr[0], sockaddr[1])
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
				peerInfoString = "%s:%d" % addrInfo[:2]
		except SocketErrors as e:
			transferError = TransferError(None, parentException = e)
			if transferError.reason == transferError.REASON_BLOCKING:
				return None
			raise AwlSimError("AwlSimServer: accept() failed: %s" % str(e))
		printInfo("Client '%s' connected" % peerInfoString)

		client = self.Client(clientSock, peerInfoString)
		self.__clientAdd(client)

		return client

	def __clientAdd(self, client):
		self.__clients.append(client)
		self.__rebuildSelectReadList()

	def __clientRemove(self, client):
		self.__clients.remove(client)
		self.__rebuildSelectReadList()
		self.__updateCpuCallbacks()

	def __removeBrokenClients(self):
		for client in [ c for c in self.__clients if c.broken ]:
			self.__clientRemove(client)

	def close(self):
		"""Closes all client sockets and the main socket."""

		self.__startupDone = False

		for client in self.__clients:
			client.transceiver.shutdown()
			client.transceiver = None
			client.socket = None
		self.__clients = []

		if self.__socket:
			CALL_NOEX(self.__socket.shutdown, socket.SHUT_RDWR)
			CALL_NOEX(self.__socket.close)
			self.__socket = None
		if self.__unixSockPath:
			try:
				os.unlink(self.__unixSockPath)
			except OSError as e:
				pass
			self.__unixSockPath = None

	def shutdown(self):
		printInfo("Shutting down.")
		self.close()
		self.__sim.unregisterAllHardware()

	def signalHandler(self, sig, frame):
		printInfo("Received signal %d" % sig)
		if sig in (signal.SIGTERM, signal.SIGINT):
			self.setRunState(self.STATE_EXIT)

if __name__ == "__main__":
	# Run a server process.
	# Parameters are passed via environment.
	sys.exit(AwlSimServer._execute())

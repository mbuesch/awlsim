# -*- coding: utf-8 -*-
#
# AWL simulator - PLC core server
#
# Copyright 2013-2019 Michael Buesch <m@bues.ch>
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
#from awlsim.common.cython_support cimport * #@cy
from awlsim.common.compat import *

from awlsim.common.subprocess_wrapper import *
from awlsim.common.cpuspecs import * #+cimport
from awlsim.common.cpuconfig import *
from awlsim.common.sources import *
from awlsim.common.net import *
from awlsim.common.env import *
from awlsim.common.util import *
from awlsim.common.exceptions import *
from awlsim.common.monotonic import * #+cimport
from awlsim.common.datatypehelpers import * #+cimport
from awlsim.common.mlock import *

from awlsim.core.main import * #+cimport
from awlsim.core.symbolparser import *

from awlsim.awlcompiler import *

from awlsim.coreserver.messages import *
from awlsim.coreserver.memarea import *

from awlsim.fupcompiler import *

import sys
import os
import select as select_mod
import signal
import socket
import errno
import time
import multiprocessing
import gc

#from posix.select cimport FD_ZERO, FD_SET, FD_ISSET, select #@cy-posix
#from posix.time cimport timeval #@cy-posix


__all__ = [
	"AwlSimServer",
]


class InsnStateDump(object):
	"""Instruction dump state."""

	def __init__(self):
		# AWL line numbers that a dump is requested for.
		self.enabledLines = set()
		# Reply message queue.
		self.msgs = []
		# OB1 divider
		self.ob1Div = 1
		self.ob1Count = 0
		# Opaque user data
		self.userData = 0

class AwlSimClientInfo(object):
	"""Client information."""

	def __init__(self, sock, peerInfoString):
		# Socket
		self.socket = sock
		self.fileno = sock.fileno()
		self.transceiver = AwlSimMessageTransceiver(sock, peerInfoString)

		# Broken-flag. Set, if connection breaks.
		self.broken = False

		# CPU-dump
		self.dumpInterval = 0
		self.nextDump = 0

		# Instruction state dump state.
		# dict key: AWL source ID.
		# dict value: InsnStateDump()
		self.insnStateDump = {}
		self.insnStateDumpEnabled = False

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
	CMDMSK_DEFAULT = CMDMSK_SHUTDOWN

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
					if excErrno(e) == socket.EAI_ADDRFAMILY:
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
	def start(cls, listenHost, listenPort,
		  listenFamily=None,
		  forkInterpreter=None,
		  forkServerProcess=None,
		  commandMask=CMDMSK_DEFAULT,
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
							     env=env,
							     hideWindow=True)
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
					env=env,
					hideWindow=True)
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
		self.__initTimeStamp = monotonic_time()
		self.__startupTimeStamp = self.__initTimeStamp
		self.__rtSchedEnabled = False
		self.__os_sched_yield = getattr(os, "sched_yield", None)
		self.__gcManual = False
		self.__gcTriggerCounter = 0
		self.__gcTriggerThreshold = AwlSimEnv.getGcCycle()
		self.__gcGen0Threshold = AwlSimEnv.getGcThreshold(0)
		self.__gcGen1Threshold = AwlSimEnv.getGcThreshold(1)
		self.__gcGen2Threshold = AwlSimEnv.getGcThreshold(2)
		self.__gc_collect = getattr(gc, "collect", None)
		self.__gc_get_count = getattr(gc, "get_count", None)
		self.__emptyList = []
		self.__startupDone = False
		self.__state = -1
		self.__needOB10x = True
		self.__projectFile = None
		self.__projectWriteBack = False

		self.__setupAffinitySets()
		self.__setAffinity(core=True)

		self.setRunState(self._STATE_INIT)

		self.__nextStats = 0
		self.__commandMask = 0
		self.__raiseExceptionsFromRun = False
		self.__handleMaintenanceServerside = False
		self.__haveAnyMemReadReq = False

		self.__socket = None
#		self.__socketFileno = -1 #@cy-posix
		self.__unixSockPath = None
		self.__clients = []
		self.__sock2client = {}

		self.__sim = AwlSim()
		self.setCycleExitHook(None)

		# Container of loaded and managed AwlSource()s
		self.awlSourceContainer = SourceContainer()
		# Container of loaded and managed FupSource()s
		self.fupSourceContainer = SourceContainer()
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

	def __setupAffinitySets(self):
		"""Get the affinity settings and create the actual sets.
		"""
		affinityList = AwlSimEnv.getAffinity()
		if affinityList:
			# Let the Awlsim core run on the highest numbered CPU.
			# Let the peripherals run on all other cores in the set,
			# if there are more than one.
			rawList = sorted(affinityList, reverse=True)
			self.__affinitySetCore = frozenset(rawList[0:1])
			self.__affinitySetPeripheral = self.__affinitySetCore
			if len(rawList) > 1:
				self.__affinitySetPeripheral = frozenset(rawList[1:])
			printVerbose("Core host-CPU affinity mask: CPU %s" % (
				     listToHumanStr(self.__affinitySetCore, lastSep="and")))
			printVerbose("Peripheral host-CPU affinity mask: CPU %s" % (
				     listToHumanStr(self.__affinitySetPeripheral, lastSep="and")))
		else:
			# Disable CPU pinning.
			self.__affinitySetCore = None
			self.__affinitySetPeripheral = None

	def __setAffinity(self, core=True):
		"""Set the host CPU affinity for core or perihperal use.
		"""
		if not self.__affinitySetCore:
			return
		if hasattr(os, "sched_setaffinity"):
			try:
				if core:
					affinity = self.__affinitySetCore
				else:
					affinity = self.__affinitySetPeripheral
				printVerbose("Setting host-CPU scheduling "
					     "affinity for %s to host CPU %s." % (
					     "CORE" if core else "PERIPHERAL",
					     listToHumanStr(affinity, lastSep="and")))
				os.sched_setaffinity(0, affinity)
			except (OSError, ValueError) as e: #@nocov
				raise AwlSimError("Failed to set host CPU "
						  "affinity: %s" % str(e))
		else: #@nocov
			printError("Cannot set CPU affinity. "
				   "os.sched_setaffinity is not available.")

	def __setSched(self, allowRtPolicy=False, peripheral=False):
		"""Set the scheduling policy and priority to what is set by
		AWLSIM_SCHED and AWLSIM_PRIO environment variable.
		If allowRtPolicy is False, then don't allow any realtime policy
		and fall back to non-realtime.
		If peripheral is True, then don't allow policies unsuitable for
		peripheral threads. Fall back to sane alternatives.
		"""
		self.__rtSchedEnabled = False

		sched = AwlSimEnv.getSched()
		if (sched is not None and
		    sched != AwlSimEnv.SCHED_DEFAULT):
			if not allowRtPolicy:
				# Realtime is not allowed.
				# Fall back to NORMAL.
				sched = AwlSimEnv.SCHED_NORMAL
			policy = None
			if sched == AwlSimEnv.SCHED_NORMAL:
				policy = getattr(os, "SCHED_OTHER", None)
				isRealtime = False
			elif sched == AwlSimEnv.SCHED_FIFO:
				if peripheral:
					# No FIFO for peripheral threads.
					# Use RR instead.
					policy = getattr(os, "SCHED_RR", None)
				else:
					policy = getattr(os, "SCHED_FIFO", None)
				isRealtime = True
			elif sched == AwlSimEnv.SCHED_RR:
				policy = getattr(os, "SCHED_RR", None)
				isRealtime = True
			elif sched == AwlSimEnv.SCHED_DEADLINE:
				if peripheral:
					# No DEADLINE for peripheral threads.
					# Use RR instead.
					policy = getattr(os, "SCHED_RR", None)
				else:
					policy = getattr(os, "SCHED_DEADLINE", None)
				isRealtime = True
				policy = None #TODO we also need to set the deadline scheduling parameters.
			if policy is None: #@nocov
				raise AwlSimError("Host CPU scheduling policy "
					"'%s' is not supported by the system. "
					"Please change the AWLSIM_SCHED "
					"environment variable." % sched)
			if hasattr(os, "sched_setscheduler"):
				try:
					minPrio = getattr(os, "sched_get_priority_min",
							  lambda p: 1)(policy)
					param = os.sched_param(minPrio)
					os.sched_setscheduler(0, policy, param)
					self.__rtSchedEnabled = isRealtime
					printVerbose("Set host CPU scheduling "
						     "policy to '%s'." % sched)
				except (OSError, ValueError) as e: #@nocov
					raise AwlSimError("Failed to set host CPU "
						"scheduling policy to %s: %s" % (
						sched, str(e)))
			else: #@nocov
				printError("Cannot set CPU scheduling policy. "
					   "os.sched_setscheduler is not available.")

		prio = AwlSimEnv.getPrio()
		if prio is not None and allowRtPolicy:
			if (hasattr(os, "sched_getscheduler") and
			    hasattr(os, "sched_setparam")):
				try:
					policy = os.sched_getscheduler(0)
					minPrio = getattr(os, "sched_get_priority_min",
							  lambda p: 1)(policy)
					maxPrio = getattr(os, "sched_get_priority_max",
							  lambda p: 99)(policy)
					prio = clamp(prio, minPrio, maxPrio)
					param = os.sched_param(prio)
					os.sched_setparam(0, param)
					printVerbose("Set host CPU scheduling "
						     "priority to %d." % prio)
				except (OSError, ValueError) as e: #@nocov
					raise AwlSimError("Failed to set host CPU "
						"scheduling priority to %d: %s" % (
						prio, str(e)))
			else: #@nocov
				printError("Cannot set CPU scheduling priority. "
					   "os.sched_setparam/os.sched_getscheduler "
					   "is not available.")

		self.__setMLock(allowRtPolicy)

	def __setMLock(self, allowMLock):
		"""Lock all memory, if required.
		"""
		AwlSimMLock.lockMemory(allowMLock)

	def __yieldHostCPU(self): #@nocy
#@cy	cdef void __yieldHostCPU(self):
#@cy		cdef uint16_t trig
#@cy		cdef int32_t gen0
#@cy		cdef int32_t thres0
#@cy		cdef int32_t gen1
#@cy		cdef int32_t thres1
#@cy		cdef int32_t gen2
#@cy		cdef int32_t thres2

		# If automatic garbage collection is disabled,
		# run a manual collection now.
		if self.__gcManual:
			trig = (self.__gcTriggerCounter + 1) & 0xFFFF #+suffix-u
			if trig >= self.__gcTriggerThreshold:
				trig = 0
				assert(not gc.isenabled()) #@nocy
				gen0, gen1, gen2 = self.__gc_get_count()
				thres0 = self.__gcGen0Threshold
				thres1 = self.__gcGen1Threshold
				thres2 = self.__gcGen2Threshold
				if gen2 >= thres2 and thres2 > 0:
					self.__gc_collect(2)
				elif gen1 >= thres1 and thres1 > 0:
					self.__gc_collect(1)
				elif gen0 >= thres0 and thres0 > 0:
					self.__gc_collect(0)
			self.__gcTriggerCounter = trig

		if self.__rtSchedEnabled:
#			pass				#@cy-win
			# We are running under realtime scheduling conditions.
			# We should yield now.

			# On Posix + Cython call the system sched_yield directly.
#			with nogil:			#@cy-posix
#				sched_yield()		#@cy-posix

			# Otherwise try to call sched_yield from the os module,
			# if it is available.
			if self.__os_sched_yield:	#@nocy
				self.__os_sched_yield()	#@nocy

	def getRunState(self):
		return self.__state

	def setRunState(self, runstate):
		if self.__state == runstate:
			# Already in that state.
			return
		if self.__state == self.STATE_EXIT:
			# We are exiting. Cannot set another state.
			return

		try:
			if runstate == self.STATE_RUN or\
			   runstate == self.STATE_STOP:
				# Reset instruction state dump.
				self.__insnSerial = 0
				for client in self.__clients:
					for insnStateDump in dictValues(client.insnStateDump):
						insnStateDump.msgs = []

			if runstate == self._STATE_INIT:
				# We just entered initialization state.
				printVerbose("Putting CPU into INIT state.")
				self.__setSched(allowRtPolicy=False)
				self.__needOB10x = True
			elif runstate == self.STATE_RUN:
				# We just entered RUN state.

				try:
					if self.__projectToBeLoaded:
						self.__doLoadProject()
				except AwlSimError as e:
					# Try our best to get something running.
					printError("Entering RUN mode although "
						   "project loading failed.")

				self.__startupTimeStamp = monotonic_time()
				if self.__needOB10x:
					printVerbose("CPU startup (OB 10x).")

					# In case the hardware module spawns some threads make sure these
					# inherit the affinity set and sched policy for peripherals.
					self.__setAffinity(core=False)
					self.__setSched(allowRtPolicy=True,
							peripheral=True)
					try:
						# Start the hardware modules.
						self.__sim.hardwareStartup()
					finally:
						# Go back to core affinity mask and sched policy.
						self.__setAffinity(core=True)
						self.__setSched(allowRtPolicy=True,
								peripheral=False)

					# Run the CPU statup and the CPU statup OBs.
					self.__sim.startup()
					self.__needOB10x = False
				else:
					# Set core sched policy.
					self.__setSched(allowRtPolicy=True,
							peripheral=False)
				printVerbose("Putting CPU into RUN state.")
			elif runstate == self.STATE_STOP:
				# We just entered STOP state.
				printVerbose("Putting CPU into STOP state.")
				self.__setSched(allowRtPolicy=False)
			elif runstate == self.STATE_MAINTENANCE:
				# We just entered MAINTENANCE state.
				self.__setSched(allowRtPolicy=False)
				self.__needOB10x = True
			else:
				self.__setSched(allowRtPolicy=False)


			# Select garbage collection mode.
			if self.__gc_collect and self.__gc_get_count:
				# If we are in RUN state with realtime scheduling,
				# use manual garbage collection.
				gcMode = AwlSimEnv.getGcMode()
				wantManual = (gcMode == AwlSimEnv.GCMODE_MANUAL or
					      (gcMode == AwlSimEnv.GCMODE_RT and
					       self.__rtSchedEnabled))
				if runstate == self.STATE_RUN and wantManual:
					# Manual GC
					gc.disable()
					self.__gcManual = True
					self.__gcTriggerCounter = 0
					printVerbose("Switched to MANUAL garbage collection.")
				else:
					# Automatic GC
					gc.enable()
					self.__gcManual = False
					printVerbose("Switched to AUTO garbage collection.")
			else:
				# Manual GC control is not available.
				self.__gcManual = False
				printVerbose("Switched to AUTO garbage collection.")


			self.__state = runstate
			# Make a shortcut variable for RUN
			self.__running = bool(runstate == self.STATE_RUN)

		except Exception as e:
			# An exception occurred. Go back to normal scheduling.
			with suppressAllExc:
				self.__setSched(allowRtPolicy=False)
			raise e

	def __getMnemonics(self):
		return self.__sim.cpu.getConf().getMnemonics()

	def __rebuildSelectReadList(self):
		rlist = [ self.__socket ]
		rlist.extend(client.transceiver.sock for client in self.__clients)
		self.__selectRlist = rlist

#		FD_ZERO(&self.__select_fdset)						#@cy-posix
#		FD_SET(self.__socketFileno, &self.__select_fdset)			#@cy-posix
#		self.__select_fdset_size = self.__socketFileno				#@cy-posix
#		for client in self.__clients:						#@cy-posix
#			FD_SET(client.fileno, &self.__select_fdset)			#@cy-posix
#			self.__select_fdset_size = max(self.__select_fdset_size,	#@cy-posix
#						       client.fileno)			#@cy-posix
#		self.__select_fdset_size += 1						#@cy-posix

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
		ip = callStackElement.ip
		if ip >= callStackElement.nrInsns:
			return
		insn = callStackElement.insns[ip]
		cpu = self.__sim.cpu
		sourceId = insn.getSourceId()
		lineNr = insn.getLineNr()
		for client in self.__clients:
			if not client.insnStateDumpEnabled:
				continue
			if not sourceId in client.insnStateDump:
				continue
			insnStateDump = client.insnStateDump[sourceId]
			if lineNr not in insnStateDump.enabledLines:
				continue
			if insnStateDump.ob1Count < insnStateDump.ob1Div - 1:
				continue
			msg = AwlSimMessage_INSNSTATE(
				sourceId,
				lineNr & 0xFFFFFFFF,
				self.__insnSerial,
				0, # flags
				cpu.statusWord.getWord(),
				cpu.accu1.get(),
				cpu.accu2.get(),
				cpu.accu3.get(),
				cpu.accu4.get(),
				cpu.ar1.get(),
				cpu.ar2.get(),
				cpu.dbRegister.index & 0xFFFF,
				cpu.diRegister.index & 0xFFFF,
				insnStateDump.userData)
			insnStateDump.msgs.append(msg)
		self.__insnSerial += 1

	def __printCpuStats(self):
		cpu = self.__sim.cpu
		printVerbose("[CPU] "
			     "%s stmt/s (= %s us/stmt); %.01f stmt/cycle" % (
			     cpu.insnPerSecondHR,
			     cpu.usPerInsnHR,
			     cpu.avgInsnPerCycle))

	def __cpuCycleExitCallback(self, userData):
		# Send instruction dump messages.
		broken = False
		for client in self.__clients:
			if client.insnStateDumpEnabled:
				# Collect all messages for all sources.
				msgs = []
				for insnStateDump in dictValues(client.insnStateDump):
					msgs.extend(insnStateDump.msgs)
					insnStateDump.msgs = []

					# Update OB1 cycle counter/divider.
					insnStateDump.ob1Count += 1
					if insnStateDump.ob1Count >= insnStateDump.ob1Div:
						insnStateDump.ob1Count = 0
				# Send all messages to the client.
				if msgs:
					try:
						client.transceiver.send(msgs)
					except TransferError as e:
						client.broken = broken = True
		if broken:
			self.__removeBrokenClients()
		# The next cycle shall start with serial 0.
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
		if any(c.insnStateDumpEnabled for c in self.__clients):
			self.__sim.cpu.setPostInsnCallback(self.__cpuPostInsnCallback, None)
		else:
			self.__sim.cpu.setPostInsnCallback(None)

	def __updateCpuCycleExitCallback(self):
		if (any(c.insnStateDumpEnabled for c in self.__clients) or
		    Logging.loglevel >= Logging.LOG_VERBOSE or
		    self.__cycleExitHook):
			self.__sim.cpu.setCycleExitCallback(self.__cpuCycleExitCallback, None)
		else:
			self.__sim.cpu.setCycleExitCallback(None)

	def __updateCpuCallbacks(self):
		self.__updateCpuBlockExitCallback()
		self.__updateCpuPostInsnCallback()
		self.__updateCpuCycleExitCallback()

	def __generateProject(self):
		cpu = self.__sim.getCPU()
		awlSources = [ source
			       for source in self.awlSourceContainer.getSources()
			       if not source.volatile ]
		fupSources = [ source
			       for source in self.fupSourceContainer.getSources()
			       if not source.volatile ]
		kopSources = [] #TODO
		symTabSources = [ source
				  for source in self.symTabSourceContainer.getSources()
				  if not source.volatile ]
		libSelections = self.loadedLibSelections[:]
		cpuSpecs = cpu.getSpecs() # (Note: not a deep-copy)
		cpuConf = cpu.getConf() # (Note: not a deep-copy)
		hwmodSettings = HwmodSettings(
			loadedModules = self.loadedHwModules[:]
		)
		project = Project(
			projectFile=None,
			awlSources=awlSources,
			fupSources=fupSources,
			kopSources=kopSources,
			symTabSources=symTabSources,
			libSelections=libSelections,
			cpuSpecs=cpuSpecs,
			cpuConf=cpuConf,
			guiSettings=None,
			coreLinkSettings=None,
			hwmodSettings=hwmodSettings,
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
		self.fupSourceContainer.clear()
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

	def __removeSource(self, sourceContainer, sourceManager):
		# Remove all blocks that were created from this source.
		for block in itertools.chain(sourceManager.getCodeBlocks(),
					     sourceManager.getDataBlocks()):
			blockInfo = block.getBlockInfo()
			if not blockInfo:
				continue
			self.__sim.removeBlock(blockInfo, sanityChecks=False)

		# Unref all related source managers.
		for relatedSourceManager in sourceManager.getRelatedSourceManagers():
			ref = relatedSourceManager.getRefForObj(sourceManager)
			if ref:
				ref.destroy()
			ref = sourceManager.getRefForObj(relatedSourceManager)
			if ref:
				ref.destroy()

		#TODO remove symbols from CPU.

		# Destroy all references, that have not been destroyed, yet.
		for ref in sourceManager.refs:
			printError("Killing dangling reference: %s" % str(ref))
			ref.destroy()

		# Remove the source, if it's not gone already.
		if sourceContainer:
			sourceContainer.removeManager(sourceManager)

	def removeSource(self, identHash):
		ok = False
		try:
			for sourceContainer in (self.awlSourceContainer,
						self.fupSourceContainer,
						self.symTabSourceContainer):
				sourceManager = sourceContainer.getSourceManagerByIdent(identHash)
				if sourceManager:
					self.__removeSource(sourceContainer, sourceManager)
					# Run static sanity checks now to ensure
					# the CPU is still runnable.
					self.__sim.staticSanityChecks()
					ok = True
					break
		finally:
			if ok:
				self.__updateProjectFile()
		return ok

	def loadAwlSource(self, awlSource):
		srcManager = SourceManager(awlSource)

		if awlSource.enabled:
			needRebuild = False
			if self.__state == self.STATE_RUN or\
			   (self.__state == self.STATE_STOP and\
			    not self.__needOB10x):
				needRebuild = True

			parser = AwlParser()
			parser.parseSource(awlSource)
			self.__sim.load(parser.getParseTree(), needRebuild, srcManager)

		self.awlSourceContainer.addManager(srcManager)
		self.__updateProjectFile()
		return srcManager

	def loadFupSource(self, fupSource):
		srcManager = SourceManager(fupSource)

		if fupSource.enabled:
			compiler = FupCompiler()
			#FIXME mnemonics auto detection might cause mismatching mnemonics w.r.t. the main blocks.
			symSrcs = self.symTabSourceContainer.getSources()
			awlSource = compiler.compile(fupSource=fupSource,
						     symTabSources=symSrcs,
						     mnemonics=self.__getMnemonics())
			awlSrcManager = self.loadAwlSource(awlSource)

			# Cross-reference the generated AWL source to the FUP source.
			ObjRef.make(manager=srcManager, obj=awlSrcManager)
			ObjRef.make(manager=awlSrcManager, obj=srcManager)

		self.fupSourceContainer.addManager(srcManager)
		self.__updateProjectFile()
		return srcManager

	def loadKopSource(self, kopSource):
		if kopSource.enabled:
			pass#TODO
		return None

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
		return srcManager

	def loadHardwareModule(self, hwmodDesc):
		# In case the hardware module spawns some threads make sure these
		# inherit the affinity set for peripherals.
		self.__setAffinity(core=False)
		try:
			hwmodName = hwmodDesc.getModuleName()
			printInfo("Loading hardware module '%s'..." % hwmodName)

			hwClass = self.__sim.loadHardwareModule(hwmodDesc.getModuleName())
			self.__sim.registerHardwareClass(hwClass=hwClass,
							 parameters=hwmodDesc.getParameters())

			self.loadedHwModules.append(hwmodDesc)
			self.__updateProjectFile()
			printInfo("Hardware module '%s' loaded." % hwmodName)
		finally:
			# Go back to core affinity mask.
			self.__setAffinity(core=True)

	def loadLibraryBlock(self, libSelection):
		self.setRunState(self.STATE_STOP)
		self.__sim.loadLibraryBlock(libSelection)

		self.loadedLibSelections.append(libSelection)
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
		reply = AwlSimMessage_PONG()
		reply.setReplyTo(msg)
		client.transceiver.send(reply)

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
			if msg.shutdownType == msg.SHUTDOWN_CORE:
				printInfo("Exiting due to shutdown command")
				self.setRunState(self.STATE_EXIT)
				status = AwlSimMessage_REPLY.STAT_OK
			elif msg.shutdownType == msg.SHUTDOWN_SYSTEM_HALT:
				if osIsLinux:
					printInfo("Halting system due to shutdown command")
					self.setRunState(self.STATE_EXIT)
					process = PopenWrapper(["/sbin/poweroff"],
							       AwlSimEnv.getEnv())
					process.wait()
					status = AwlSimMessage_REPLY.STAT_OK
				else:
					printError("Halting system is not supported.")
			elif msg.shutdownType == msg.SHUTDOWN_SYSTEM_REBOOT:
				if osIsLinux:
					printInfo("Rebooting system due to shutdown command")
					self.setRunState(self.STATE_EXIT)
					process = PopenWrapper(["/sbin/reboot"],
							       AwlSimEnv.getEnv())
					process.wait()
					status = AwlSimMessage_REPLY.STAT_OK
				else:
					printError("Rebooting system is not supported.")
			else:
				printError("Unknown shutdown command")
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
		reply.setReplyTo(msg)
		client.transceiver.send(reply)

	def __rx_GET_AWLSRC(self, client, msg):
		printDebug("Received message: GET_AWLSRC")
		awlSource = self.awlSourceContainer.getSourceByIdent(msg.identHash)
		reply = AwlSimMessage_AWLSRC(awlSource)
		reply.setReplyTo(msg)
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
		reply.setReplyTo(msg)
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

	def __rx_GET_FUPSRC(self, client, msg):
		printDebug("Received message: GET_FUPSRC")
		fupSource = self.fupSourceContainer.getSourceByIdent(msg.identHash)
		reply = AwlSimMessage_FUPSRC(fupSource)
		reply.setReplyTo(msg)
		client.transceiver.send(reply)

	def __rx_FUPSRC(self, client, msg):
		printDebug("Received message: FUPSRC")
		status = AwlSimMessage_REPLY.STAT_OK
		self.loadFupSource(msg.source)
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_GET_KOPSRC(self, client, msg):
		printDebug("Received message: GET_KOPSRC")
		kopSource = self.kopSourceContainer.getSourceByIdent(msg.identHash)
		reply = AwlSimMessage_KOPSRC(kopSource)
		reply.setReplyTo(msg)
		client.transceiver.send(reply)

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
		elif msg.name == "periodic_dump_int":
			client.dumpInterval = msg.getIntValue()
			if client.dumpInterval:
				client.nextDump = self.__sim.cpu.now
			else:
				client.nextDump = None
			self.__updateCpuCallbacks()
		else:
			status = AwlSimMessage_REPLY.STAT_FAIL

		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_GET_BLOCKINFO(self, client, msg):
		printDebug("Received message: GET_BLOCKINFO")

		blockInfos = self.__sim.cpu.getBlockInfos(
			getOBInfo=bool(msg.getFlags & msg.GET_OB_INFO),
			getFCInfo=bool(msg.getFlags & msg.GET_FC_INFO),
			getFBInfo=bool(msg.getFlags & msg.GET_FB_INFO),
			getDBInfo=bool(msg.getFlags & msg.GET_DB_INFO),
			getUDTInfo=bool(msg.getFlags & msg.GET_UDT_INFO))
		reply = AwlSimMessage_BLOCKINFO(blockInfos)
		reply.setReplyTo(msg)
		client.transceiver.send(reply)

	def __rx_GET_CPUSPECS(self, client, msg):
		printDebug("Received message: GET_CPUSPECS")
		reply = AwlSimMessage_CPUSPECS(self.__sim.cpu.getSpecs())
		reply.setReplyTo(msg)
		client.transceiver.send(reply)

	def __rx_CPUSPECS(self, client, msg):
		printDebug("Received message: CPUSPECS")
		status = AwlSimMessage_REPLY.STAT_OK
		self.cpuSetSpecs(msg.cpuspecs)
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_GET_CPUCONF(self, client, msg):
		printDebug("Received message: GET_CPUCONF")
		reply = AwlSimMessage_CPUCONF(self.__sim.cpu.getConf())
		reply.setReplyTo(msg)
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
				msg, AwlSimMessage_REPLY.STAT_OK))

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

		if msg.flags & msg.FLG_CLEAR:
			# Clear dump requests on this client.
			if msg.sourceId:
				# Only for the selected source.
				if msg.sourceId in client.insnStateDump:
					del client.insnStateDump[msg.sourceId]
			else:
				# Clear all.
				client.insnStateDump = {}

		if msg.flags & msg.FLG_SET:
			if msg.sourceId:
				# Get the dump request structure or create a new one.
				if msg.sourceId in client.insnStateDump:
					insnStateDump = client.insnStateDump[msg.sourceId]
				else:
					insnStateDump = InsnStateDump()
					client.insnStateDump[msg.sourceId] = insnStateDump

				# Add the new lines to the enabled-lines set.
				fromLine = msg.fromLine
				toLine = msg.toLine
				if fromLine >= 0 and toLine >= 0 and toLine >= fromLine:
					maxLines = max(100000 - len(insnStateDump.enabledLines), 0)
					if toLine - fromLine > maxLines:
						toLine = fromLine + maxLines
					rangeSet = set(range(fromLine, toLine + 1))
				else:
					rangeSet = set()
				insnStateDump.enabledLines |= rangeSet

				# Clear message queue.
				if not insnStateDump.enabledLines:
					insnStateDump.msgs = []

				# Store OB1 divider.
				insnStateDump.ob1Div = clamp(msg.ob1Div, 1, 1024 * 16)
				# Store opaque user data.
				insnStateDump.userData = msg.userData
			else:
				status = AwlSimMessage_REPLY.STAT_FAIL

		# Set the client-wide enable-flag, if any dump is enabled.
		if any(bool(insnStateDump.enabledLines)
		       for insnStateDump in dictValues(client.insnStateDump)):
			client.insnStateDumpEnabled = True
			printVerbose("Instruction state dumping enabled")
		else:
			client.insnStateDumpEnabled = False
			printVerbose("Instruction state dumping disabled")

		# Setup or remove the CPU callbacks.
		self.__updateCpuCallbacks()

		# Send reply to the client.
		if msg.flags & msg.FLG_SYNC:
			client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_MEAS_CONFIG(self, client, msg):
		printDebug("Received message: MEAS_CONFIG")
		replyFlags = 0
		replyStr = ""
		insnMeas = None
		if msg.flags & msg.FLG_ENABLE:
			printDebug("Enabling instruction time measurements")
			insnMeas = self.__sim.cpu.setupInsnMeas(True)
			if not insnMeas:
				replyFlags |= AwlSimMessage_MEAS.FLG_FAIL
		else:
			printDebug("Disabling instruction time measurements")
			insnMeas = self.__sim.cpu.setupInsnMeas(False)
		if msg.flags & msg.FLG_GETMEAS:
			if insnMeas:
				if msg.flags & msg.FLG_CSV:
					replyStr = insnMeas.dumpCSV()
				else:
					replyStr = insnMeas.dump()
				if replyStr:
					replyFlags |= AwlSimMessage_MEAS.FLG_HAVEDATA
		reply = AwlSimMessage_MEAS(flags=replyFlags,
					   reportStr=replyStr)
		reply.setReplyTo(msg)
		client.transceiver.send(reply)

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
			fupSrcs = self.fupSourceContainer.getSources()
		if msg.getFlags & msg.GET_KOPSRCS:
			pass#TODO
		reply = AwlSimMessage_IDENTS(awlSrcs, symSrcs,
					     hwMods, libSels,
					     fupSrcs, kopSrcs)
		reply.setReplyTo(msg)
		client.transceiver.send(reply)

	def __rx_GET_CPUSTATS(self, client, msg):
		printDebug("Received message: GET_CPUSTATS")
		cpu = self.__sim.cpu
		now = monotonic_time()
		uptime = now - self.__initTimeStamp
		runtime = (now - self.__startupTimeStamp) if self.__running else 0.0
		reply = AwlSimMessage_CPUSTATS(
			running=self.__running,
			uptime=uptime,
			runtime=runtime,
			insnPerSecond=cpu.insnPerSecond,
			insnPerCycle=cpu.avgInsnPerCycle,
			avgCycleTime=cpu.avgCycleTime,
			minCycleTime=cpu.minCycleTime,
			maxCycleTime=cpu.maxCycleTime,
			padCycleTime=cpu.padCycleTime,
		)
		reply.setReplyTo(msg)
		client.transceiver.send(reply)

	# Message receive control flags.
	RXFLG_NONE	= 0		# No flags
	RXFLG_EXFATAL	= 1 << 0	# AwlSimError exceptions are fatal

	__msgRxHandlers = {
		AwlSimMessage.MSG_ID_PING		: (__rx_PING,		RXFLG_NONE),
		AwlSimMessage.MSG_ID_PONG		: (__rx_PONG,		RXFLG_NONE),
		AwlSimMessage.MSG_ID_RESET		: (__rx_RESET,		RXFLG_EXFATAL),
		AwlSimMessage.MSG_ID_SHUTDOWN		: (__rx_SHUTDOWN,	RXFLG_EXFATAL),
		AwlSimMessage.MSG_ID_RUNSTATE		: (__rx_RUNSTATE,	RXFLG_EXFATAL),
		AwlSimMessage.MSG_ID_GET_RUNSTATE	: (__rx_GET_RUNSTATE,	RXFLG_NONE),
		AwlSimMessage.MSG_ID_GET_AWLSRC		: (__rx_GET_AWLSRC,	RXFLG_NONE),
		AwlSimMessage.MSG_ID_AWLSRC		: (__rx_AWLSRC,		RXFLG_EXFATAL),
		AwlSimMessage.MSG_ID_GET_SYMTABSRC	: (__rx_GET_SYMTABSRC,	RXFLG_NONE),
		AwlSimMessage.MSG_ID_SYMTABSRC		: (__rx_SYMTABSRC,	RXFLG_EXFATAL),
		AwlSimMessage.MSG_ID_HWMOD		: (__rx_HWMOD,		RXFLG_EXFATAL),
		AwlSimMessage.MSG_ID_LIBSEL		: (__rx_LIBSEL,		RXFLG_EXFATAL),
		AwlSimMessage.MSG_ID_GET_FUPSRC		: (__rx_GET_FUPSRC,	RXFLG_NONE),
		AwlSimMessage.MSG_ID_FUPSRC		: (__rx_FUPSRC,		RXFLG_EXFATAL),
#		AwlSimMessage.MSG_ID_GET_KOPSRC		: (__rx_GET_KOPSRC,	RXFLG_NONE),
#		AwlSimMessage.MSG_ID_KOPSRC		: (__rx_KOPSRC,		RXFLG_EXFATAL),
		AwlSimMessage.MSG_ID_BUILD		: (__rx_BUILD,		RXFLG_EXFATAL),
		AwlSimMessage.MSG_ID_REMOVESRC		: (__rx_REMOVESRC,	RXFLG_EXFATAL),
		AwlSimMessage.MSG_ID_REMOVEBLK		: (__rx_REMOVEBLK,	RXFLG_EXFATAL),
#		AwlSimMessage.MSG_ID_GET_OPT		: (__rx_GET_OPT,	RXFLG_NONE),
		AwlSimMessage.MSG_ID_OPT		: (__rx_OPT,		RXFLG_EXFATAL),
		AwlSimMessage.MSG_ID_GET_BLOCKINFO	: (__rx_GET_BLOCKINFO,	RXFLG_NONE),
		AwlSimMessage.MSG_ID_GET_CPUSPECS	: (__rx_GET_CPUSPECS,	RXFLG_NONE),
		AwlSimMessage.MSG_ID_CPUSPECS		: (__rx_CPUSPECS,	RXFLG_EXFATAL),
		AwlSimMessage.MSG_ID_GET_CPUCONF	: (__rx_GET_CPUCONF,	RXFLG_NONE),
		AwlSimMessage.MSG_ID_CPUCONF		: (__rx_CPUCONF,	RXFLG_EXFATAL),
		AwlSimMessage.MSG_ID_REQ_MEMORY		: (__rx_REQ_MEMORY,	RXFLG_NONE),
		AwlSimMessage.MSG_ID_MEMORY		: (__rx_MEMORY,		RXFLG_NONE),
		AwlSimMessage.MSG_ID_INSNSTATE_CONFIG	: (__rx_INSNSTATE_CONFIG, RXFLG_NONE),
		AwlSimMessage.MSG_ID_MEAS_CONFIG	: (__rx_MEAS_CONFIG,	RXFLG_NONE),
		AwlSimMessage.MSG_ID_GET_IDENTS		: (__rx_GET_IDENTS,	RXFLG_NONE),
#		AwlSimMessage.MSG_ID_GET_CPUDUMP	: (__rx_GET_CPUDUMP,	RXFLG_NONE),
		AwlSimMessage.MSG_ID_GET_CPUSTATS	: (__rx_GET_CPUSTATS,	RXFLG_NONE),
	}

	def __clientCommTransferError(self, exception, client):
		if exception.reason == exception.REASON_REMOTEDIED:
			printInfo("Client '%s' disconnected" % (
				  client.transceiver.peerInfoString))
		else:
			printInfo("Client '%s' data "
				  "transfer error:\n%s" % (
				  client.transceiver.peerInfoString,
				  str(exception)))
		self.__clientRemove(client)

	def __handleClientComm(self, client): #+cdef
		flags = self.RXFLG_EXFATAL
		try:
			msg = client.transceiver.receive(0.0)
			if not msg:
				return
			if msg.msgId not in self.__msgRxHandlers:
				printInfo("Received unsupported "
					  "message 0x%02X" % msg.msgId)
				return
			handler, flags = self.__msgRxHandlers[msg.msgId]
			handler(self, client, msg)
		except AwlSimError as e:
			if not (flags & self.RXFLG_EXFATAL):
				# Just report this nonfatal exception.
				e.setReportOnlyFlag(True)
			raise e
		except TransferError as e:
			self.__clientCommTransferError(e, client)
			return

	def __handleSocketComm(self, sockList): #@nocy
#@cy	cdef __handleSocketComm(self, list sockList):
		if self.__socket in sockList:
			sockList.remove(self.__socket)
			self.__accept()
		for sock in sockList:
			self.__handleClientComm(self.__sock2client[sock.fileno()])

	def __selectException(self):
		raise AwlSimError("AwlSimServer: Communication error. "
				  "'select' failed")

	def __handleCommunication(self, __select=select_mod.select, __Exception=Exception):
		try:
			rlist, wlist, xlist = __select(self.__selectRlist,
						       self.__emptyList,
						       self.__emptyList, 0.0)
			if not rlist:
				return
		except __Exception:
			self.__selectException()
		self.__handleSocketComm(rlist)

		# Check again to receive more data (with a small timeout).
		while True:
			try:
				rlist, wlist, xlist = __select(self.__selectRlist,
							       self.__emptyList,
							       self.__emptyList, 0.01)
				if not rlist:
					return
			except __Exception:
				self.__selectException()
			self.__handleSocketComm(rlist)

	# Optimized version of __handleCommunication()
	# that calls posix select directly.
#	cdef __handleCommunicationPosix(self):				#@cy-posix
#		cdef fd_set rfds					#@cy-posix
#		cdef int ret						#@cy-posix
#		cdef timeval timeout					#@cy-posix
#		cdef list rlist						#@cy-posix
#									#@cy-posix
#		timeout.tv_sec = 0					#@cy-posix
#		timeout.tv_usec = 0					#@cy-posix
#		while True:						#@cy-posix
#			rfds = self.__select_fdset			#@cy-posix
#			ret = select(self.__select_fdset_size,		#@cy-posix
#				     &rfds, NULL, NULL,			#@cy-posix
#				     &timeout)				#@cy-posix
#			if likely(ret == 0):				#@cy-posix
#				return					#@cy-posix
#			if ret < 0:					#@cy-posix
#				self.__selectException()		#@cy-posix
#				return					#@cy-posix
#			rlist = [ client.socket				#@cy-posix
#				for client in self.__clients		#@cy-posix
#				if FD_ISSET(client.fileno, &rfds)	#@cy-posix
#			]						#@cy-posix
#			if FD_ISSET(self.__socketFileno, &rfds):	#@cy-posix
#				rlist.append(self.__socket)		#@cy-posix
#			self.__handleSocketComm(rlist)			#@cy-posix
#									#@cy-posix
#			# Check again to receive more data		#@cy-posix
#			# (with a small timeout).			#@cy-posix
#			timeout.tv_sec = 0				#@cy-posix
#			timeout.tv_usec = 10000				#@cy-posix

	def __handleCommunicationBlocking(self):
		handleComm = False
		try:
			# Use blocking select(), but with a timeout.
			# This gives us the chance to exit the main loop,
			# if we got shutdown due to a signal.
			handleComm = any(select_mod.select(
				self.__selectRlist, [], [], 0.2))
		except Exception:
			self.__selectException()
		if handleComm:
			self.__handleCommunication()
		return handleComm

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

	def __loadProject(self, project, writeBack=False):
		"""Load a project.
		project: Path to the project, or Project instance.
		writeBack: Enable write access to the project file.
		"""
		self.setRunState(self.STATE_STOP)

		self.__projectFile = None
		self.__projectWriteBack = writeBack and bool(project)
		self.__projectToBeLoaded = project

	def __doLoadProject(self):
		project = self.__projectToBeLoaded
		writeBack = self.__projectWriteBack
		self.__projectToBeLoaded = None
		self.__projectFile = None
		self.__projectWriteBack = False

		if not project:
			return

		self.__projectFile = project if isString(project) else project.getProjectFile()
		self.__projectWriteBack = writeBack

		printDebug("Loading project '%s'" % str(project))
		try:
			if isString(project):
				projectFile = project

				if writeBack:
					# If the project file exists and it has zero size
					# then delete the file.
					if os.path.exists(projectFile):
						with contextlib.suppress(IOError, OSError):
							if not os.path.getsize(projectFile):
								os.unlink(projectFile)
								printInfo("Purged empty project "
									  "file at '%s'." % projectFile)
					if not os.path.exists(projectFile):
						# The project file does not exist.
						# Create an empty one.
						printInfo("Creating empty project at '%s'" % (
							  projectFile))
						empty = Project(projectFile)
						empty.toFile()
				# Load the project data.
				try:
					project = Project.fromFile(projectFile)
				except AwlSimError as e:
					raise AwlSimError("AwlSimServer: "
							  "Failed to load project file '%s':\n%s" % (
							  projectFile, e.message))

			self.__resetAll()

			for modDesc in project.getHwmodSettings().getLoadedModules():
				self.loadHardwareModule(modDesc)
			self.cpuSetSpecs(project.getCpuSpecs())
			self.cpuSetConf(project.getCpuConf())

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
		except (AwlSimError, AwlParserError, MaintenanceRequest, TransferError) as e:
			# Don't reset here.
			# Keep the partially loaded content.
			printError("Failed to load project: " + str(e))
			raise e

	def __extendAwlSimError(self, e):
		"""Try to add more useful information to an exception.
		"""
		# If we have a source ident hash in the exception, but no
		# source name, try to get it.
		sourceIdentHash = e.getSourceId()
		if not e.getSourceName() and sourceIdentHash:
			# The source name is not set, yet, but we have a source-ID.
			# Try to get the name.
			for sourceContainer in (self.awlSourceContainer,
						self.fupSourceContainer,
						self.symTabSourceContainer):
				srcMgr = sourceContainer.getSourceManagerByIdent(sourceIdentHash)
				if srcMgr and srcMgr.source:
					# We got it. Set the name.
					e.setSourceName(srcMgr.source.name)
					break

	def startup(self, host, port, family=None,
		    commandMask=0,
		    raiseExceptionsFromRun=False,
		    handleMaintenanceServerside=False,
		    project=None,
		    projectWriteBack=False):
		"""Start the server on 'host':'port'.
		family -> Address family. Either None or one of socket.AF_...
		commanMask -> Mask of allowed commands (CMDMSK_...).
		raiseExceptionsFromRun -> Flag whether to raise AwlSimError()
					  from the run() method and let the caller handle them.
		handleMaintenanceServerside -> Flag whether to raise maintenance
		                               request exceptions on the server only.
		project -> If this is a .awlpro path string or Project(), it uses the data
		           from the specified project as an initial program.
		projectWriteBack -> If True, all data changes (e.g. source download)
		                    be written to the projectFile (if available).
		This must be called once before run()."""

		assert(not self.__startupDone)
		self.__commandMask = commandMask
		self.__raiseExceptionsFromRun = raiseExceptionsFromRun
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

				if self.__projectToBeLoaded:
					self.__doLoadProject()

				if self.__state in {self.STATE_STOP,
						    self.STATE_MAINTENANCE}:
					handleComm = True
					while self.__state in {self.STATE_STOP,
							       self.STATE_MAINTENANCE}:
						if handleComm:
							self.__sendCpuDump(constrained=False)
							self.__handleMemReadReqs(constrained=False)
						handleComm = self.__handleCommunicationBlocking()
					continue

				if self.__state == self.STATE_RUN:
					while self.__running:
						sim.runCycle()
						if self.__haveAnyMemReadReq:
							self.__handleMemReadReqs()
						self.__handleCommunication()		#@cy-win
#						self.__handleCommunicationPosix()	#@cy-posix
						self.__yieldHostCPU()
					continue

			except (AwlSimError, AwlParserError) as e:
				printVerbose("Main loop exception: %s" % (
					     e.getMessage()))

				if not e.getReportOnlyFlag():
					# Stop the CPU
					self.setRunState(self.STATE_STOP)
					# Schedule a CPU restart/rebuild.
					self.__needOB10x = True

				# Try to add more information to the exception.
				self.__extendAwlSimError(e)

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

				if self.__raiseExceptionsFromRun:
					if e.getReportOnlyFlag():
						printError(e.getReport())
					else:
						# Let the caller handle the exception
						raise e
			except MaintenanceRequest as e:
				printVerbose("Main loop maintenance request: %d" % (
					     e.requestType))
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
		sock, ok = None, False
		_SocketErrors = SocketErrors
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
			ok = True
		except _SocketErrors as e:
			raise AwlSimError("AwlSimServer: Failed to create server "
				"socket: " + str(e))
		finally:
			if not ok and sock:
				with suppressAllExc:
					if hasattr(sock, "shutdown"):
						sock.shutdown(socket.SHUT_RDWR)
				with suppressAllExc:
					sock.close()
		self.__socket = sock
#		self.__socketFileno = sock.fileno() #@cy-posix

	def __accept(self):
		"""Accept a client connection.
		Returns the Client instance or None."""

		if not self.__socket:
			raise AwlSimError("AwlSimServer: No server socket")

		_SocketErrors = SocketErrors
		try:
			clientSock, addrInfo = self.__socket.accept()
			if self.__unixSockPath:
				peerInfoString = self.__unixSockPath
			else:
				peerInfoString = "[%s]:%d" % addrInfo[:2]
		except _SocketErrors as e:
			transferError = TransferError(None, e)
			if transferError.reason == transferError.REASON_BLOCKING:
				return None
			raise AwlSimError("AwlSimServer: accept() failed: %s" % str(e))
		printInfo("Client '%s' connected" % peerInfoString)

		client = AwlSimClientInfo(clientSock, peerInfoString)
		self.__clientAdd(client)

		return client

	def __clientAdd(self, client):
		if client.fileno in self.__sock2client:
			self.__clientRemove(self.__sock2client[client.fileno])
		self.__clients.append(client)
		self.__sock2client[client.fileno] = client
		self.__rebuildSelectReadList()

	def __clientRemove(self, client):
		self.__clients.remove(client)
		self.__sock2client.pop(client.fileno)
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
				self.__socket.setblocking(False)
			with suppressAllExc:
				if hasattr(self.__socket, "shutdown"):
					self.__socket.shutdown(socket.SHUT_RDWR)
			with suppressAllExc:
				self.__socket.close()
			self.__socket = None
#			self.__socketFileno = -1 #@cy-posix
		if self.__unixSockPath:
			with contextlib.suppress(OSError):
				os.unlink(self.__unixSockPath)
			self.__unixSockPath = None

	def shutdown(self):
		printInfo("Shutting down.")
		with suppressAllExc:
			self.close()
		with suppressAllExc:
			self.__sim.shutdown()

	def signalHandler(self, sig, frame):
		printInfo("Received signal %d" % sig)
		if sig in (signal.SIGTERM, signal.SIGINT):
			self.setRunState(self.STATE_EXIT)

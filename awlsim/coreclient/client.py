# -*- coding: utf-8 -*-
#
# AWL simulator - PLC core server client
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

from awlsim.common.util import *
from awlsim.common.subprocess_wrapper import *
from awlsim.common.net import *
from awlsim.common.exceptions import *

from awlsim.coreclient.sshtunnel import *
from awlsim.coreclient.util import *

from awlsim.coreserver.server import *

import sys
import socket
import errno
import time


class MsgWaiter(object):
	"""Message waiter queue entry.
	"""

	def __init__(self, checkCallback):
		self.checkCallback = checkCallback
		self.rxMsg = None

	def receiveMsg(self, rxMsg):
		if rxMsg is None:
			return False
		if self.rxMsg is None:
			if self.checkCallback(rxMsg):
				self.rxMsg = rxMsg
				return True
		return False

class AwlSimClient(object):
	"""Awlsim coreserver client API.
	"""

	def __init__(self):
		self.serverProcess = None
		self.serverProcessHost = None
		self.serverProcessPort = None
		self.__transceiver = None
		self.__defaultTimeout = 3.0
		self.__msgWaiters = []

	def spawnServer(self,
			interpreter=None,
			serverExecutable=None,
			listenHost=AwlSimServer.DEFAULT_HOST,
			listenPort=AwlSimServer.DEFAULT_PORT,
			frozenExecutableMagic=True):
		"""Spawn a new AwlSim-core server process.
		interpreter -> The python interpreter to use. Must be either:
			       - None: Use sys.executable as interpreter.
			       - a string: Use the specified interpreter binary.
			       - list of strings: Try with the interpreters in the
						  list, until the first working one is found.
		serverExecutable -> The server executable to run.
				    This has precedence over 'interpreter'.
				    May be a list of strings.
		listenHost -> The hostname or IP address to listen on.
		listenPort -> The port to listen on.
			      This may be an iterable to try multiple ports.
		Returns the spawned process' PID."""

		if self.serverProcess:
			raise AwlSimError("Server already running")

		if frozenExecutableMagic and isWinStandalone:
			# We are running the frozen executable
			# and the magic is turned on.
			# Enforce the server executable name.
			oldExecutable = serverExecutable
			serverExecutable = standaloneServerExe
			if oldExecutable:
				printWarning("spawnServer: Overriding server "
					     "executable '%s' -> '%s'" %(
					     oldExecutable, serverExecutable))

		actualListenPort = None
		for port in toList(listenPort):
			if not netPortIsUnused(listenHost, port):
				continue
			if serverExecutable:
				for serverExe in toList(serverExecutable):
					if not findExecutable(serverExe):
						continue
					try:
						self.serverProcess = AwlSimServer.start(
							listenHost = listenHost,
							listenPort = port,
							forkServerProcess = serverExe)
					except AwlSimError as e:
						if not isiterable(listenPort):
							raise e
					else:
						actualListenPort = port
					break
				else:
					raise AwlSimError("Unable to fork any of the supplied "
						"server executables: %s" %\
						str(toList(serverExecutable)))
			else:
				if interpreter is None:
					interpreter = sys.executable
				for interp in toList(interpreter):
					if not findExecutable(interp):
						continue
					try:
						self.serverProcess = AwlSimServer.start(
							listenHost = listenHost,
							listenPort = port,
							forkInterpreter = interp)
					except AwlSimError as e:
						if not isiterable(listenPort):
							raise e
					else:
						actualListenPort = port
					break
				else:
					raise AwlSimError("Unable to fork an awlsim core server with "
						"any of the supplied Python interpreters: %s\n"
						"No interpreter found." %\
						str(toList(interpreter)))
			if actualListenPort:
				break
		else:
			raise AwlSimError("Unable to find a port to spawn the "
				"awlsim core server on.\nTried port %d to %d on '%s'." %(
				toList(listenPort)[0], toList(listenPort)[-1], listenHost))
		self.serverProcessHost = listenHost
		self.serverProcessPort = actualListenPort
		if isJython:
			#XXX Workaround: Jython's socket module does not like connecting
			# to a starting server. Wait a few seconds for the server
			# to start listening on the socket.
			time.sleep(10)

	def killSpawnedServer(self):
		"""Shutdown the server process started with spawnServer()."""

		if not self.serverProcess:
			return

		if self.__transceiver:
			with contextlib.suppress(AwlSimError, MaintenanceRequest):
				msg = AwlSimMessage_SHUTDOWN()
				status = self.__sendAndWaitFor_REPLY(msg)
				if status != AwlSimMessage_REPLY.STAT_OK:
					printError("AwlSimClient: Failed to shut "
						"down server via message")

		self.serverProcess.terminate()
		self.serverProcess.wait()
		self.serverProcess = None
		self.serverProcessHost = None
		self.serverProcessPort = None

	def connectToServer(self,
			    host=AwlSimServer.DEFAULT_HOST,
			    port=AwlSimServer.DEFAULT_PORT,
			    timeout=3.0):
		"""Connect to a AwlSim-core server.
		host -> The hostname or IP address to connect to.
		port -> The port to connect to."""

		self.__defaultTimeout = timeout
		startTime = monotonic_time()
		readableSockaddr = host
		try:
			family, socktype, sockaddr = netGetAddrInfo(host, port)
			if family == AF_UNIX:
				readableSockaddr = sockaddr
			else:
				readableSockaddr = "[%s]:%d" % (sockaddr[0], sockaddr[1])
			printInfo("AwlSimClient: Connecting to server '%s'..." % readableSockaddr)
			sock = socket.socket(family, socktype)
			while 1:
				if monotonic_time() - startTime > timeout:
					raise AwlSimError("Timeout connecting "
						"to AwlSimServer %s" % readableSockaddr)
				try:
					sock.connect(sockaddr)
				except SocketErrors as e:
					if e.errno == errno.ECONNREFUSED or\
					   e.errno == errno.ENOENT:
						self.sleep(0.1)
						continue
					if isJython and\
					   e.strerror.endswith("java.nio.channels.CancelledKeyException"):
						# XXX Jython workaround: Ignore this exception
						printInfo("Warning: Jython connect workaround")
						continue
					raise
				break
		except SocketErrors as e:
			raise AwlSimError("Failed to connect to AwlSimServer %s: %s" %\
				(readableSockaddr, str(e)))
		printInfo("AwlSimClient: Connected.")
		self.__transceiver = AwlSimMessageTransceiver(sock, readableSockaddr)
		self.__msgWaiters = []

		# Ping the server
		try:
			self.__transceiver.send(AwlSimMessage_PING())
			msg = self.__transceiver.receive(timeout = timeout)
			if not msg:
				raise AwlSimError("AwlSimClient: Server did not "
					"respond to PING request.")
			if msg.msgId != AwlSimMessage.MSG_ID_PONG:
				raise AwlSimError("AwlSimClient: Server did not "
					"respond properly to PING request. "
					"(Expected ID %d, but got ID %d)" %\
					(AwlSimMessage.MSG_ID_PONG, msg.msgId))
		except TransferError as e:
			raise AwlSimError("AwlSimClient: PING to server failed")

	def shutdownTransceiver(self):
		"""Shutdown transceiver and close the socket."""

		if not self.__transceiver:
			return

		self.__transceiver.shutdown()
		self.__transceiver = None

	def shutdown(self):
		"""Shutdown all sockets and spawned processes."""

		self.killSpawnedServer()
		self.shutdownTransceiver()

	def __rx_NOP(self, msg):
		pass # Nothing

	def handle_EXCEPTION(self, exception):
		raise exception

	def __rx_EXCEPTION(self, msg):
		self.handle_EXCEPTION(msg.exception)

	def __rx_PING(self, msg):
		self.__send(AwlSimMessage_PONG())

	def handle_PONG(self):
		printInfo("AwlSimClient: Received PONG")

	def __rx_PONG(self, msg):
		self.handle_PONG()

	def handle_AWLSRC(self, awlSource):
		pass # Don't do anything by default

	def __rx_AWLSRC(self, msg):
		self.handle_AWLSRC(msg.source)

	def handle_SYMTABSRC(self, symTabSource):
		pass # Don't do anything by default

	def __rx_SYMTABSRC(self, msg):
		self.handle_SYMTABSRC(msg.source)

	def handle_CPUDUMP(self, dumpText):
		pass # Don't do anything by default

	def __rx_CPUDUMP(self, msg):
		self.handle_CPUDUMP(msg.dumpText)

	def __rx_MAINTREQ(self, msg):
		raise msg.maintRequest

	def handle_MEMORY(self, memAreas):
		pass # Don't do anything by default

	def __rx_MEMORY(self, msg):
		self.handle_MEMORY(msg.memAreas)
		if msg.flags & msg.FLG_SYNC:
			# The server should never send us a synchronous
			# memory image. So just output an error message.
			printError("Received synchronous memory request")

	def handle_INSNSTATE(self, msg):
		pass # Don't do anything by default

	def __rx_INSNSTATE(self, msg):
		self.handle_INSNSTATE(msg)

	def handle_IDENTS(self, msg):
		pass # Don't do anything by default

	def __rx_IDENTS(self, msg):
		self.handle_IDENTS(msg)

	def handle_BLOCKINFO(self, msg):
		pass # Don't do anything by default

	def __rx_BLOCKINFO(self, msg):
		self.handle_BLOCKINFO(msg)

	__msgRxHandlers = {
		AwlSimMessage.MSG_ID_REPLY		: __rx_NOP,
		AwlSimMessage.MSG_ID_EXCEPTION		: __rx_EXCEPTION,
		AwlSimMessage.MSG_ID_MAINTREQ		: __rx_MAINTREQ,
		AwlSimMessage.MSG_ID_PING		: __rx_PING,
		AwlSimMessage.MSG_ID_PONG		: __rx_PONG,
		AwlSimMessage.MSG_ID_AWLSRC		: __rx_AWLSRC,
		AwlSimMessage.MSG_ID_SYMTABSRC		: __rx_SYMTABSRC,
		AwlSimMessage.MSG_ID_IDENTS		: __rx_IDENTS,
		AwlSimMessage.MSG_ID_BLOCKINFO		: __rx_BLOCKINFO,
		AwlSimMessage.MSG_ID_CPUSPECS		: __rx_NOP,
		AwlSimMessage.MSG_ID_CPUCONF		: __rx_NOP,
		AwlSimMessage.MSG_ID_RUNSTATE		: __rx_NOP,
		AwlSimMessage.MSG_ID_CPUDUMP		: __rx_CPUDUMP,
		AwlSimMessage.MSG_ID_MEMORY		: __rx_MEMORY,
		AwlSimMessage.MSG_ID_INSNSTATE		: __rx_INSNSTATE,
	}

	# Main message processing
	# timeout: None -> Blocking. Block until packet is received.
	#          0 -> No timeout (= Nonblocking). Return immediately.
	#          x -> Timeout, in seconds.
	def processMessages(self, timeout=None):
		if not self.__transceiver:
			return False
		try:
			msg = self.__transceiver.receive(timeout)
		except TransferError as e:
			if e.reason == e.REASON_BLOCKING:
				return False
			raise AwlSimError("AwlSimClient: "
				"I/O error in connection to server '%s':\n"
				"%s (errno = %s)" %\
				(self.__transceiver.peerInfoString, str(e), str(e.errno)))
		except TransferError as e:
			raise AwlSimError("AwlSimClient: "
				"Connection to server '%s' died. "
				"Failed to receive message." %\
				self.__transceiver.peerInfoString)
		if not msg:
			return False
		printDebug("AwlSimClient: Received message 0x%04X" % msg.msgId)
		for waiter in self.__msgWaiters:
			if waiter.receiveMsg(msg):
				break
		else:
			try:
				handler = self.__msgRxHandlers[msg.msgId]
			except KeyError:
				raise AwlSimError("AwlSimClient: Received unsupported "
					"message 0x%02X" % msg.msgId)
			handler(self, msg)
		return True

	def sleep(self, seconds):
		time.sleep(seconds)

	def __send(self, txMsg):
		printDebug("AwlSimClient: Sending message 0x%04X" % txMsg.msgId)
		try:
			self.__transceiver.send(txMsg)
		except TransferError as e:
			raise AwlSimError("AwlSimClient: "
				"Send error in connection to server '%s':\n"
				"%s (errno = %s)" %\
				(self.__transceiver.peerInfoString,
				 str(e), str(e.errno)))

	def __sendAndWait(self, txMsg, checkRxMsg,
			  waitTimeout=None,
			  ignoreMaintenanceRequests=False):
		waiter = MsgWaiter(checkRxMsg)
		self.__msgWaiters.append(waiter)
		try:
			self.__send(txMsg)
			now = monotonic_time()
			end = now + (self.__defaultTimeout if waitTimeout is None\
				     else waitTimeout)
			while now < end:
				try:
					if self.processMessages(0.1):
						if waiter.rxMsg is not None:
							return waiter.rxMsg
				except MaintenanceRequest as e:
					if not ignoreMaintenanceRequests:
						raise e
				now = monotonic_time()
			raise AwlSimError("AwlSimClient: Timeout waiting for server reply.")
		finally:
			self.__msgWaiters.remove(waiter)

	def __sendAndWaitFor_REPLY(self, msg, timeout=None,
				   ignoreMaintenanceRequests=False):
		def checkRxMsg(rxMsg):
			return rxMsg.msgId == AwlSimMessage.MSG_ID_REPLY and\
			       rxMsg.inReplyToId == msg.msgId and\
			       rxMsg.inReplyToSeq == msg.seq
		return self.__sendAndWait(msg, checkRxMsg, timeout,
					  ignoreMaintenanceRequests).status

	def reset(self):
		if not self.__transceiver:
			return False
		msg = AwlSimMessage_RESET()
		status = self.__sendAndWaitFor_REPLY(msg,
			ignoreMaintenanceRequests = True)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to reset CPU")
		return True

	def setRunState(self, run=True):
		if not self.__transceiver:
			return False
		if run:
			runState = AwlSimMessage_RUNSTATE.STATE_RUN
		else:
			runState = AwlSimMessage_RUNSTATE.STATE_STOP
		msg = AwlSimMessage_RUNSTATE(runState)
		status = self.__sendAndWaitFor_REPLY(msg,
			ignoreMaintenanceRequests = True)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to set run state")
		return True

	def getRunState(self):
		if not self.__transceiver:
			return False
		msg = AwlSimMessage_GET_RUNSTATE()
		rxMsg = self.__sendAndWait(msg,
			lambda rxMsg: rxMsg.msgId == AwlSimMessage.MSG_ID_RUNSTATE)
		if rxMsg.runState == AwlSimMessage_RUNSTATE.STATE_RUN:
			return True
		return False

	def getAwlSource(self, identHash, sync=True):
		if not self.__transceiver:
			return False
		msg = AwlSimMessage_GET_AWLSRC(identHash)
		if sync:
			rxMsg = self.__sendAndWait(msg,
				lambda rxMsg: rxMsg.msgId == AwlSimMessage.MSG_ID_AWLSRC)
			return rxMsg.source
		else:
			self.__send(msg)
		return True

	def loadAwlSource(self, awlSource):
		if not self.__transceiver:
			return False
		msg = AwlSimMessage_AWLSRC(awlSource)
		self.__transceiver.txCork(True)
		try:
			status = self.__sendAndWaitFor_REPLY(msg, 10.0)
		finally:
			self.__transceiver.txCork(False)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to load AWL source")
		return True

	def loadFupSource(self, fupSource):
		if not self.__transceiver:
			return False
		msg = AwlSimMessage_FUPSRC(fupSource)
		self.__transceiver.txCork(True)
		try:
			status = self.__sendAndWaitFor_REPLY(msg, 10.0)
		finally:
			self.__transceiver.txCork(False)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to load FUP source")
		return True

	def loadKopSource(self, kopSource):
		if not self.__transceiver:
			return False
		msg = AwlSimMessage_KOPSRC(kopSource)
		self.__transceiver.txCork(True)
		try:
			status = self.__sendAndWaitFor_REPLY(msg, 10.0)
		finally:
			self.__transceiver.txCork(False)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to load FUP source")
		return True

	def loadAwlSources(self, awlSources):
		return all(self.loadAwlSource(awlSource)
			   for awlSource in awlSources)

	def loadFupSources(self, fupSources):
		return all(self.loadFupSource(fupSource)
			   for fupSource in fupSources)

	def loadKopSources(self, kopSources):
		return all(self.loadKopSource(kopSource)
			   for kopSource in kopSources)

	def getSymTabSource(self, identHash, sync=True):
		if not self.__transceiver:
			return False
		msg = AwlSimMessage_GET_SYMTABSRC(identHash)
		if sync:
			rxMsg = self.__sendAndWait(msg,
				lambda rxMsg: rxMsg.msgId == AwlSimMessage.MSG_ID_SYMTABSRC)
			return rxMsg.source
		else:
			self.__send(msg)
		return True

	def loadSymTabSource(self, symTabSource):
		if not self.__transceiver:
			return False
		msg = AwlSimMessage_SYMTABSRC(symTabSource)
		self.__transceiver.txCork(True)
		try:
			status = self.__sendAndWaitFor_REPLY(msg)
		finally:
			self.__transceiver.txCork(False)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to load symbol table source")
		return True

	def loadSymTabSources(self, symTabSources):
		return all(self.loadSymTabSource(symTabSource)
			   for symTabSource in symTabSources)

	def loadLibraryBlock(self, libSelection):
		if not self.__transceiver:
			return False
		msg = AwlSimMessage_LIBSEL(libSelection)
		status = self.__sendAndWaitFor_REPLY(msg)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to load library block selection")
		return True

	def loadLibraryBlocks(self, libSelections):
		return all(self.loadLibraryBlock(libSel)
			   for libSel in libSelections)

	def loadHardwareModule(self, hwmodDesc):
		if not self.__transceiver:
			return False
		msg = AwlSimMessage_HWMOD(hwmodDesc)
		status = self.__sendAndWaitFor_REPLY(msg)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to load hardware module")
		return True

	def loadHardwareModules(self, hwmodDescs):
		return all(self.loadHardwareModule(hwmodDesc)
			   for hwmodDesc in hwmodDescs)

	def build(self):
		if not self.__transceiver:
			return False
		msg = AwlSimMessage_BUILD()
		status = self.__sendAndWaitFor_REPLY(msg)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to build sources")
		return True

	def removeSource(self, identHash):
		if not self.__transceiver:
			return False
		msg = AwlSimMessage_REMOVESRC(identHash)
		status = self.__sendAndWaitFor_REPLY(msg)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to remove source")
		return True

	def removeBlock(self, blockInfo):
		if not self.__transceiver:
			return False
		msg = AwlSimMessage_REMOVEBLK(blockInfo)
		status = self.__sendAndWaitFor_REPLY(msg)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to remove block")
		return True

	# Request the (source) ident hashes from the CPU.
	# This method is asynchronous.
	# The idents are returned via handle_IDENTS()
	def requestIdents(self, reqAwlSources = False,
			  reqSymTabSources = False,
			  reqHwModules = False,
			  reqLibSelections = False):
		if not self.__transceiver:
			return False
		self.__send(AwlSimMessage_GET_IDENTS(
			(AwlSimMessage_GET_IDENTS.GET_AWLSRCS if reqAwlSources else 0) |\
			(AwlSimMessage_GET_IDENTS.GET_SYMTABSRCS if reqSymTabSources else 0) |\
			(AwlSimMessage_GET_IDENTS.GET_HWMODS if reqHwModules else 0) |\
			(AwlSimMessage_GET_IDENTS.GET_LIBSELS if reqLibSelections else 0)))
		return True

	# Request the compiled block info from the CPU.
	# This method is asynchronous.
	# The idents are returned via handle_BLOCKINFO()
	def requestBlockInfo(self, reqOBInfo = False,
			     reqFCInfo = False,
			     reqFBInfo = False,
			     reqDBInfo = False):
		if not self.__transceiver:
			return False
		self.__send(AwlSimMessage_GET_BLOCKINFO(
			(AwlSimMessage_GET_BLOCKINFO.GET_OB_INFO if reqOBInfo else 0) |\
			(AwlSimMessage_GET_BLOCKINFO.GET_FC_INFO if reqFCInfo else 0) |\
			(AwlSimMessage_GET_BLOCKINFO.GET_FB_INFO if reqFBInfo else 0) |\
			(AwlSimMessage_GET_BLOCKINFO.GET_DB_INFO if reqDBInfo else 0)))
		return True

	def __setOption(self, name, value, sync=True):
		if not self.__transceiver:
			return False
		msg = AwlSimMessage_OPT(name, str(value))
		if sync:
			status = self.__sendAndWaitFor_REPLY(msg)
			if status != AwlSimMessage_REPLY.STAT_OK:
				raise AwlSimError("AwlSimClient: Failed to set option '%s'" % name)
		else:
			self.__send(msg)
		return True

	def setLoglevel(self, level=Logging.LOG_INFO,
			setClientSide=True,
			setServerSide=True):
		if setClientSide:
			Logging.setLoglevel(level)
		if setServerSide:
			if not self.__setOption("loglevel", int(level)):
				return False
		return True

	def enableOBTempPresets(self, enable=True):
		return self.__setOption("ob_temp_presets", int(bool(enable)))

	def enableExtendedInsns(self, enable=True):
		return self.__setOption("extended_insns", int(bool(enable)))

	def setPeriodicDumpInterval(self, interval=0):
		return self.__setOption("periodic_dump_int", int(interval))

	def setCycleTimeLimit(self, seconds=5.0):
		return self.__setOption("cycle_time_limit", float(seconds))

	def setRunTimeLimit(self, seconds=0.0):
		return self.__setOption("runtime_limit", float(seconds))

	# Set instruction state dumping.
	# fromLine, toLine is the range of AWL line numbers for which
	# dumping is enabled.
	def setInsnStateDump(self, enable=True,
			     sourceId=0, fromLine=1, toLine=0x7FFFFFFF,
			     sync=True):
		if not self.__transceiver:
			return None
		msg = AwlSimMessage_INSNSTATE_CONFIG(
			flags = 0,
			sourceId = sourceId,
			fromLine = fromLine,
			toLine = toLine)
		if enable:
			msg.flags |= msg.FLG_CLEAR
		else:
			msg.flags |= msg.FLG_CLEAR_ONLY
		if sync:
			msg.flags |= msg.FLG_SYNC
			status = self.__sendAndWaitFor_REPLY(msg)
			if status != AwlSimMessage_REPLY.STAT_OK:
				raise AwlSimError("AwlSimClient: Failed to set insn state dump")
		else:
			self.__send(msg)

	def getCpuSpecs(self):
		if not self.__transceiver:
			return None
		msg = AwlSimMessage_GET_CPUSPECS()
		rxMsg = self.__sendAndWait(msg,
			lambda rxMsg: rxMsg.msgId == AwlSimMessage.MSG_ID_CPUSPECS)
		return rxMsg.cpuspecs

	def setCpuSpecs(self, cpuspecs):
		if not self.__transceiver:
			return False
		msg = AwlSimMessage_CPUSPECS(cpuspecs)
		status = self.__sendAndWaitFor_REPLY(msg)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to set cpuspecs")
		return True

	def getCpuConf(self):
		if not self.__transceiver:
			return None
		msg = AwlSimMessage_GET_CPUCONF()
		rxMsg = self.__sendAndWait(msg,
			lambda rxMsg: rxMsg.msgId == AwlSimMessage.MSG_ID_CPUCONF)
		return rxMsg.cpuconf

	def setCpuConf(self, cpuconf):
		if not self.__transceiver:
			return False
		msg = AwlSimMessage_CPUCONF(cpuconf)
		status = self.__sendAndWaitFor_REPLY(msg)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to set cpuconf")
		return True

	def loadProject(self, project,
			loadCpuSpecs=True, loadCpuConf=True,
			loadTempPresets=True,
			loadExtInsns=True, loadHwMods=True,
			loadSymTabs=True, loadLibSelections=True,
			loadSources=True,
			loadFup=True, loadKop=True):
		"""Load selected settings and sources from project.
		"""
		if loadCpuSpecs:
			self.setCpuSpecs(project.getCpuSpecs())
		if loadCpuConf:
			self.setCpuConf(project.getCpuConf())
		if loadTempPresets:
			self.enableOBTempPresets(project.getObTempPresetsEn())
		if loadExtInsns:
			self.enableExtendedInsns(project.getExtInsnsEn())
		if loadHwMods:
			self.loadHardwareModules(project.getHwmodSettings().getLoadedModules())
		if loadSymTabs:
			self.loadSymTabSources(project.getSymTabSources())
		if loadLibSelections:
			self.loadLibraryBlocks(project.getLibSelections())
		if loadSources:
			self.loadAwlSources(project.getAwlSources())
		if loadFup:
			self.loadFupSources(project.getFupSources())
		if loadKop:
			self.loadKopSources(project.getKopSources())

	# Set the memory areas we are interested in receiving
	# dumps for, in the server.
	# memAreas is a list of MemoryArea instances.
	# The repetitionPeriod tells whether to
	#  - only run the request once (repetitionneriod < 0.0)
	#  - repeat every n'th second (repetitionFactor = n)
	# If sync is true, wait for a reply from the server.
	def setMemoryReadRequests(self, memAreas, repetitionPeriod = -1.0,
				  sync = False):
		if not self.__transceiver:
			return False
		msg = AwlSimMessage_REQ_MEMORY(0, repetitionPeriod, memAreas)
		if sync:
			msg.flags |= msg.FLG_SYNC
			status = self.__sendAndWaitFor_REPLY(msg)
			if status != AwlSimMessage_REPLY.STAT_OK:
				raise AwlSimError("AwlSimClient: Failed to set "
					"memory read reqs")
		else:
			self.__send(msg)
		return True

	# Write memory areas in the server.
	# memAreas is a list of MemoryAreaData instances.
	# If sync is true, wait for a reply from the server.
	def writeMemory(self, memAreas, sync=False):
		if not self.__transceiver:
			return False
		msg = AwlSimMessage_MEMORY(0, memAreas)
		if sync:
			msg.flags |= msg.FLG_SYNC
			status = self.__sendAndWaitFor_REPLY(msg)
			if status != AwlSimMessage_REPLY.STAT_OK:
				raise AwlSimError("AwlSimClient: Failed to write "
					"to memory")
		else:
			self.__send(msg)
		return True

# -*- coding: utf-8 -*-
#
# AWL simulator - PLC core server client
#
# Copyright 2013 Michael Buesch <m@bues.ch>
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
from awlsim.core.compat import *

from awlsim.coreserver.server import *
from awlsim.coreserver.messages import *

import sys
import socket
import errno
import time


class AwlSimClient(object):
	def __init__(self):
		self.serverProcess = None
		self.transceiver = None

	def spawnServer(self, interpreter=None,
			listenHost=AwlSimServer.DEFAULT_HOST,
			listenPort=AwlSimServer.DEFAULT_PORT):
		"""Spawn a new AwlSim-core server process.
		interpreter -> The python interpreter to use. Must be either:
			       - None: Use sys.executable as interpreter.
			       - a string: Use the specified interpreter binary.
			       - list of strings: Try with the interpreters in the
			                          list, until the first working one is found.
		listenHost -> The hostname or IP address to listen on.
		listenPort -> The port to listen on.
		Returns the spawned process' PID."""

		if self.serverProcess:
			raise AwlSimError("Server already running")

		if interpreter is None:
			interpreter = [ sys.executable, ]
		elif not isinstance(interpreter, list) and\
		     not isinstance(interpreter, tuple):
			interpreter = [ interpreter, ]

		for interp in interpreter:
			if not AwlSimServer.findExecutable(interp):
				continue
			self.serverProcess = AwlSimServer.start(listenHost = listenHost,
								listenPort = listenPort,
								forkInterpreter = interp)
			break
		else:
			raise AwlSimError("Unable to fork an awlsim core server with "
				"any of the supplied Python interpreters: %s\n"
				"No interpreter found." %\
				str(interpreter))
		if isJython:
			#XXX Workaround: Jython's socket module does not like connecting
			# to a starting server. Wait a few seconds for the server
			# to start listening on the socket.
			time.sleep(10)

	def connectToServer(self,
			    host=AwlSimServer.DEFAULT_HOST,
			    port=AwlSimServer.DEFAULT_PORT):
		"""Connect to a AwlSim-core server.
		host -> The hostname or IP address to connect to.
		port -> The port to connect to."""

		try:
			family, socktype, sockaddr = AwlSimServer.getaddrinfo(host, port)
			if family == AF_UNIX:
				readableSockaddr = sockaddr
			else:
				readableSockaddr = "%s:%d" % (sockaddr[0], sockaddr[1])
			printInfo("AwlSimClient: Connecting to server '%s'..." % readableSockaddr)
			sock = socket.socket(family, socktype)
			count = 0
			while 1:
				try:
					sock.connect(sockaddr)
				except (OSError, socket.error) as e:
					if e.errno == errno.ECONNREFUSED or\
					   e.errno == errno.ENOENT:
						count += 1
						if count >= 100:
							raise AwlSimError("Timeout connecting "
								"to AwlSimServer %s" % readableSockaddr)
						self.sleep(0.1)
						continue
					if isJython and\
					   e.strerror.endswith("java.nio.channels.CancelledKeyException"):
						# XXX Jython workaround: Ignore this exception
						printInfo("Warning: Jython connect workaround")
						continue
					raise
				break
		except socket.error as e:
			raise AwlSimError("Failed to connect to AwlSimServer %s: %s" %\
				(readableSockaddr, str(e)))
		printInfo("AwlSimClient: Connected.")
		self.transceiver = AwlSimMessageTransceiver(sock, readableSockaddr)
		self.lastRxMsg = None

		# Ping the server
		try:
			self.transceiver.send(AwlSimMessage_PING())
			msg = self.transceiver.receive(timeout = 5.0)
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

	def shutdown(self):
		"""Shutdown all sockets and spawned processes."""

		if self.serverProcess:
			try:
				msg = AwlSimMessage_SHUTDOWN()
				status = self.__sendAndWaitFor_REPLY(msg)
				if status != AwlSimMessage_REPLY.STAT_OK:
					printError("AwlSimClient: Failed to shut down server via message")
			except (AwlSimError, MaintenanceRequest) as e:
				pass

			self.serverProcess.terminate()
			self.serverProcess.wait()
			self.serverProcess = None
		if self.transceiver:
			self.transceiver.shutdown()
			self.transceiver = None

	def __rx_NOP(self, msg):
		pass # Nothing

	def __rx_EXCEPTION(self, msg):
		raise AwlSimErrorText(msg.exceptionText)

	def __rx_PING(self, msg):
		self.transceiver.send(AwlSimMessage_PONG())

	def handle_PONG(self):
		printInfo("AwlSimClient: Received PONG")

	def __rx_PONG(self, msg):
		self.handle_PONG()

	def handle_CPUDUMP(self, dumpText):
		pass # Don't do anything by default

	def __rx_CPUDUMP(self, msg):
		self.handle_CPUDUMP(msg.dumpText)

	def __rx_MAINTREQ(self, msg):
		if msg.requestType == MaintenanceRequest.TYPE_SHUTDOWN:
			raise MaintenanceRequest(msg.requestType)
		else:
			printError("Received unknown maintenance request: %d" %\
				   msg.requestType)

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

	__msgRxHandlers = {
		AwlSimMessage.MSG_ID_REPLY		: __rx_NOP,
		AwlSimMessage.MSG_ID_EXCEPTION		: __rx_EXCEPTION,
		AwlSimMessage.MSG_ID_PING		: __rx_PING,
		AwlSimMessage.MSG_ID_PONG		: __rx_PONG,
		AwlSimMessage.MSG_ID_CPUDUMP		: __rx_CPUDUMP,
		AwlSimMessage.MSG_ID_MAINTREQ		: __rx_MAINTREQ,
		AwlSimMessage.MSG_ID_CPUSPECS		: __rx_NOP,
		AwlSimMessage.MSG_ID_MEMORY		: __rx_MEMORY,
		AwlSimMessage.MSG_ID_INSNSTATE		: __rx_INSNSTATE,
	}

	# Main message processing
	# timeout: None -> Blocking. Block until packet is received.
	#          0 -> No timeout (= Nonblocking). Return immediately.
	#          x -> Timeout, in seconds.
	def processMessages(self, timeout=None):
		self.lastRxMsg = None
		if not self.transceiver:
			return False
		try:
			msg = self.transceiver.receive(timeout)
		except (socket.error, BlockingIOError) as e:
			if isinstance(e, socket.timeout) or\
			   isinstance(e, BlockingIOError) or\
			   e.errno == errno.EAGAIN or\
			   e.errno == errno.EWOULDBLOCK:
				return False
			raise AwlSimError("AwlSimClient: "
				"I/O error in connection to server '%s':\n"
				"%s (errno = %s)" %\
				(self.transceiver.peerInfoString, str(e), str(e.errno)))
		except (AwlSimMessageTransceiver.RemoteEndDied, TransferError) as e:
			raise AwlSimError("AwlSimClient: "
				"Connection to server '%s' died. "
				"Failed to receive message." %\
				self.transceiver.peerInfoString)
		if not msg:
			return False
		self.lastRxMsg = msg
		try:
			handler = self.__msgRxHandlers[msg.msgId]
		except KeyError:
			raise AwlSimError("AwlSimClient: Received unsupported "
				"message 0x%02X" % msg.msgId)
		handler(self, msg)
		return True

	def sleep(self, seconds):
		time.sleep(seconds)

	def __sendAndWait(self, txMsg, checkRxMsg, waitTimeout=3.0):
		self.transceiver.send(txMsg)
		now = monotonic_time()
		end = now + waitTimeout
		while now < end:
			if self.processMessages(0.1):
				rxMsg = self.lastRxMsg
				if checkRxMsg(rxMsg):
					return rxMsg
			now = monotonic_time()
		raise AwlSimError("AwlSimClient: Timeout waiting for server reply.")

	def __sendAndWaitFor_REPLY(self, msg, timeout=3.0):
		def checkRxMsg(rxMsg):
			return rxMsg.msgId == AwlSimMessage.MSG_ID_REPLY and\
			       rxMsg.inReplyToId == msg.msgId and\
			       rxMsg.inReplyToSeq == msg.seq
		return self.__sendAndWait(msg, checkRxMsg, timeout).status

	def reset(self):
		msg = AwlSimMessage_RESET()
		status = self.__sendAndWaitFor_REPLY(msg)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to reset CPU")

	def setRunState(self, run=True):
		if not self.transceiver:
			return False
		if run:
			runState = AwlSimMessage_RUNSTATE.STATE_RUN
		else:
			runState = AwlSimMessage_RUNSTATE.STATE_STOP
		msg = AwlSimMessage_RUNSTATE(runState)
		status = self.__sendAndWaitFor_REPLY(msg)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to set run state")
		return True

	def loadCode(self, code):
		if not self.transceiver:
			return False
		msg = AwlSimMessage_LOAD_CODE(code)
		status = self.__sendAndWaitFor_REPLY(msg, 10.0)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to load code")
		return True

	def loadSymbolTable(self, symTabText):
		msg = AwlSimMessage_LOAD_SYMTAB(symTabText)
		status = self.__sendAndWaitFor_REPLY(msg)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to load symbol table")

	def loadHardwareModule(self, name, parameters={}):
		if not self.transceiver:
			return False
		msg = AwlSimMessage_LOAD_HW(name = name,
					    paramDict = parameters)
		status = self.__sendAndWaitFor_REPLY(msg)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to load hardware module")
		return True

	def __setOption(self, name, value, sync=True):
		if not self.transceiver:
			return False
		msg = AwlSimMessage_SET_OPT(name, str(value))
		if sync:
			status = self.__sendAndWaitFor_REPLY(msg)
			if status != AwlSimMessage_REPLY.STAT_OK:
				raise AwlSimError("AwlSimClient: Failed to set option '%s'" % name)
		else:
			self.transceiver.send(msg)
		return True

	def setLoglevel(self, level=Logging.LOG_INFO):
		Logging.setLoglevel(level)
		return self.__setOption("loglevel", int(level))

	def enableOBTempPresets(self, enable=True):
		return self.__setOption("ob_temp_presets", int(bool(enable)))

	def enableExtendedInsns(self, enable=True):
		return self.__setOption("extended_insns", int(bool(enable)))

	def setPeriodicDumpInterval(self, interval=0):
		return self.__setOption("periodic_dump_int", int(interval))

	def setCycleTimeLimit(self, seconds=5.0):
		return self.__setOption("cycle_time_limit", float(seconds))

	# Set instruction state dumping.
	# fromLine, toLine is the range of AWL line numbers for which
	# dumping is enabled.
	# If fromLine=0, dumping is disabled.
	def setInsnStateDump(self, fromLine=1, toLine=0x7FFFFFFF, sync=True):
		return self.__setOption("insn_state_dump",
					"%d-%d" % (fromLine, toLine),
					sync = sync)

	def getCpuSpecs(self):
		if not self.transceiver:
			return None
		msg = AwlSimMessage_GET_CPUSPECS()
		rxMsg = self.__sendAndWait(msg,
			lambda rxMsg: rxMsg.msgId == AwlSimMessage.MSG_ID_CPUSPECS)
		return rxMsg.cpuspecs

	def setCpuSpecs(self, cpuspecs):
		if not self.transceiver:
			return False
		msg = AwlSimMessage_CPUSPECS(cpuspecs)
		status = self.__sendAndWaitFor_REPLY(msg)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to set cpuspecs")
		return True

	# Set the memory areas we are interested in receiving
	# dumps for, in the server.
	# memAreas is a list of MemoryArea instances.
	# The repetitionFactor tells whether to
	#  - only run the request once (repetitionFactor=0)
	#  - repeat on n'th every cycle (repetitionFactor=n)
	# If sync is true, wait for a reply from the server.
	def setMemoryReadRequests(self, memAreas, repetitionFactor=0, sync=False):
		if not self.transceiver:
			return False
		msg = AwlSimMessage_REQ_MEMORY(0, repetitionFactor, memAreas)
		if sync:
			msg.flags |= msg.FLG_SYNC
			status = self.__sendAndWaitFor_REPLY(msg)
			if status != AwlSimMessage_REPLY.STAT_OK:
				raise AwlSimError("AwlSimClient: Failed to set "
					"memory read reqs")
		else:
			self.transceiver.send(msg)
		return True

	# Write memory areas in the server.
	# memAreas is a list of MemoryAreaData instances.
	# If sync is true, wait for a reply from the server.
	def writeMemory(self, memAreas, sync=False):
		if not self.transceiver:
			return False
		msg = AwlSimMessage_MEMORY(0, memAreas)
		if sync:
			msg.flags |= msg.FLG_SYNC
			status = self.__sendAndWaitFor_REPLY(msg)
			if status != AwlSimMessage_REPLY.STAT_OK:
				raise AwlSimError("AwlSimClient: Failed to write "
					"to memory")
		else:
			self.transceiver.send(msg)
		return True

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

from awlsim.coreserver.server import *
from awlsim.coreserver.messages import *

import sys
import socket
import errno


class AwlSimClient(object):
	def __init__(self):
		self.serverProcess = None
		self.socket = None
		self.transceiver = None

	def spawnServer(self, interpreter=None,
			listenHost=AwlSimServer.DEFAULT_HOST,
			listenPort=AwlSimServer.DEFAULT_PORT):
		"""Spawn a new AwlSim-core server process.
		interpreter -> The python interpreter to use.
		listenHost -> The hostname or IP address to listen on.
		listenPort -> The port to listen on.
		Returns the spawned process' PID."""

		if self.serverProcess:
			raise AwlSimError("Server already running")
		if not interpreter:
			interpreter = sys.executable
		assert(interpreter)

		self.serverProcess = AwlSimServer.start(listenHost = listenHost,
							listenPort = listenPort,
							forkInterpreter = interpreter)

	def connectToServer(self,
			    host=AwlSimServer.DEFAULT_HOST,
			    port=AwlSimServer.DEFAULT_PORT):
		"""Connect to a AwlSim-core server.
		host -> The hostname or IP address to connect to.
		port -> The port to connect to."""

		printInfo("AwlSimClient: Connecting to server '%s (port %d)'..." %\
			(host, port))
		try:
			family, socktype, proto, canonname, sockaddr =\
				socket.getaddrinfo(host, port, socket.AF_INET,
						   0, socket.SOL_TCP)[0]
			sock = socket.socket(family, socktype)
			count = 0
			while 1:
				try:
					sock.connect(sockaddr)
				except (OSError, socket.error) as e:
					if e.errno == errno.ECONNREFUSED:
						count += 1
						if count >= 100:
							raise AwlSimError("Timeout connecting "
								"to AwlSimServer %s (port %d)" %\
								(host, port))
						time.sleep(0.1)
						continue
					raise
				break
		except socket.error as e:
			raise AwlSimError("Failed to connect to AwlSimServer %s (port %d): %s" %\
				(host, port, str(e)))
		printInfo("AwlSimClient: Connected.")
		self.socket = sock
		self.transceiver = AwlSimMessageTransceiver(sock)
		self.lastReply = None

		# Ping the server
		try:
			self.transceiver.send(AwlSimMessage_PING())
			msg = self.transceiver.receiveBlocking(timeoutSec = 5.0)
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

		if self.socket:
			try:
				self.socket.shutdown(socket.SHUT_RDWR)
			except socket.error as e:
				pass
			try:
				self.socket.close()
			except socket.error as e:
				pass
			self.socket = None
		if self.serverProcess:
			self.serverProcess.terminate()
			self.serverProcess.wait()
			self.serverProcess = None

	def __rx_REPLY(self, msg):
		self.lastReply = msg

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

	__msgRxHandlers = {
		AwlSimMessage.MSG_ID_REPLY		: __rx_REPLY,
		AwlSimMessage.MSG_ID_EXCEPTION		: __rx_EXCEPTION,
		AwlSimMessage.MSG_ID_PING		: __rx_PING,
		AwlSimMessage.MSG_ID_PONG		: __rx_PONG,
		AwlSimMessage.MSG_ID_CPUDUMP		: __rx_CPUDUMP,
		AwlSimMessage.MSG_ID_MAINTREQ		: __rx_MAINTREQ,
	}

	def processMessages(self, blocking=False):
		try:
			if blocking:
				msg = self.transceiver.receiveBlocking()
			else:
				msg = self.transceiver.receive()
		except socket.error as e:
			if e.errno == errno.EAGAIN:
				return None
			host, port = self.socket.getpeername()
			raise AwlSimError("AwlSimClient: "
				"I/O error in connection to server '%s (port %d)':\n%s" %\
				(host, port, str(e)))
		except (AwlSimMessageTransceiver.RemoteEndDied, TransferError) as e:
			host, port = self.socket.getpeername()
			raise AwlSimError("AwlSimClient: "
				"Connection to server '%s:%s' died. "
				"Failed to receive message." %\
				(host, port))
		if not msg:
			return
		try:
			handler = self.__msgRxHandlers[msg.msgId]
		except KeyError:
			raise AwlSimError("AwlSimClient: Received unsupported "
				"message 0x%02X" % msg.msgId)
		handler(self, msg)

	def __sendAndWaitReply(self, msg, timeoutMs=10000):
		self.transceiver.send(msg)
		count = 0
		while count < timeoutMs:
			self.processMessages()
			reply = self.lastReply
			if reply and\
			   reply.inReplyToId == msg.msgId and\
			   reply.inReplyToSeq == msg.seq:
				self.lastReply = None
				return reply.status
			time.sleep(0.01)
			count += 10
		raise AwlSimError("AwlSimClient: Timeout waiting for server reply.")

	def setRunState(self, run=True):
		if run:
			runState = AwlSimMessage_RUNSTATE.STATE_RUN
		else:
			runState = AwlSimMessage_RUNSTATE.STATE_STOP
		msg = AwlSimMessage_RUNSTATE(runState)
		status = self.__sendAndWaitReply(msg)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to set run state")

	def loadCode(self, code):
		msg = AwlSimMessage_LOAD_CODE(code)
		status = self.__sendAndWaitReply(msg)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to load code")

	def loadHardwareModule(self, name, parameters={}):
		msg = AwlSimMessage_LOAD_HW(name = name,
					    paramDict = parameters)
		status = self.__sendAndWaitReply(msg)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to load hardware module")

	def __setOption(self, name, value):
		msg = AwlSimMessage_SET_OPT(name, value)
		status = self.__sendAndWaitReply(msg)
		if status != AwlSimMessage_REPLY.STAT_OK:
			raise AwlSimError("AwlSimClient: Failed to set option '%s'" % name)

	def setLoglevel(self, level=Logging.LOG_INFO):
		Logging.setLoglevel(level)
		self.__setOption("loglevel", str(int(level)))

	def enableOBTempPresets(self, enable=True):
		self.__setOption("ob_temp_presets", str(int(bool(enable))))

	def enableExtendedInsns(self, enable=True):
		self.__setOption("extended_insns", str(int(bool(enable))))

	def setPeriodicDumpInterval(self, interval=0):
		self.__setOption("periodic_dump_int", str(int(interval)))

	def setMnemonics(self, mnemonics=S7CPUSpecs.MNEMONICS_AUTO):
		self.__setOption("mnemonics", str(int(mnemonics)))

	def setNrAccus(self, nrAccus=2):
		self.__setOption("nr_accus", str(int(nrAccus)))

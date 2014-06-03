# -*- coding: utf-8 -*-
#
# AWL simulator - PLC core server
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

from awlsim.core.main import *
from awlsim.core.parser import *
from awlsim.core.cpuspecs import *

from awlsim.coreserver.messages import *
from awlsim.coreserver.subprocess_wrapper import *

import sys
import os
import distutils.spawn
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
	STATE_INIT	= EnumGen.item
	STATE_RUN	= EnumGen.item
	STATE_EXIT	= EnumGen.item
	EnumGen.end

	# Command mask bits
	CMDMSK_SHUTDOWN	= (1 << 0) # Allow shutdown command

	class Client(object):
		"""Client information."""

		def __init__(self, sock, peerInfoString):
			# Socket
			self.socket = sock
			self.transceiver = AwlSimMessageTransceiver(sock, peerInfoString)

			# CPU-dump
			self.dumpInterval = 0
			self.nextDump = 0
			# Instruction state dump
			self.insnStateDump_fromLine = 0
			self.insnStateDump_toLine = 0

			# Memory read requests
			self.memReadRequestMsg = None
			self.repetitionFactor = 0
			self.repetitionCount = 0

	@classmethod
	def getaddrinfo(cls, host, port):
		family, socktype = socket.AF_INET, socket.SOCK_STREAM
		if os.name == "posix" and host == "localhost" and False: #XXX disabled, for now
			# We are on posix OS. Instead of AF_INET on localhost,
			# we use Unix domain sockets.
			family, socktype = AF_UNIX, socket.SOCK_STREAM
			sockaddr = "/tmp/awlsim-server-%d.socket" % port
		else:
			family, socktype, proto, canonname, sockaddr =\
				socket.getaddrinfo(host, port, family, socktype)[0]
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
		except socket.error as e:
			result = False
		if sock:
			try:
				sock.shutdown(socket.SHUT_RDWR)
			except socket.error as e:
				pass
			try:
				sock.close()
			except socket.error as e:
				pass
		return result

	@classmethod
	def findExecutable(cls, executable):
		return distutils.spawn.find_executable(executable)

	@classmethod
	def start(cls, listenHost, listenPort,
		  forkInterpreter=None,
		  commandMask=CMDMSK_SHUTDOWN):
		"""Start a new server.
		If 'forkInterpreter' is not None, spawn a subprocess.
		If 'forkInterpreter' is None, run the server in this process."""

		# Prepare the environment for the server process.
		# Inherit from the starter and add awlsim specific variables.
		env = dict(os.environ)
		env[AwlSimServer.ENV_MAGIC]		= AwlSimServer.ENV_MAGIC
		env["AWLSIM_CORESERVER_HOST"]		= str(listenHost)
		env["AWLSIM_CORESERVER_PORT"]		= str(int(listenPort))
		env["AWLSIM_CORESERVER_LOGLEVEL"]	= str(Logging.getLoglevel())
		env["AWLSIM_CORESERVER_CMDMSK"]		= str(int(commandMask))

		if forkInterpreter is None:
			# Do not fork. Just run the server in this process.
			return cls._execute(env)
		else:
			# Fork a new interpreter process and run server.py as module.
			interp = cls.findExecutable(forkInterpreter)
			printInfo("Forking awlsim core server with interpreter '%s'" % interp)
			if not interp:
				raise AwlSimError("Failed to find interpreter "
						  "executable '%s'" % forkInterpreter)
			serverProcess = PopenWrapper([interp, "-m", "awlsim.coreserver.server"],
						     env = env,
						     shell = False)
			return serverProcess

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
				server.close()
		return retval

	def __init__(self):
		self.state = -1
		self.__setRunState(self.STATE_INIT)
		self.commandMask = 0
		self.sim = None
		self.socket = None
		self.unixSockPath = None
		self.clients = []

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
		Logging.setLoglevel(loglevel)

		if self.socket:
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

		self.run(host, port, commandMask)

	def __setRunState(self, runstate):
		if self.state == self.STATE_EXIT:
			# We are exiting. Cannot set another state.
			return
		self.state = runstate
		# Make a shortcut variable for RUN
		self.__running = bool(runstate == self.STATE_RUN)

		self.__insnSerial = 0

	def __rebuildSelectReadList(self):
		rlist = [ self.socket ]
		rlist.extend(client.transceiver.sock for client in self.clients)
		self.__selectRlist = rlist

	def __cpuBlockExitCallback(self, userData):
		now = self.sim.cpu.now
		if any(c.dumpInterval and now >= c.nextDump for c in self.clients):
			msg = AwlSimMessage_CPUDUMP(str(self.sim.cpu))
			for client in self.clients:
				if client.dumpInterval and now >= client.nextDump:
					client.nextDump = now + client.dumpInterval / 1000.0
					client.transceiver.send(msg)

	def __cpuPostInsnCallback(self, userData):
		cpu = self.sim.cpu
		insn = cpu.getCurrentInsn()
		if not insn:
			return
		lineNr, msg = insn.getLineNr(), None
		for client in self.clients:
			if client.insnStateDump_fromLine == 0 or\
			   lineNr < client.insnStateDump_fromLine or\
			   lineNr > client.insnStateDump_toLine:
				continue
			if not msg:
				msg = AwlSimMessage_INSNSTATE(
					lineNr & 0xFFFFFFFF,
					self.__insnSerial,
					0,
					cpu.statusWord.getWord(),
					cpu.accu1.get(),
					cpu.accu2.get(),
					cpu.ar1.get(),
					cpu.ar2.get(),
					cpu.dbRegister.index & 0xFFFF,
					cpu.diRegister.index & 0xFFFF)
			client.transceiver.send(msg)
		self.__insnSerial += 1

	def __cpuCycleExitCallback(self, userData):
		self.__insnSerial = 0

	def __updateCpuBlockExitCallback(self):
		if any(c.dumpInterval for c in self.clients):
			self.sim.cpu.setBlockExitCallback(self.__cpuBlockExitCallback, None)
		else:
			self.sim.cpu.setBlockExitCallback(None)

	def __updateCpuPostInsnCallback(self):
		if any(c.insnStateDump_fromLine != 0 for c in self.clients):
			self.sim.cpu.setPostInsnCallback(self.__cpuPostInsnCallback, None)
		else:
			self.sim.cpu.setPostInsnCallback(None)

	def __updateCpuCycleExitCallback(self):
		if any(c.insnStateDump_fromLine != 0 for c in self.clients):
			self.sim.cpu.setCycleExitCallback(self.__cpuCycleExitCallback, None)
		else:
			self.sim.cpu.setCycleExitCallback(None)

	def __rx_PING(self, client, msg):
		client.transceiver.send(AwlSimMessage_PONG())

	def __rx_PONG(self, client, msg):
		printInfo("AwlSimServer: Received PONG")

	def __rx_RESET(self, client, msg):
		status = AwlSimMessage_REPLY.STAT_OK
		self.__setRunState(self.STATE_INIT)
		self.sim.reset()
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_SHUTDOWN(self, client, msg):
		status = AwlSimMessage_REPLY.STAT_FAIL
		if self.commandMask & AwlSimServer.CMDMSK_SHUTDOWN:
			printInfo("AwlSimServer: Exiting due to shutdown command")
			self.__setRunState(self.STATE_EXIT)
			status = AwlSimMessage_REPLY.STAT_OK
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_RUNSTATE(self, client, msg):
		status = AwlSimMessage_REPLY.STAT_OK
		if msg.runState == msg.STATE_STOP:
			self.__setRunState(self.STATE_INIT)
		elif msg.runState == msg.STATE_RUN:
			self.sim.startup()
			self.__setRunState(self.STATE_RUN)
		else:
			status = AwlSimMessage_REPLY.STAT_FAIL
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_LOAD_CODE(self, client, msg):
		status = AwlSimMessage_REPLY.STAT_OK
		parser = AwlParser()
		parser.parseData(msg.code)
		self.__setRunState(self.STATE_INIT)
		self.sim.load(parser.getParseTree())
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_LOAD_SYMTAB(self, client, msg):
		status = AwlSimMessage_REPLY.STAT_OK
		symbolTable = SymTabParser.parseData(msg.symTabText,
						     autodetectFormat = True,
						     mnemonics = self.sim.cpu.getSpecs().getMnemonics())
		self.__setRunState(self.STATE_INIT)
		self.sim.loadSymbolTable(symbolTable)
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_LOAD_HW(self, client, msg):
		status = AwlSimMessage_REPLY.STAT_OK
		printInfo("Loading hardware module '%s'..." % msg.name)
		hwClass = self.sim.loadHardwareModule(msg.name)
		self.sim.registerHardwareClass(hwClass = hwClass,
					       parameters = msg.paramDict)
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_SET_OPT(self, client, msg):
		status = AwlSimMessage_REPLY.STAT_OK

		if msg.name == "loglevel":
			Logging.setLoglevel(msg.getIntValue())
		elif msg.name == "ob_temp_presets":
			self.sim.cpu.enableObTempPresets(msg.getBoolValue())
		elif msg.name == "extended_insns":
			self.sim.cpu.enableExtendedInsns(msg.getBoolValue())
		elif msg.name == "periodic_dump_int":
			client.dumpInterval = msg.getIntValue()
			if client.dumpInterval:
				client.nextDump = self.sim.cpu.now
			else:
				client.nextDump = None
			self.__updateCpuBlockExitCallback()
		elif msg.name == "cycle_time_limit":
			self.sim.cpu.setCycleTimeLimit(msg.getFloatValue())
		elif msg.name == "insn_state_dump":
			val = msg.getStrValue().split("-")
			try:
				if len(val) != 2:
					raise ValueError
				fromLine = int(val[0])
				toLine = int(val[1])
			except ValueError as e:
				raise AwlSimError("insn_state_dump: invalid value")
			client.insnStateDump_fromLine = fromLine
			client.insnStateDump_toLine = toLine
			self.__updateCpuPostInsnCallback()
			self.__updateCpuCycleExitCallback()
		else:
			status = AwlSimMessage_REPLY.STAT_FAIL

		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_GET_CPUSPECS(self, client, msg):
		reply = AwlSimMessage_CPUSPECS(self.sim.cpu.getSpecs())
		client.transceiver.send(reply)

	def __rx_CPUSPECS(self, client, msg):
		status = AwlSimMessage_REPLY.STAT_OK
		self.sim.cpu.getSpecs().assignFrom(msg.cpuspecs)
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_REQ_MEMORY(self, client, msg):
		client.memReadRequestMsg = AwlSimMessage_MEMORY(0, msg.memAreas)
		client.repetitionFactor = msg.repetitionFactor
		client.repetitionCount = client.repetitionFactor
		if msg.flags & msg.FLG_SYNC:
			client.transceiver.send(AwlSimMessage_REPLY.make(
				msg, AwlSimMessage_REPLY.STAT_OK)
			)

	def __rx_MEMORY(self, client, msg):
		cpu = self.sim.cpu
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

	__msgRxHandlers = {
		AwlSimMessage.MSG_ID_PING		: __rx_PING,
		AwlSimMessage.MSG_ID_PONG		: __rx_PONG,
		AwlSimMessage.MSG_ID_RESET		: __rx_RESET,
		AwlSimMessage.MSG_ID_SHUTDOWN		: __rx_SHUTDOWN,
		AwlSimMessage.MSG_ID_RUNSTATE		: __rx_RUNSTATE,
		AwlSimMessage.MSG_ID_LOAD_CODE		: __rx_LOAD_CODE,
		AwlSimMessage.MSG_ID_LOAD_SYMTAB	: __rx_LOAD_SYMTAB,
		AwlSimMessage.MSG_ID_LOAD_HW		: __rx_LOAD_HW,
		AwlSimMessage.MSG_ID_SET_OPT		: __rx_SET_OPT,
		AwlSimMessage.MSG_ID_GET_CPUSPECS	: __rx_GET_CPUSPECS,
		AwlSimMessage.MSG_ID_CPUSPECS		: __rx_CPUSPECS,
		AwlSimMessage.MSG_ID_REQ_MEMORY		: __rx_REQ_MEMORY,
		AwlSimMessage.MSG_ID_MEMORY		: __rx_MEMORY,
	}

	def __handleClientComm(self, client):
		try:
			msg = client.transceiver.receive(0.0)
		except AwlSimMessageTransceiver.RemoteEndDied as e:
			printInfo("AwlSimServer: Client '%s' died" % client.transceiver.peerInfoString)
			self.__clientRemove(client)
			return
		except (TransferError, socket.error) as e:
			printInfo("AwlSimServer: Client '%s' data "
				"transfer error:\n%s" %\
				(client.transceiver.peerInfoString, str(e)))
			return
		if not msg:
			return
		try:
			handler = self.__msgRxHandlers[msg.msgId]
		except KeyError:
			printInfo("AwlSimServer: Received unsupported "
				"message 0x%02X" % msg.msgId)
			return
		handler(self, client, msg)

	def __handleCommunication(self):
		while 1:
			try:
				rlist, wlist, xlist = select.select(self.__selectRlist, [], [], 0)
			except Exception as e:
				raise AwlSimError("AwlSimServer: Communication error. "
					"'select' failed")
			if not rlist:
				break
			if self.socket in rlist:
				rlist.remove(self.socket)
				self.__accept()
			for sock in rlist:
				client = [ c for c in self.clients if c.socket is sock ][0]
				self.__handleClientComm(client)

	def __handleMemReadReqs(self):
		for client in self.clients:
			if not client.memReadRequestMsg:
				continue
			client.repetitionCount -= 1
			if client.repetitionCount <= 0:
				cpu, memAreas = self.sim.cpu, client.memReadRequestMsg.memAreas
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
				client.transceiver.send(client.memReadRequestMsg)
				client.repetitionCount = client.repetitionFactor
				if not client.repetitionFactor:
					self.memReadRequestMsg = None

	def run(self, host, port, commandMask):
		"""Run the server on 'host':'port'."""

		self.commandMask = commandMask

		self.__listen(host, port)
		self.__rebuildSelectReadList()

		self.sim = AwlSim()
		nextComm = 0.0

		while self.state != self.STATE_EXIT:
			try:
				sim = self.sim

				if self.state == self.STATE_INIT:
					while self.state == self.STATE_INIT:
						self.__handleCommunication()
						time.sleep(0.01)
					continue

				if self.state == self.STATE_RUN:
					while self.__running:
						sim.runCycle()
						self.__handleMemReadReqs()
						self.__handleCommunication()
					continue

			except (AwlSimError, AwlParserError) as e:
				msg = AwlSimMessage_EXCEPTION(e.getReport())
				for client in self.clients:
					try:
						client.transceiver.send(msg)
					except TransferError as e:
						printError("AwlSimServer: Failed to forward "
							   "exception to client.")
				self.__setRunState(self.STATE_INIT)
			except MaintenanceRequest as e:
				try:
					if self.clients:
						# Forward it to the first client
						msg = AwlSimMessage_MAINTREQ(e.requestType)
						self.clients[0].transceiver.send(msg)
				except TransferError as e:
					pass
			except TransferError as e:
				printError("AwlSimServer: Transfer error: " + str(e))
				self.__setRunState(self.STATE_INIT)

	def __listen(self, host, port):
		"""Listen on 'host':'port'."""

		self.close()
		try:
			family, socktype, sockaddr = AwlSimServer.getaddrinfo(host, port)
			if family == AF_UNIX:
				self.unixSockPath = sockaddr
				readableSockaddr = sockaddr
			else:
				readableSockaddr = "%s:%d" % (sockaddr[0], sockaddr[1])
			printInfo("AwlSimServer: Listening on %s..." % readableSockaddr)
			sock = socket.socket(family, socktype)
			sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			sock.setblocking(False)
			sock.bind(sockaddr)
			sock.listen(5)
		except socket.error as e:
			raise AwlSimError("AwlSimServer: Failed to create server "
				"socket: " + str(e))
		self.socket = sock

	def __accept(self):
		"""Accept a client connection.
		Returns the Client instance or None."""

		if not self.socket:
			raise AwlSimError("AwlSimServer: No server socket")

		try:
			clientSock, addrInfo = self.socket.accept()
			if self.unixSockPath:
				peerInfoString = self.unixSockPath
			else:
				peerInfoString = "%s:%d" % addrInfo[:2]
		except (socket.error, BlockingIOError) as e:
			if isinstance(e, BlockingIOError) or\
			   e.errno == errno.EWOULDBLOCK or\
			   e.errno == errno.EAGAIN:
				return None
			raise AwlSimError("AwlSimServer: accept() failed: %s" % str(e))
		printInfo("AwlSimServer: Client '%s' connected" % peerInfoString)

		client = self.Client(clientSock, peerInfoString)
		self.__clientAdd(client)

		return client

	def __clientAdd(self, client):
		self.clients.append(client)
		self.__rebuildSelectReadList()

	def __clientRemove(self, client):
		self.clients.remove(client)
		self.__rebuildSelectReadList()

	def close(self):
		"""Closes all client sockets and the main socket."""

		if self.socket:
			printInfo("AwlSimServer: Shutting down.")

		if self.sim:
			self.sim.shutdown()
			self.sim = None

		for client in self.clients:
			client.transceiver.shutdown()
			client.transceiver = None
			client.socket = None
		self.clients = []

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
		if self.unixSockPath:
			try:
				os.unlink(self.unixSockPath)
			except OSError as e:
				pass
			self.unixSockPath = None

	def signalHandler(self, sig, frame):
		printInfo("AwlSimServer: Received signal %d" % sig)
		if sig in (signal.SIGTERM, signal.SIGINT):
			self.__setRunState(self.STATE_EXIT)

if __name__ == "__main__":
	# Run a server process.
	# Parameters are passed via environment.
	sys.exit(AwlSimServer._execute())

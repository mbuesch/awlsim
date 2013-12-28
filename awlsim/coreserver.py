# -*- coding: utf-8 -*-
#
# AWL simulator - PLC core server
#
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
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

from awlsim.main import *
from awlsim.parser import *
from awlsim.cpuspecs import *

import sys
import os
import distutils.spawn
import subprocess
import socket
import select
import errno
import signal
import struct


_strLenStruct = struct.Struct(">H")

def packString(string):
	try:
		data = string.encode("utf-8", "strict")
		return _strLenStruct.pack(len(data)) + data
	except (UnicodeError, struct.error) as e:
		raise ValueError

def unpackString(data, offset = 0):
	try:
		(length, ) = _strLenStruct.unpack_from(data, offset)
		strBytes = data[offset + _strLenStruct.size :
				offset + _strLenStruct.size + length]
		if len(strBytes) != length:
			raise ValueError
		return (strBytes.decode("utf-8", "strict"),
			_strLenStruct.size + length)
	except (UnicodeError, struct.error) as e:
		raise ValueError

class TransferError(Exception):
	pass

class AwlSimMessage(object):
	# Header format:
	#	Magic (16 bit)
	#	Message ID (16 bit)
	#	Sequence count (16 bit)
	#	Reserved (16 bit)
	#	Payload length (32 bit)
	#	Payload (optional)
	hdrStruct = struct.Struct(">HHHHI")

	HDR_MAGIC		= 0x5710
	HDR_LENGTH		= hdrStruct.size

	enum.start
	MSG_ID_REPLY		= enum.item # Generic status reply
	MSG_ID_EXCEPTION	= enum.item
	MSG_ID_PING		= enum.item
	MSG_ID_PONG		= enum.item
	MSG_ID_LOAD_CODE	= enum.item
	MSG_ID_LOAD_HW		= enum.item
	MSG_ID_SET_OPT		= enum.item
	MSG_ID_CPUDUMP		= enum.item
	enum.end

	def __init__(self, msgId, seq=0):
		self.msgId = msgId
		self.seq = seq

	def toBytes(self, payloadLength=0):
		return self.hdrStruct.pack(self.HDR_MAGIC,
					   self.msgId,
					   self.seq,
					   0,
					   payloadLength)

	@classmethod
	def fromBytes(cls, payload):
		return cls()

class AwlSimMessage_REPLY(AwlSimMessage):
	enum.start
	STAT_OK		= enum.item
	STAT_FAIL	= enum.item
	enum.end

	plStruct = struct.Struct(">HHH")

	@classmethod
	def make(cls, inReplyToMsg, status):
		return cls(inReplyToMsg.msgId, inReplyToMsg.seq, status)

	def __init__(self, inReplyToId, inReplyToSeq, status):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_REPLY)
		self.inReplyToId = inReplyToId
		self.inReplyToSeq = inReplyToSeq
		self.status = status

	def toBytes(self):
		pl = self.plStruct.pack(self.inReplyToId,
					self.inReplyToSeq,
					self.status)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			inReplyToId, inReplyToSeq, status =\
				cls.plStruct.unpack(payload)
		except struct.error as e:
			raise TransferError("REPLY: Invalid data format")
		return cls(inReplyToId, inReplyToSeq, status)

class AwlSimMessage_PING(AwlSimMessage):
	def __init__(self):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_PING)

class AwlSimMessage_PONG(AwlSimMessage):
	def __init__(self):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_PONG)

class AwlSimMessage_EXCEPTION(AwlSimMessage):
	def __init__(self, exceptionText):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_EXCEPTION)
		self.exceptionText = exceptionText

	def toBytes(self):
		try:
			textBytes = self.exceptionText.encode()
			return AwlSimMessage.toBytes(self, len(textBytes)) + textBytes
		except UnicodeError:
			raise TransferError("EXCEPTION: Unicode error")

	@classmethod
	def fromBytes(cls, payload):
		try:
			text = payload.decode()
		except UnicodeError:
			raise TransferError("EXCEPTION: Unicode error")
		return cls(text)

class AwlSimMessage_LOAD_CODE(AwlSimMessage):
	def __init__(self, code):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_LOAD_CODE)
		self.code = code

	def toBytes(self):
		try:
			code = self.code.encode()
			return AwlSimMessage.toBytes(self, len(code)) + code
		except UnicodeError:
			raise TransferError("LOAD_CODE: Unicode error")

	@classmethod
	def fromBytes(cls, payload):
		try:
			code = payload.decode()
		except UnicodeError:
			raise TransferError("LOAD_CODE: Unicode error")
		return cls(code)

class AwlSimMessage_LOAD_HW(AwlSimMessage):
	def __init__(self, name, paramDict):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_LOAD_HW)
		self.name = name
		self.paramDict = paramDict

	def toBytes(self):
		payload = b""
		try:
			payload += packString(self.name)
			for pname, pval in self.paramDict.items():
				payload += packString(pname)
				payload += packString(pval)
			return AwlSimMessage.toBytes(self, len(payload)) + payload
		except (ValueError) as e:
			raise TransferError("LOAD_HW: Invalid data format")

	@classmethod
	def fromBytes(cls, payload):
		paramDict = {}
		offset = 0
		try:
			name, count = unpackString(payload, offset)
			offset += count
			while offset < len(payload):
				pname, count = unpackString(payload, offset)
				offset += count
				pval, count = unpackString(payload, offset)
				offset += count
				paramDict[pname] = pval
		except (ValueError) as e:
			raise TransferError("LOAD_HW: Invalid data format")
		return cls(name = name, paramDict = paramDict)

class AwlSimMessage_SET_OPT(AwlSimMessage):
	def __init__(self, name, value):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_SET_OPT)
		self.name = name
		self.value = value

	def getIntValue(self):
		try:
			return int(self.value)
		except ValueError as e:
			raise AwlSimError("SET_OPT: Value is not an integer")

	def getBoolValue(self):
		try:
			return bool(self.value)
		except ValueError as e:
			raise AwlSimError("SET_OPT: Value is not a boolean")

	def toBytes(self):
		try:
			payload = packString(self.name)
			payload += packString(self.value)
		except ValueError as e:
			raise TransferError("SET_OPT: Invalid data format")
		return AwlSimMessage.toBytes(self, len(payload)) + payload

	@classmethod
	def fromBytes(cls, payload):
		try:
			offset = 0
			name, count = unpackString(payload, offset)
			offset += count
			value, count = unpackString(payload, offset)
			offset += count
		except ValueError as e:
			raise TransferError("SET_OPT: Invalid data format")
		return cls(name = name, value = value)

class AwlSimMessage_CPUDUMP(AwlSimMessage):
	def __init__(self, dumpText):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_CPUDUMP)
		self.dumpText = dumpText

	def toBytes(self):
		try:
			dumpBytes = self.dumpText.encode()
			return AwlSimMessage.toBytes(self, len(dumpBytes)) + dumpBytes
		except UnicodeError:
			raise TransferError("CPUDUMP: Unicode error")

	@classmethod
	def fromBytes(cls, payload):
		try:
			dumpText = payload.decode()
		except UnicodeError:
			raise TransferError("CPUDUMP: Unicode error")
		return cls(dumpText)

class AwlSimMessageTransceiver(object):
	class RemoteEndDied(Exception): pass

	id2class = {
		AwlSimMessage.MSG_ID_REPLY		: AwlSimMessage_REPLY,
		AwlSimMessage.MSG_ID_EXCEPTION		: AwlSimMessage_EXCEPTION,
		AwlSimMessage.MSG_ID_PING		: AwlSimMessage_PING,
		AwlSimMessage.MSG_ID_PONG		: AwlSimMessage_PONG,
		AwlSimMessage.MSG_ID_LOAD_CODE		: AwlSimMessage_LOAD_CODE,
		AwlSimMessage.MSG_ID_LOAD_HW		: AwlSimMessage_LOAD_HW,
		AwlSimMessage.MSG_ID_SET_OPT		: AwlSimMessage_SET_OPT,
		AwlSimMessage.MSG_ID_CPUDUMP		: AwlSimMessage_CPUDUMP,
	}

	def __init__(self, sock):
		self.sock = sock

		# Transmit status
		self.txSeqCount = 0

		# Receive buffer
		self.buf = b""
		self.msgId = None
		self.seq = None
		self.payloadLen = None

		self.sock.setblocking(False)

	def send(self, msg):
		msg.seq = self.txSeqCount
		self.txSeqCount = (self.txSeqCount + 1) & 0xFFFF

		offset, data = 0, msg.toBytes()
		while offset < len(data):
			try:
				offset += self.sock.send(data[offset : ])
			except socket.error as e:
				if e.errno != errno.EAGAIN:
					raise TransferError(str(e))

	def receive(self):
		hdrLen = AwlSimMessage.HDR_LENGTH
		if len(self.buf) < hdrLen:
			data = self.sock.recv(hdrLen - len(self.buf))
			if not data:
				# The remote end closed the connection
				raise self.RemoteEndDied()
			self.buf += data
			if len(self.buf) < hdrLen:
				return None
			try:
				magic, self.msgId, self.seq, _reserved, self.payloadLen =\
					AwlSimMessage.hdrStruct.unpack(self.buf)
			except struct.error as e:
				raise AwlSimError("Received message with invalid "
					"header format.")
			if magic != AwlSimMessage.HDR_MAGIC:
				raise AwlSimError("Received message with invalid "
					"magic value (was 0x%04X, expected 0x%04X)." %\
					(magic, AwlSimMessage.HDR_MAGIC))
			if self.payloadLen:
				return None
		if len(self.buf) < hdrLen + self.payloadLen:
			data = self.sock.recv(hdrLen + self.payloadLen - len(self.buf))
			if not data:
				# The remote end closed the connection
				raise self.RemoteEndDied()
			self.buf += data
			if len(self.buf) < hdrLen + self.payloadLen:
				return None
		try:
			cls = self.id2class[self.msgId]
		except KeyError:
			raise AwlSimError("Received unknown message: 0x%04X" %\
				self.msgId)
		msg = cls.fromBytes(self.buf[hdrLen : ])
		msg.seq = self.seq
		self.buf, self.msgId, self.seq, self.payloadLen = b"", None, None, None
		return msg

	def receiveBlocking(self):
		try:
			self.sock.setblocking(True)
			#TODO timeout
			msg = self.receive()
		finally:
			self.sock.setblocking(False)
		return msg

class AwlSimServer(object):
	DEFAULT_HOST	= "localhost"
	DEFAULT_PORT	= 4151

	ENV_MAGIC	= "AWLSIM_CORESERVER_MAGIC"

	enum.start
	STATE_INIT	= enum.item
	STATE_RUN	= enum.item
	STATE_EXIT	= enum.item
	enum.end

	class Client(object):
		"""Client information."""

		def __init__(self, sock):
			self.socket = sock
			self.transceiver = AwlSimMessageTransceiver(sock)
			self.dumpInterval = 0
			self.nextDump = None

	@classmethod
	def start(cls, listenHost, listenPort, forkInterpreter=None):
		"""Start a new server.
		If 'forkInterpreter' is not None, spawn a subprocess.
		If 'forkInterpreter' is None, run the server in this process."""

		environment = {
			AwlSimServer.ENV_MAGIC		: AwlSimServer.ENV_MAGIC,
			"AWLSIM_CORESERVER_HOST"	: str(listenHost),
			"AWLSIM_CORESERVER_PORT"	: str(listenPort),
		}

		if forkInterpreter is None:
			return cls._execute(environment)
		else:
			interp = distutils.spawn.find_executable(forkInterpreter)
			if not interp:
				raise AwlSimError("Failed to find interpreter "
						  "executable '%s'" % forkInterpreter)
			serverProcess = subprocess.Popen([interp, "-m", "awlsim.coreserver"],
							 env = environment,
							 shell = False)
			return serverProcess

	@classmethod
	def _execute(cls, env=None):
		"""Execute the server process.
		Returns the exit() return value."""

		server, retval = None, 0
		try:
			server = AwlSimServer()
			for sig in (signal.SIGTERM, signal.SIGINT):
				signal.signal(sig, server.signalHandler)
			server.runFromEnvironment(env)
		except AwlSimError as e:
			print(e.getReport())
			retval = 1
		except KeyboardInterrupt:
			print("Interrupted.")
		finally:
			if server:
				server.close()
		return retval

	def __init__(self):
		self.state = self.STATE_INIT
		self.sim = None
		self.socket = None
		self.clients = []

	def runFromEnvironment(self, env=None):
		"""Run the server.
		Configuration is passed via environment variables in 'env'.
		If 'env' is not passed, os.environ is used."""

		if not env:
			env = dict(os.environ)

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

		self.run(host, port)

	def __rebuildSelectReadList(self):
		rlist = [ self.socket ]
		rlist.extend(client.socket for client in self.clients)
		self.__selectRlist = rlist

	def __cpuBlockExitCallback(self, userData):
		now = self.sim.cpu.now
		if any(now >= c.nextDump for c in self.clients):
			msg = AwlSimMessage_CPUDUMP(str(self.sim.cpu))
			for client in self.clients:
				if now >= client.nextDump:
					client.nextDump = now + client.dumpInterval / 1000.0
					client.transceiver.send(msg)

	def __updateCpuBlockExitCallback(self):
		if any(c.nextDump is not None for c in self.clients):
			self.sim.cpu.setBlockExitCallback(self.__cpuBlockExitCallback, None)
		else:
			self.sim.cpu.setBlockExitCallback(None)

	def __rx_PING(self, client, msg):
		client.transceiver.send(AwlSimMessage_PONG())

	def __rx_PONG(self, client, msg):
		printInfo("AwlSimServer: Received PONG")

	def __rx_LOAD_CODE(self, client, msg):
		status = AwlSimMessage_REPLY.STAT_OK
		parser = AwlParser()
		parser.parseData(msg.code)
		self.sim.load(parser.getParseTree())
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))
		self.state = self.STATE_RUN

	def __rx_LOAD_HW(self, client, msg):
		status = AwlSimMessage_REPLY.STAT_OK
		printInfo("Loading hardware module '%s'..." % msg.name)
		hwClass = self.sim.loadHardwareModule(msg.name)
		self.sim.registerHardwareClass(hwClass = hwClass,
					       parameters = msg.paramDict)
		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	def __rx_SET_OPT(self, client, msg):
		status = AwlSimMessage_REPLY.STAT_OK

		if msg.name == "ob_temp_presets":
			pass#TODO
		elif msg.name == "extended_insns":
			pass#TODO
		elif msg.name == "periodic_dump_int":
			client.dumpInterval = msg.getIntValue()
			if client.dumpInterval:
				client.nextDump = self.sim.cpu.now
			else:
				client.nextDump = None
			self.__updateCpuBlockExitCallback()
		elif msg.name == "mnemonics":
			pass#TODO
		elif msg.name == "nr_accus":
			pass#TODO
		else:
			status = AwlSimMessage_REPLY.STAT_FAIL

		client.transceiver.send(AwlSimMessage_REPLY.make(msg, status))

	__msgRxHandlers = {
		AwlSimMessage.MSG_ID_PING		: __rx_PING,
		AwlSimMessage.MSG_ID_PONG		: __rx_PONG,
		AwlSimMessage.MSG_ID_LOAD_CODE		: __rx_LOAD_CODE,
		AwlSimMessage.MSG_ID_LOAD_HW		: __rx_LOAD_HW,
		AwlSimMessage.MSG_ID_SET_OPT		: __rx_SET_OPT,
	}

	def __handleClientComm(self, client):
		try:
			msg = client.transceiver.receive()
		except AwlSimMessageTransceiver.RemoteEndDied as e:
			host, port = client.socket.getpeername()
			printInfo("AwlSimServer: Client '%s:%d' died" %\
				(host, port))
			self.__clientRemove(client)
			return
		except (TransferError, socket.error) as e:
			host, port = client.socket.getpeername()
			printInfo("AwlSimServer: Client '%s:%d' data "
				"transfer error:\n" %\
				(host, port, str(e)))
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

	def run(self, host, port):
		"""Run the server on 'host':'port'."""

		self.__listen(host, port)
		self.__rebuildSelectReadList()

		self.sim = sim = AwlSim()
		nextComm = 0.0

		while self.state != self.STATE_EXIT:
			try:
				if self.state == self.STATE_RUN:
					if self.sim.cpu.now >= nextComm:
						nextComm = self.sim.cpu.now + 0.01
						self.__handleCommunication()
					sim.runCycle()
				else:
					self.__handleCommunication()
					time.sleep(0.01)
			except (AwlSimError, AwlParserError) as e:
				msg = AwlSimMessage_EXCEPTION(e.getReport())
				for client in self.clients:
					client.transceiver.send(msg)
				self.state = self.STATE_INIT
			except TransferError as e:
				printError("AwlSimServer: Transfer error: " + str(e))
				self.state = self.STATE_INIT

	def __listen(self, host, port):
		"""Listen on 'host':'port'."""

		self.close()
		printInfo("AwlSimServer: Listening on %s:%d..." % (host, port))
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			sock.setblocking(False)
			sock.bind((host, port))
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
		except socket.error as e:
			if e.errno == errno.EWOULDBLOCK or\
			   e.errno == errno.EAGAIN:
				return None
			raise AwlSimError("AwlSimServer: accept() failed: %s" % str(e))
		host, port = addrInfo
		printInfo("AwlSimServer: Client '%s:%d' connected" % (host, port))

		client = self.Client(clientSock)
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
			try:
				client.socket.shutdown(socket.SHUT_RDWR)
			except socket.error as e:
				pass
			try:
				client.socket.close()
			except socket.error as e:
				pass
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

	def signalHandler(self, sig, frame):
		printInfo("AwlSimServer: Received signal %d" % sig)
		if sig in (signal.SIGTERM, signal.SIGINT):
			self.state = self.STATE_EXIT

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

		printInfo("AwlSimClient: Connecting to server %s:%d..." %\
			(host, port))
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			count = 0
			while 1:
				try:
					sock.connect((host, port))
				except ConnectionRefusedError as e:
					count += 1
					if count >= 100:
						raise AwlSimError("Timeout connecting "
							"to AwlSimServer %s:%d" %\
							(host, port))
					time.sleep(0.1)
					continue
				break
		except socket.error as e:
			raise AwlSimError("Failed to connect to AwlSimServer %s:%d: %s" %\
				(host, port, str(e)))
		printInfo("AwlSimClient: Connected.")
		self.socket = sock
		self.transceiver = AwlSimMessageTransceiver(sock)
		self.lastReply = None

		# Ping the server
		try:
			self.transceiver.send(AwlSimMessage_PING())
			msg = self.transceiver.receiveBlocking()
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

	__msgRxHandlers = {
		AwlSimMessage.MSG_ID_REPLY		: __rx_REPLY,
		AwlSimMessage.MSG_ID_EXCEPTION		: __rx_EXCEPTION,
		AwlSimMessage.MSG_ID_PING		: __rx_PING,
		AwlSimMessage.MSG_ID_PONG		: __rx_PONG,
		AwlSimMessage.MSG_ID_CPUDUMP		: __rx_CPUDUMP,
	}

	def processMessages(self):
		try:
			msg = self.transceiver.receive()
		except socket.error as e:
			if e.errno == errno.EAGAIN:
				return None
			host, port = self.socket.getpeername()
			raise AwlSimError("AwlSimClient: "
				"I/O error in connection to server '%s:%d':\n%s" %\
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
			raise AwlSimError("AwlSimClient: Receive unsupported "
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

if __name__ == "__main__":
	# Run a server process.
	# Parameters are passed via environment.
	sys.exit(AwlSimServer._execute())

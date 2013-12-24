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

import sys
import os
import subprocess
import socket
import select
import errno
import signal
import struct


class TransferError(Exception):
	pass

class AwlSimMessage(object):
	hdrStruct = struct.Struct(">HHI")

	HDR_MAGIC		= 0x5710
	HDR_LENGTH		= hdrStruct.size

	enum.start
	MSG_ID_PING		= enum.item
	MSG_ID_PONG		= enum.item
	MSG_ID_LOAD_CODE	= enum.item
	MSG_ID_LOAD_HW		= enum.item
	MSG_ID_SET_OPT		= enum.item
	MSG_ID_GET_CPUDUMP	= enum.item
	MSG_ID_CPUDUMP		= enum.item
	enum.end

	def __init__(self, msgId):
		self.msgId = msgId

	def toBytes(self, payloadLength=0):
		return self.hdrStruct.pack(self.HDR_MAGIC,
					   self.msgId,
					   payloadLength)

	@classmethod
	def fromBytes(cls, payload):
		return cls()

	def send(self, sock):
		sock.sendall(self.toBytes())

class AwlSimMessage_PING(AwlSimMessage):
	def __init__(self):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_PING)

class AwlSimMessage_PONG(AwlSimMessage):
	def __init__(self):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_PONG)

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
	def __init__(self):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_LOAD_HW)

	def toBytes(self):
		pass#TODO

	@classmethod
	def fromBytes(cls, payload):
		pass#TODO

class AwlSimMessage_SET_OPT(AwlSimMessage):
	def __init__(self):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_SET_OPT)

	def toBytes(self):
		pass#TODO

	@classmethod
	def fromBytes(cls, payload):
		pass#TODO

class AwlSimMessage_GET_CPUDUMP(AwlSimMessage):
	def __init__(self):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_GET_CPUDUMP)

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

class AwlSimMessageReceiver(object):
	class RemoteEndDied(Exception): pass

	id2class = {
		AwlSimMessage.MSG_ID_PING		: AwlSimMessage_PING,
		AwlSimMessage.MSG_ID_PONG		: AwlSimMessage_PONG,
		AwlSimMessage.MSG_ID_LOAD_CODE		: AwlSimMessage_LOAD_CODE,
		AwlSimMessage.MSG_ID_LOAD_HW		: AwlSimMessage_LOAD_HW,
		AwlSimMessage.MSG_ID_SET_OPT		: AwlSimMessage_SET_OPT,
		AwlSimMessage.MSG_ID_GET_CPUDUMP	: AwlSimMessage_GET_CPUDUMP,
		AwlSimMessage.MSG_ID_CPUDUMP		: AwlSimMessage_CPUDUMP,
	}

	def __init__(self, sock):
		self.sock = sock
		self.buf = b""
		self.msgId = None
		self.payloadLen = None

		self.sock.setblocking(False)

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
			magic, self.msgId, self.payloadLen =\
				AwlSimMessage.hdrStruct.unpack(self.buf)
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
		self.buf, self.msgId, self.payloadLen = b"", None, None
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
	ENV_MAGIC	= "AWLSIM_CORESERVER_MAGIC"
	DEFAULT_PORT	= 4151

	enum.start
	STATE_INIT	= enum.item
	STATE_LOADED	= enum.item
	STATE_EXIT	= enum.item
	enum.end

	class Client(object):
		"""Client information."""

		def __init__(self, sock):
			self.socket = sock
			self.receiver = AwlSimMessageReceiver(sock)

	@classmethod
	def execute(cls):
		"""Execute the server process.
		Returns the exit() return value."""

		server, retval = None, 0
		try:
			server = AwlSimServer()
			for sig in (signal.SIGTERM, signal.SIGINT):
				signal.signal(sig, server.signalHandler)
			server.runFromEnvironment()
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
		self.receiver = None
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

	def __rx_PING(self, client, msg):
		AwlSimMessage_PONG().send(client.socket)

	def __rx_PONG(self, client, msg):
		printInfo("AwlSimServer: Received PONG")

	def __rx_LOAD_CODE(self, client, msg):
		pass#TODO

	def __rx_LOAD_HW(self, client, msg):
		pass#TODO

	def __rx_SET_OPT(self, client, msg):
		pass#TODO

	def __rx_GET_CPUDUMP(self, client, msg):
		AwlSimMessage_CPUDUMP(str(self.sim.cpu)).send(client.socket)

	__msgRxHandlers = {
		AwlSimMessage.MSG_ID_PING		: __rx_PING,
		AwlSimMessage.MSG_ID_PONG		: __rx_PONG,
		AwlSimMessage.MSG_ID_LOAD_CODE		: __rx_LOAD_CODE,
		AwlSimMessage.MSG_ID_LOAD_HW		: __rx_LOAD_HW,
		AwlSimMessage.MSG_ID_SET_OPT		: __rx_SET_OPT,
		AwlSimMessage.MSG_ID_GET_CPUDUMP	: __rx_GET_CPUDUMP,
	}

	def __handleClientComm(self, client):
		try:
			msg = client.receiver.receive()
		except AwlSimMessageReceiver.RemoteEndDied as e:
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

		while self.state != self.STATE_EXIT:
			self.__handleCommunication()
			if self.state == self.STATE_LOADED:
				sim.runCycle()

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
			client.socket.shutdown(socket.SHUT_RDWR)
			client.socket.close()
			client.socket = None
		self.clients = []

		if self.socket:
			self.socket.shutdown(socket.SHUT_RDWR)
			self.socket.close()
			self.socket = None

	def signalHandler(self, sig, frame):
		printInfo("AwlSimServer: Received signal %d" % sig)
		if sig in (signal.SIGTERM, signal.SIGINT):
			self.state = self.STATE_EXIT

class AwlSimClient(object):
	def __init__(self):
		self.serverProcess = None
		self.socket = None

	def spawnServer(self, interpreter=None,
			listenHost="localhost",
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
		environment = {
			AwlSimServer.ENV_MAGIC		: AwlSimServer.ENV_MAGIC,
			"AWLSIM_CORESERVER_HOST"	: str(listenHost),
			"AWLSIM_CORESERVER_PORT"	: str(listenPort),
		}
		self.serverProcess = subprocess.Popen([interpreter, "-m", "awlsim.coreserver"],
						      env = environment,
						      shell = False)
		return self.serverProcess.pid

	def connectToServer(self,
			    host="localhost",
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
		self.receiver = AwlSimMessageReceiver(sock)

		try:
			AwlSimMessage_PING().send(sock)
			msg = self.receiver.receiveBlocking()
			if msg.msgId != AwlSimMessage.MSG_ID_PONG:
				raise TransferError()
		except TransferError as e:
			raise AwlSimError("AwlSimClient: PING to server failed")

	def shutdown(self):
		"""Shutdown all sockets and spawned processes."""

		if self.socket:
			self.socket.shutdown(socket.SHUT_RDWR)
			self.socket.close()
			self.socket = None
		if self.serverProcess:
			self.serverProcess.terminate()
			self.serverProcess.wait()
			self.serverProcess = None

	def __rx_PING(self, msg):
		AwlSimMessage_PONG().send(client.socket)

	def handle_PONG(self):
		printInfo("AwlSimClient: Received PONG")

	def __rx_PONG(self, msg):
		self.handle_PONG()

	def handle_CPUDUMP(self, dumpText):
		pass # Don't do anything by default

	def __rx_CPUDUMP(self, msg):
		self.handle_CPUDUMP(msg.dumpText)

	__msgRxHandlers = {
		AwlSimMessage.MSG_ID_PING		: __rx_PING,
		AwlSimMessage.MSG_ID_PONG		: __rx_PONG,
		AwlSimMessage.MSG_ID_CPUDUMP		: __rx_CPUDUMP,
	}

	def processMessages(self):
		try:
			msg = self.receiver.receive()
		except socket.error as e:
			if e.errno == errno.EAGAIN:
				return None
			host, port = self.socket.getpeername()
			raise AwlSimError("AwlSimClient: "
				"I/O error in connection to server '%s:%d':\n%s" %\
				(host, port, str(e)))
		except (AwlSimMessageReceiver.RemoteEndDied, TransferError) as e:
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

	def loadCode(self, code):
		pass#TODO

	def loadHardwareModule(self, name, parameters):
		pass#TODO

	def setCpuSpec(self, name, value):
		pass#TODO

	def setOptions(self,
		       obTempPresetsEnabled,
		       extendedInsnsEnabled):
		pass#TODO

	def requestCpuDump(self):
		AwlSimMessage_GET_CPUDUMP().send(self.socket)

if __name__ == "__main__":
	# Run a server process.
	# Parameters are passed via environment.
	sys.exit(AwlSimServer.execute())

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

		def __init__(self, socket):
			self.socket = socket

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

	def __handleClientComm(self, client):
		pass#TODO

	def __handleCommunication(self):
		try:
			rlist, wlist, xlist = select.select(self.__selectRlist, [], [], 0)
		except Exception as e:
			raise AwlSimError("AwlSimServer: Communication error. "
				"'select' failed")
		if rlist:
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
		clientSock.setblocking(False)
		printInfo("AwlSimServer: Client %s:%d connected" % (host, port))

		client = self.Client(clientSock)
		self.clients.append(client)
		self.__rebuildSelectReadList()

		return client

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

if __name__ == "__main__":
	sys.exit(AwlSimServer.execute())

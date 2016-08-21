# -*- coding: utf-8 -*-
#
# AWL simulator - SSH tunnel helper
#
# Copyright 2016 Michael Buesch <m@bues.ch>
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

from awlsim.common.exceptions import *
from awlsim.common.net import *
from awlsim.common.util import *

import pty
import os
import select
import signal
import time


class SSHTunnel(object):
	"""SSH tunnel helper.
	"""

	SSH_DEFAULT_USER	= "pi"
	SSH_PORT		= 22
	SSH_LOCAL_PORT_START	= 4151 + 10
	SSH_LOCAL_PORT_END	= SSH_LOCAL_PORT_START + 4096
	SSH_DEFAULT_EXECUTABLE	= "ssh"

	def __init__(self, remoteHost, remotePort,
		     sshUser=SSH_DEFAULT_USER,
		     localPort=None,
		     sshExecutable=SSH_DEFAULT_EXECUTABLE,
		     sshPort=SSH_PORT):
		"""Create an SSH tunnel.
		"""
		self.remoteHost = remoteHost
		self.remotePort = remotePort
		self.sshUser = sshUser
		self.localPort = localPort
		self.sshExecutable = sshExecutable
		self.sshPort = sshPort
		self.__sshPid = None

	def connect(self, timeout=10.0):
		"""Establish the SSH tunnel.
		"""
		localPort = self.localPort
		if localPort is None:
			localPort = self.SSH_LOCAL_PORT_START
			while not netPortIsUnused("localhost", localPort):
				localPort += 1
				if localPort > self.SSH_LOCAL_PORT_END:
					raise AwlSimError("Failed to find an "
						"unused local port for the "
						"SSH tunnel.")
		actualLocalPort = localPort
		self.__sshPid = None
		try:
			# Prepare SSH environment and arguments.
			env = envClearLang(os.environ)
			argv = [ self.sshExecutable,
				"-p", "%d" % self.sshPort,
				"-l", self.sshUser,
				"-L", "localhost:%d:localhost:%d" % (
					localPort, self.remotePort),
				"-N",
				"-v",
				self.remoteHost, ]

			# Create a PTY and fork.
			childPid, ptyMasterFd = pty.fork()
			if childPid == pty.CHILD:
				# Run SSH
				execargs = argv + [env]
				os.execlpe(argv[0], *execargs)
				assert(0) # unreachable
			self.__sshPid = childPid
			self.__handshake(ptyMasterFd, timeout)
		except (OSError, ValueError, IOError) as e:
			with suppressAllExc:
				self.shutdown()
			raise AwlSimError("Failed to execute SSH to "
					  "establish SSH tunnel:\n%s" %\
					  str(e))
		except KeyboardInterrupt as e:
			with suppressAllExc:
				self.shutdown()
			raise AwlSimError("Interrupted by user.")
		return "localhost", actualLocalPort

	def shutdown(self):
		if self.__sshPid is None:
			return
		try:
			with suppressAllExc:
				os.kill(self.__sshPid, signal.SIGTERM)
		finally:
			self.__sshPid = None

	@staticmethod
	def __read(fd):
		data = []
		while True:
			rfds, wfds, xfds = select.select([fd], [], [], 0)
			if fd not in rfds:
				break
			d = os.read(fd, 1024)
			if not d:
				break
			data.append(d)
		return b''.join(data)

	@staticmethod
	def __write(fd, data):
		while data:
			count = os.write(fd, data)
			data = data[count:]

	PROMPT_PW	= "'s Password:"
	PROMPT_AUTH	= "The authenticity of host "
	PROMPT_YESNO	= " (yes/no)?"
	AUTH_FINISH	= "Authenticated to "

	def __handshake(self, ptyMasterFd, timeout):
		timeoutEnd = monotonic_time() + (timeout or 0)
		sentPw, authReq, finished = False, False, False
		while not finished:
			time.sleep(0.1)
			if timeout and monotonic_time() >= timeoutEnd:
				raise AwlSimError("Timeout establishing SSH tunnel.")
			fromSsh = self.__read(ptyMasterFd)
			try:
				fromSsh = fromSsh.decode("UTF-8", "ignore")
			except UnicodeError:
				fromSsh = ""
			for line in fromSsh.splitlines():
				if not line:
					continue
				lineLow = line.lower()
				isDebug = lineLow.strip().startswith("debug")
				self.sshMessage(line, isDebug)
				if isDebug:
					continue
				if self.PROMPT_PW.lower() in lineLow:
					if sentPw:
						# Second try.
						raise AwlSimError("SSH tunnel passphrase "
							"was not accepted.")
					passphrase = self.getPassphrase(line)
					if passphrase is None:
						raise AwlSimError("SSH tunnel connection "
							"requires a passphrase, but "
							"no passphrase was given.")
					self.__write(ptyMasterFd, passphrase)
					if not passphrase.endswith(b"\n"):
						self.__write(ptyMasterFd, b"\n")
					sentPw = True
					timeoutEnd = monotonic_time() + (timeout or 0)
					continue
				if self.PROMPT_AUTH.lower() in lineLow:
					authReq = True
					continue
				if self.PROMPT_YESNO.lower() in lineLow and authReq:
					ok = self.hostAuth(line)
					if not ok:
						raise AwlSimError("SSH tunnel host "
							"authentication failed.")
					self.__write(ptyMasterFd, b"yes\n")
					authReq = False
					timeoutEnd = monotonic_time() + (timeout or 0)
					continue
				if self.AUTH_FINISH.lower() in lineLow:
					# Successfully authenticated.
					finished = True
					continue

	def sshMessage(self, message, isDebug):
		"""Print a SSH log message.
		"""
		if not isDebug:
			printInfo("[SSH]:  %s" % message)

	def getPassphrase(self, prompt):
		"""Get a password from the user.
		"""
		try:
			return input(prompt).encode("UTF-8", "ignore")
		except UnicodeError:
			return ""

	def hostAuth(self, prompt):
		"""Get the user answer to the host authentication question.
		This function returns a boolean.
		"""
		return str2bool(input(prompt))

# -*- coding: utf-8 -*-
#
# subprocess wrapper
#
# Copyright 2014 Michael Buesch <m@bues.ch>
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
from awlsim.core.util import *

if isIronPython:
	import os
	import signal
else:
	import subprocess

class PopenWrapper(object):
	def __init__(self, argv, env, shell):
		self.__noWait = False
		if isIronPython:
			self.__pid = os.spawnve(os.P_NOWAIT, argv[0], argv, env)
		else:
			self.__proc = subprocess.Popen(argv, env = env, shell = shell)

	def terminate(self):
		if isIronPython:
			try:
				os.kill(self.__pid, signal.SIGTERM)
			except ValueError:
				pass
		else:
			try:
				self.__proc.terminate()
			except NameError:
				# XXX: Workaround: Jython currently does not implement terminate
				if not isJython:
					raise
				printInfo("AwlSimClient: Jython Popen.terminate workaround: "
					  "Not terminating server.")
				self.__noWait = True

	def wait(self):
		if self.__noWait:
			return
		if isIronPython:
			pass#TODO
		else:
			self.__proc.wait()

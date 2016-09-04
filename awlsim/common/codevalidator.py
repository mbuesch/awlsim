# -*- coding: utf-8 -*-
#
# AWL simulator - Code validator
#
# Copyright 2014-2016 Michael Buesch <m@bues.ch>
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

from awlsim.coreclient.client import *


class AwlValidator(object):
	"""Source code validation.
	"""

	__globalInstance = None

	PORT_RANGE = range(30000, 32000)

	@classmethod
	def startup(cls):
		if cls.__globalInstance:
			return cls.__globalInstance
		printDebug("AwlValidator: Startup")
		try:
			val = cls()
		except AwlSimError as e:
			printDebug("Failed to startup validator: %s" % str(e))
			return None
		cls.__globalInstance = val
		return val

	@classmethod
	def shutdown(cls):
		if cls.__globalInstance:
			cls.__globalInstance.doShutdown()
			cls.__globalInstance = None

	@classmethod
	def get(cls):
		return cls.startup()

	def __init__(self):
		self.__client = AwlSimClient()
		extraArgs = {}
		if isWinStandalone:
			extraArgs["serverExecutable"] = "awlsim-server-module.exe"
		try:
			self.__client.spawnServer(listenHost = "localhost",
						  listenPort = self.PORT_RANGE,
						  **extraArgs)
			self.__client.connectToServer(host = "localhost",
						      port = self.__client.serverProcessPort)
			self.__client.setLoglevel(Logging.LOG_NONE)
		except AwlSimError as e:
			self.doShutdown()
			raise e

	def doShutdown(self):
		printDebug("AwlValidator: Shutdown")
		if self.__client:
			self.__client.shutdown()
			self.__client = None

	def validate(self, project, symTabSources, libSelections, awlSources):
		"""Run a validation.
		This will raise an AwlSimError on validation failure.
		"""
		if not project or not symTabSources or\
		   not libSelections or not awlSources:
			return
		self.__client.setRunState(False)
		self.__client.reset()
		self.__client.loadProject(project, loadSymTabs=False,
					  loadLibSelections=False,
					  loadSources=False)
		self.__client.loadSymTabSources(symTabSources)
		self.__client.loadLibraryBlocks(libSelections)
		self.__client.loadAwlSources(awlSources)
		self.__client.build()

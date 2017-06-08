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
from awlsim.common.exceptions import *

from awlsim.coreclient.client import *

import threading


__all__ = [
	"AwlValidator",
]


class AwlValidator(object):
	"""Source code validation.
	"""

	__globalInstance = None

	_PORT_RANGE	= range(30000, 32000)
	_EXIT_THREAD	= -1

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
		self.__thread = None
		self.__job = None
		self.__exception = None
		self.__running = False
		self.__lock = threading.Lock()
		self.__condition = threading.Condition(self.__lock)

		self.__client = AwlSimClient()
		try:
			self.__client.setLoglevel(Logging.LOG_ERROR,
						  setClientSide=False,
						  setServerSide=True)
			self.__client.spawnServer(listenHost = "localhost",
						  listenPort = self._PORT_RANGE)
			self.__client.connectToServer(host = "localhost",
						      port = self.__client.serverProcessPort)
			self.__client.setLoglevel(Logging.LOG_NONE,
						  setClientSide=False,
						  setServerSide=True)
		except AwlSimError as e:
			self.doShutdown()
			raise e

		self.__thread = threading.Thread(target=self.__threadFunc)
		self.__thread.daemon = False
		self.__thread.start()

	def doShutdown(self):
		printDebug("AwlValidator: Shutdown")
		if self.__client:
			self.__client.shutdown()
			self.__client = None
		if self.__thread:
			with self.__lock:
				self.__job = self._EXIT_THREAD
				self.__condition.notify_all()
			self.__thread.join()
			self.__thread = None
			self.__exception = None
			self.__running = False

	def __runJob(self, job):
		(project,
		 symTabSources, libSelections, awlSources,
		 fupSources, kopSources) = job

		client = self.__client
		exception = None
		try:
			client.setRunState(False)
			client.reset()
			client.loadProject(project, loadSymTabs=False,
					   loadLibSelections=False,
					   loadSources=False,
					   loadFup=False,
					   loadKop=False)
			client.loadSymTabSources(symTabSources)
			client.loadLibraryBlocks(libSelections)
			client.loadAwlSources(awlSources)
			client.loadFupSources(fupSources)
			client.loadKopSources(kopSources)
			client.build()
			client.reset()
		except AwlSimError as e:
			exception = e
		with self.__lock:
			if self.__job is None:
				self.__running = False
			self.__exception = exception

	def __threadFunc(self):
		"""This is the validation thread.
		"""
		while True:
			with self.__lock:
				if self.__job is None:
					self.__condition.wait()
				job, self.__job = self.__job, None
			if job is self._EXIT_THREAD:
				break
			if job:
				self.__runJob(job)

	def validate(self, project,
		     symTabSources, libSelections, awlSources,
		     fupSources, kopSources):
		"""Schedule a validation.
		Get the result with getState().
		"""
		if not project or not awlSources:
			return
		with self.__lock:
			if self.__job is self._EXIT_THREAD:
				return
			self.__job = (project,
				      symTabSources, libSelections, awlSources,
				      fupSources, kopSources)
			self.__running = True
			self.__condition.notify_all()

	def getState(self):
		"""Get the validation result.
		Returns a tuple (running, exception).
		"""
		with self.__lock:
			running = self.__running
			exception = self.__exception
		return running, exception

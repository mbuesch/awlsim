# -*- coding: utf-8 -*-
#
# AWL simulator
#
# Copyright 2012-2019 Michael Buesch <m@bues.ch>
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
#from awlsim.common.cython_support cimport * #@cy
from awlsim.common.compat import *

from awlsim.common.project import *
from awlsim.common.env import *
from awlsim.common.exceptions import *
from awlsim.common.profiler import *
from awlsim.common.util import *

from awlsim.core.cpu import * #+cimport
from awlsim.core.hardware import * #+cimport
from awlsim.core.hardware_loader import *

import sys

#cimport cython #@cy


__all__ = [
	"AwlSim",
]


def AwlSim_decorator_profiled(profileLevel):
	"""Profiled call decorator.
	"""
	def profiled_decorator(func):
		@functools.wraps(func) #@nocy
		def profiled_wrapper(self, *args, **kwargs):
			if self._profileLevel >= profileLevel:
				self._profileStart() #@nocov
			try:
				func(self, *args, **kwargs)
			finally:
				if self._profileLevel >= profileLevel:
					self._profileStop() #@nocov
		return profiled_wrapper
	return profiled_decorator

def AwlSim_decorator_throwsAwlSimError(func):
	"""Handler decorator for AwlSimError exceptions.
	"""
	@functools.wraps(func) #@nocy
	def awlSimErrorExtension_wrapper(self, *args, **kwargs):
		try:
			func(self, *args, **kwargs)
		except AwlSimError as e:
			self._handleSimException(e)
	return awlSimErrorExtension_wrapper

class AwlSim(object): #+cdef
	"""Main awlsim core object.
	"""

	profiled		= AwlSim_decorator_profiled
	throwsAwlSimError	= AwlSim_decorator_throwsAwlSimError

	def __init__(self):
		self.__registeredHardware = []
		self.__registeredHardwareCount = 0
		self.__hwStartupRequired = True
		self._fatalHwErrors = True
		self.cpu = S7CPU()
		self.cpu.setPeripheralReadCallback(self.__peripheralReadCallback)
		self.cpu.setPeripheralWriteCallback(self.__peripheralWriteCallback)

		self.__setProfiler(AwlSimEnv.getProfileLevel())

	def getCPU(self):
		return self.cpu

	def __setProfiler(self, profileLevel): #@nocov
		self._profileLevel = profileLevel
		if self._profileLevel <= 0:
			return

		self.__profiler = Profiler()

	def _profileStart(self): #@nocov
		self.__profiler.start()

	def _profileStop(self): #@nocov
		self.__profiler.stop()

	def getProfileStats(self): #@nocov
		if self._profileLevel <= 0:
			return None
		return self.__profiler.getResult()

	def _handleSimException(self, e, fatal = True):
		"""Handle an exception and add some information
		to it. Note that this might get called twice or more often
		for the same exception object.
		"""
		if not e.getCpu():
			# The CPU reference is not set, yet.
			# Set it to the current CPU.
			e.setCpu(self.cpu)
		if fatal:
			# Re-raise the exception for upper layers to catch.
			raise e
		else:
			# Non-fatal. Just log an error.
			printError(str(e)) #@nocov

	@throwsAwlSimError
	def __handleMaintenanceRequest(self, e):
		if e.requestType in (MaintenanceRequest.TYPE_SHUTDOWN,
				     MaintenanceRequest.TYPE_STOP,
				     MaintenanceRequest.TYPE_RTTIMEOUT):
			# This is handled in the toplevel loop, so
			# re-raise the exception.
			raise e
		try:
			if e.requestType == MaintenanceRequest.TYPE_SOFTREBOOT:
				# Run the CPU startup sequence again
				self.cpu.startup()
			else:
				assert(0)
		except MaintenanceRequest as e: #@nocov
			raise AwlSimError("Recursive maintenance request")

	@profiled(2)
	@throwsAwlSimError
	def reset(self):
		self.cpu.reset()
		self.unregisterAllHardware()

	@profiled(2)
	@throwsAwlSimError
	def build(self):
		self.cpu.build()

	@profiled(2)
	@throwsAwlSimError
	def load(self, parseTree, rebuild = False, sourceManager = None):
		self.cpu.load(parseTree, rebuild, sourceManager)

	@profiled(2)
	@throwsAwlSimError
	def loadSymbolTable(self, symTab, rebuild = False):
		self.cpu.loadSymbolTable(symTab, rebuild)

	@profiled(2)
	@throwsAwlSimError
	def loadLibraryBlock(self, libSelection, rebuild = False):
		self.cpu.loadLibraryBlock(libSelection, rebuild)

	@profiled(2)
	@throwsAwlSimError
	def removeBlock(self, blockInfo, sanityChecks = True):
		self.cpu.removeBlock(blockInfo, sanityChecks)

	@profiled(2)
	@throwsAwlSimError
	def staticSanityChecks(self):
		self.cpu.staticSanityChecks()

	@profiled(2)
	@throwsAwlSimError
	def startup(self):
		# Startup the hardware modules, if required.
		if self.__hwStartupRequired:
			self.hardwareStartup()
		# Next time we need a startup again.
		self.__hwStartupRequired = True

		# Startup the CPU core.
		try:
			self.__readHwInputs()
			self.cpu.startup()
			self.__writeHwOutputs()
		except MaintenanceRequest as e:
			self.__handleMaintenanceRequest(e)

	def runCycle(self): #+cpdef
		if self._profileLevel >= 1:
			self._profileStart() #@nocov

		try:
			if self.__registeredHardwareCount:
				self.__readHwInputs()
			self.cpu.runCycle()
			if self.__registeredHardwareCount:
				self.__writeHwOutputs()
			self.cpu.sleepCyclePadding()
		except AwlSimError as e:
			self._handleSimException(e)
		except MaintenanceRequest as e:
			self.__handleMaintenanceRequest(e)

		if self._profileLevel >= 1:
			self._profileStop() #@nocov

	@throwsAwlSimError
	def shutdown(self):
		"""Shutdown the Awlsim core.
		This will unregister all hardware modules and shut down execution.
		"""
		self.unregisterAllHardware()
		ps = self.getProfileStats()
		if ps: #@nocov
			sys.stdout.write("\n\nAwlsim core profile stats "
					 "(level %d) follow:\n" %\
					 self._profileLevel)
			sys.stdout.write(ps)
			sys.stdout.write("\n")
			sys.stdout.flush()

	def unregisterAllHardware(self):
		for hw in self.__registeredHardware:
			hw.shutdown()
		self.__registeredHardware = []
		self.__registeredHardwareCount = 0

	def registerHardware(self, hwClassInst):
		"""Register a new hardware interface."""

		if hwClassInst.getParamValueByName("enabled"):
			self.__registeredHardware.append(hwClassInst)
			self.__registeredHardwareCount = len(self.__registeredHardware)
			self.__hwStartupRequired = True

	def registerHardwareClass(self, hwClass, parameters={}):
		"""Register a new hardware interface class.
		'parameters' is a dict of hardware specific parameters.
		Returns the instance of the hardware class."""

		hwClassInst = hwClass(sim = self,
				      parameters = parameters)
		self.registerHardware(hwClassInst)
		return hwClassInst

	@classmethod
	def loadHardwareModule(cls, name):
		"""Load a hardware interface module.
		'name' is the name of the module to load (without 'awlsimhw_' prefix).
		Returns the HardwareInterface class."""

		return HwModLoader.loadModule(name).getInterface()

	@profiled(2)
	@throwsAwlSimError
	def hardwareStartup(self):
		"""Startup all attached hardware modules.
		"""

		# Hw errors are fatal if debugging.
		# Otherwise just log the errors, but don't abort the program.
		self._fatalHwErrors = bool(Logging.loglevel >= Logging.LOG_DEBUG)

		for hw in self.__registeredHardware:
			try:
				hw.startup()
			except AwlSimError as e:
				# Always fatal in startup.
				self._handleSimException(e, fatal=True)
		self.__hwStartupRequired = False

#@cy	@cython.boundscheck(False)
	def __readHwInputs(self): #+cdef
		"""Read all hardware module inputs.
		"""
#@cy		cdef AbstractHardwareInterface hw
#@cy		cdef uint32_t i

		# Note: Bounds checking of the indexing operator [] is disabled
		#       by @cython.boundscheck(False) in this method.

		for i in range(self.__registeredHardwareCount):
			try:
				hw = self.__registeredHardware[i]
				hw.readInputs()
			except AwlSimError as e:
				self._handleSimException(e,
					fatal = self._fatalHwErrors)

#@cy	@cython.boundscheck(False)
	def __writeHwOutputs(self): #+cdef
		"""Write all hardware module outputs.
		"""
#@cy		cdef AbstractHardwareInterface hw
#@cy		cdef uint32_t i

		# Note: Bounds checking of the indexing operator [] is disabled
		#       by @cython.boundscheck(False) in this method.

		for i in range(self.__registeredHardwareCount):
			try:
				hw = self.__registeredHardware[i]
				hw.writeOutputs()
			except AwlSimError as e:
				self._handleSimException(e,
					fatal = self._fatalHwErrors)

	def __peripheralReadCallback(self, userData, width, offset):
		"""The CPU issued a direct peripheral read access.
		Poke all registered hardware modules, but only return the value
		from the last module returning a valid value.
		"""
#@cy		cdef AbstractHardwareInterface hw
#@cy		cdef bytearray retValue
#@cy		cdef bytearray value

		for hw in self.__registeredHardware:
			try:
				value = hw.directReadInput(width, offset)
				if value:
					return value
			except AwlSimError as e:
				self._handleSimException(e,
					fatal = self._fatalHwErrors)
				break
		return bytearray()

	def __peripheralWriteCallback(self, userData, width, offset, value):
		"""The CPU issued a direct peripheral write access.
		Send the write request down to all hardware modules.
		Returns true, if any hardware accepted the value.
		"""
#@cy		cdef AbstractHardwareInterface hw
#@cy		cdef _Bool retOk
#@cy		cdef ExBool_t ok

		retOk = False
		try:
			for hw in self.__registeredHardware:
				ok = hw.directWriteOutput(width, offset, value)
				retOk = ok or retOk
		except AwlSimError as e:
			self._handleSimException(e,
				fatal = self._fatalHwErrors)
			return False
		return retOk

	def __repr__(self): #@nocov
		return str(self.cpu)

# -*- coding: utf-8 -*-
#
# AWL simulator
#
# Copyright 2012-2017 Michael Buesch <m@bues.ch>
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

from awlsim.common.project import *
from awlsim.common.env import *
from awlsim.common.exceptions import *

from awlsim.core.util import *
from awlsim.core.cpu import * #+cimport
from awlsim.core.hardware import * #+cimport
from awlsim.core.hardware_loader import *

import sys


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
				self._profileStart()
			try:
				func(self, *args, **kwargs)
			finally:
				if self._profileLevel >= profileLevel:
					self._profileStop()
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
		self._fatalHwErrors = True
		self.cpu = S7CPU()
		self.cpu.setPeripheralReadCallback(self.__peripheralReadCallback)
		self.cpu.setPeripheralWriteCallback(self.__peripheralWriteCallback)

		self.__setProfiler(AwlSimEnv.getProfileLevel())

	def getCPU(self):
		return self.cpu

	def __setProfiler(self, profileLevel):
		self._profileLevel = profileLevel
		if self._profileLevel <= 0:
			return

		try:
			import cProfile as profileModule
		except ImportError:
			profileModule = None
		self.__profileModule = profileModule
		try:
			import pstats as pstatsModule
		except ImportError:
			pstatsModule = None
		self.__pstatsModule = pstatsModule

		if not self.__profileModule or\
		   not self.__pstatsModule:
			raise AwlSimError("Failed to load cProfile/pstats modules. "
				"Cannot enable profiling.")

		self.__profiler = self.__profileModule.Profile()

	def _profileStart(self):
		self.__profiler.enable()

	def _profileStop(self):
		self.__profiler.disable()

	def getProfileStats(self):
		if self._profileLevel <= 0:
			return None

		sio = StringIO()
		ps = self.__pstatsModule.Stats(self.__profiler,
					       stream = sio)
		ps.sort_stats("time")
		ps.print_stats()

		return sio.getvalue()

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
			printError(str(e))

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
		except MaintenanceRequest as e:
			raise AwlSimError("Recursive maintenance request")

	@profiled(2)
	@throwsAwlSimError
	def reset(self):
		self.cpu.reset()
		self.unregisterAllHardware(inCpuReset = True)

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
		self.__hwStartup()
		try:
			self.__readHwInputs()
			self.cpu.startup()
			self.__writeHwOutputs()
		except MaintenanceRequest as e:
			self.__handleMaintenanceRequest(e)

	def runCycle(self): #+cpdef
		if self._profileLevel >= 1:
			self._profileStart()

		try:
			if self.__registeredHardwareCount:
				self.__readHwInputs()
			self.cpu.runCycle()
			if self.__registeredHardwareCount:
				self.__writeHwOutputs()
		except AwlSimError as e:
			self._handleSimException(e)
		except MaintenanceRequest as e:
			self.__handleMaintenanceRequest(e)

		if self._profileLevel >= 1:
			self._profileStop()

	@throwsAwlSimError
	def shutdown(self):
		"""Shutdown the Awlsim core.
		This will unregister all hardware modules and shut down execution.
		"""
		self.unregisterAllHardware()
		ps = self.getProfileStats()
		if ps:
			sys.stdout.write("\n\nAwlsim core profile stats "
					 "(level %d) follow:\n" %\
					 self._profileLevel)
			sys.stdout.write(ps)
			sys.stdout.write("\n")
			sys.stdout.flush()

	def unregisterAllHardware(self, inCpuReset = False):
		newHwList = []
		for hw in self.__registeredHardware:
			if not hw.getParam("removeOnReset") and inCpuReset:
				# This module has "removeOnReset" set to False
				# and we are in a CPU reset.
				# Do shutdown the module, but keep it in the
				# list of registered modules.
				newHwList.append(hw)
			hw.shutdown()
		self.__registeredHardware = newHwList
		self.__registeredHardwareCount = len(self.__registeredHardware)

	def registerHardware(self, hwClassInst):
		"""Register a new hardware interface."""

		self.__registeredHardware.append(hwClassInst)
		self.__registeredHardwareCount = len(self.__registeredHardware)

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

	def __hwStartup(self):
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
				self._handleSimException(e, fatal = True)

	def __readHwInputs(self): #+cdef
		"""Read all hardware module inputs.
		"""
#@cy		cdef AbstractHardwareInterface hw

		for hw in self.__registeredHardware:
			try:
				hw.readInputs()
			except AwlSimError as e:
				self._handleSimException(e,
					fatal = self._fatalHwErrors)

	def __writeHwOutputs(self): #+cdef
		"""Write all hardware module outputs.
		"""
#@cy		cdef AbstractHardwareInterface hw

		for hw in self.__registeredHardware:
			try:
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

		retValue = bytearray()
		for hw in self.__registeredHardware:
			try:
				value = hw.directReadInput(width, offset)
				if value:
					retValue = value
			except AwlSimError as e:
				self._handleSimException(e,
					fatal = self._fatalHwErrors)
		return retValue

	def __peripheralWriteCallback(self, userData, width, offset, value):
		"""The CPU issued a direct peripheral write access.
		Send the write request down to all hardware modules.
		Returns true, if any hardware accepted the value.
		"""
#@cy		cdef AbstractHardwareInterface hw
#@cy		cdef _Bool retOk

		retOk = False
		try:
			for hw in self.__registeredHardware:
				ok = hw.directWriteOutput(width, offset, value)
				if not retOk:
					retOk = ok
		except AwlSimError as e:
			self._handleSimException(e,
				fatal = self._fatalHwErrors)
		return retOk

	def __repr__(self):
		return str(self.cpu)

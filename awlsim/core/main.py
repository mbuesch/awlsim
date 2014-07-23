# -*- coding: utf-8 -*-
#
# AWL simulator
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

from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim.core.compat import *

from awlsim.core.version import *
from awlsim.core.util import *
from awlsim.core.parser import *
from awlsim.core.cpu import *
from awlsim.core.hardware import *

import importlib


class AwlSim(object):
	def __init__(self, profileLevel=0):
		self.__registeredHardware = []
		self.cpu = S7CPU(self)
		self.cpu.setPeripheralReadCallback(self.__peripheralReadCallback)
		self.cpu.setPeripheralWriteCallback(self.__peripheralWriteCallback)

		self.__setProfiler(profileLevel)

	def getCPU(self):
		return self.cpu

	def __setProfiler(self, profileLevel):
		self.__profileLevel = profileLevel
		if self.__profileLevel <= 0:
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

	def __profileStart(self):
		self.__profiler.enable()

	def __profileStop(self):
		self.__profiler.disable()

	def getProfileStats(self):
		if self.__profileLevel <= 0:
			return None

		sio = StringIO()
		ps = self.__pstatsModule.Stats(self.__profiler,
					       stream = sio)
		ps.sort_stats("cumulative")
		ps.print_stats()

		return sio.getvalue()

	def __handleSimException(self, e):
		if not e.getCpu():
			# The CPU reference is not set, yet.
			# Set it to the current CPU.
			e.setCpu(self.cpu)
		raise e

	def __handleMaintenanceRequest(self, e):
		try:
			if e.requestType == MaintenanceRequest.TYPE_SHUTDOWN:
				# This is handled in the toplevel loop, so
				# re-raise the exception.
				raise
			try:
				if e.requestType == MaintenanceRequest.TYPE_SOFTREBOOT:
					# Run the CPU startup sequence again
					self.cpu.startup()
				else:
					assert(0)
			except MaintenanceRequest as e:
				raise AwlSimError("Recursive maintenance request")
		except AwlSimError as e:
			self.__handleSimException(e)

	def shutdown(self):
		self.unregisterAllHardware()

	def reset(self):
		try:
			self.cpu.reset()
			self.unregisterAllHardware()
		except AwlSimError as e:
			self.__handleSimException(e)

	def load(self, parseTree):
		if self.__profileLevel >= 2:
			self.__profileStart()

		try:
			self.cpu.load(parseTree)
		except AwlSimError as e:
			self.__handleSimException(e)

		if self.__profileLevel >= 2:
			self.__profileStop()

	def loadSymbolTable(self, symTab):
		if self.__profileLevel >= 2:
			self.__profileStart()

		try:
			self.cpu.loadSymbolTable(symTab)
		except AwlSimError as e:
			self.__handleSimException(e)

		if self.__profileLevel >= 2:
			self.__profileStop()

	def startup(self):
		if self.__profileLevel >= 2:
			self.__profileStart()

		try:
			for hw in self.__registeredHardware:
				hw.startup()
			try:
				self.cpu.startup()
			except MaintenanceRequest as e:
				self.__handleMaintenanceRequest(e)
		except AwlSimError as e:
			self.__handleSimException(e)

		if self.__profileLevel >= 2:
			self.__profileStop()

	def runCycle(self):
		if self.__profileLevel >= 1:
			self.__profileStart()

		try:
			for hw in self.__registeredHardware:
				hw.readInputs()
			self.cpu.runCycle()
			for hw in self.__registeredHardware:
				hw.writeOutputs()
		except AwlSimError as e:
			self.__handleSimException(e)
		except MaintenanceRequest as e:
			self.__handleMaintenanceRequest(e)

		if self.__profileLevel >= 1:
			self.__profileStop()

	def unregisterAllHardware(self):
		for hw in self.__registeredHardware:
			hw.shutdown()
		self.__registeredHardware = []

	def registerHardware(self, hwClassInst):
		"""Register a new hardware interface."""

		self.__registeredHardware.append(hwClassInst)

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

		# Construct the python module name
		moduleName = "awlsimhw_%s" % name
		# Try to import the module
		try:
			mod = importlib.import_module(moduleName)
		except ImportError as e:
			raise AwlSimError("Failed to import hardware interface "
				"module '%s' (import name '%s'): %s" %\
				(name, moduleName, str(e)))
		# Fetch and instantiate the interface object
		hwClassName = "HardwareInterface"
		hwClass = getattr(mod, hwClassName, None)
		if not hwClass:
			raise AwlSimError("Hardware module '%s' (import name '%s') "
				"does not have a '%s' class." %\
				(name, moduleName, hwClassName))
		return hwClass

	def __peripheralReadCallback(self, userData, width, offset):
		# The CPU issued a direct peripheral read access.
		# Poke all registered hardware modules, but only return the value
		# from the last module returning a valid value.

		retValue = None
		for hw in self.__registeredHardware:
			value = hw.directReadInput(width, offset)
			if value is not None:
				retValue = value
		return retValue

	def __peripheralWriteCallback(self, userData, width, offset, value):
		# The CPU issued a direct peripheral write access.
		# Send the write request down to all hardware modules.
		# Returns true, if any hardware accepted the value.

		retOk = False
		for hw in self.__registeredHardware:
			ok = hw.directWriteOutput(width, offset, value)
			if not retOk:
				retOk = ok
		return retOk

	def __repr__(self):
		return str(self.cpu)

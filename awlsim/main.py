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

from awlsim.cpu import *
from awlsim.util import *
from awlsim.version import *
from awlsim.hardware import *

import importlib


class AwlSim(object):
	def __init__(self):
		self.__registeredHardware = []
		self.cpu = S7CPU(self)
		self.cpu.setPeripheralReadCallback(self.__peripheralReadCallback)
		self.cpu.setPeripheralWriteCallback(self.__peripheralWriteCallback)

	def __handleSimException(self, e):
		if not e.getCpu():
			# The CPU reference is not set, yet.
			# Set it to the current CPU.
			e.setCpu(self.cpu)
		raise e

	def shutdown(self):
		for hw in self.__registeredHardware:
			hw.shutdown()

	def load(self, parseTree):
		try:
			self.cpu.load(parseTree)
			for hw in self.__registeredHardware:
				hw.startup()
			self.cpu.startup()
		except AwlSimError as e:
			self.__handleSimException(e)

	def getCPU(self):
		return self.cpu

	def runCycle(self):
		try:
			for hw in self.__registeredHardware:
				hw.readInputs()
			self.cpu.runCycle()
			for hw in self.__registeredHardware:
				hw.writeOutputs()
		except AwlSimError as e:
			self.__handleSimException(e)

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

	def loadHardwareModule(self, name):
		"""Load a hardware interface module and
		register the interface.
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

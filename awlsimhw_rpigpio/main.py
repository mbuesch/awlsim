# -*- coding: utf-8 -*-
#
# AWL simulator - Raspberry Pi GPIO hardware interface
#
# Copyright 2016-2017 Michael Buesch <m@bues.ch>
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

#from awlsimhw_rpigpio.main cimport * #@cy

from awlsim.core.hardware_params import *
from awlsim.core.hardware import * #+cimport
from awlsim.core.operators import * #+cimport
from awlsim.core.offset import * #+cimport
from awlsim.core.cpu import * #+cimport

import re


class HwParamDesc_IOMap(HwParamDesc):
	typeStr = "BCM-port-number"
	_valueRe = re.compile(r'^\s*(?:BCM)?(\d+)\s*$')

	def __init__(self, mem):
		HwParamDesc.__init__(self,
				     name = "%s0.0" % mem,
				     description = "Example:  %s1.4=BCM26" % mem)

	def parse(self, value):
		try:
			if not value:
				raise ValueError
			m = self._valueRe.match(value.upper())
			if not m:
				raise ValueError
			bcm = int(m.group(1), 10)
			if bcm < 0:
				raise ValueError
			return bcm
		except ValueError:
			raise self.ParseError("Invalid BCM port number: %s" % value)

	def match(self, matchName):
		if not matchName:
			return False
		return bool(self._nameRe.match(matchName))

class HwParamDesc_IMap(HwParamDesc_IOMap):
	_nameRe = re.compile(r'^\s*[EI]([0-9]+)\.([0-7])\s*$')

	def __init__(self):
		HwParamDesc_IOMap.__init__(self, mem = "I")

class HwParamDesc_QMap(HwParamDesc_IOMap):
	_nameRe = re.compile(r'^\s*[AQ]([0-9])+\.([0-7])\s*$')

	def __init__(self):
		HwParamDesc_IOMap.__init__(self, mem = "Q")

class RpiGPIO_BitMapping(object):
	"""Awlsim -> RaspiGPIO memory bit mapping.
	"""

	def __init__(self):
		# Bit number to BCM GPIO number map.
		self.bit2bcm = [ None, ] * 8
		self.mapList = []

	def setBit(self, bitOffset, bcmNumber):
		assert(bitOffset >= 0 and bitOffset <= 7)
		self.bit2bcm[bitOffset] = bcmNumber

	def build(self):
		self.mapList = [ (bitOffset, self.bit2bcm[bitOffset])
				 for bitOffset in range(8)
				 if self.bit2bcm[bitOffset] is not None ]

	def __repr__(self):
		return "{ " +\
			", ".join("%d: %s" % (i, str(self.bit2bcm[i]))
				  for i in range(8)) +\
		       " }"

class RpiGPIO_HwInterface(AbstractHardwareInterface): #+cdef
	"""Raspberry Pi GPIO hardware interface.
	"""
	name = "RPi.GPIO"

	paramDescs = [
		HwParamDesc_IMap(),
		HwParamDesc_QMap(),
	]

	def __init__(self, sim, parameters={}):
		AbstractHardwareInterface.__init__(self,
						   sim = sim,
						   parameters = parameters)
		self.__tmpStoreBytes = bytearray(1)

	def doStartup(self):
		"""Startup the hardware module.
		"""
		# Get the configuration
		inputs = self.getParamsByDescType(HwParamDesc_IMap)
		outputs = self.getParamsByDescType(HwParamDesc_QMap)

		# Import the Raspberry Pi GPIO module
		try:
			import RPi.GPIO as RPi_GPIO
			self.__RPi_GPIO = RPi_GPIO
		except ImportError as e:
			self.raiseException("Failed to import Raspberry Pi GPIO "
				"module 'RPi.GPIO': %s" % str(e))

		# Initialize the GPIO library
		try:
			RPi_GPIO.setmode(self.__RPi_GPIO.BCM)
			RPi_GPIO.setwarnings(False)
		except RuntimeError as e:
			self.raiseException("Failed to init Raspberry Pi "
				"GPIO library: %s" % str(e))

		# Build the memory mappings
		self.__inputMap, self.__inputList = self.__mapGPIO(
				inputs, HwParamDesc_IMap._nameRe, RPi_GPIO.IN,
				self.inputAddressBase)
		self.__outputMap, self.__outputList = self.__mapGPIO(
				outputs, HwParamDesc_QMap._nameRe, RPi_GPIO.OUT,
				self.outputAddressBase)

	def __mapGPIO(self, configs, nameRegEx, gpioDir, byteBaseOffset):
		mapDict = {}
		RPi_GPIO = self.__RPi_GPIO
		for address, bcmNumber in configs:
			m = nameRegEx.match(address)
			byteOffset = int(m.group(1), 10)
			bitOffset = int(m.group(2), 10)
			mapping = mapDict.setdefault(byteBaseOffset + byteOffset,
						     RpiGPIO_BitMapping())
			mapping.setBit(bitOffset, bcmNumber)
			try:
				if gpioDir == RPi_GPIO.IN:
					RPi_GPIO.setup(bcmNumber,
						       gpioDir,
						       pull_up_down = RPi_GPIO.PUD_DOWN)
				else:
					RPi_GPIO.setup(bcmNumber,
						       gpioDir,
						       initial = RPi_GPIO.LOW)
			except RuntimeError as e:
				self.raiseException("Failed to init Raspberry Pi "
					"BCM%d: %s" % (bcmNumber, str(e)))
		for bitMapping in dictValues(mapDict):
			bitMapping.build()
		mapList = list(sorted(
			[ (byteOffset, bitMapping)
			  for byteOffset, bitMapping in dictItems(mapDict) ],
			key = lambda _tuple: _tuple[0]
		))
		return mapDict, mapList

	def doShutdown(self):
		pass # Do nothing

	def readInputs(self): #+cdef
#@cy		cdef S7CPU cpu
#@cy		cdef uint8_t inByte
#@cy		cdef uint32_t byteOffset
#@cy		cdef uint32_t bitOffset
#@cy		cdef bytearray tmpBytes

		RPi_GPIO = self.__RPi_GPIO
		tmpBytes = self.__tmpStoreBytes
		cpu = self.sim.cpu
		for byteOffset, bitMapping in self.__inputList:
			inByte = 0
			for bitOffset, bcmNumber in bitMapping.mapList:
				if RPi_GPIO.input(bcmNumber):
					inByte |= 1 << bitOffset
			tmpBytes[0] = inByte
			self.sim.cpu.storeInputRange(byteOffset, tmpBytes)

	def writeOutputs(self): #+cdef
#@cy		cdef S7CPU cpu
#@cy		cdef uint32_t byteOffset
#@cy		cdef uint32_t bitOffset

		RPi_GPIO = self.__RPi_GPIO
		cpu = self.sim.cpu
		for byteOffset, bitMapping in self.__outputList:
			outByte = cpu.fetchOutputRange(byteOffset, 1)[0]
			for bitOffset, bcmNumber in bitMapping.mapList:
				RPi_GPIO.output(bcmNumber,
						outByte & (1 << bitOffset))

	def directReadInput(self, accessWidth, accessOffset): #@nocy
#@cy	cdef bytearray directReadInput(self, uint32_t accessWidth, uint32_t accessOffset):
#@cy		cdef uint32_t nrBytes

		if accessOffset < self.inputAddressBase:
			return None

		RPi_GPIO = self.__RPi_GPIO
		nrBytes = accessWidth // 8
		pass#TODO

		return bytearray()

	def directWriteOutput(self, accessWidth, accessOffset, data): #@nocy
#@cy	cdef ExBool_t directWriteOutput(self, uint32_t accessWidth, uint32_t accessOffset, bytearray data) except ExBool_val:
#@cy		cdef uint32_t nrBytes

		if accessOffset < self.outputAddressBase:
			return False

		RPi_GPIO = self.__RPi_GPIO
		nrBytes = accessWidth // 8
		pass#TODO

		return True

# Module entry point
HardwareInterface = RpiGPIO_HwInterface

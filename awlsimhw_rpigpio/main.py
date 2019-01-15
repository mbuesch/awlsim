# -*- coding: utf-8 -*-
#
# AWL simulator - Raspberry Pi GPIO hardware interface
#
# Copyright 2016-2019 Michael Buesch <m@bues.ch>
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

from awlsim.common.util import *
from awlsim.common.exceptions import *

#from awlsimhw_rpigpio.main cimport * #@cy

from awlsim.core.hardware_params import *
from awlsim.core.hardware import * #+cimport
from awlsim.core.operators import * #+cimport
from awlsim.core.offset import * #+cimport
from awlsim.core.cpu import * #+cimport

import re

#cimport cython #@cy


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

class RpiGPIO_BitMapping(object): #+cdef
	"""Awlsim -> RaspiGPIO memory bit mapping.
	"""

	__slots__ = (
		"__bit2bcm",
		"bitOffsets",
		"bcmNumbers",
		"currentOutputValues",
		"size",
	)

	def __init__(self):
		# Bit number to BCM GPIO number map.
		self.__bit2bcm = {}
		self.bitOffsets = [None] * 8 #@nocy
		self.bcmNumbers = [None] * 8
		self.currentOutputValues = [None] * 8 #@nocy

	def setBit(self, bitOffset, bcmNumber):
		assert(bitOffset >= 0 and bitOffset <= 7)
		self.__bit2bcm[bitOffset] = bcmNumber

	def build(self):
		self.bitOffsets = [None] * 8 #@nocy
		self.bcmNumbers = [None] * 8
		self.currentOutputValues = [None] * 8 #@nocy
		self.size = 0
		for bitOffset, bcmNumber in sorted(dictItems(self.__bit2bcm),
						   key=lambda x: x[0]):
			self.bitOffsets[self.size] = bitOffset
			self.bcmNumbers[self.size] = bcmNumber
			self.currentOutputValues[self.size] = 0xFF # Neither 0 nor 1
			self.size += 1

	def __repr__(self): #@nocov
		return "{ " +\
			", ".join("%d: %s" % (bitOffset, str(bcmNumber))
				  for bitOffset, bcmNumber in sorted(dictItems(self.__bit2bcm),
								     key=lambda x: x[0])) +\
		       " }"

class RpiGPIO_HwInterface(AbstractHardwareInterface): #+cdef
	"""Raspberry Pi GPIO hardware interface.
	"""
	name		= "RPi.GPIO"
	description	= "Raspberry Pi GPIO support.\n"\
			  "https://www.raspberrypi.org/"

	paramDescs = [
		HwParamDesc_IMap(),
		HwParamDesc_QMap(),
	]

	def __init__(self, sim, parameters={}):
		AbstractHardwareInterface.__init__(self,
						   sim = sim,
						   parameters = parameters)

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
		except ImportError as e: #@nocov
			self.raiseException("Failed to import Raspberry Pi GPIO "
				"module 'RPi.GPIO': %s" % str(e))

		# Copy shortcuts to Raspberry Pi GPIO module
		self.__RPi_GPIO_input = self.__RPi_GPIO.input
		self.__RPi_GPIO_output = self.__RPi_GPIO.output

		# Initialize the GPIO library
		try:
			RPi_GPIO.setmode(self.__RPi_GPIO.BCM)
			RPi_GPIO.setwarnings(False)
		except RuntimeError as e: #@nocov
			self.raiseException("Failed to init Raspberry Pi "
				"GPIO library: %s" % str(e))

		# Build the memory mappings
		self.__inputByteOffsetList, self.__inputBitMappingList = self.__mapGPIO(
				inputs, HwParamDesc_IMap._nameRe, RPi_GPIO.IN,
				self.inputAddressBase)
		self.__inputListSize = len(self.__inputByteOffsetList)
		self.__outputByteOffsetList, self.__outputBitMappingList = self.__mapGPIO(
				outputs, HwParamDesc_QMap._nameRe, RPi_GPIO.OUT,
				self.outputAddressBase)
		self.__outputListSize = len(self.__outputByteOffsetList)

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
			except RuntimeError as e: #@nocov
				self.raiseException("Failed to init Raspberry Pi "
					"BCM%d: %s" % (bcmNumber, str(e)))

		for bitMapping in dictValues(mapDict):
			bitMapping.build()

		byteOffsetList = []
		bitMappingList = []
		for byteOffset, bitMapping in sorted(dictItems(mapDict),
						     key=lambda x: x[0]):
			byteOffsetList.append(byteOffset)
			bitMappingList.append(bitMapping)
		return byteOffsetList, bitMappingList

	def doShutdown(self):
		pass # Do nothing

#@cy	@cython.boundscheck(False)
	def readInputs(self): #+cdef
#@cy		cdef uint8_t inByte
#@cy		cdef RpiGPIO_BitMapping bitMapping
#@cy		cdef uint32_t byteOffset
#@cy		cdef uint32_t i
#@cy		cdef uint32_t j

		# Note: Bounds checking of the indexing operator [] is disabled
		#       by @cython.boundscheck(False) in this method.

		for i in range(self.__inputListSize):
			byteOffset = self.__inputByteOffsetList[i]
			bitMapping = self.__inputBitMappingList[i]
			inByte = 0
			for j in range(bitMapping.size):
				if self.__RPi_GPIO_input(bitMapping.bcmNumbers[j]):
					inByte |= 1 << bitMapping.bitOffsets[j] #+suffix-u
			self.sim.cpu.storeInputByte(byteOffset, inByte)

#@cy	@cython.boundscheck(False)
	def writeOutputs(self): #+cdef
#@cy		cdef RpiGPIO_BitMapping bitMapping
#@cy		cdef uint32_t byteOffset
#@cy		cdef uint8_t outByte
#@cy		cdef uint8_t newValue
#@cy		cdef uint32_t i
#@cy		cdef uint32_t j

		# Note: Bounds checking of the indexing operator [] is disabled
		#       by @cython.boundscheck(False) in this method.

		for i in range(self.__outputListSize):
			byteOffset = self.__outputByteOffsetList[i]
			bitMapping = self.__outputBitMappingList[i]
			outByte = self.sim.cpu.fetchOutputByte(byteOffset)
			for j in range(bitMapping.size):
				newValue = (outByte >> bitMapping.bitOffsets[j]) & 1 #+suffix-u
				if newValue != bitMapping.currentOutputValues[j]:
					self.__RPi_GPIO_output(bitMapping.bcmNumbers[j], newValue)
					bitMapping.currentOutputValues[j] = newValue

#@cy	@cython.boundscheck(False)
	def directReadInput(self, accessWidth, accessOffset): #@nocy
#@cy	cdef bytearray directReadInput(self, uint32_t accessWidth, uint32_t accessOffset):
#@cy		cdef uint32_t nrBytes
#@cy		cdef uint32_t accessEndOffset
#@cy		cdef RpiGPIO_BitMapping bitMapping
#@cy		cdef uint32_t byteOffset
#@cy		cdef uint32_t dataOffset
#@cy		cdef uint8_t inByte
#@cy		cdef uint32_t i
#@cy		cdef uint32_t j
#@cy		cdef bytearray retData

		# Note: Bounds checking of the indexing operator [] is disabled
		#       by @cython.boundscheck(False) in this method.

		if accessOffset < self.inputAddressBase:
			return None

		nrBytes = accessWidth // 8			#+suffix-u
		accessEndOffset = accessOffset + (nrBytes - 1)	#+suffix-u

		retData = bytearray(nrBytes)
		for i in range(self.__inputListSize):
			byteOffset = self.__inputByteOffsetList[i]
			if not (accessOffset <= byteOffset <= accessEndOffset):
				continue
			bitMapping = self.__inputBitMappingList[i]
			inByte = 0
			for j in range(bitMapping.size):
				if self.__RPi_GPIO_input(bitMapping.bcmNumbers[j]):
					inByte |= 1 << bitMapping.bitOffsets[j] #+suffix-u
			dataOffset = byteOffset - accessOffset
			retData[dataOffset] = inByte
		return retData

#@cy	@cython.boundscheck(False)
	def directWriteOutput(self, accessWidth, accessOffset, data): #@nocy
#@cy	cdef ExBool_t directWriteOutput(self, uint32_t accessWidth, uint32_t accessOffset, bytearray data) except ExBool_val:
#@cy		cdef uint32_t nrBytes
#@cy		cdef uint32_t accessEndOffset
#@cy		cdef RpiGPIO_BitMapping bitMapping
#@cy		cdef uint32_t byteOffset
#@cy		cdef uint32_t dataOffset
#@cy		cdef uint8_t outByte
#@cy		cdef uint8_t newValue
#@cy		cdef uint32_t i
#@cy		cdef uint32_t j
#@cy		cdef _Bool wroteAny

		# Note: Bounds checking of the indexing operator [] is disabled
		#       by @cython.boundscheck(False) in this method.

		if accessOffset < self.outputAddressBase:
			return False

		nrBytes = accessWidth // 8			#+suffix-u
		accessEndOffset = accessOffset + (nrBytes - 1)	#+suffix-u
		wroteAny = False

		for i in range(self.__outputListSize):
			byteOffset = self.__outputByteOffsetList[i]
			if not (accessOffset <= byteOffset <= accessEndOffset):
				continue
			bitMapping = self.__outputBitMappingList[i]
			dataOffset = byteOffset - accessOffset
			outByte = data[dataOffset]
			for j in range(bitMapping.size):
				newValue = (outByte >> bitMapping.bitOffsets[j]) & 1 #+suffix-u
				if newValue != bitMapping.currentOutputValues[j]:
					self.__RPi_GPIO_output(bitMapping.bcmNumbers[j], newValue)
					bitMapping.currentOutputValues[j] = newValue
			wroteAny = True
		return wroteAny

# Module entry point
HardwareInterface = RpiGPIO_HwInterface

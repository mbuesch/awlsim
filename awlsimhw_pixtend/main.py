# -*- coding: utf-8 -*-
#
# AWL simulator - PiXtend HAL interface
#
# Copyright 2018 Michael Buesch <m@bues.ch>
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

#from awlsimhw_pixtend.main cimport * #@cy

from awlsim.common.datatypehelpers import * #+cimport

from awlsim.core.hardware_params import *
from awlsim.core.hardware import * #+cimport
from awlsim.core.operators import * #+cimport
from awlsim.core.offset import * #+cimport
from awlsim.core.cpu import * #+cimport

import time


class AbstractIO(object):
	setters = ()
	getters = ()
	directionSetters = ()

	def __init__(self, pixtend, index, bitOffset):
		self.pixtend = pixtend
		self.index = index
		self.byteOffset = bitOffset // 8
		self.bitOffset = bitOffset % 8

	def setup(self, secondaryOffset):
		self.byteOffset += secondaryOffset
		self.bitMask = 1 << self.bitOffset
		self.invBitMask = (~self.bitMask) & 0xFF
		try:
			self.setter = self.setters[self.index]
		except IndexError:
			self.setter = None
		try:
			self.getter = self.getters[self.index]
		except IndexError:
			self.getter = None
		try:
			self.directionSetter = self.directionSetters[self.index]
		except IndexError:
			self.directionSetter = None

	def set(self, dataBytes):
		self.setter(self, (dataBytes[self.byteOffset] >> self.bitOffset) & 1)

	def get(self, dataBytes):
		if self.getter(self):
			dataBytes[self.byteOffset] |= self.bitMask
		else:
			dataBytes[self.byteOffset] &= self.invBitMask

	def setDirection(self, outDirection):
		if self.directionSetter:
			self.directionSetter(self, outDirection)

class Relay(AbstractIO):
	def __setRelay0(self, state):
		self.pixtend.relay0 = state

	def __setRelay1(self, state):
		self.pixtend.relay1 = state

	def __setRelay2(self, state):
		self.pixtend.relay2 = state

	def __setRelay3(self, state):
		self.pixtend.relay3 = state

	setters = (
		__setRelay0,
		__setRelay1,
		__setRelay2,
		__setRelay3,
	)

class DigitalOut(AbstractIO):
	def __setDO0(self, state):
		self.pixtend.digital_output0 = state

	def __setDO1(self, state):
		self.pixtend.digital_output1 = state

	def __setDO2(self, state):
		self.pixtend.digital_output2 = state

	def __setDO3(self, state):
		self.pixtend.digital_output3 = state

	def __setDO4(self, state):
		self.pixtend.digital_output4 = state

	def __setDO5(self, state):
		self.pixtend.digital_output5 = state

	setters = (
		__setDO0,
		__setDO1,
		__setDO2,
		__setDO3,
		__setDO4,
		__setDO5,
	)

class DigitalIn(AbstractIO):
	def __getDI0(self):
		return self.pixtend.digital_input0

	def __getDI1(self):
		return self.pixtend.digital_input1

	def __getDI2(self):
		return self.pixtend.digital_input2

	def __getDI3(self):
		return self.pixtend.digital_input3

	def __getDI4(self):
		return self.pixtend.digital_input4

	def __getDI5(self):
		return self.pixtend.digital_input5

	def __getDI6(self):
		return self.pixtend.digital_input6

	def __getDI7(self):
		return self.pixtend.digital_input7

	getters = (
		__getDI0,
		__getDI1,
		__getDI2,
		__getDI3,
		__getDI4,
		__getDI5,
		__getDI6,
		__getDI7,
	)

class GPIO(AbstractIO):
	def __getGPIO0(self):
		return self.pixtend.gpio0

	def __getGPIO1(self):
		return self.pixtend.gpio1

	def __getGPIO2(self):
		return self.pixtend.gpio2

	def __getGPIO3(self):
		return self.pixtend.gpio3

	getters = (
		__getGPIO0,
		__getGPIO1,
		__getGPIO2,
		__getGPIO3,
	)

	def __setGPIO0(self, state):
		self.pixtend.gpio0 = state

	def __setGPIO1(self, state):
		self.pixtend.gpio1 = state

	def __setGPIO2(self, state):
		self.pixtend.gpio2 = state

	def __setGPIO3(self, state):
		self.pixtend.gpio3 = state

	setters = (
		__setGPIO0,
		__setGPIO1,
		__setGPIO2,
		__setGPIO3,
	)

	def __setDirGPIO0(self, outDirection):
		self.pixtend.gpio0_direction =\
			self.pixtend.GPIO_OUTPUT if outDirection else\
			self.pixtend.GPIO_INPUT

	def __setDirGPIO1(self, outDirection):
		self.pixtend.gpio1_direction =\
			self.pixtend.GPIO_OUTPUT if outDirection else\
			self.pixtend.GPIO_INPUT

	def __setDirGPIO2(self, outDirection):
		self.pixtend.gpio2_direction =\
			self.pixtend.GPIO_OUTPUT if outDirection else\
			self.pixtend.GPIO_INPUT

	def __setDirGPIO3(self, outDirection):
		self.pixtend.gpio3_direction =\
			self.pixtend.GPIO_OUTPUT if outDirection else\
			self.pixtend.GPIO_INPUT

	directionSetters = (
		__setDirGPIO0,
		__setDirGPIO1,
		__setDirGPIO2,
		__setDirGPIO3,
	)

class HardwareInterface_PiXtend(AbstractHardwareInterface): #+cdef
	name = "PiXtend"

	#TODO DHT
	#TODO servo
	#TODO PWM
	#TODO analog in
	#TODO hum
	#TODO DAC
	#TODO RS232
	#TODO RS485

	NR_RELAYS	= 4
	NR_DO		= 6
	NR_DI		= 8
	NR_GPIO		= 4
	NR_DAC		= 2
	NR_ADC		= 4

	paramDescs = [
		HwParamDesc_int("pollIntMs",
				defaultValue=100,
				minValue=25,
				maxValue=10000,
				description="PiXtend auto-mode poll interval time, in milliseconds"),
		HwParamDesc_bool("testMode",
				defaultValue=False,
				description="Enable testing mode. DO NOT USE THIS OPTION!",
				hidden=True),
	]
	for i in range(NR_RELAYS):
		paramDescs.append(HwParamDesc_outAddr(
				"relay%d" % i,
				description="Relay output %d address" % i))
	for i in range(NR_DO):
		paramDescs.append(HwParamDesc_outAddr(
				"do%d" % i,
				description="Digital output %d address" % i))
	for i in range(NR_DI):
		paramDescs.append(HwParamDesc_inAddr(
				"di%d" % i,
				description="Digital input %d address" % i))
	for i in range(NR_GPIO):
		paramDescs.append(HwParamDesc_inOutAddr(
				"gpio%d" % i,
				description="GPIO %d address (can be input (I/E) or output (Q/A))" % i))
	for i in range(NR_DAC):
		paramDescs.append(HwParamDesc_outAddr(
				"analogOut%s" % ("AB"[i]),
				description="Analog output (DAC) %s address" % ("AB"[i])))
	for i in range(NR_ADC):
		paramDescs.append(HwParamDesc_inAddr(
				"analogIn%d" % i,
				description="Analog input %d address" % i))

	def __init__(self, sim, parameters={}):
		AbstractHardwareInterface.__init__(self,
						   sim = sim,
						   parameters = parameters)
		self.__pixtendInitialized = False
		self.__pixtend = None

	def __build(self):
		def updateOffs(byteOffset, first, last):
			if first is None or byteOffset < first:
				first = byteOffset
			if last is None or byteOffset > last:
				last = byteOffset
			return first, last

		# Build all Relay() objects
		self.__relays = []
		firstRelayByte = lastRelayByte = None
		for i in range(self.NR_RELAYS):
			bitOffset = self.getParamValueByName("relay%d" % i)
			if bitOffset is None:
				continue
			r = Relay(self.__pixtend, i, bitOffset)
			self.__relays.append(r)
			firstRelayByte, lastRelayByte = updateOffs(
					bitOffset // 8, firstRelayByte, lastRelayByte)

		# Build all DigitalOut() objects
		self.__DOs = []
		firstDOByte = lastDOByte = None
		for i in range(self.NR_DO):
			bitOffset = self.getParamValueByName("do%d" % i)
			if bitOffset is None:
				continue
			do = DigitalOut(self.__pixtend, i, bitOffset)
			self.__DOs.append(do)
			firstDOByte, lastDOByte = updateOffs(
					bitOffset // 8, firstDOByte, lastDOByte)

		# Build all DigitalIn() objects
		self.__DIs = []
		firstDIByte = lastDIByte = None
		for i in range(self.NR_DI):
			bitOffset = self.getParamValueByName("di%d" % i)
			if bitOffset is None:
				continue
			di = DigitalIn(self.__pixtend, i, bitOffset)
			self.__DIs.append(di)
			firstDIByte, lastDIByte = updateOffs(
					bitOffset // 8, firstDIByte, lastDIByte)

		# Build all GPIO output objects
		self.__GPIO_out = []
		firstGPIOOutByte = lastGPIOOutByte = None
		for i in range(self.NR_GPIO):
			param = self.getParamValueByName("gpio%d" % i)
			if param is None:
				continue
			direction, bitOffset = param
			if direction != HwParamDesc_inOutAddr.OUT:
				continue
			gpio = GPIO(self.__pixtend, i, bitOffset)
			self.__GPIO_out.append(gpio)
			firstGPIOOutByte, lastGPIOOutByte = updateOffs(
					bitOffset // 8, firstGPIOOutByte, lastGPIOOutByte)

		# Build all GPIO input objects
		self.__GPIO_in = []
		firstGPIOInByte = lastGPIOInByte = None
		for i in range(self.NR_GPIO):
			param = self.getParamValueByName("gpio%d" % i)
			if param is None:
				continue
			direction, bitOffset = param
			if direction != HwParamDesc_inOutAddr.IN:
				continue
			gpio = GPIO(self.__pixtend, i, bitOffset)
			self.__GPIO_in.append(gpio)
			firstGPIOInByte, lastGPIOInByte = updateOffs(
					bitOffset // 8, firstGPIOInByte, lastGPIOInByte)

		# Find the offsets of the first and the last output byte
		firstOutByte = lastOutByte = None
		for offs in (firstRelayByte, firstDOByte, firstGPIOOutByte):
			if offs is not None:
				firstOutByte, lastOutByte = updateOffs(offs,
					firstOutByte, lastOutByte)

		# Find the offsets of the first and the last input byte
		firstInByte = lastInByte = None
		for offs in (firstDIByte, firstGPIOInByte):
			if offs is not None:
				firstInByte, lastInByte = updateOffs(offs,
					firstInByte, lastInByte)

		# Store the output base and size
		if firstOutByte is None or lastOutByte is None:
			self.__outBase = 0
			self.__outSize = 0
		else:
			self.__outBase = self.outputAddressBase + firstOutByte
			self.__outSize = lastOutByte - firstOutByte + 1

			# Setup all outputs
			for out in itertools.chain(self.__relays,
						   self.__DOs,
						   self.__GPIO_out):
				out.setup(secondaryOffset=(-firstOutByte))
				out.setDirection(outDirection=True)

		# Store the input base and size
		if firstInByte is None or lastInByte is None:
			self.__inBase = 0
			self.__inSize = 0
		else:
			self.__inBase = self.inputAddressBase + firstInByte
			self.__inSize = lastInByte - firstInByte + 1

			# Setup all inputs
			for inp in itertools.chain(self.__DIs,
						   self.__GPIO_in):
				inp.setup(secondaryOffset=(-firstInByte))
				inp.setDirection(outDirection=False)

	def doStartup(self):
		if not self.__pixtendInitialized:
			try:
				from pixtendlib import Pixtend
				self.__PiXtend_class = Pixtend
			except ImportError as e:
				self.raiseException("Failed to import pixtendlib.Pixtend module"
					":\n%s" % str(e))

			self.__pollInt = float(self.getParamValueByName("pollIntMs")) / 1000.0
			if self.getParamValueByName("testMode"):
				self.__pollInt = 0.0 # In test mode use poll interval = 0

			# Initialize PiXtend
			try:
				self.__pixtend = self.__PiXtend_class()
				self.__pixtend.open()
				t = 0
				while not self.__pixtendPoll(self.cpu.now):
					t += 1
					if t >= 50:
						self.raiseException("Timeout waiting "
							"for PiXtend auto-mode.")
					time.sleep(self.__pollInt)
			except Exception as e:
				self.raiseException("Failed to init PiXtend: %s" % (
					str(e)))
			self.__build()

			self.__nextPoll = self.cpu.now + self.__pollInt
			self.__pixtendInitialized = True

	def doShutdown(self):
		if self.__pixtendInitialized:
			self.__pixtend.close()
			self.__pixtend = None
			self.__pixtendInitialized = False

	def readInputs(self): #+cdef
		cpu = self.cpu

		size = self.__inSize
		if size:
			data = cpu.fetchInputRange(self.__inBase, size)

			# Handle digital inputs
			for di in self.__DIs:
				di.get(data)
			# Handle all GPIO inputs
			for gpio in self.__GPIO_in:
				gpio.get(data)

			cpu.storeInputRange(self.__inBase, data)

	def writeOutputs(self): #+cdef
		cpu = self.cpu

		size = self.__outSize
		if size:
			data = cpu.fetchOutputRange(self.__outBase, size)

			# Handle relays
			for relay in self.__relays:
				relay.set(data)
			# Handle digital outputs
			for do in self.__DOs:
				do.set(data)
			# Handle all GPIO outputs
			for gpio in self.__GPIO_out:
				gpio.set(data)

		# Run one PiXtend poll cycle, if required.
		now = cpu.now
		if now >= self.__nextPoll:
			if not self.__pixtendPoll(now):
				self.raiseException("PiXtend auto_mode() poll failed.")

	def __pixtendPoll(self, now):
		# Poll PiXtend auto_mode
		self.__nextPoll = now + self.__pollInt
		return self.__pixtend.auto_mode() == 0 and\
		       (self.__pixtend.uc_status & 1) != 0

	def __syncPixtendPoll(self):
		# Synchronously run one PiXtend poll cycle.
		cpu = self.cpu
		retries = 0
		while True:
			# Wait for the next possible poll slot.
			timeout = int(self.__pollInt * 2000.0)
			while cpu.now < self.__nextPoll:
				timeout -= 1
				if timeout <= 0:
					self.raiseException("PiXtend poll wait timeout.")
				time.sleep(0.001)
				cpu.updateTimestamp()
			# Poll PiXtend.
			if not self.__pixtendPoll(cpu.now):
				retries += 1
				if retries >= 3:
					self.raiseException("PiXtend auto_mode() poll failed (sync).")

	def directReadInput(self, accessWidth, accessOffset): #@nocy
#@cy	cdef bytearray directReadInput(self, uint32_t accessWidth, uint32_t accessOffset):
		self.__syncPixtendPoll()
		pass#TODO
		return bytearray()

	def directWriteOutput(self, accessWidth, accessOffset, data): #@nocy
#@cy	cdef ExBool_t directWriteOutput(self, uint32_t accessWidth, uint32_t accessOffset, bytearray data) except ExBool_val:
		pass#TODO
		self.__syncPixtendPoll()
		return False

# Module entry point
HardwareInterface = HardwareInterface_PiXtend

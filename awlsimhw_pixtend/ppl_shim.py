# -*- coding: utf-8 -*-
#
# AWL simulator - PiXtend hardware interface
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
from awlsim.common.enumeration import *
from awlsim.common.exceptions import *
from awlsim.common.datatypehelpers import * #+cimport


__all__ = [
	"Relay",
	"DigitalOut",
	"DigitalIn",
	"GPIO",
	"AnalogIn",
	"AnalogOut",
	"PWMPeriod",
	"PWM",
]

class AbstractIO(object): #+cdef
	"""PiXtend abstract I/O handler.
	"""

	setters = ()
	getters = ()
	directionSetters = ()

	def __init__(self, pixtend, index, bitOffset, directOnly=False, bitSize=1):
		"""PiXtend I/O abstraction layer.
		pixtend:	class Pixtend instance
		index:		Index number of this I/O resource.
				e.g. 2 for DI2.
		bitOffset:	The bit offset in the AWL E or A region this
				PiXtend resource is mapped to.
		directOnly:	If False, then the resource is read/written in the
				user cycle and stored in or written to the process image
				region specified by bitOffset.
				If True, this resource is only accessible by
				direct PEx or PAx access only.
		bitSize:	The size of this I/O instance, in bits.
		"""
		self.pixtend = pixtend
		self.index = index
		self.byteOffset = bitOffset // 8
		self.bitOffset = bitOffset % 8
		self.directOnly = directOnly
		self.bitSize = bitSize
		self.byteSize = intDivRoundUp(self.bitSize, 8)

	def setup(self, secondaryOffset): #+cpdef
		self.byteOffset += secondaryOffset
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

	def set(self, dataBytes): #@nocy
#@cy	cdef set(self, bytearray dataBytes):
		self.setWithByteOffset(dataBytes, self.byteOffset)

	def setWithByteOffset(self, dataBytes, byteOffset): #@nocy
#@cy	cdef setWithByteOffset(self, bytearray dataBytes, uint32_t byteOffset):
		raise NotImplementedError

	def get(self, dataBytes): #@nocy
#@cy	cdef get(self, bytearray dataBytes):
		self.getWithByteOffset(dataBytes, self.byteOffset)

	def getWithByteOffset(self, dataBytes, byteOffset): #@nocy
#@cy	cdef getWithByteOffset(self, bytearray dataBytes, uint32_t byteOffset):
		raise NotImplementedError

	def setDirection(self, outDirection): #+cpdef
		if self.directionSetter:
			self.directionSetter(self, outDirection)

class AbstractBitIO(AbstractIO): #+cdef
	"""PiXtend abstract bit I/O handler.
	"""

	def __init__(self, *args, **kwargs):
		AbstractIO.__init__(self, *args, bitSize=1, **kwargs)

	def setup(self, secondaryOffset): #+cpdef
		AbstractIO.setup(self, secondaryOffset)

		self.bitMask = 1 << self.bitOffset
		self.invBitMask = (~self.bitMask) & 0xFF

	def setWithByteOffset(self, dataBytes, byteOffset): #@nocy
#@cy	cdef setWithByteOffset(self, bytearray dataBytes, uint32_t byteOffset):
		self.setter(self, (dataBytes[byteOffset] >> self.bitOffset) & 1)

	def getWithByteOffset(self, dataBytes, byteOffset): #@nocy
#@cy	cdef getWithByteOffset(self, bytearray dataBytes, uint32_t byteOffset):
		if self.getter(self):
			dataBytes[byteOffset] |= self.bitMask
		else:
			dataBytes[byteOffset] &= self.invBitMask

class AbstractWordIO(AbstractIO): #+cdef
	"""PiXtend abstract word I/O handler.
	"""

	def __init__(self, *args, **kwargs):
		AbstractIO.__init__(self, *args, bitSize=16, **kwargs)

	def setWithByteOffset(self, dataBytes, byteOffset): #@nocy
#@cy	cdef setWithByteOffset(self, bytearray dataBytes, uint32_t byteOffset):
		self.setter(self,
			    (dataBytes[byteOffset] << 8) |\
			    (dataBytes[byteOffset + 1]))

	def getWithByteOffset(self, dataBytes, byteOffset): #@nocy
#@cy	cdef getWithByteOffset(self, bytearray dataBytes, uint32_t byteOffset):
#@cy		cdef uint16_t value

		value = self.getter(self)
		dataBytes[byteOffset] = (value >> 8) & 0xFF
		dataBytes[byteOffset + 1] = value & 0xFF

class Relay(AbstractBitIO): #+cdef
	"""PiXtend relay I/O handler.
	"""

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

class DigitalOut(AbstractBitIO): #+cdef
	"""PiXtend digital output I/O handler.
	"""

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

class DigitalIn(AbstractBitIO): #+cdef
	"""PiXtend digital input I/O handler.
	"""

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

class GPIO(AbstractBitIO): #+cdef
	"""PiXtend GPIO I/O handler.
	"""

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

class AnalogIn(AbstractWordIO): #+cdef
	"""PiXtend analog input I/O handler.
	"""

	def __init__(self, *args, **kwargs):
		AbstractWordIO.__init__(self, *args, **kwargs)

		self.jumper10V = None
		self.numberOfSamples = None

	def __convertV(self, V): #@nocy
#@cy	cdef uint16_t __convertV(self, double V):
		return max(min(int(round(V * 2764.8)), 32767), -32768)

	def __convertMA(self, mA): #@nocy
#@cy	cdef uint16_t __convertMA(self, double mA):
		return max(min(int(round((mA - 4.0) * 1728.0)), 32767), -32768)

	def __getAI0(self):
		return self.__convertV(self.pixtend.analog_input0)

	def __getAI1(self):
		return self.__convertV(self.pixtend.analog_input1)

	def __getAI2(self):
		return self.__convertMA(self.pixtend.analog_input2)

	def __getAI3(self):
		return self.__convertMA(self.pixtend.analog_input3)

	getters = (
		__getAI0,
		__getAI1,
		__getAI2,
		__getAI3,
	)

	def __setJumper10V_AI0(self, jumper10V):
		self.pixtend.analog_input0_10volts_jumper = jumper10V

	def __setJumper10V_AI1(self, jumper10V):
		self.pixtend.analog_input1_10volts_jumper = jumper10V

	settersJumper10V = (
		__setJumper10V_AI0,
		__setJumper10V_AI1,
	)

	def __setNos_AI0(self, nos):
		self.pixtend.analog_input0_nos = nos

	def __setNos_AI1(self, nos):
		self.pixtend.analog_input1_nos = nos

	def __setNos_AI2(self, nos):
		self.pixtend.analog_input2_nos = nos

	def __setNos_AI3(self, nos):
		self.pixtend.analog_input3_nos = nos

	settersNos = (
		__setNos_AI0,
		__setNos_AI1,
		__setNos_AI2,
		__setNos_AI3,
	)

	@staticmethod
	def setFreq(pixtend, freqKHz):
		kHz2MHz = {
			125	: 0.125,
			250	: 0.250,
			500	: 0.500,
			1000	: 1.0,
			2000	: 2.0,
			4000	: 4.0,
			8000	: 8.0,
		}
		try:
			freqMHz = kHz2MHz[freqKHz]
		except KeyError as e:
			raise ValueError
		pixtend.analog_input_nos_freq = freqMHz

	def setup(self, secondaryOffset): #+cpdef
		AbstractWordIO.setup(self, secondaryOffset)

		if self.jumper10V is not None:
			setJumper10V = self.settersJumper10V[self.index]
			setJumper10V(self, self.pixtend.ON if self.jumper10V
					   else self.pixtend.OFF)

		if self.numberOfSamples is not None:
			setNos = self.settersNos[self.index]
			setNos(self, self.numberOfSamples)

class AnalogOut(AbstractWordIO): #+cdef
	"""PiXtend analog output I/O handler.
	"""

	def __convert(self, s7Value): #@nocy
#@cy	cdef uint16_t __convert(self, uint16_t s7Value):
		# dac = (s7Value / 27648) * 1023
		return clamp(int(round((wordToSignedPyInt(s7Value) * 1023) / 27648)),
			     0, 1023)

	def __setAO0(self, value):
		pixtend = self.pixtend
		pixtend.dac_selection = pixtend.DAC_A
		pixtend.set_dac_output(self.__convert(value))

	def __setAO1(self, value):
		pixtend = self.pixtend
		pixtend.dac_selection = pixtend.DAC_B
		pixtend.set_dac_output(self.__convert(value))

	setters = (
		__setAO0,
		__setAO1,
	)

class PWMPeriod(AbstractWordIO): #+cdef
	"""PiXtend PWM period I/O handler.
	"""

	def setPWMPeriod(self, period):
		self.pixtend.pwm_ctrl_period = clamp(period, 0, 65000)
		self.pixtend.pwm_ctrl_configure()

	setters = (
		setPWMPeriod,
	)

class PWM(AbstractWordIO): #+cdef
	"""PiXtend PWM output I/O handler.
	"""

	def __init__(self, *args, **kwargs):
		AbstractWordIO.__init__(self, *args, **kwargs)

		self.overDrive = None

	def __setPWM0(self, value):
		self.pixtend.pwm0 = clamp(value, 0, 65000)

	def __setPWM1(self, value):
		self.pixtend.pwm1 = clamp(value, 0, 65000)

	setters = (
		__setPWM0,
		__setPWM1,
	)

	@staticmethod
	def setServoMode(pixtend, enServoMode):
		pixtend.pwm_ctrl_mode = 0 if enServoMode else 1
		pixtend.pwm_ctrl_configure()

	def __setServoOverDrive0(self, enOverDrive):
		self.pixtend.pwm_ctrl_od0 = 1 if enOverDrive else 0
		self.pixtend.pwm_ctrl_configure()

	def __setServoOverDrive1(self, enOverDrive):
		self.pixtend.pwm_ctrl_od1 = 1 if enOverDrive else 0
		self.pixtend.pwm_ctrl_configure()

	settersOverDrive = (
		__setServoOverDrive0,
		__setServoOverDrive1,
	)

	@staticmethod
	def setBaseFreq(pixtend, freqHz):
		cpuHz = 16000000
		csMap = {
			0		: (0, 0, 0), # PS=off
			cpuHz // 1	: (0, 0, 1), # PS=1
			cpuHz // 8	: (0, 1, 0), # PS=8
			cpuHz // 64	: (0, 1, 1), # PS=64
			cpuHz // 256	: (1, 0, 0), # PS=256
			cpuHz // 1024	: (1, 0, 1), # PS=1024
		}
		try:
			cs2, cs1, cs0 = csMap[freqHz]
		except KeyError as e:
			raise ValueError
		pixtend.pwm_ctrl_cs0 = cs0
		pixtend.pwm_ctrl_cs1 = cs1
		pixtend.pwm_ctrl_cs2 = cs2
		pixtend.pwm_ctrl_configure()

	def setup(self, secondaryOffset): #+cpdef
		AbstractWordIO.setup(self, secondaryOffset)

		if self.overDrive is not None:
			setOverDrive = self.settersOverDrive[self.index]
			setOverDrive(self, self.overDrive)

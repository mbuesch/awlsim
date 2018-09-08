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
#from awlsim.common.cython_support cimport * #@cy
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
	"EnvSensorBase",
	"TempIn",
	"HumIn",
	"AnalogIn",
	"AnalogOut",
	"PWM0Period",
	"PWM0",
	"PWM1Period",
	"PWM1",
]

class AbstractIO(object): #+cdef
	"""PiXtend abstract I/O handler.
	"""

	setters = ()
	getters = ()

	def __init__(self, pixtend, isV2, index, bitOffset, directOnly=False, bitSize=1):
		"""PiXtend I/O abstraction layer.
		pixtend:	class Pixtend instance
		isV2:		True, if 'pixtend' is V2.x.
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
		self.isV2 = isV2
		self.index = index
		self.byteOffset = bitOffset // 8
		self.bitOffset = bitOffset % 8
		self.directOnly = directOnly
		self.bitSize = bitSize
		self.byteSize = intDivRoundUp(self.bitSize, 8)

	def setup(self, secondaryOffset): #+cpdef
		self.byteOffset = max(self.byteOffset + secondaryOffset, 0)
		try:
			self.setter = self.setters[self.index]
		except IndexError:
			self.setter = None
		try:
			self.getter = self.getters[self.index]
		except IndexError:
			self.getter = None

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
		pixtend = self.pixtend
		pixtend.relay0 = pixtend.ON if state else pixtend.OFF

	def __setRelay1(self, state):
		pixtend = self.pixtend
		pixtend.relay1 = pixtend.ON if state else pixtend.OFF

	def __setRelay2(self, state):
		pixtend = self.pixtend
		pixtend.relay2 = pixtend.ON if state else pixtend.OFF

	def __setRelay3(self, state):
		pixtend = self.pixtend
		pixtend.relay3 = pixtend.ON if state else pixtend.OFF

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
		pixtend = self.pixtend
		if self.isV2:
			pixtend.digital_out0 = pixtend.ON if state else pixtend.OFF
		else:
			pixtend.digital_output0 = pixtend.ON if state else pixtend.OFF

	def __setDO1(self, state):
		pixtend = self.pixtend
		if self.isV2:
			pixtend.digital_out1 = pixtend.ON if state else pixtend.OFF
		else:
			pixtend.digital_output1 = pixtend.ON if state else pixtend.OFF

	def __setDO2(self, state):
		pixtend = self.pixtend
		if self.isV2:
			pixtend.digital_out2 = pixtend.ON if state else pixtend.OFF
		else:
			pixtend.digital_output2 = pixtend.ON if state else pixtend.OFF

	def __setDO3(self, state):
		pixtend = self.pixtend
		if self.isV2:
			pixtend.digital_out3 = pixtend.ON if state else pixtend.OFF
		else:
			pixtend.digital_output3 = pixtend.ON if state else pixtend.OFF

	def __setDO4(self, state):
		pixtend = self.pixtend
		if self.isV2:
			assert(0)
		else:
			pixtend.digital_output4 = pixtend.ON if state else pixtend.OFF

	def __setDO5(self, state):
		pixtend = self.pixtend
		if self.isV2:
			assert(0)
		else:
			pixtend.digital_output5 = pixtend.ON if state else pixtend.OFF

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
		pixtend = self.pixtend
		if self.isV2:
			return 1 if pixtend.digital_in0 == pixtend.ON else 0
		return 1 if pixtend.digital_input0 == pixtend.ON else 0

	def __getDI1(self):
		pixtend = self.pixtend
		if self.isV2:
			return 1 if pixtend.digital_in1 == pixtend.ON else 0
		return 1 if pixtend.digital_input1 == pixtend.ON else 0

	def __getDI2(self):
		pixtend = self.pixtend
		if self.isV2:
			return 1 if pixtend.digital_in2 == pixtend.ON else 0
		return 1 if pixtend.digital_input2 == pixtend.ON else 0

	def __getDI3(self):
		pixtend = self.pixtend
		if self.isV2:
			return 1 if pixtend.digital_in3 == pixtend.ON else 0
		return 1 if pixtend.digital_input3 == pixtend.ON else 0

	def __getDI4(self):
		pixtend = self.pixtend
		if self.isV2:
			return 1 if pixtend.digital_in4 == pixtend.ON else 0
		return 1 if pixtend.digital_input4 == pixtend.ON else 0

	def __getDI5(self):
		pixtend = self.pixtend
		if self.isV2:
			return 1 if pixtend.digital_in5 == pixtend.ON else 0
		return 1 if pixtend.digital_input5 == pixtend.ON else 0

	def __getDI6(self):
		pixtend = self.pixtend
		if self.isV2:
			return 1 if pixtend.digital_in6 == pixtend.ON else 0
		return 1 if pixtend.digital_input6 == pixtend.ON else 0

	def __getDI7(self):
		pixtend = self.pixtend
		if self.isV2:
			return 1 if pixtend.digital_in7 == pixtend.ON else 0
		return 1 if pixtend.digital_input7 == pixtend.ON else 0

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

	EnumGen.start
	MODE_OUTPUT	= EnumGen.item
	MODE_INPUT	= EnumGen.item
	MODE_DHT11	= EnumGen.item
	MODE_DHT22	= EnumGen.item
	EnumGen.end

	def __init__(self, *args, **kwargs):
		AbstractBitIO.__init__(self, *args, **kwargs)

		self.mode = None
		self.pullUp = None

	def __getGPIO0(self):
		pixtend = self.pixtend
		return 1 if pixtend.gpio0 == pixtend.ON else 0

	def __getGPIO1(self):
		pixtend = self.pixtend
		return 1 if pixtend.gpio1 == pixtend.ON else 0

	def __getGPIO2(self):
		pixtend = self.pixtend
		return 1 if pixtend.gpio2 == pixtend.ON else 0

	def __getGPIO3(self):
		pixtend = self.pixtend
		return 1 if pixtend.gpio3 == pixtend.ON else 0

	getters = (
		__getGPIO0,
		__getGPIO1,
		__getGPIO2,
		__getGPIO3,
	)

	def __setGPIO0(self, state):
		pixtend = self.pixtend
		pixtend.gpio0 = pixtend.ON if state else pixtend.OFF

	def __setGPIO1(self, state):
		pixtend = self.pixtend
		pixtend.gpio1 = pixtend.ON if state else pixtend.OFF

	def __setGPIO2(self, state):
		pixtend = self.pixtend
		pixtend.gpio2 = pixtend.ON if state else pixtend.OFF

	def __setGPIO3(self, state):
		pixtend = self.pixtend
		pixtend.gpio3 = pixtend.ON if state else pixtend.OFF

	setters = (
		__setGPIO0,
		__setGPIO1,
		__setGPIO2,
		__setGPIO3,
	)

	def __getV2Ctrl(self, mode):
		pixtend = self.pixtend
		ctrlValue = {
			self.MODE_OUTPUT : pixtend.GPIO_OUTPUT,
			self.MODE_INPUT  : pixtend.GPIO_INPUT,
			self.MODE_DHT11  : pixtend.GPIO_DHT11,
			self.MODE_DHT22  : pixtend.GPIO_DHT22,
		}[mode]
		return ctrlValue

	def __getV1Dir(self, mode):
		pixtend = self.pixtend
		if mode == self.MODE_OUTPUT:
			return pixtend.GPIO_OUTPUT
		return pixtend.GPIO_INPUT

	def __getV1DHTOn(self, mode):
		pixtend = self.pixtend
		if mode in {self.MODE_DHT11, self.MODE_DHT22}:
			return pixtend.ON
		return pixtend.OFF

	def __setModeGPIO0(self, mode):
		pixtend = self.pixtend
		if self.isV2:
			pixtend.gpio0_ctrl = self.__getV2Ctrl(mode)
		else:
			pixtend.gpio0_direction = self.__getV1Dir(mode)
			pixtend.dht0 = self.__getV1DHTOn(mode)

	def __setModeGPIO1(self, mode):
		pixtend = self.pixtend
		if self.isV2:
			pixtend.gpio1_ctrl = self.__getV2Ctrl(mode)
		else:
			pixtend.gpio1_direction = self.__getV1Dir(mode)
			pixtend.dht1 = self.__getV1DHTOn(mode)

	def __setModeGPIO2(self, mode):
		pixtend = self.pixtend
		if self.isV2:
			pixtend.gpio2_ctrl = self.__getV2Ctrl(mode)
		else:
			pixtend.gpio2_direction = self.__getV1Dir(mode)
			pixtend.dht2 = self.__getV1DHTOn(mode)

	def __setModeGPIO3(self, mode):
		pixtend = self.pixtend
		if self.isV2:
			pixtend.gpio3_ctrl = self.__getV2Ctrl(mode)
		else:
			pixtend.gpio3_direction = self.__getV1Dir(mode)
			pixtend.dht3 = self.__getV1DHTOn(mode)

	settersMode = (
		__setModeGPIO0,
		__setModeGPIO1,
		__setModeGPIO2,
		__setModeGPIO3,
	)

	def __setPullUp0(self, state):
		pixtend = self.pixtend
		if self.isV2:
			if pixtend.gpio_pullups_enable:
				pixtend.gpio0 = pixtend.ON if state else pixtend.OFF

	def __setPullUp1(self, state):
		pixtend = self.pixtend
		if self.isV2:
			if pixtend.gpio_pullups_enable:
				pixtend.gpio1 = pixtend.ON if state else pixtend.OFF

	def __setPullUp2(self, state):
		pixtend = self.pixtend
		if self.isV2:
			if pixtend.gpio_pullups_enable:
				pixtend.gpio2 = pixtend.ON if state else pixtend.OFF

	def __setPullUp3(self, state):
		pixtend = self.pixtend
		if self.isV2:
			if pixtend.gpio_pullups_enable:
				pixtend.gpio3 = pixtend.ON if state else pixtend.OFF

	settersPullUp = (
		__setPullUp0,
		__setPullUp1,
		__setPullUp2,
		__setPullUp3,
	)

	@staticmethod
	def setGlobalPullUpEnable(pixtend, isV2, pullUpEnable):
		if isV2:
			pixtend.gpio_pullups_enable = pixtend.ON if pullUpEnable else pixtend.OFF

	def setup(self, secondaryOffset): #+cpdef
		AbstractBitIO.setup(self, secondaryOffset)

		if self.mode is not None:
			setMode = self.settersMode[self.index]
			setMode(self, self.mode)

		if self.pullUp is not None:
			setPullUp = self.settersPullUp[self.index]
			setPullUp(self, self.pixtend.ON if self.pullUp
					else self.pixtend.OFF)

class EnvSensorBase(AbstractWordIO): #+cdef
	"""Environmental sensor base class.
	"""

	EnumGen.start
	TYPE_DHT11	= EnumGen.item
	TYPE_DHT22	= EnumGen.item
	EnumGen.end

	def __init__(self, sensorType, *args, **kwargs):
		AbstractWordIO.__init__(self, *args, **kwargs)
		self.sensorType = sensorType

		# Create a child GPIO object.
		gpioMode = {
			self.TYPE_DHT11 : GPIO.MODE_DHT11,
			self.TYPE_DHT22 : GPIO.MODE_DHT22,
		}[self.sensorType]
		self.gpio = GPIO(self.pixtend, self.isV2, self.index, 0, True)
		self.gpio.mode = gpioMode

	def setup(self, secondaryOffset): #+cpdef
		AbstractWordIO.setup(self, secondaryOffset)

		# Configure the child GPIO object.
		self.gpio.setup(secondaryOffset)

		#TODO Fahrenheit

class TempIn(EnvSensorBase): #+cdef
	"""DHT11/DHT22 temperature input.
	"""

	def __convert(self, temp): #@nocy
#@cy	cdef uint16_t __convert(self, double temp):
		return max(min(int(round(temp * 10.0)), 8500), -2000) & 0xFFFF

	def __getTemp0(self):
		if self.isV2:
			return self.__convert(self.pixtend.temp0)
		if self.sensorType == self.TYPE_DHT11:
			return self.__convert(self.pixtend.t0_dht11)
		return self.__convert(self.pixtend.t0_dht22)

	def __getTemp1(self):
		if self.isV2:
			return self.__convert(self.pixtend.temp1)
		if self.sensorType == self.TYPE_DHT11:
			return self.__convert(self.pixtend.t1_dht11)
		return self.__convert(self.pixtend.t1_dht22)

	def __getTemp2(self):
		if self.isV2:
			return self.__convert(self.pixtend.temp2)
		if self.sensorType == self.TYPE_DHT11:
			return self.__convert(self.pixtend.t2_dht11)
		return self.__convert(self.pixtend.t2_dht22)

	def __getTemp3(self):
		if self.isV2:
			return self.__convert(self.pixtend.temp3)
		if self.sensorType == self.TYPE_DHT11:
			return self.__convert(self.pixtend.t3_dht11)
		return self.__convert(self.pixtend.t3_dht22)

	getters = (
		__getTemp0,
		__getTemp1,
		__getTemp2,
		__getTemp3,
	)

class HumIn(EnvSensorBase): #+cdef
	"""DHT11/DHT22 humidity input.
	"""

	def __convert(self, hum): #@nocy
#@cy	cdef uint16_t __convert(self, double hum):
		return max(min(int(round(hum * 10.0)), 1000), 0)

	def __getHum0(self):
		if self.isV2:
			return self.__convert(self.pixtend.humid0)
		if self.sensorType == self.TYPE_DHT11:
			return self.__convert(self.pixtend.h0_dht11)
		return self.__convert(self.pixtend.h0_dht22)

	def __getHum1(self):
		if self.isV2:
			return self.__convert(self.pixtend.humid1)
		if self.sensorType == self.TYPE_DHT11:
			return self.__convert(self.pixtend.h1_dht11)
		return self.__convert(self.pixtend.h1_dht22)

	def __getHum2(self):
		if self.isV2:
			return self.__convert(self.pixtend.humid2)
		if self.sensorType == self.TYPE_DHT11:
			return self.__convert(self.pixtend.h2_dht11)
		return self.__convert(self.pixtend.h2_dht22)

	def __getHum3(self):
		if self.isV2:
			return self.__convert(self.pixtend.humid3)
		if self.sensorType == self.TYPE_DHT11:
			return self.__convert(self.pixtend.h3_dht11)
		return self.__convert(self.pixtend.h3_dht22)

	getters = (
		__getHum0,
		__getHum1,
		__getHum2,
		__getHum3,
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
		if self.isV2:
			return self.__convertV(self.pixtend.analog_in0)
		return self.__convertV(self.pixtend.analog_input0)

	def __getAI1(self):
		if self.isV2:
			return self.__convertV(self.pixtend.analog_in1)
		return self.__convertV(self.pixtend.analog_input1)

	def __getAI2(self):
		if self.isV2:
			assert(0)
			return 0
		return self.__convertMA(self.pixtend.analog_input2)

	def __getAI3(self):
		if self.isV2:
			assert(0)
			return 0
		return self.__convertMA(self.pixtend.analog_input3)

	getters = (
		__getAI0,
		__getAI1,
		__getAI2,
		__getAI3,
	)

	def __setJumper10V_AI0(self, jumper10V):
		pixtend = self.pixtend
		value = pixtend.ON if jumper10V else pixtend.OFF
		if self.isV2:
			pixtend.jumper_setting_ai0 = value
		else:
			pixtend.analog_input0_10volts_jumper = value

	def __setJumper10V_AI1(self, jumper10V):
		pixtend = self.pixtend
		value = pixtend.ON if jumper10V else pixtend.OFF
		if self.isV2:
			pixtend.jumper_setting_ai1 = value
		else:
			pixtend.analog_input1_10volts_jumper = value

	settersJumper10V = (
		__setJumper10V_AI0,
		__setJumper10V_AI1,
	)

	def __setNos_AI0(self, nos):
		if not self.isV2:
			self.pixtend.analog_input0_nos = nos

	def __setNos_AI1(self, nos):
		if not self.isV2:
			self.pixtend.analog_input1_nos = nos

	def __setNos_AI2(self, nos):
		if not self.isV2:
			self.pixtend.analog_input2_nos = nos

	def __setNos_AI3(self, nos):
		if not self.isV2:
			self.pixtend.analog_input3_nos = nos

	settersNos = (
		__setNos_AI0,
		__setNos_AI1,
		__setNos_AI2,
		__setNos_AI3,
	)

	@staticmethod
	def setFreq(pixtend, isV2, freqKHz):
		if isV2:
			return
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
		if self.isV2:
			pixtend.set_dac_output(pixtend.DAC_A, self.__convert(value))
		else:
			pixtend.dac_selection = pixtend.DAC_A
			pixtend.set_dac_output(self.__convert(value))

	def __setAO1(self, value):
		pixtend = self.pixtend
		if self.isV2:
			pixtend.set_dac_output(pixtend.DAC_B, self.__convert(value))
		else:
			pixtend.dac_selection = pixtend.DAC_B
			pixtend.set_dac_output(self.__convert(value))

	setters = (
		__setAO0,
		__setAO1,
	)

class PWM0Period(AbstractWordIO): #+cdef
	"""PiXtend PWM0 period I/O handler.
	"""

	def setPWMPeriod(self, period):
		if self.isV2:
			self.pixtend.pwm0_ctrl1 = clamp(period, 0, 65535)
		else:
			self.pixtend.pwm_ctrl_period = clamp(period, 0, 65000)
			self.pixtend.pwm_ctrl_configure()

	setters = (
		setPWMPeriod,
	)

	@staticmethod
	def setBaseFreq(pixtend, isV2, freqHz):
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
		if isV2:
			ctrl0 = pixtend.pwm0_ctrl0
			ctrl0 &= ~((1 << 5) | (1 << 6) | (1 << 7))
			ctrl0 |= (cs0 << 5) | (cs1 << 6) | (cs2 << 7)
			if freqHz == 0:
				ctrl0 &= ~((1 << 3) | (1 << 4)) # Disable A and B
			pixtend.pwm0_ctrl0 = ctrl0 & 0xFF
		else:
			pixtend.pwm_ctrl_cs0 = cs0
			pixtend.pwm_ctrl_cs1 = cs1
			pixtend.pwm_ctrl_cs2 = cs2
			pixtend.pwm_ctrl_configure()

class PWM0(AbstractWordIO): #+cdef
	"""PiXtend PWM0 output I/O handler.
	"""

	def __init__(self, *args, **kwargs):
		AbstractWordIO.__init__(self, *args, **kwargs)

		self.enabled = False
		self.servoMode = False

	def __setPWMA(self, value):
		if self.enabled:
			if self.servoMode:
				if self.isV2:
					self.pixtend.servo0 = clamp(value, 0, 16000)
				else:
					self.pixtend.servo0 = clamp(value, 0, 250)
			else:
				if self.isV2:
					self.pixtend.pwm0a = clamp(value, 0, 65535)
				else:
					self.pixtend.pwm0 = clamp(value, 0, 65000)

	def __setPWMB(self, value):
		if self.enabled:
			if self.servoMode:
				if self.isV2:
					self.pixtend.servo1 = clamp(value, 0, 16000)
				else:
					self.pixtend.servo1 = clamp(value, 0, 250)
			else:
				if self.isV2:
					self.pixtend.pwm0b = clamp(value, 0, 65535)
				else:
					self.pixtend.pwm1 = clamp(value, 0, 65000)

	setters = (
		__setPWMA,
		__setPWMB,
	)

	@staticmethod
	def setServoMode(pixtend, isV2, enServoMode):
		if isV2:
			ctrl0 = pixtend.pwm0_ctrl0
			ctrl0 &= ~((1 << 0) | (1 << 1))
			if not enServoMode:
				ctrl0 |= 1 << 0
			pixtend.pwm0_ctrl0 = ctrl0
		else:
			pixtend.pwm_ctrl_mode = 0 if enServoMode else 1
			pixtend.pwm_ctrl_configure()

	def __doSetEnabled(self, enabled, bitNr):
		self.enabled = enabled
		if self.isV2:
			ctrl0 = self.pixtend.pwm0_ctrl0
			ctrl0 &= ~(1 << bitNr)
			if enabled:
				ctrl0 |= (1 << bitNr)
			self.pixtend.pwm0_ctrl0 = ctrl0

	def __setEnabled0(self, enabled):
		self.__doSetEnabled(enabled, 3)

	def __setEnabled1(self, enabled):
		self.__doSetEnabled(enabled, 4)

	settersEnabled = (
		__setEnabled0,
		__setEnabled1,
	)

	def setup(self, secondaryOffset): #+cpdef
		AbstractWordIO.setup(self, secondaryOffset)

		setEnabled = self.settersEnabled[self.index]
		setEnabled(self, self.enabled)

class PWM1Period(AbstractWordIO): #+cdef
	"""PiXtend PWM1 period I/O handler. (v2.x only)
	"""

	def setPWMPeriod(self, period):
		if self.isV2:
			self.pixtend.pwm1_ctrl1 = clamp(period, 0, 255)
		else:
			assert(0)

	setters = (
		setPWMPeriod,
	)

	@staticmethod
	def setBaseFreq(pixtend, freqHz):
		cpuHz = 16000000
		csMap = {
			0		: (0, 0, 0), # PS=off
			cpuHz // 1	: (0, 0, 1), # PS=1
			cpuHz // 8	: (0, 1, 0), # PS=8
			cpuHz // 32	: (0, 1, 1), # PS=32
			cpuHz // 64	: (1, 0, 0), # PS=64
			cpuHz // 128	: (1, 0, 1), # PS=128
			cpuHz // 256	: (1, 1, 0), # PS=256
			cpuHz // 1024	: (1, 1, 1), # PS=1024
		}
		try:
			cs2, cs1, cs0 = csMap[freqHz]
		except KeyError as e:
			raise ValueError
		ctrl0 = pixtend.pwm1_ctrl0
		ctrl0 &= ~((1 << 5) | (1 << 6) | (1 << 7))
		ctrl0 |= (cs0 << 5) | (cs1 << 6) | (cs2 << 7)
		if freqHz == 0:
			ctrl0 &= ~((1 << 3) | (1 << 4)) # Disable A and B
		pixtend.pwm1_ctrl0 = ctrl0 & 0xFF

class PWM1(AbstractWordIO): #+cdef
	"""PiXtend PWM1 output I/O handler. (v2.x only)
	"""

	def __init__(self, *args, **kwargs):
		AbstractWordIO.__init__(self, *args, **kwargs)

		self.enabled = False
		self.servoMode = False

	def __setPWMA(self, value):
		if self.enabled:
			if self.servoMode:
				if self.isV2:
					self.pixtend.servo2 = clamp(value, 0, 125)
				else:
					assert(0)
			else:
				if self.isV2:
					self.pixtend.pwm1a = clamp(value, 0, 255)
				else:
					assert(0)

	def __setPWMB(self, value):
		if self.enabled:
			if self.servoMode:
				if self.isV2:
					self.pixtend.servo3 = clamp(value, 0, 125)
				else:
					assert(0)
			else:
				if self.isV2:
					self.pixtend.pwm1b = clamp(value, 0, 255)
				else:
					assert(0)

	setters = (
		__setPWMA,
		__setPWMB,
	)

	@staticmethod
	def setServoMode(pixtend, enServoMode):
		ctrl0 = pixtend.pwm1_ctrl0
		ctrl0 &= ~((1 << 0) | (1 << 1))
		if not enServoMode:
			ctrl0 |= 1 << 0
		pixtend.pwm1_ctrl0 = ctrl0

	def __doSetEnabled(self, enabled, bitNr):
		self.enabled = enabled
		if self.isV2:
			ctrl0 = self.pixtend.pwm1_ctrl0
			ctrl0 &= ~(1 << bitNr)
			if enabled:
				ctrl0 |= (1 << bitNr)
			self.pixtend.pwm1_ctrl0 = ctrl0
		else:
			assert(0)

	def __setEnabled0(self, enabled):
		self.__doSetEnabled(enabled, 3)

	def __setEnabled1(self, enabled):
		self.__doSetEnabled(enabled, 4)

	settersEnabled = (
		__setEnabled0,
		__setEnabled1,
	)

	def setup(self, secondaryOffset): #+cpdef
		AbstractWordIO.setup(self, secondaryOffset)

		setEnabled = self.settersEnabled[self.index]
		setEnabled(self, self.enabled)

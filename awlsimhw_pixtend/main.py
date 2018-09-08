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

from awlsim.core.hardware_params import *
from awlsim.core.hardware import * #+cimport
from awlsim.core.operators import * #+cimport
from awlsim.core.operatortypes import * #+cimport
from awlsim.core.offset import * #+cimport
from awlsim.core.cpu import * #+cimport

#from awlsimhw_pixtend.main cimport * #@cy
from awlsimhw_pixtend.ppl_shim import * #+cimport

import time


__all__ = [
	"HardwareInterface",
]


class HwParamDesc_boardType(HwParamDesc_str):
	typeStr = "BoardType"

	EnumGen.start
	BOARD_AUTO	= EnumGen.item
	BOARD_V1_X	= EnumGen.item
	BOARD_V2_X	= EnumGen.item
	EnumGen.end

	str2type = {
		"auto"		: BOARD_AUTO,
		"v1.x"		: BOARD_V1_X,
		"v1.2"		: BOARD_V1_X,
		"v1.3"		: BOARD_V1_X,
		"v2.x"		: BOARD_V2_X,
		"v2.0"		: BOARD_V2_X,
		"v2.1"		: BOARD_V2_X,
	}
	type2str = {
		BOARD_AUTO	: "auto",
		BOARD_V1_X	: "v1.x",
		BOARD_V2_X	: "v2.x",
	}

	def __init__(self, name, defaultValue, description, **kwargs):
		HwParamDesc_str.__init__(self,
					 name=name,
					 defaultValue=None,
					 description=description,
					 **kwargs)
		self.defaultValue = defaultValue
		self.defaultValueStr = self.type2str[defaultValue]

	def parse(self, value):
		lowerValue = value.lower().strip()
		if not lowerValue:
			return self.defaultValue
		try:
			return self.str2type[lowerValue]
		except KeyError as e:
			pass
		raise self.ParseError("Invalid board type '%s'. "
			"A valid boardType can be either %s." % (
			value, listToHumanStr(sorted(dictKeys(self.str2type)))))

class HwParamDesc_pwmMode(HwParamDesc_str):
	typeStr = "pwmMode"

	EnumGen.start
	MODE_SERVO	= EnumGen.item
	MODE_DUTYCYCLE	= EnumGen.item
	EnumGen.end

	type2str = {
		MODE_SERVO	: "servo",
		MODE_DUTYCYCLE	: "dutycycle",
	}
	str2type = pivotDict(type2str)

	def __init__(self, name, defaultValue, description, **kwargs):
		HwParamDesc_str.__init__(self,
					 name=name,
					 defaultValue=None,
					 description=description,
					 **kwargs)
		self.defaultValue = defaultValue
		self.defaultValueStr = self.type2str[defaultValue]

	def parse(self, value):
		lowerValue = value.lower().strip()
		if not lowerValue:
			return self.defaultValue
		lowerValue = lowerValue.replace("-", "").replace("_", "")
		try:
			return self.str2type[lowerValue]
		except KeyError as e:
			pass
		raise self.ParseError("Invalid PWM mode '%s'. "
			"A valid pwmMode can be either %s." % (
			value, listToHumanStr(sorted(dictKeys(self.str2type)))))

class HwParamDesc_gpioMode(HwParamDesc_str):
	typeStr = "GPIO-mode"

	EnumGen.start
	MODE_GPIO	= EnumGen.item
	MODE_DHT11	= EnumGen.item
	MODE_DHT22	= EnumGen.item
	EnumGen.end

	type2str = {
		MODE_GPIO	: "GPIO",
		MODE_DHT11	: "DHT11",
		MODE_DHT22	: "DHT22",
	}
	str2type = pivotDict(type2str)

	def __init__(self, name, defaultValue, description, **kwargs):
		HwParamDesc_str.__init__(self,
					 name=name,
					 defaultValue=None,
					 description=description,
					 **kwargs)
		self.defaultValue = defaultValue
		self.defaultValueStr = self.type2str[defaultValue]

	def parse(self, value):
		upperValue = value.upper().strip()
		if not upperValue:
			return self.defaultValue
		upperValue = upperValue.replace("-", "").replace("_", "")
		try:
			return self.str2type[upperValue]
		except KeyError as e:
			pass
		raise self.ParseError("Invalid GPIO mode '%s'. "
			"A valid gpioMode can be either %s." % (
			value, listToHumanStr(sorted(dictKeys(self.str2type)))))

class HardwareInterface_PiXtend(AbstractHardwareInterface): #+cdef
	name		= "PiXtend"
	description	= "PiXtend V1.x and V2.x "\
			  "extension board support.\n"\
			  "https://www.pixtend.de/"

	#TODO watchdog

	NR_RELAYS	= 4
	NR_DO_V1	= 6
	NR_DO_V2	= 4
	NR_DI		= 8
	NR_GPIO		= 4
	NR_AO		= 2
	NR_AI_V1	= 4
	NR_AI_V2	= 2
	NR_PWM0		= 2
	NR_PWM1		= 2

	paramDescs = [
		HwParamDesc_boardType("boardType",
				defaultValue=HwParamDesc_boardType.BOARD_AUTO,
				description="PiXtend board type. This can be either %s." % (
				listToHumanStr(sorted(dictKeys(HwParamDesc_boardType.str2type))))),
		HwParamDesc_float("pollIntMs",
				defaultValue=100.0,
				minValue=2.5,
				maxValue=10000.0,
				description="PiXtend auto-mode poll interval time, in milliseconds"),
		HwParamDesc_bool("rs485",
				 defaultValue=False,
				 description="Enable RS485 mode. (PiXtend v1.x only)\n"
				 "If set to True the RS485 output is enabled "
				 "and the RS232 output is disabled.\n"
				 "If set to False the RS485 output is disabled "
				 "and the RS232 output is enabled."),
		HwParamDesc_bool("testMode",
				defaultValue=False,
				description="Enable testing mode. DO NOT USE THIS OPTION!",
				hidden=True),
	]
	for i in range(NR_RELAYS):
		paramDescs.append(HwParamDesc_oper(
				"relay%d_addr" % i,
				allowedOperTypes=(AwlOperatorTypes.MEM_A,),
				allowedOperWidths=(1,),
				description="Relay output %d address" % i))
	for i in range(max(NR_DO_V1, NR_DO_V2)):
		paramDescs.append(HwParamDesc_oper(
				"digitalOut%d_addr" % i,
				allowedOperTypes=(AwlOperatorTypes.MEM_A,),
				allowedOperWidths=(1,),
				description="Digital output %d address" % i))
	for i in range(NR_DI):
		paramDescs.append(HwParamDesc_oper(
				"digitalIn%d_addr" % i,
				allowedOperTypes=(AwlOperatorTypes.MEM_E,),
				allowedOperWidths=(1,),
				description="Digital input %d address" % i))
	for i in range(NR_GPIO):
		paramDescs.append(HwParamDesc_oper(
				"gpio%d_addr" % i,
				allowedOperTypes=(AwlOperatorTypes.MEM_E,
						  AwlOperatorTypes.MEM_A,),
				allowedOperWidths=(1,),
				description="GPIO %d bit address (can be input (I/E) or output (Q/A))" % i))
		paramDescs.append(HwParamDesc_oper(
				"gpio%d_temp_addr" % i,
				allowedOperTypes=(AwlOperatorTypes.MEM_E,),
				allowedOperWidths=(16,),
				description="DHT11/DHT22 on GPIO %d temperature sensor input address" % i))
		paramDescs.append(HwParamDesc_oper(
				"gpio%d_hum_addr" % i,
				allowedOperTypes=(AwlOperatorTypes.MEM_E,),
				allowedOperWidths=(16,),
				description="DHT11/DHT22 on GPIO %d humidity sensor input address" % i))
		paramDescs.append(HwParamDesc_gpioMode(
				"gpio%d_mode" % i,
				defaultValue=HwParamDesc_gpioMode.MODE_GPIO,
				description="GPIO %d operation mode."
					    "Possible values: %s" % (i,
				listToHumanStr(sorted(dictKeys(HwParamDesc_gpioMode.str2type))))))
		paramDescs.append(HwParamDesc_bool(
				"gpio%d_pullup" % i,
				defaultValue=False,
				description="Enable the pull-up resistors for GPIO input %d" % i))
	for i in range(NR_AO):
		paramDescs.append(HwParamDesc_oper(
				"analogOut%d_addr" % i,
				allowedOperTypes=(AwlOperatorTypes.MEM_A,),
				allowedOperWidths=(16,),
				description="Analog output (DAC) %d address" % i))
	for i in range(max(NR_AI_V1, NR_AI_V2)):
		paramDescs.append(HwParamDesc_oper(
				"analogIn%d_addr" % i,
				allowedOperTypes=(AwlOperatorTypes.MEM_E,),
				allowedOperWidths=(16,),
				description="Analog input %d word address" % i))
		if i <= 1:
			paramDescs.append(HwParamDesc_bool(
					"analogIn%d_10V" % i,
					defaultValue=True,
					description="TRUE: Use 10 volts input. FALSE: Use 5 volts input"))
		paramDescs.append(HwParamDesc_int(
				"analogIn%d_nos" % i,
				defaultValue=10,
				minValue=1,
				maxValue=50,
				description="Number of samples for analog input (1, 5, 10 or 50)"))
	paramDescs.append(HwParamDesc_int(
			"analogIn_kHz",
			defaultValue=125,
			minValue=125,
			maxValue=8000,
			description="Analog sampling frequency in kHz. Default: 125 kHz."))
	for i in range(NR_PWM0):
		__name = "AB"[i]
		paramDescs.append(HwParamDesc_oper(
				"pwm0%s_addr" % __name,
				allowedOperTypes=(AwlOperatorTypes.MEM_A,),
				allowedOperWidths=(16,),
				description="Output word address of 16 bit PWM "
					"(Pulse Width Modulation) module 0%s" % __name))
		paramDescs.append(HwParamDesc_oper(
				"pwm%d_addr" % i,
				allowedOperTypes=(AwlOperatorTypes.MEM_A,),
				allowedOperWidths=(16,),
				deprecated=True,
				compatReplacement=("pwm0%s_addr" % __name)))
		paramDescs.append(HwParamDesc_bool(
				"pwm%d_servoOverDrive" % i,
				deprecated=True))
	paramDescs.append(HwParamDesc_pwmMode(
			"pwm0_mode",
			defaultValue=HwParamDesc_pwmMode.MODE_DUTYCYCLE,
			description="Set PWM0 operation mode. "
				"Possible values: %s" % (
				listToHumanStr(sorted(dictKeys(HwParamDesc_pwmMode.str2type))))))
	paramDescs.append(HwParamDesc_bool(
			"pwm_servoMode",
			defaultValue=False,
			deprecated=True,
			replacement="pwm0_mode"))
	paramDescs.append(HwParamDesc_int(
			"pwm0_baseFreqHz",
			defaultValue=0,
			minValue=0,
			maxValue=16000000,
			description="PWM0 base frequency, in Hz. "
				    "Possible values: 16000000, 2000000, 250000, 62500, 15625, 0. "
				    "Set to 0 to disable PWM0."))
	paramDescs.append(HwParamDesc_oper(
			"pwm0_period",
			allowedOperTypes=(AwlOperatorTypes.MEM_A,
					  AwlOperatorTypes.IMM),
			description="PWM0 period.\n"
				"This can either be an integer between 0 and L#65000.\n"
				"Or an output word (AW, QW) where the program "
				"writes the desired period to.\n"
				"Defaults to L#65000, if not specified."))
	paramDescs.append(HwParamDesc_int(
			"pwm_baseFreqHz",
			defaultValue=0,
			minValue=0,
			maxValue=16000000,
			deprecated=True,
			compatReplacement="pwm0_baseFreqHz"))
	paramDescs.append(HwParamDesc_oper(
			"pwm_period",
			allowedOperTypes=(AwlOperatorTypes.MEM_A,
					  AwlOperatorTypes.IMM),
			deprecated=True,
			compatReplacement="pwm0_period"))
	for i in range(NR_PWM1):
		__name = "AB"[i]
		paramDescs.append(HwParamDesc_oper(
				"pwm1%s_addr" % __name,
				allowedOperTypes=(AwlOperatorTypes.MEM_A,),
				allowedOperWidths=(16,),
				description="Output word address of 8 bit PWM "
					"(Pulse Width Modulation) module 1%s" % __name))
	paramDescs.append(HwParamDesc_pwmMode(
			"pwm1_mode",
			defaultValue=HwParamDesc_pwmMode.MODE_DUTYCYCLE,
			description="Set PWM1 operation mode. "
				"Possible values: %s" % (
				listToHumanStr(sorted(dictKeys(HwParamDesc_pwmMode.str2type))))))
	paramDescs.append(HwParamDesc_int(
			"pwm1_baseFreqHz",
			defaultValue=0,
			minValue=0,
			maxValue=16000000,
			description="PWM1 base frequency, in Hz. "
				    "Possible values: 16000000, 2000000, 500000, "
				    "250000, 125000, 62500, 15625, 0. "
				    "Set to 0 to disable PWM1."))
	paramDescs.append(HwParamDesc_oper(
			"pwm1_period",
			allowedOperTypes=(AwlOperatorTypes.MEM_A,
					  AwlOperatorTypes.IMM),
			description="PWM1 period.\n"
				"This can either be an integer between 0 and 255.\n"
				"Or an output word (AW, QW) where the program "
				"writes the desired period to.\n"
				"Defaults to 255, if not specified."))

	def __init__(self, sim, parameters={}):
		AbstractHardwareInterface.__init__(self,
						   sim = sim,
						   parameters = parameters)
		self.__pixtendInitialized = False
		self.__pixtend = None
		self.__haveInputData = False

	def __build(self):
		# Build all Relay() objects
		self.__relays = []
		for i in range(self.NR_RELAYS):
			oper = self.getParamValueByName("relay%d_addr" % i)
			if oper is None:
				continue
			bitOffset = oper.offset.toLongBitOffset()
			r = Relay(self.__pixtend, self.__isV2, i, bitOffset,
				  not self.isInProcessImage(oper.offset, 1, True))
			self.__relays.append(r)

		# Build all DigitalOut() objects
		self.__DOs = []
		for i in range(self.NR_DO_V2 if self.__isV2 else self.NR_DO_V1):
			oper = self.getParamValueByName("digitalOut%d_addr" % i)
			if oper is None:
				continue
			bitOffset = oper.offset.toLongBitOffset()
			directOnly = not self.isInProcessImage(oper.offset, 1, True)
			do = DigitalOut(self.__pixtend, self.__isV2, i, bitOffset, directOnly)
			self.__DOs.append(do)

		# Build all DigitalIn() objects
		self.__DIs = []
		for i in range(self.NR_DI):
			oper = self.getParamValueByName("digitalIn%d_addr" % i)
			if oper is None:
				continue
			bitOffset = oper.offset.toLongBitOffset()
			directOnly = not self.isInProcessImage(oper.offset, 1, False)
			di = DigitalIn(self.__pixtend, self.__isV2, i, bitOffset, directOnly)
			self.__DIs.append(di)

		# Build all GPIO output objects
		self.__GPIO_out = []
		for i in range(self.NR_GPIO):
			mode = self.getParamValueByName("gpio%d_mode" % i)
			if mode != HwParamDesc_gpioMode.MODE_GPIO:
				continue
			oper = self.getParamValueByName("gpio%d_addr" % i)
			if oper is None:
				continue
			if oper.operType != AwlOperatorTypes.MEM_A:
				continue
			bitOffset = oper.offset.toLongBitOffset()
			gpio = GPIO(self.__pixtend, self.__isV2, i, bitOffset,
				    not self.isInProcessImage(oper.offset, 1, True))
			gpio.mode = GPIO.MODE_OUTPUT
			self.__GPIO_out.append(gpio)

		# Build all GPIO input objects
		self.__GPIO_in = []
		for i in range(self.NR_GPIO):
			mode = self.getParamValueByName("gpio%d_mode" % i)
			if mode != HwParamDesc_gpioMode.MODE_GPIO:
				continue
			oper = self.getParamValueByName("gpio%d_addr" % i)
			if oper is None:
				continue
			if oper.operType != AwlOperatorTypes.MEM_E:
				continue
			bitOffset = oper.offset.toLongBitOffset()
			gpio = GPIO(self.__pixtend, self.__isV2, i, bitOffset,
				    not self.isInProcessImage(oper.offset, 1, False))
			gpio.mode = GPIO.MODE_INPUT
			gpio.pullUp = self.getParamValueByName("gpio%d_pullup" % i)
			self.__GPIO_in.append(gpio)
		GPIO.setGlobalPullUpEnable(self.__pixtend, self.__isV2,
					   any(gpio.pullUp for gpio in self.__GPIO_in))

		# Build all DHT11/DHT22 input objects
		self.__temps = []
		self.__hums = []
		for i in range(self.NR_GPIO):
			mode = self.getParamValueByName("gpio%d_mode" % i)
			if mode not in {HwParamDesc_gpioMode.MODE_DHT11,
					HwParamDesc_gpioMode.MODE_DHT22}:
				continue
			sensorType = {
				HwParamDesc_gpioMode.MODE_DHT11 : EnvSensorBase.TYPE_DHT11,
				HwParamDesc_gpioMode.MODE_DHT22 : EnvSensorBase.TYPE_DHT22,
			}[mode]
			tempOper = self.getParamValueByName("gpio%d_temp_addr" % i)
			humOper = self.getParamValueByName("gpio%d_hum_addr" % i)
			if tempOper is not None:
				bitOffset = tempOper.offset.toLongBitOffset()
				temp = TempIn(sensorType,
					self.__pixtend, self.__isV2, i, bitOffset,
					not self.isInProcessImage(tempOper.offset, 16, False))
				self.__temps.append(temp)
			if humOper is not None:
				bitOffset = humOper.offset.toLongBitOffset()
				hum = HumIn(sensorType,
					self.__pixtend, self.__isV2, i, bitOffset,
					not self.isInProcessImage(humOper.offset, 16, False))
				self.__hums.append(hum)

		# Build all analog input objects
		self.__AIs = []
		for i in range(self.NR_AI_V2 if self.__isV2 else self.NR_AI_V1):
			oper = self.getParamValueByName("analogIn%d_addr" % i)
			if oper is None:
				continue
			bitOffset = oper.offset.toLongBitOffset()
			ai = AnalogIn(self.__pixtend, self.__isV2, i, bitOffset,
				      not self.isInProcessImage(oper.offset, 16, False))
			self.__AIs.append(ai)
			if i <= 1:
				ai.jumper10V = self.getParamValueByName("analogIn%d_10V" % i)
			ai.numberOfSamples = self.getParamValueByName("analogIn%d_nos" % i)

		# Build all analog output objects
		self.__AOs = []
		for i in range(self.NR_AO):
			oper = self.getParamValueByName("analogOut%d_addr" % i)
			if oper is None:
				continue
			bitOffset = oper.offset.toLongBitOffset()
			ao = AnalogOut(self.__pixtend, self.__isV2, i, bitOffset,
				       not self.isInProcessImage(oper.offset, 16, True))
			self.__AOs.append(ao)

		# Build all PWM() objects for PWM0
		self.__PWM0s = []
		for i in range(self.NR_PWM0):
			pwmName = "AB"[i]
			oper = self.getParamValueByName("pwm%d_addr" % i,
							fallbackToDefault=False)
			if oper is None:
				oper = self.getParamValueByName("pwm0%s_addr" % pwmName)
			if oper is None:
				continue
			bitOffset = oper.offset.toLongBitOffset()
			pwm = PWM0(self.__pixtend, self.__isV2, i, bitOffset,
				   not self.isInProcessImage(oper.offset, 16, True))
			self.__PWM0s.append(pwm)
			pwm.enabled = True
			servoMode = self.getParamValueByName("pwm_servoMode",
							     fallbackToDefault=False)
			if servoMode is None:
				mode = self.getParamValueByName("pwm0_mode")
				servoMode = (mode == HwParamDesc_pwmMode.MODE_SERVO)
			pwm.servoMode = servoMode
		# Handle pwm0_period parameter.
		try:
			maxPeriod = 65535 if self.__isV2 else 65000
			oper = self.getParamValueByName("pwm_period")
			if not oper:
				oper = self.getParamValueByName("pwm0_period")
			if not oper:
				# Use default constant pwm0_period
				PWM0Period(self.__pixtend, self.__isV2, 0, 0).setPWMPeriod(maxPeriod)
			else:
				if oper.operType == AwlOperatorTypes.IMM:
					# Use custom constant pwm0_period
					period = oper.immediate
					if period < 0 or period > maxPeriod:
						raise ValueError
					PWM0Period(self.__pixtend, self.__isV2, 0, 0).setPWMPeriod(period)
				elif oper.operType == AwlOperatorTypes.MEM_A and\
				     oper.width == 16:
					# Use custom dynamic pwm0_period
					bitOffset = oper.offset.toLongBitOffset()
					pwm = PWM0Period(self.__pixtend, self.__isV2, 0, bitOffset,
							 not self.isInProcessImage(oper.offset, 16, True))
					self.__PWM0s.append(pwm)
					pwm.setPWMPeriod(0)
				else:
					raise ValueError
		except ValueError as e:
			self.raiseException("Unsupported 'pwm0_period' parameter value.")

		# Build all PWM() objects for PWM1
		self.__PWM1s = []
		if self.__isV2:
			for i in range(self.NR_PWM1):
				pwmName = "AB"[i]
				oper = self.getParamValueByName("pwm1%s_addr" % pwmName)
				if oper is None:
					continue
				bitOffset = oper.offset.toLongBitOffset()
				pwm = PWM1(self.__pixtend, self.__isV2, i, bitOffset,
					   not self.isInProcessImage(oper.offset, 16, True))
				self.__PWM1s.append(pwm)
				pwm.enabled = True
				mode = self.getParamValueByName("pwm1_mode")
				pwm.servoMode = (mode == HwParamDesc_pwmMode.MODE_SERVO)
			# Handle pwm1_period parameter.
			try:
				maxPeriod = 255
				oper = self.getParamValueByName("pwm1_period")
				if not oper:
					# Use default constant pwm1_period
					PWM1Period(self.__pixtend, self.__isV2, 0, 0).setPWMPeriod(maxPeriod)
				else:
					if oper.operType == AwlOperatorTypes.IMM:
						# Use custom constant pwm1_period
						period = oper.immediate
						if period < 0 or period > maxPeriod:
							raise ValueError
						PWM1Period(self.__pixtend, self.__isV2, 0, 0).setPWMPeriod(period)
					elif oper.operType == AwlOperatorTypes.MEM_A and\
					     oper.width == 16:
						# Use custom dynamic pwm1_period
						bitOffset = oper.offset.toLongBitOffset()
						pwm = PWM1Period(self.__pixtend, self.__isV2, 0, bitOffset,
								 not self.isInProcessImage(oper.offset, 16, True))
						self.__PWM1s.append(pwm)
						pwm.setPWMPeriod(0)
					else:
						raise ValueError
			except ValueError as e:
				self.raiseException("Unsupported 'pwm1_period' parameter value.")

		# Build a list of all outputs
		self.__allOutputs = []
		self.__allOutputs.extend(self.__relays)
		self.__allOutputs.extend(self.__DOs)
		self.__allOutputs.extend(self.__GPIO_out)
		self.__allOutputs.extend(self.__AOs)
		self.__allOutputs.extend(self.__PWM0s)
		self.__allOutputs.extend(self.__PWM1s)

		# Build a list of all inputs
		self.__allInputs = []
		self.__allInputs.extend(self.__DIs)
		self.__allInputs.extend(self.__GPIO_in)
		self.__allInputs.extend(self.__temps)
		self.__allInputs.extend(self.__hums)
		self.__allInputs.extend(self.__AIs)

		# Build a list of all process image accessible outputs.
		self.__allProcOutputs = [ o for o in self.__allOutputs if not o.directOnly ]

		# Build a list of all process image accessible inputs.
		self.__allProcInputs = [ i for i in self.__allInputs if not i.directOnly ]

		def calcFirstLastByte(IOs):
			first = last = None
			for io in IOs:
				beginByteOffset = ((io.byteOffset * 8) + io.bitOffset) // 8
				endByteOffset = beginByteOffset + io.byteSize - 1
				if first is None or beginByteOffset < first:
					first = beginByteOffset
				if last is None or endByteOffset > last:
					last = endByteOffset
			return first, last

		# Find the offsets of the first and the last output byte
		firstOutByte, lastOutByte = calcFirstLastByte(self.__allProcOutputs)
		firstInByte, lastInByte = calcFirstLastByte(self.__allProcInputs)

		# Build dicts to map from byteOffset to I/O wrapper.
		self.__byteOffsetToInput = {
			inp.byteOffset : inp
			for inp in self.__allInputs
		}
		self.__byteOffsetToOutput = {
			out.byteOffset : out
			for out in self.__allOutputs
		}

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
						   self.__GPIO_out,
						   self.__AOs,
						   self.__PWM0s,
						   self.__PWM1s):
				out.setup(-firstOutByte)

		# Store the input base and size
		if firstInByte is None or lastInByte is None:
			self.__inBase = 0
			self.__inSize = 0
		else:
			self.__inBase = self.inputAddressBase + firstInByte
			self.__inSize = lastInByte - firstInByte + 1

			# Setup all inputs
			for inp in itertools.chain(self.__DIs,
						   self.__GPIO_in,
						   self.__temps,
						   self.__hums,
						   self.__AIs):
				inp.setup(-firstInByte)

		if not self.__isV2:
			# Configure RS232/RS485
			try:
				rs485 = self.getParamValueByName("rs485")
				if rs485:
					self.__pixtend.serial_mode = self.__pixtend.RS485
				else:
					self.__pixtend.serial_mode = self.__pixtend.RS232
			except Exception as e:
				self.raiseException("Failed to set RS232/RS485 mode: %s" % str(e))

		if not self.__isV2:
			# Configure AnalogOut SPI communication.
			try:
				if self.__AOs:
					self.__pixtend.open_dac()
			except (IOError, ValueError) as e:
				self.raiseException("Failed to open DAC communication: %s" % str(e))

		# Configure global values of AnalogIn.
		try:
			AnalogIn.setFreq(self.__pixtend, self.__isV2,
					 self.getParamValueByName("analogIn_kHz"))
		except ValueError as e:
			self.raiseException("Unsupported 'analogIn_kHz' parameter value. "
				"Supported values are: 125, 250, 500, 1000, 4000, 8000.")

		# Configure global values of PWM0.
		try:
			if self.__PWM0s:
				PWM0.setServoMode(self.__pixtend, self.__isV2,
						  self.__PWM0s[0].servoMode)
		except ValueError as e:
			self.raiseException("Unsupported 'pwm_servoMode' parameter value.")
		try:
			freqHz = self.getParamValueByName("pwm_baseFreqHz",
							  fallbackToDefault=False)
			if freqHz is None:
				freqHz = self.getParamValueByName("pwm0_baseFreqHz")
			if not self.__PWM0s:
				freqHz = 0
			PWM0Period.setBaseFreq(self.__pixtend, self.__isV2, freqHz)
		except ValueError as e:
			self.raiseException("Unsupported 'pwm0_baseFreqHz' parameter value. "
				"Supported values are: 16000000, 2000000, 250000, 62500, 15625, 0.")

		if self.__isV2:
			# Configure global values of PWM1.
			try:
				if self.__PWM1s:
					PWM1.setServoMode(self.__pixtend,
							  self.__PWM1s[0].servoMode)
			except ValueError as e:
				self.raiseException("Unsupported 'pwm1_mode' parameter value.")
			try:
				freqHz = self.getParamValueByName("pwm1_baseFreqHz")
				if not self.__PWM1s:
					freqHz = 0
				PWM1Period.setBaseFreq(self.__pixtend, freqHz)
			except ValueError as e:
				self.raiseException("Unsupported 'pwm1_baseFreqHz' parameter value. "
					"Supported values are: 16000000, 2000000, "
					"500000, 250000, 125000, 62500, 15625, 0.")

	def __tryConnect(self, boardType, timeout=5.0):
		"""Try to connect to the PiXtend board.
		"""
#@cy		cdef double minPollIntV1
#@cy		cdef double minPollIntV2

		self.__prevSpiCount = 0

		# Import the Pixtend library.
		if boardType == HwParamDesc_boardType.BOARD_V1_X:
			self.__isV2 = False
			printDebug("Trying to import PiXtend v1.x library")
			try:
				from pixtendlib import Pixtend as pixtend_class
			except ImportError as e:
				self.raiseException("Failed to import pixtendlib.Pixtend module"
					":\n%s" % str(e))
		elif boardType == HwParamDesc_boardType.BOARD_V2_X:
			self.__isV2 = True
			printDebug("Trying to import PiXtend v2.x library")
			try:
				from pixtendv2s import PiXtendV2S as pixtend_class
			except ImportError as e:
				self.raiseException("Failed to import pixtendv2s.PiXtendV2S module"
					":\n%s" % str(e))
		else:
			self.raiseException("Unknown board type.")
		self.__pixtend_class = pixtend_class

		# Get the configured poll interval
		self.__pollInt = float(self.getParamValueByName("pollIntMs")) / 1000.0
		minPollIntV1 = 0.025
		minPollIntV2 = 0.0025
		if not self.__isV2 and\
		   not pyFloatEqual(self.__pollInt, minPollIntV1) and\
		   self.__pollInt < minPollIntV1:
			self.raiseException("pollIntMs is too low. It must be at least 25 ms.")
		if self.__isV2 and\
		   not pyFloatEqual(self.__pollInt, minPollIntV2) and\
		   self.__pollInt < minPollIntV2:
			self.raiseException("pollIntMs is too low. It must be at least 2.5 ms.")
		self.__testMode = self.getParamValueByName("testMode")
		if self.__testMode:
			# In test mode use poll interval as small as possible.
			self.__pollInt = 0.0025 if self.__isV2 else 0.0

		# Initialize PiXtend
		self.__pixtend = None
		try:
			printDebug("Trying to connect to PiXtend v%d.x" % (2 if self.__isV2 else 1))
			if self.__isV2:
				# PiXtend v2.x
				self.__pixtend = self.__pixtend_class(
					com_interval=self.__pollInt,
					model=self.__pixtend_class.PIXTENDV2S_MODEL,
				)
				initialSpiCount = self.__pixtend.spi_transfers & 0xFFFF
			else:
				# PiXtend v1.x
				self.__pixtend = self.__pixtend_class()
				self.__pixtend.open()
			# Wait for PiXtend to wake up.
			t, tMax = 0, int(round(timeout * 10))
			while True:
				self.cpu.updateTimestamp()
				if self.__isV2:
					if self.__pixtendPoll(self.cpu.now):
						spiCount = self.__pixtend.spi_transfers & 0xFFFF
						if spiCount != initialSpiCount:
							break # success
					else:
						initialSpiCount = self.__pixtend.spi_transfers & 0xFFFF
				else:
					if self.__pixtendPoll(self.cpu.now):
						break # success
				t += 1
				if t >= tMax:
					self.raiseException("Timeout waiting "
						"for PiXtend auto-mode.")
				time.sleep(0.1)
			if self.__isV2 and self.__pixtend.model_in_error:
				self.raiseException("Invalid board model number detected")
		except Exception as e:
			with suppressAllExc:
				self.__shutdown()
			self.raiseException("Failed to init PiXtend: %s" % (
				str(e)))
		printInfo("Connected to PiXtend v%d.x" % (2 if self.__isV2 else 1))

	def doStartup(self):
		if self.__pixtendInitialized:
			return

		# Connect to the PiXtend board
		boardType = self.getParamValueByName("boardType")
		if boardType == HwParamDesc_boardType.BOARD_AUTO:
			try:
				self.__tryConnect(HwParamDesc_boardType.BOARD_V1_X,
						  timeout=1.0)
			except AwlSimError as e:
				self.__tryConnect(HwParamDesc_boardType.BOARD_V2_X)
		else:
			self.__tryConnect(boardType)

		# Build the HW shim and configure the hardware
		try:
			self.__build()
		except Exception as e:
			with suppressAllExc:
				self.__shutdown()
			raise e

		if self.__isV2:
			self.__prevSpiCount = self.__pixtend.spi_transfers & 0xFFFF
		self.__haveInputData = False
		self.__nextPoll = self.cpu.now + self.__pollInt
		self.__pixtendInitialized = True

	def __shutdown(self):
		if self.__pixtend:
			self.__pixtend.close()
			self.__pixtend = None
			self.__pixtendInitialized = False

	def doShutdown(self):
		if self.__pixtendInitialized:
			self.__shutdown()

	def readInputs(self): #+cdef
#@cy		cdef S7CPU cpu
#@cy		cdef uint32_t size
#@cy		cdef bytearray data
#@cy		cdef AbstractIO inp

		if self.__haveInputData:
			self.__haveInputData = False
			cpu = self.cpu
			size = self.__inSize
			if size:
				data = cpu.fetchInputRange(self.__inBase, size)

				# Handle all process image inputs
				for inp in self.__allProcInputs:
					inp.get(data)

				cpu.storeInputRange(self.__inBase, data)

	def writeOutputs(self): #+cdef
#@cy		cdef S7CPU cpu
#@cy		cdef uint32_t size
#@cy		cdef double now
#@cy		cdef bytearray data
#@cy		cdef AbstractIO out

		cpu = self.cpu

		# Run one PiXtend poll cycle, if required.
		now = cpu.now
		if self.__isV2 or now >= self.__nextPoll:
			size = self.__outSize
			if size:
				data = cpu.fetchOutputRange(self.__outBase, size)

				# Handle all process image outputs
				for out in self.__allProcOutputs:
					out.set(data)

			if not self.__pixtendPoll(now):
				self.raiseException("PiXtend auto_mode() poll failed.")

	def __pixtendPoll(self, now): #@nocy
#@cy	cdef ExBool_t __pixtendPoll(self, double now):
#@cy		cdef uint16_t spiCount

		pixtend = self.__pixtend
		if self.__isV2:
			# Check if we have new data from the poll thread
			# In test mode actually wait for the worker thread.
			if self.__testMode:
				self.__waitV2Transfer(True)
			spiCount = pixtend.spi_transfers & 0xFFFF
			self.__haveInputData = (spiCount != self.__prevSpiCount)
			self.__prevSpiCount = spiCount
			# Check for errors from the poll thread
			if not pixtend.crc_header_in_error and\
			   not pixtend.crc_data_in_error and\
			   ((pixtend.uc_state & 1) != 0):
				return True
		else:
			# Poll PiXtend auto_mode
			self.__nextPoll = now + self.__pollInt
			if (pixtend.auto_mode() == 0) and\
			   ((pixtend.uc_status & 1) != 0):
				self.__haveInputData = True
				return True
		# An error occurred.
		self.__haveInputData = False
		return False

	def __waitV2Transfer(self, waitForBegin): #@nocy
#@cy	cdef __waitV2Transfer(self, _Bool waitForBegin):
		"""Wait for the V2 I/O thread to run completely at least once.
		"""
#@cy		cdef S7CPU cpu
#@cy		cdef uint16_t spiCount
#@cy		cdef uint16_t spiBeginCount
#@cy		cdef uint16_t prevSpiCount
#@cy		cdef uint16_t prevSpiBeginCount
#@cy		cdef double timeout
#@cy		cdef _Bool begin

		cpu = self.cpu
		pixtend = self.__pixtend

		timeout = cpu.now + (self.__pollInt * 10000.0)
		prevSpiCount = pixtend.spi_transfers & 0xFFFF
		prevSpiBeginCount = pixtend.spi_transfers_begin & 0xFFFF
		begin = not waitForBegin
		while True:
			cpu.updateTimestamp()
			if cpu.now >= timeout:
				self.raiseException("PiXtend poll wait timeout.")
			time.sleep(0.001)

			spiBeginCount = pixtend.spi_transfers_begin & 0xFFFF
			spiCount = pixtend.spi_transfers & 0xFFFF
			if begin:
				if spiCount != prevSpiCount:
					# The I/O thread ran at least once.
					break
			else:
				if spiBeginCount == prevSpiBeginCount:
					# The thread did not begin, yet.
					prevSpiCount = spiCount
				else:
					begin = True

	def __syncPixtendPoll(self, waitForBegin): #@nocy
#@cy	cdef __syncPixtendPoll(self, _Bool waitForBegin):
		"""Synchronously wait for the data transfer to/from PiXtend.
		"""
#@cy		cdef S7CPU cpu
#@cy		cdef uint32_t retries

		# Synchronously run one PiXtend poll cycle.
		cpu = self.cpu
		retries = 0
		while True:
			cpu.updateTimestamp()
			if self.__isV2:
				# Wait until the I/O thread did one transfer.
				self.__waitV2Transfer(waitForBegin)
			else:
				# Wait for the next possible poll slot.
				waitTime = self.__nextPoll - cpu.now
				if waitTime > 0.0:
					if waitTime > self.__pollInt * 2.0:
						# Wait time is too big.
						self.raiseException("PiXtend poll wait timeout.")
					time.sleep(waitTime)
			cpu.updateTimestamp()

			# Poll PiXtend.
			if self.__pixtendPoll(cpu.now):
				break # Success
			retries += 1
			if retries >= 3:
				self.raiseException("PiXtend auto_mode() poll failed (sync).")

	def directReadInput(self, accessWidth, accessOffset): #@nocy
#@cy	cdef bytearray directReadInput(self, uint32_t accessWidth, uint32_t accessOffset):
#@cy		cdef AbstractIO inp

		try:
			inp = self.__byteOffsetToInput[accessOffset]
		except KeyError as e:
			return bytearray()
		if accessWidth != inp.bitSize:
			self.raiseException("Directly accessing input at I %d.0 "
				"with width %d bit, but only %d bit wide "
				"accesses are supported." % (
				accessOffset, accessWidth, inp.bitSize))

		self.__syncPixtendPoll(True)
		data = bytearray(accessWidth // 8)
		inp.getWithByteOffset(data, 0)

		return data

	def directWriteOutput(self, accessWidth, accessOffset, data): #@nocy
#@cy	cdef ExBool_t directWriteOutput(self, uint32_t accessWidth, uint32_t accessOffset, bytearray data) except ExBool_val:
#@cy		cdef AbstractIO out

		try:
			out = self.__byteOffsetToOutput[accessOffset]
		except KeyError as e:
			return False
		if accessWidth != out.bitSize:
			self.raiseException("Directly accessing output at Q %d.0 "
				"with width %d bit, but only %d bit wide "
				"accesses are supported." % (
				accessOffset, accessWidth, out.bitSize))

		out.setWithByteOffset(data, 0)
		self.__syncPixtendPoll(True)

		return True

# Module entry point
HardwareInterface = HardwareInterface_PiXtend

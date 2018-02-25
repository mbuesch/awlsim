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
	BOARD_V1_X	= EnumGen.item
	BOARD_V2_X	= EnumGen.item
	EnumGen.end

	str2type = {
		"v1.x"		: BOARD_V1_X,
		"v1.2"		: BOARD_V1_X,
		"v1.3"		: BOARD_V1_X,
		"v2.x"		: BOARD_V2_X,
		"v2.0"		: BOARD_V2_X,
	}
	type2str = {
		BOARD_V1_X	: "v1.x",
		BOARD_V2_X	: "v2.x",
	}

	def __init__(self, name, defaultValue, description, mandatory=False, hidden=False):
		HwParamDesc_str.__init__(self,
					 name=name,
					 defaultValue=None,
					 description=description,
					 mandatory=mandatory,
					 hidden=hidden)
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
			value, listToHumanStr(sorted(self.str2type.keys()))))

class HardwareInterface_PiXtend(AbstractHardwareInterface): #+cdef
	name = "PiXtend"

	#TODO DHT
	#TODO hum
	#TODO watchdog

	NR_RELAYS	= 4
	NR_DO_V1	= 6
	NR_DO_V2	= 4
	NR_DI		= 8
	NR_GPIO		= 4
	NR_AO		= 2
	NR_AI_V1	= 4
	NR_AI_V2	= 2
	NR_PWM		= 2

	paramDescs = [
		HwParamDesc_boardType("boardType",
				defaultValue=HwParamDesc_boardType.BOARD_V1_X,
				description="PiXtend board type. This can be either %s." % (
				listToHumanStr(sorted(HwParamDesc_boardType.str2type.keys())))),
		HwParamDesc_int("pollIntMs",
				defaultValue=100,
				minValue=3,
				maxValue=10000,
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
				description="GPIO %d address (can be input (I/E) or output (Q/A))" % i))
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
	for i in range(NR_PWM):
		paramDescs.append(HwParamDesc_oper(
				"pwm%d_addr" % i,
				allowedOperTypes=(AwlOperatorTypes.MEM_A,),
				allowedOperWidths=(16,),
				description="PWM (Pulse Width Modulation) output %d word address" % i))
		paramDescs.append(HwParamDesc_bool(
				"pwm%d_servoOverDrive" % i,
				defaultValue=False,
				description="Enable PWM %d servo mode "
					    "over drive (only if pwm_servoMode=True)." % i))
	paramDescs.append(HwParamDesc_bool(
			"pwm_servoMode",
			defaultValue=False,
			description="Enable PWM servo mode."))
	paramDescs.append(HwParamDesc_int(
			"pwm_baseFreqHz",
			defaultValue=0,
			minValue=0,
			maxValue=16000000,
			description="PWM base frequency, in Hz. "
				    "Possible values: 16000000, 2000000, 250000, 62500, 15625, 0. "
				    "Set to 0 to disable PWM."))
	paramDescs.append(HwParamDesc_oper(
			"pwm_period",
			allowedOperTypes=(AwlOperatorTypes.MEM_A,
					  AwlOperatorTypes.IMM),
			description="PWM period.\n"
				"This can either be an integer between 0 and L#65000.\n"
				"Or an output word (AW, QW) where the program "
				"writes the desired period to.\n"
				"Defaults to L#65000, if not specified."))

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
			r = Relay(self.__pixtend, i, bitOffset,
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
			if self.__isV2:
				do = DigitalOut_V2(self.__pixtend, i, bitOffset, directOnly)
			else:
				do = DigitalOut_V1(self.__pixtend, i, bitOffset, directOnly)
			self.__DOs.append(do)

		# Build all DigitalIn() objects
		self.__DIs = []
		for i in range(self.NR_DI):
			oper = self.getParamValueByName("digitalIn%d_addr" % i)
			if oper is None:
				continue
			bitOffset = oper.offset.toLongBitOffset()
			directOnly = not self.isInProcessImage(oper.offset, 1, False)
			if self.__isV2:
				di = DigitalIn_V2(self.__pixtend, i, bitOffset, directOnly)
			else:
				di = DigitalIn_V1(self.__pixtend, i, bitOffset, directOnly)
			self.__DIs.append(di)

		# Build all GPIO output objects
		self.__GPIO_out = []
		for i in range(self.NR_GPIO):
			oper = self.getParamValueByName("gpio%d_addr" % i)
			if oper is None:
				continue
			if oper.operType != AwlOperatorTypes.MEM_A:
				continue
			bitOffset = oper.offset.toLongBitOffset()
			gpio = GPIO(self.__pixtend, i, bitOffset,
				    not self.isInProcessImage(oper.offset, 1, True))
			self.__GPIO_out.append(gpio)

		# Build all GPIO input objects
		self.__GPIO_in = []
		for i in range(self.NR_GPIO):
			oper = self.getParamValueByName("gpio%d_addr" % i)
			if oper is None:
				continue
			if oper.operType != AwlOperatorTypes.MEM_E:
				continue
			bitOffset = oper.offset.toLongBitOffset()
			gpio = GPIO(self.__pixtend, i, bitOffset,
				    not self.isInProcessImage(oper.offset, 1, False))
			self.__GPIO_in.append(gpio)

		# Build all analog input objects
		self.__AIs = []
		for i in range(self.NR_AI_V2 if self.__isV2 else self.NR_AI_V1):
			oper = self.getParamValueByName("analogIn%d_addr" % i)
			if oper is None:
				continue
			bitOffset = oper.offset.toLongBitOffset()
			ai = AnalogIn(self.__pixtend, i, bitOffset,
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
			ao = AnalogOut(self.__pixtend, i, bitOffset,
				       not self.isInProcessImage(oper.offset, 16, True))
			self.__AOs.append(ao)

		# Build all PWM() objects
		self.__PWMs = []
		for i in range(self.NR_PWM):
			oper = self.getParamValueByName("pwm%d_addr" % i)
			if oper is None:
				continue
			bitOffset = oper.offset.toLongBitOffset()
			pwm = PWM(self.__pixtend, i, bitOffset,
				  not self.isInProcessImage(oper.offset, 16, True))
			self.__PWMs.append(pwm)
			pwm.overDrive = self.getParamValueByName("pwm%d_servoOverDrive" % i)
		# Handle pwm_period parameter.
		try:
			oper = self.getParamValueByName("pwm_period")
			if not oper:
				# Use default constant pwm_period
				PWMPeriod(self.__pixtend, 0, 0).setPWMPeriod(65000)
			else:
				if oper.operType == AwlOperatorTypes.IMM:
					# Use custom constant pwm_period
					period = oper.immediate
					if period < 0 or period > 65000:
						raise ValueError
					PWMPeriod(self.__pixtend, 0, 0).setPWMPeriod(period)
				elif oper.operType == AwlOperatorTypes.MEM_A and\
				     oper.width == 16:
					# Use custom dynamic pwm_period
					bitOffset = oper.offset.toLongBitOffset()
					pwm = PWMPeriod(self.__pixtend, 0, bitOffset,
							not self.isInProcessImage(oper.offset, 16, True))
					self.__PWMs.append(pwm)
					pwm.setPWMPeriod(0)
				else:
					raise ValueError
		except ValueError as e:
			self.raiseException("Unsupported 'pwm_period' parameter value.")

		# Build a list of all outputs
		self.__allOutputs = []
		self.__allOutputs.extend(self.__relays)
		self.__allOutputs.extend(self.__DOs)
		self.__allOutputs.extend(self.__GPIO_out)
		self.__allOutputs.extend(self.__AOs)
		self.__allOutputs.extend(self.__PWMs)

		# Build a list of all inputs
		self.__allInputs = []
		self.__allInputs.extend(self.__DIs)
		self.__allInputs.extend(self.__GPIO_in)
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
						   self.__PWMs):
				out.setup(-firstOutByte)
				out.setDirection(True)

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
						   self.__AIs):
				inp.setup(-firstInByte)
				inp.setDirection(False)

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

		# Configure AnalogOut SPI communication.
		try:
			if self.__AOs:
				self.__pixtend.open_dac()
		except (IOError, ValueError) as e:
			self.raiseException("Failed to open DAC communication: %s" % str(e))

		# Configure global values of AnalogIn.
		try:
			AnalogIn.setFreq(self.__pixtend,
					 self.getParamValueByName("analogIn_kHz"))
		except ValueError as e:
			self.raiseException("Unsupported 'analogIn_kHz' parameter value. "
				"Supported values are: 125, 250, 500, 1000, 4000, 8000.")

		# Configure global values of PWM.
		try:
			PWM.setServoMode(self.__pixtend,
					 self.getParamValueByName("pwm_servoMode"))
		except ValueError as e:
			self.raiseException("Unsupported 'pwm_servoMode' parameter value.")
		try:
			freqHz = self.getParamValueByName("pwm_baseFreqHz")
			if not self.__PWMs:
				freqHz = 0
			PWM.setBaseFreq(self.__pixtend, freqHz)
		except ValueError as e:
			self.raiseException("Unsupported 'pwm_baseFreqHz' parameter value. "
				"Supported values are: 16000000, 2000000, 250000, 62500, 15625, 0.")

	def doStartup(self):
		if self.__pixtendInitialized:
			return

		self.__prevSpiCount = 0

		# Import the Pixtend library.
		boardType = self.getParamValueByName("boardType")
		if boardType == HwParamDesc_boardType.BOARD_V1_X:
			self.__isV2 = False
			try:
				from pixtendlib import Pixtend as pixtend_class
			except ImportError as e:
				self.raiseException("Failed to import pixtendlib.Pixtend module"
					":\n%s" % str(e))
		elif boardType == HwParamDesc_boardType.BOARD_V2_X:
			self.__isV2 = True
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
		if not self.__isV2 and self.__pollInt < 0.025:
			self.raiseException("pollIntMs is too low. It must be at least 25 ms.")
		if self.__isV2 and self.__pollInt < 0.0025:
			self.raiseException("pollIntMs is too low. It must be at least 3 ms.")
		if self.getParamValueByName("testMode"):
			# In test mode use poll interval as small as possible.
			self.__pollInt = 0.0025 if self.__isV2 else 0.0

		# Initialize PiXtend
		self.__pixtend = None
		try:
			if self.__isV2:
				# PiXtend v2.x
				self.__pixtend = self.__pixtend_class(
					com_interval=self.__pollInt,
					model=self.__pixtend_class.PIXTENDV2S_MODEL,
				)
				self.__prevSpiCount = self.__pixtend._spi_transfers & 0xFFFF
			else:
				# PiXtend v1.x
				self.__pixtend = self.__pixtend_class()
				self.__pixtend.open()
			# Wait for PiXtend to wake up.
			t = 0
			while True:
				self.cpu.updateTimestamp()
				if self.__isV2:
					spiCount = self.__pixtend._spi_transfers & 0xFFFF
					if self.__pixtendPoll(self.cpu.now) and\
					   spiCount != self.__prevSpiCount:
						break # success
				else:
					if self.__pixtendPoll(self.cpu.now):
						break # success
				t += 1
				if t >= 50:
					self.raiseException("Timeout waiting "
						"for PiXtend auto-mode.")
				time.sleep(self.__pollInt)
			if self.__isV2 and self.__pixtend.model_in_error:
				self.raiseException("Invalid board model number detected")
		except Exception as e:
			with suppressAllExc:
				self.__shutdown()
			self.raiseException("Failed to init PiXtend: %s" % (
				str(e)))

		# Build the HW shim and configure the hardware
		try:
			self.__build()
		except Exception as e:
			with suppressAllExc:
				self.__shutdown()
			raise e

		if self.__isV2:
			self.__prevSpiCount = self.__pixtend._spi_transfers & 0xFFFF
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
			spiCount = pixtend._spi_transfers & 0xFFFF
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

	def __syncPixtendPoll(self): #+cdef
#@cy		cdef S7CPU cpu
#@cy		cdef uint32_t retries
#@cy		cdef uint16_t spiCount
#@cy		cdef uint16_t prevSpiCount
#@cy		cdef double timeout

		# Synchronously run one PiXtend poll cycle.
		cpu = self.cpu
		retries = 0
		while True:
			cpu.updateTimestamp()
			if self.__isV2:
				pixtend = self.__pixtend
				# Wait until the poll thread did one transfer.
				timeout = cpu.now + (self.__pollInt * 10000.0)
				prevSpiCount = pixtend._spi_transfers & 0xFFFF
				while True:
					spiCount = pixtend._spi_transfers & 0xFFFF
					if spiCount != prevSpiCount:
						break
					cpu.updateTimestamp()
					if cpu.now >= timeout:
						self.raiseException("PiXtend poll wait timeout.")
					time.sleep(0.001)
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

		self.__syncPixtendPoll()
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
		self.__syncPixtendPoll()

		return True

# Module entry point
HardwareInterface = HardwareInterface_PiXtend

# -*- coding: utf-8 -*-
#
# PiXtend emulation
#
# Copyright 2018 Michael Buesch <m@bues.ch>
#
# Copyright (C) 2017 Robin Turner
# Qube Solutions UG (haftungsbeschränkt), Arbachtalstr. 6
# 72800 Eningen, Germany
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from abstract_spidev import Abstract_SpiDev
import os


class Fake_SpiDev_PiXtend_1_3(Abstract_SpiDev):
	"""PiXtend v1.3 emulation.

	This class contains code from pixtendlib.
	The following copyright notices apply in addition:

	# This file is part of the PiXtend(R) Project.
	#
	# For more information about PiXtend(R) and this program,
	# see <http://www.pixtend.de> or <http://www.pixtend.com>
	#
	# Copyright (C) 2017 Robin Turner
	# Qube Solutions UG (haftungsbeschränkt), Arbachtalstr. 6
	# 72800 Eningen, Germany
	#
	# This program is free software: you can redistribute it and/or modify
	# it under the terms of the GNU General Public License as published by
	# the Free Software Foundation, either version 3 of the License, or
	# (at your option) any later version.
	#
	# This program is distributed in the hope that it will be useful,
	# but WITHOUT ANY WARRANTY; without even the implied warranty of
	# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	# GNU General Public License for more details.
	#
	# You should have received a copy of the GNU General Public License
	# along with this program.  If not, see <http://www.gnu.org/licenses/>.
	"""

	__slots__ = (
		"__autoCount"
	)

	PIXTEND_SPI_HANDSHAKE = 0b10101010
	# 4-Byte Command length
	PIXTEND_SPI_SET_DOUT = 0b00000001
	PIXTEND_SPI_GET_DIN = 0b00000010
	PIXTEND_SPI_SET_RELAY = 0b00000111
	PIXTEND_SPI_SET_GPIO = 0b00001000
	PIXTEND_SPI_GET_GPIO = 0b00001001
	PIXTEND_SPI_GET_DOUT = 0b00010010
	PIXTEND_SPI_GET_RELAY = 0b00010011
	PIXTEND_SPI_SET_SERVO0 = 0b10000000
	PIXTEND_SPI_SET_SERVO1 = 0b10000001
	PIXTEND_SPI_SET_GPIO_CTRL = 0b10000101
	PIXTEND_SPI_SET_UC_CTRL = 0b10000110
	PIXTEND_SPI_SET_RASPSTAT = 0b10001000
	PIXTEND_SPI_GET_UC_STAT = 0b10001010
	# 5-Byte Command length
	PIXTEND_SPI_GET_AIN0 = 0b00000011
	PIXTEND_SPI_GET_AIN1 = 0b00000100
	PIXTEND_SPI_GET_AIN2 = 0b00000101
	PIXTEND_SPI_GET_AIN3 = 0b00000110
	PIXTEND_SPI_GET_TEMP0 = 0b00001010
	PIXTEND_SPI_GET_TEMP1 = 0b00001011
	PIXTEND_SPI_GET_TEMP2 = 0b00001100
	PIXTEND_SPI_GET_TEMP3 = 0b00001101
	PIXTEND_SPI_GET_HUM0 = 0b00001110
	PIXTEND_SPI_GET_HUM1 = 0b00001111
	PIXTEND_SPI_GET_HUM2 = 0b00010000
	PIXTEND_SPI_GET_HUM3 = 0b00010001
	PIXTEND_SPI_SET_PWM0 = 0b10000010
	PIXTEND_SPI_SET_PWM1 = 0b10000011
	PIXTEND_SPI_SET_AI_CTRL = 0b10000111
	PIXTEND_SPI_GET_UC_VER = 0b10001001
	# 6-Byte Command length
	PIXTEND_SPI_SET_PWM_CTRL = 0b10000100
	# Auto Mode - 34 bytes Command length
	PIXTEND_SPI_AUTO_MODE = 0b11100111

	def __init__(self, *args, **kwargs):
		Abstract_SpiDev.__init__(self, *args, **kwargs)

		self.__autoCount = 0

	def __command_generic(self, data):
		return [0] * len(data)

	def __command_autoMode(self, data):
		assert(data[0] == 128)
		assert(data[1] == 255)
		crc = self.__crc16Block(data[2:31])
		assert(data[31] == crc & 0xFF)
		assert(data[32] == (crc >> 8) & 0xFF)
		assert(data[33] == 128)

		DOs = data[2]
		relays = data[3]
		gpiosOut = data[4]
		pwm00 = data[5]
		pwm01 = data[6]
		pwm10 = data[7]
		pwm11 = data[8]
		pwmCtrl0 = data[9]
		pwmCtrl1 = data[10]
		pwmCtrl2 = data[11]
		gpioCtrl = data[12]
		ucCtrl = data[13]
		aiCtrl0 = data[14]
		aiCtrl1 = data[15]
		piStatus = data[16]
		assert(all((d == 0) for d in data[17:31]))

		# Check PWM values
		pwmCS = (pwmCtrl0 >> 5) & 7
		if pwmCS: # PWM enabled?
			if os.getenv("PIXTEND_IOTEST", ""):
				# Check the magic values that are set by pixtend-iotest.awlpro
				assert(pwm01 == 0x12 and pwm00 == 0x34)
				assert(pwm11 == 0x43 and pwm10 == 0x21)
				assert(((pwmCtrl0 >> 5) & 7) == 1) # 16 MHz
				assert((pwmCtrl0 & (1 << 0)) != 0) # PWM mode
				assert((pwmCtrl0 & (1 << 1)) == 0) # OD 0 off
				assert((pwmCtrl0 & (1 << 2)) == 0) # OD 1 off
				assert(pwmCtrl2 == 0xFD and pwmCtrl1 == 0xE8) # period = 65000
			elif os.getenv("PIXTEND_PERIPHERALIOTEST", ""):
				# Check the magic values that are set by pixtend-peripheral-io.awlpro
				if self.__autoCount >= 2:
					assert(pwm01 == 0x13 and pwm00 == 0x37)
					assert(pwm11 == 0x42 and pwm10 == 0x24)
		else:
			assert(pwm01 == 0 and pwm00 == 0)
			assert(pwm11 == 0 and pwm10 == 0)

		ret = [0] * 34
		ret[1] = 128

		ai0 = int(round(1.0 * 1024 / 10))
		ai1 = int(round(2.0 * 1024 / 10))
		ai2 = int(round(20.0 / 0.024194115990990990990990990991))
		ai3 = int(round(14.0 / 0.024194115990990990990990990991))

		ret[2] = (DOs & 0x3F) | (((DOs ^ 0x03) & 0x03) << 6) # DI
		ret[3] = ai0 & 0xFF # AI0/0
		ret[4] = (ai0 >> 8) & 0xFF # AI0/1
		ret[5] = ai1 & 0xFF # AI1/0
		ret[6] = (ai1 >> 8) & 0xFF # AI1/1
		ret[7] = ai2 & 0xFF # AI2/0
		ret[8] = (ai2 >> 8) & 0xFF # AI2/1
		ret[9] = ai3 & 0xFF # AI3/0
		ret[10] = (ai3 >> 8) & 0xFF # AI3/1
		ret[11] = (gpiosOut & 0x02) >> 1 # GPIO-in
		ret[12] = 0x10 # temp0/0
		ret[13] = 0x11 # temp0/1
		ret[14] = 0x12 # temp1/0
		ret[15] = 0x13 # temp1/1
		ret[16] = 0x14 # temp2/0
		ret[17] = 0x15 # temp2/1
		ret[18] = 0x16 # temp3/0
		ret[19] = 0x17 # temp3/1
		ret[20] = 0x20 # humid0/0
		ret[21] = 0x21 # humid0/1
		ret[22] = 0x22 # humid1/0
		ret[23] = 0x3B # humid1/1
		ret[24] = 0x3C # humid2/0
		ret[25] = 0x3D # humid2/1
		ret[26] = 0x3E # humid3/0
		ret[27] = 0x3F # humid3/1
		ret[28] = 0x02 # UC-ver-l
		ret[29] = 0x0D # UC-ver-h
		ret[30] = 0x01 # UC-status

		crc = self.__crc16Block(ret[2:31])
		ret[31] = crc & 0xFF
		ret[32] = (crc >> 8) & 0xFF
		ret[33] = 128

		self.__autoCount += 1

		return ret

	__commandHandlers = {
		# 4-Byte Command length
		PIXTEND_SPI_SET_DOUT		: __command_generic,
		PIXTEND_SPI_GET_DIN		: __command_generic,
		PIXTEND_SPI_SET_RELAY		: __command_generic,
		PIXTEND_SPI_SET_GPIO		: __command_generic,
		PIXTEND_SPI_GET_GPIO		: __command_generic,
		PIXTEND_SPI_GET_DOUT		: __command_generic,
		PIXTEND_SPI_GET_RELAY		: __command_generic,
		PIXTEND_SPI_SET_SERVO0		: __command_generic,
		PIXTEND_SPI_SET_SERVO1		: __command_generic,
		PIXTEND_SPI_SET_GPIO_CTRL	: __command_generic,
		PIXTEND_SPI_SET_UC_CTRL		: __command_generic,
		PIXTEND_SPI_SET_RASPSTAT	: __command_generic,
		PIXTEND_SPI_GET_UC_STAT		: __command_generic,
		# 5-Byte Command length
		PIXTEND_SPI_GET_AIN0		: __command_generic,
		PIXTEND_SPI_GET_AIN1		: __command_generic,
		PIXTEND_SPI_GET_AIN2		: __command_generic,
		PIXTEND_SPI_GET_AIN3		: __command_generic,
		PIXTEND_SPI_GET_TEMP0		: __command_generic,
		PIXTEND_SPI_GET_TEMP1		: __command_generic,
		PIXTEND_SPI_GET_TEMP2		: __command_generic,
		PIXTEND_SPI_GET_TEMP3		: __command_generic,
		PIXTEND_SPI_GET_HUM0		: __command_generic,
		PIXTEND_SPI_GET_HUM1		: __command_generic,
		PIXTEND_SPI_GET_HUM2		: __command_generic,
		PIXTEND_SPI_GET_HUM3		: __command_generic,
		PIXTEND_SPI_SET_PWM0		: __command_generic,
		PIXTEND_SPI_SET_PWM1		: __command_generic,
		PIXTEND_SPI_SET_AI_CTRL		: __command_generic,
		PIXTEND_SPI_GET_UC_VER		: __command_generic,
		# 6-Byte Command length
		PIXTEND_SPI_SET_PWM_CTRL	: __command_generic,
	}

	def xfer2(self, data, speed_hz=0, delay_usecs=0, bits_per_word=0):
		if (self._bus, self._device) == (0, 0):
			# PiXtend microcontroller
			if data[0] == self.PIXTEND_SPI_HANDSHAKE:
				command = data[1]
				try:
					handler = self.__commandHandlers[command]
				except KeyError as e:
					assert(0)
				ret = handler(self, data)
			elif data[0] == 128:
				ret = self.__command_autoMode(data)
			else:
				assert(0)
			return ret
		elif (self._bus, self._device) == (0, 1):
			# MCP4812 DAC chip
			GA = data[0] & 0x20
			assert(GA == 0)
			SHDN = data[0] & 0x10
			assert(SHDN != 0)
			D = ((data[0] & 0xF) << 6) | ((data[1] & 0xFF) >> 2)
			if (data[0] & 0x80) == 0:
				# DAC_A
				if os.getenv("PIXTEND_IOTEST", ""):
					assert(D == 1023)
			else:
				# DAC_B
				if os.getenv("PIXTEND_IOTEST", ""):
					assert(D == 102)
			return [0] * len(data)
		else:
			assert(0)

	@classmethod
	def __crc16(cls, crc, data):
		crc = crc ^ data
		for _ in range(8):
			if crc & 1:
				crc = (crc >> 1) ^ 0xA001
			else:
				crc = crc >> 1
		return crc

	@classmethod
	def __crc16Block(cls, dataSequence):
		crc = 0xFFFF
		for d in dataSequence:
			crc = cls.__crc16(crc, d)
		return crc

SpiDev = Fake_SpiDev_PiXtend_1_3

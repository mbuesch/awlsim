# -*- coding: utf-8 -*-
#
# PiXtend v2.x emulation
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


class Fake_SpiDev_PiXtend_2_0(Abstract_SpiDev):
	"""PiXtend v2.0 emulation.

	This class contains code from pixtendv2s and pixtendv2core.
	The following copyright notices apply in addition:

	# This file is part of the PiXtend(R) V2 Project.
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
	)

	def __init__(self, *args, **kwargs):
		Abstract_SpiDev.__init__(self, *args, **kwargs)

	def __handlePixtendComm(self, data):
		# Received header
		model_out = data[0]
		uc_mode = data[1]
		uc_ctrl0 = data[2]
		uc_ctrl1 = data[3]
		hdrCrc = self.__crc16Block(data[0:7])
		hdrCrcAct = data[7] | (data[8] << 8)
		assert(hdrCrc == hdrCrcAct)
		assert(model_out == 83)
		assert(uc_mode == 0)

		# Received data
		digital_in_debounce01 = data[9]
		digital_in_debounce23 = data[10]
		digital_in_debounce45 = data[11]
		digital_in_debounce67 = data[12]
		digital_out = data[13]
		relay_out = data[14]
		gpio_ctrl = data[15]
		gpio_out = data[16]
		gpio_debounce01 = data[17]
		gpio_debounce23 = data[18]
		pwm0_ctrl0 = data[19]
		pwm0_ctrl1L = data[20]
		pwm0_ctrl1H = data[21]
		pwm0aL = data[22]
		pwm0aH = data[23]
		pwm0bL = data[24]
		pwm0bH = data[25]
		pwm1_ctrl0 = data[26]
		pwm1_ctrl1L = data[27]
		pwm1_ctrl1H = data[28]
		pwm1aL = data[29]
		pwm1aH = data[30]
		pwm1bL = data[31]
		pwm1bH = data[32]

		retain_data = data[33:65]

		dataCrc = self.__crc16Block(data[9:65])
		dataCrcAct = data[65] | (data[66] << 8)
		assert(dataCrc == dataCrcAct)


		ret = [0] * len(data)

		# Sent header
		ret[0] = 42	# firmware version
		ret[1] = 21	# hardware version
		ret[2] = 83	# model_in
		ret[3] = 1	# uc_state
		ret[4] = 0	# uc_warnings
		hdrCrc = self.__crc16Block(ret[0:7])
		ret[7] = hdrCrc & 0xFF
		ret[8] = (hdrCrc >> 8) & 0xFF

		ai0 = int(round(1.0 * 1024 / 10))
		ai1 = int(round(2.0 * 1024 / 10))

		# Sent data
		ret[9] = (digital_out & 0x0F) | (((digital_out ^ 0x0F) & 0x0F) << 4) # Digital in
		ret[10] = ai0 & 0xFF		# Analog in 0L
		ret[11] = (ai0 >> 8) & 0xFF	# Analog in 0H
		ret[12] = ai1 & 0xFF		# Analog in 1L
		ret[13] = (ai1 >> 8) & 0xFF	# Analog in 1H
		ret[14] = (gpio_out & 0x02) >> 1 # GPIO in
		ret[15] = 0			# Temp 0L
		ret[16] = 0			# Temp 0H
		ret[17] = 0			# Humid 0L
		ret[18] = 0			# Humid 0H
		ret[19] = 0			# Temp 1L
		ret[20] = 0			# Temp 1H
		ret[21] = 0			# Humid 1L
		ret[22] = 0			# Humid 1H
		ret[23] = 0			# Temp 2L
		ret[24] = 0			# Temp 2H
		ret[25] = 0			# Humid 2L
		ret[26] = 0			# Humid 2H
		ret[27] = 0			# Temp 3L
		ret[28] = 0			# Temp 3H
		ret[29] = 0			# Humid 3L
		ret[30] = 0			# Humid 3H

		ret[32:64] = retain_data

		dataCrc = self.__crc16Block(ret[9:65])
		ret[65] = dataCrc & 0xFF
		ret[66] = (dataCrc >> 8) & 0xFF

		return ret

	def xfer2(self, data, speed_hz=0, delay_usecs=0, bits_per_word=0):
		if (self._bus, self._device) == (0, 0):
			# PiXtend microcontroller
			return self.__handlePixtendComm(data)
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

SpiDev = Fake_SpiDev_PiXtend_2_0

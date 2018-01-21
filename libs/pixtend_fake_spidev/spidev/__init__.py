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


class Fake_SpiDev(object):

	__slots__ = (
		"mode",
		"bits_per_word",
		"max_speed_hz",
		"_opened",
	)

	def __init__(self, bus=-1, client=-1):
		self.mode = 0
		self.bits_per_word = 0
		self.max_speed_hz = 0
		self._opened = -1
		if bus >= 0:
			self.open(bus, client)

	@property
	def cshigh(self):
		raise NotImplementedError

	@cshigh.setter
	def cshigh(self, cshigh):
		raise NotImplementedError

	@property
	def threewire(self):
		raise NotImplementedError

	@threewire.setter
	def threewire(self, threewire):
		raise NotImplementedError

	@property
	def lsbfirst(self):
		raise NotImplementedError

	@lsbfirst.setter
	def lsbfirst(self, lsbfirst):
		raise NotImplementedError

	@property
	def loop(self):
		raise NotImplementedError

	@loop.setter
	def loop(self, loop):
		raise NotImplementedError

	@property
	def no_cs(self):
		raise NotImplementedError

	@no_cs.setter
	def no_cs(self, no_cs):
		raise NotImplementedError

	def open(self, bus, device):
		assert(bus >= 0)
		assert(device >= 0)
		self._opened = 42

	def close(self):
		if self._opened >= 0:
			self._opened = -1

	def fileno(self):
		raise NotImplementedError

	def readbytes(self, length):
		raise NotImplementedError

	def writebytes(self, data):
		raise NotImplementedError

	def xfer(self, data, speed_hz=0, delay_usecs=0, bits_per_word=0):
		raise NotImplementedError

	def xfer2(self, data, speed_hz=0, delay_usecs=0, bits_per_word=0):
		raise NotImplementedError

	def __enter__(self):
		pass

	def __exit__(self, exc_type, exc_value, traceback):
		self.close()
		return False

class Fake_SpiDev_PiXtend_1_3(Fake_SpiDev):
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

	def __command_generic(self, data):
		return [0] * len(data)

	def __command_autoMode(self, data):
		ret = [0] * 34
		ret[0] = 128
		ret[1] = 255
		ret[33] = 128
		#TODO
		crc = self.__crc16Block(ret[2:31])
		ret[31] = crc & 0xFF
		ret[32] = (crc >> 8) & 0xFF
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

# -*- coding: utf-8 -*-
#
# PiLC Raspberry Pi HAT configuration library
#
# Copyright 2016 Michael Buesch <m@bues.ch>
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

import math
import smbus


class PilcConf(object):
	"""Hardware configuration of the PiLC hat.
	"""

	DEFAULT_BUS	= 0x00
	DEFAULT_DEV	= 0x2F

	CONF_NONE	= 0
	CONF_XTALCAL	= 1
	CONF_EEMUWE	= 2
	CONF_PBTXENDBG	= 3
	CONF_PBTXENTO	= 4

	sizes = {
		CONF_NONE	: 0,
		CONF_XTALCAL	: 8,
		CONF_EEMUWE	: 1,
		CONF_PBTXENDBG	: 8,
		CONF_PBTXENTO	: 16,
	}

	PBTXEN_DBG_OFF		= 0
	PBTXEN_DBG_RETRIG	= 1
	PBTXEN_DBG_NOTRIG	= 2

	TRIES = 5

	class Error(Exception):
		pass

	@classmethod
	def havePilcHat(cls):
		"""Returns True, if a PiLC HAT is attached to the device.
		"""
		try:
			with open("/proc/device-tree/hat/product", "rb") as fd:
				prod = fd.read().decode("UTF-8").rstrip('\0').strip()
				if prod != "PiLC":
					return False
		except (IOError, UnicodeError) as e:
			return False
		return True

	def __init__(self, bus = DEFAULT_BUS, dev = DEFAULT_DEV):
		try:
			self.__i2c = smbus.SMBus()
			self.__i2c.open(bus)
			self.__dev = dev
		except (OSError, IOError) as e:
			raise self.Error("Failed to init I2C communication:\n" + str(e))

	def close(self):
		try:
			return self.__i2c.close()
		except (OSError, IOError) as e:
			raise self.Error("Failed to close I2C communication:\n" + str(e))

	def __baudToFrameUs(self, kBaud):
		"""Get the frame length in microseconds.
		"""
		symsPerFrame = 1 + 8 + 1 + 1
		symUs = (1.0 / (kBaud * 1000)) * 1000000
		frameUs = symUs * symsPerFrame
		return int(math.ceil(frameUs))

	def setBaudrate(self, kBaud):
		self.set(self.CONF_PBTXENTO, self.__baudToFrameUs(kBaud))

	def get(self, confItem):
		itemSize = self.sizes[confItem]
		handlers = {
			0	: lambda confItem: None,
			1	: self.__readBool,
			8	: self.__readU8,
			16	: self.__readU16,
		}
		for i in range(self.TRIES):
			try:
				return handlers[itemSize](confItem)
			except (OSError, IOError) as e:
				continue
		raise self.Error("Failed to read config item %d" % confItem)

	def set(self, confItem, value):
		itemSize = self.sizes[confItem]
		handlers = {
			0	: lambda confItem, data: None,
			1	: self.__writeBool,
			8	: self.__writeU8,
			16	: self.__writeU16,
		}
		for i in range(self.TRIES):
			try:
				handlers[itemSize](confItem, value)
				checkValue = self.get(confItem)
				if value == checkValue:
					return
			except (OSError, IOError) as e:
				continue
		raise self.Error("Failed to write config item %d" % confItem)

	def __writeBool(self, confItem, data):
		data = 1 if data else 0
		self.__writeU8(confItem, data)

	def __writeU8(self, confItem, data):
		payload = [ (data & 0xFF), (~data & 0xFF), ]
		self.__i2c.write_i2c_block_data(self.__dev, confItem, payload)

	def __writeU16(self, confItem, data):
		payload = [ (data & 0xFF), ((data >> 8) & 0xFF),
			    (~data & 0xFF), ((~data >> 8) & 0xFF), ]
		self.__i2c.write_i2c_block_data(self.__dev, confItem, payload)

	def __readBool(self, confItem):
		return True if self.__readU8(confItem) else False

	def __readU8(self, confItem):
		payload = self.__i2c.read_i2c_block_data(self.__dev, confItem, 1)
		return payload[0]

	def __readU16(self, confItem):
		payload = self.__i2c.read_i2c_block_data(self.__dev, confItem, 2)
		return payload[0] | (payload[1] << 8)

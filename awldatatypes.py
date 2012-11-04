# -*- coding: utf-8 -*-
#
# AWL data types
# Copyright 2012 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

class GenericInteger(object):
	def __init__(self, value, mask):
		self.value = value
		self.mask = mask

	def set(self, value):
		self.value = value & self.mask

	def get(self):
		return self.value

	def setBit(self, bitNumber):
		self.value = (self.value | (1 << bitNumber)) & self.mask

	def clearBit(self, bitNumber):
		self.value &= ~(1 << bitNumber)

	def setBitValue(self, bitNumber, value):
		if value:
			self.setBit(bitNumber)
		else:
			self.clearBit(bitNumber)

	def getBit(self, bitNumber):
		return 1 if (self.value & (1 << bitNumber)) else 0

	def toHex(self):
		if self.mask == 0xFF:
			return "%02X" % self.value
		elif self.mask == 0xFFFF:
			return "%04X" % self.value
		elif self.mask == 0xFFFFFFFF:
			return "%08X" % self.value
		else:
			assert(0)

class GenericByte(GenericInteger):
	def __init__(self, value=0):
		GenericInteger.__init__(self, value, 0xFF)

class GenericWord(GenericInteger):
	def __init__(self, value=0):
		GenericInteger.__init__(self, value, 0xFFFF)

class GenericDWord(GenericInteger):
	def __init__(self, value=0):
		GenericInteger.__init__(self, value, 0xFFFFFFFF)

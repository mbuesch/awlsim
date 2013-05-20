# -*- coding: utf-8 -*-
#
# AWL simulator - data structs
# Copyright 2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from util import *
from awldatatypes import *


class AwlStructField(object):
	"Data structure field"

	def __init__(self, name, offset, bitSize, initialValue=0):
		self.name = name
		self.offset = offset
		self.__bitSize = bitSize # Size, in bits
		assert(self.__bitSize in (1, 8, 16, 32))
		self.initialValue = initialValue

	# Return size, in bits.
	@property
	def bitSize(self):
		return self.__bitSize

	# Return size, in bytes.
	@property
	def byteSize(self):
		return intDivRoundUp(self.bitSize, 8)

class AwlStruct(object):
	"Data structure"

	def __init__(self):
		self.fields = []
		self.name2field = {}

	# Return size, in bytes.
	def getSize(self):
		if not self.fields:
			return 0
		lastField = self.fields[-1]
		return lastField.offset.byteOffset + lastField.byteSize

	def addField(self, name, bitSize):
		if not bitSize:
			return
		if bitSize == 1 and self.fields and\
		   self.fields[-1].bitSize == 1 and\
		   self.fields[-1].offset.bitOffset < 7:
			# Consecutive bitfields are merged into one byte
			offset = AwlOffset(self.fields[-1].offset.byteOffset,
					   self.fields[-1].offset.bitOffset + 1)
		else:
			offset = AwlOffset(self.getSize())
		field = AwlStructField(name, offset, bitSize)
		self.fields.append(field)
		if name:
			self.name2field[name] = field

	def addFieldAligned(self, name, bitSize, byteAlignment):
		padding = byteAlignment - self.getSize() % byteAlignment
		if padding == byteAlignment:
			padding = 0
		self.addField(None, padding * 8)
		self.addField(name, bitSize)

	def addFieldNaturallyAligned(self, name, bitSize):
		alignment = 1
		if bitSize > 8:
			alignment = 2
		self.addFieldAligned(name, bitSize, alignment)

	def getField(self, name):
		try:
			return self.name2field[name]
		except KeyError:
			raise AwlSimError("Data structure field '%s' not found" % name)

class AwlStructInstanceByte(GenericByte):
	"Data structure byte"

	def __init__(self, value=0):
		GenericByte.__init__(self, value)

class AwlStructInstance(object):
	"Data structure instance"

	def __init__(self, struct):
		self.struct = struct
		self.__allocate()

	def __allocate(self):
		self.dataBytes = []
		for field in self.struct.fields:
			bsize = field.byteSize
			value = field.initialValue
			for i in range(field.byteSize):
				b = (value >> ((bsize - i - 1) * 8)) & 0xFF
				self.dataBytes.append(AwlStructInstanceByte(b))

	def getData(self, offset, bitSize):
		if bitSize % 8 == 0:
			nrBytes, value = bitSize // 8, 0
			off = offset.byteOffset
			assert(offset.bitOffset == 0)
			while nrBytes:
				value = (value << 8) | self.dataBytes[off].get()
				nrBytes -= 1
				off += 1
			return value
		if bitSize == 1:
			return self.dataBytes[offset.byteOffset].getBit(offset.bitOffset)
		raise AwlSimError("Invalid struct fetch of %d bits" % bitSize)

	def setData(self, offset, bitSize, value):
		if bitSize % 8 == 0:
			nrBytes = bitSize // 8
			off = offset.byteOffset + nrBytes - 1
			assert(offset.bitOffset == 0)
			while nrBytes:
				self.dataBytes[off].set(value)
				value >>= 8
				nrBytes -= 1
				off -= 1
			return
		if bitSize == 1:
			self.dataBytes[offset.byteOffset].setBitValue(
				offset.bitOffset, value)
			return
		raise AwlSimError("Invalid struct write of %d bits" % bitSize)

	def getFieldData(self, name):
		field = self.struct.getField(name)
		return self.getData(field.offset, field.bitSize)

	def setFieldData(self, name, value):
		field = self.struct.getField(name)
		self.setData(field.offset, field.bitSize, value)

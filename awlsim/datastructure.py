# -*- coding: utf-8 -*-
#
# AWL simulator - data structs
# Copyright 2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from awlsim.util import *
from awlsim.datatypes import *


class AwlStructField(object):
	"Data structure field"

	# name => Field name string
	# offset => Field offset as AwlOffset
	# dataType => AwlDataType
	# initialValue => The initilization value
	def __init__(self, name, offset, dataType, initialValue=0):
		self.name = name
		self.offset = offset
		self.dataType = dataType
		self.initialValue = initialValue

		# Store a copy of the data type size, in bits and bytes.
		self.bitSize = self.dataType.width
		self.byteSize = intDivRoundUp(self.bitSize, 8)

		assert(self.bitSize in (1, 8, 16, 32, 64))

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

	def addField(self, name, dataType):
		if dataType.width == 1 and self.fields and\
		   self.fields[-1].bitSize == 1 and\
		   self.fields[-1].offset.bitOffset < 7:
			# Consecutive bitfields are merged into one byte
			offset = AwlOffset(self.fields[-1].offset.byteOffset,
					   self.fields[-1].offset.bitOffset + 1)
		else:
			offset = AwlOffset(self.getSize())
		field = AwlStructField(name, offset, dataType)
		self.fields.append(field)
		if name:
			self.name2field[name] = field

	def addFieldAligned(self, name, dataType, byteAlignment):
		padding = byteAlignment - self.getSize() % byteAlignment
		if padding == byteAlignment:
			padding = 0
		while padding:
			self.addField(None, AwlDataType.makeByName("BYTE"))
			padding -= 1
		self.addField(name, dataType)

	def addFieldNaturallyAligned(self, name, dataType):
		alignment = 1
		if dataType.width > 8:
			alignment = 2
		self.addFieldAligned(name, dataType, alignment)

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

	def getFieldData(self, field):
		offset, bitSize = field.offset, field.bitSize
		if bitSize % 8 == 0:
			nrBytes, value, off = bitSize // 8, 0, offset.byteOffset
			assert(offset.bitOffset == 0)
			while nrBytes:
				value = (value << 8) | self.dataBytes[off].get()
				nrBytes -= 1
				off += 1
			return value
		elif bitSize == 1:
			return self.dataBytes[offset.byteOffset].getBit(offset.bitOffset)
		else:
			raise AwlSimError("Invalid struct fetch of %d bits" % bitSize)

	def setFieldData(self, field, value):
		offset, bitSize = field.offset, field.bitSize
		if bitSize % 8 == 0:
			nrBytes = bitSize // 8
			off = offset.byteOffset + nrBytes - 1
			assert(offset.bitOffset == 0)
			while nrBytes:
				self.dataBytes[off].set(value)
				value >>= 8
				nrBytes -= 1
				off -= 1
		elif bitSize == 1:
			self.dataBytes[offset.byteOffset].setBitValue(
				offset.bitOffset, value)
		else:
			raise AwlSimError("Invalid struct write of %d bits" % bitSize)

	def getFieldDataByName(self, name):
		return self.getFieldData(self.struct.getField(name))

	def setFieldDataByName(self, name, value):
		self.setFieldData(self.struct.getField(name), value)

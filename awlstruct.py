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

	def __init__(self, name, offset, size, initialValue=0):
		self.name = name
		self.offset = offset
		self.size = size # Size, in bits
		self.initialValue = initialValue

	# Return size, in bytes
	@property
	def byteSize(self):
		return intDivRoundUp(self.size, 8)

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
		return lastField.byteOffset + lastField.byteSize

	def addField(self, name, size):
		if not size:
			return
		offset = self.getSize()
		field = AwlStructField(name, offset, size)
		self.fields.append(field)
		if name:
			self.name2field[name] = field

	def addFieldAligned(self, name, size, alignment):
		padding = alignment - self.getSize() % alignment
		if padding == alignment:
			padding = 0
		self.addField(None, padding)
		self.addField(name, size)

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

	def getData(self, offset, size):
		if size % 8 == 0:
			nrBytes, value = size // 8, 0
			off = offset.byteOffset
			assert(offset.bitOffset == 0)
			while nrBytes:
				value = (value << 8) | self.dataBytes[off].get()
				nrBytes -= 1
				off += 1
			return value
		if size == 1:
			return self.dataBytes[offset.byteOffset].getBit(offset.bitOffset)
		raise AwlSimError("Invalid struct fetch size of %d" % size)

	def setData(self, offset, size, value):
		if size % 8 == 0:
			nrBytes = size // 8
			off = offset.byteOffset + nrBytes - 1
			assert(offset.bitOffset == 0)
			while nrBytes:
				self.dataBytes[off].set(value)
				value >>= 8
				nrBytes -= 1
				off -= 1
			return
		if size == 1:
			self.dataBytes[offset.byteOffset].setBitValue(
				offset.bitOffset, value)
			return
		raise AwlSimError("Invalid struct write size of %d" % size)

	def getFieldData(self, name):
		field = self.struct.getField(name)
		return self.getData(field.offset, field.size)

	def setFieldData(self, name, value):
		field = self.struct.getField(name)
		self.setData(field.offset, field.size, value)

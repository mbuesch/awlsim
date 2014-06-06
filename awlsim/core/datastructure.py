# -*- coding: utf-8 -*-
#
# AWL simulator - data structs
#
# Copyright 2013 Michael Buesch <m@bues.ch>
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
from awlsim.core.compat import *

from awlsim.core.util import *
from awlsim.core.datatypes import *


class AwlStructField(object):
	"Data structure field"

	# name => Field name string
	# offset => Field offset as AwlOffset
	# dataType => AwlDataType
	def __init__(self, name, offset, dataType):
		self.name = name
		self.offset = offset
		self.dataType = dataType

		# Store a copy of the data type size, in bits and bytes.
		self.bitSize = self.dataType.width
		self.byteSize = intDivRoundUp(self.bitSize, 8)

		assert(self.bitSize in (1, 8, 16, 32, 64))

class AwlStruct(object):
	"Data structure"

	def __init__(self):
		self.fields = []
		self.name2field = {}

	# Return aligned size, in bytes.
	def getSize(self):
		size = self.__getUnalignedSize()
		if size % 2:
			size += 1
		return size

	# Return unaligned size, in bytes.
	def __getUnalignedSize(self):
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
			offset = AwlOffset(self.__getUnalignedSize())
		field = AwlStructField(name, offset, dataType)
		self.fields.append(field)
		if name:
			self.name2field[name] = field

	def addFieldAligned(self, name, dataType, byteAlignment):
		padding = byteAlignment - self.__getUnalignedSize() % byteAlignment
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

class AwlStructInstance(object):
	"Data structure instance"

	def __init__(self, struct):
		self.struct = struct
		self.__allocate()

	def __allocate(self):
		# Allocate the structure
		self.dataBytes = ByteArray(self.struct.getSize())

	def getFieldData(self, field):
		return self.dataBytes.fetch(field.offset, field.bitSize)

	def setFieldData(self, field, value):
		self.dataBytes.store(field.offset, field.bitSize, value)

	def getFieldDataByName(self, name):
		return self.getFieldData(self.struct.getField(name))

	def setFieldDataByName(self, name, value):
		self.setFieldData(self.struct.getField(name), value)

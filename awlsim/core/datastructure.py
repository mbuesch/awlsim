# -*- coding: utf-8 -*-
#
# AWL simulator - data structs
#
# Copyright 2013-2014 Michael Buesch <m@bues.ch>
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

from awlsim.core.util import *
from awlsim.core.datatypes import *


class AwlStructField(object):
	"Data structure field"

	# name => Field name string
	# offset => Field offset as AwlOffset
	# dataType => AwlDataType
	# initBytes => bytes or bytearray of initialization data
	# dummy => If true, this is a dummy field that does not
	#          account to the combined struct size.
	def __init__(self, name, offset, dataType, initBytes=None, dummy=False):
		self.name = name
		self.offset = offset
		self.dataType = dataType
		self.initBytes = initBytes
		self.dummy = dummy

		self.bitSize = self.dataType.width
		self.byteSize = intDivRoundUp(self.bitSize, 8)

		if self.initBytes is not None:
			assert(len(self.initBytes) == self.byteSize)

	def __repr__(self):
		return "AwlStructField(\"%s\"%s, %s, %s, %s)" %\
			(str(self.name),
			 " (dummy)" if self.dummy else "",
			 str(self.offset),
			 str(self.dataType),
			 str(self.initBytes))

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
		# Get the offset of the last field and
		# add its size, if it is not a dummy field.
		lastField = self.fields[-1]
		return lastField.offset.byteOffset +\
			(0 if lastField.dummy else lastField.byteSize)

	def __registerField(self, field):
		self.fields.append(field)
		if field.name:
			self.name2field[field.name] = field

	# Compose a data structure field name.
	# nameComponents is a list of name components, or a name string.
	# linearArrayIndex is the linear array index to the last component, or None.
	# Returns the composed field name string.
	@classmethod
	def composeFieldName(cls, nameComponents, linearArrayIndex=None):
		nameComponents = toList(nameComponents)
		if not all(nameComponents):
			return None
		name = ".".join(nameComponents)
		if linearArrayIndex is not None:
			name += "[%d]" % linearArrayIndex
		return name

	# Add zero-length field.
	def __addDummyField(self, name=None):
		offset = AwlOffset(self.__getUnalignedSize())
		field = AwlStructField(name, offset,
				       AwlDataType.makeByName("VOID"),
				       dummy=True)
		self.__registerField(field)

	# Merge another struct 'otherStruct' into this struct 'self'.
	# 'otherStructName' is the name string of the other struct.
	# 'otherStructDataType' is the AwlDataType of the other struct.
	def merge(self, otherStruct, otherStructName=None, otherStructDataType=None):
		if not otherStructDataType:
			otherStructDataType = AwlDataType.makeByName("VOID")
		# First add a field with the sub-structure's name.
		# This field is used for retrieval of a pointer to the sub-struct,
		# for alignment and for informational purposes only.
		baseOffset = AwlOffset(self.__getUnalignedSize())
		field = AwlStructField(otherStructName,
				       baseOffset, otherStructDataType,
				       dummy=True)
		self.__registerField(field)
		# Add all fields from the other struct.
		baseOffset = AwlOffset(self.__getUnalignedSize())
		for otherField in otherStruct.fields:
			newName = self.composeFieldName((otherStructName, otherField.name))
			field = AwlStructField(newName,
					       baseOffset + otherField.offset,
					       otherField.dataType,
					       otherField.initBytes)
			self.__registerField(field)
		# Add a zero-length sub-struct-end guard field,
		# to enforce alignment of following fields.
		self.__addDummyField()

	def addField(self, cpu, name, dataType, initBytes=None):
		if dataType.type == dataType.TYPE_UDT_X:
			# Add an UDT.
			try:
				udt = cpu.udts[dataType.index]
			except KeyError:
				assert(0) # Should never happen
			assert(not initBytes)
			self.merge(udt.struct, name, dataType)
			return

		if dataType.width < 0:
			raise AwlSimError("With of data structure field '%s : %s' "
				"is undefined. This probably means that its data "
				"type is unsupported." %\
				(name, str(dataType)))

		if dataType.type == dataType.TYPE_ARRAY:
			# Add an ARRAY.
			# First add a field with the array's name.
			# It has the data type 'ARRAY' and is informational only.
			offset = AwlOffset(self.__getUnalignedSize())
			field = AwlStructField(name, offset, dataType, dummy=True)
			self.__registerField(field)
			# Add fields for each array entry.
			initOffset = AwlOffset()
			for i, childType in enumerate(dataType.children):
				childName = self.composeFieldName(name, i)
				try:
					if not initBytes:
						raise ValueError
					fieldInitData = ByteArray(intDivRoundUp(childType.width, 8))
					fieldInitData.storeBytes(AwlOffset(), childType.width,
								 initBytes.fetchBytes(initOffset,
										      childType.width))
				except (AwlSimError, ValueError) as e:
					fieldInitData = None
				self.addField(cpu, childName, childType,
					      fieldInitData)
				initOffset += AwlOffset.fromBitOffset(childType.width)
			# Add a zero-length array-end guard field,
			# to enforce alignment of following fields.
			self.__addDummyField()
		else:
			# Add a single data type.
			if dataType.width == 1 and self.fields and\
			   self.fields[-1].bitSize == 1 and\
			   self.fields[-1].offset.bitOffset < 7:
				# Consecutive bitfields are merged into one byte
				offset = AwlOffset(self.fields[-1].offset.byteOffset,
						   self.fields[-1].offset.bitOffset + 1)
			else:
				offset = AwlOffset(self.__getUnalignedSize())
			field = AwlStructField(name, offset, dataType, initBytes)
			self.__registerField(field)

	def addFieldAligned(self, cpu, name, dataType, byteAlignment, initBytes=None):
		padding = byteAlignment - self.__getUnalignedSize() % byteAlignment
		if padding == byteAlignment:
			padding = 0
		while padding:
			self.addField(cpu, None, AwlDataType.makeByName("BYTE"), None)
			padding -= 1
		self.addField(cpu, name, dataType, initBytes)

	def addFieldNaturallyAligned(self, cpu, name, dataType, initBytes=None):
		alignment = 1
		if dataType.type == dataType.TYPE_ARRAY or\
		   dataType.width > 8:
			alignment = 2
		self.addFieldAligned(cpu, name, dataType, alignment, initBytes)

	def getField(self, name, arrayIndex=None):
		if arrayIndex is not None:
			name = self.composeFieldName(name, arrayIndex)
		try:
			return self.name2field[name]
		except KeyError:
			raise AwlSimError("Data structure field '%s' not found" % name)

	def __repr__(self):
		return "\n".join(str(field) for field in self.fields)

class AwlStructInstance(object):
	"Data structure instance"

	def __init__(self, struct):
		# Store a reference to the data structure
		self.struct = struct
		# Allocate self.dataBytes
		self.dataBytes = ByteArray(self.struct.getSize())
		# Initialize the data structure
		for field in self.struct.fields:
			if not field.initBytes:
				continue
			try:
				self.dataBytes.storeBytes(field.offset, field.bitSize,
							  field.initBytes)
			except AwlSimError as e:
				raise AwlSimError("Data structure field '%s' "
					"initialization is out of range." %\
					str(field))

	def getFieldData(self, field, baseOffset=None):
		if baseOffset is None:
			return self.dataBytes.fetch(field.offset, field.bitSize)
		return self.dataBytes.fetch(baseOffset + field.offset, field.bitSize)

	def setFieldData(self, field, value, baseOffset=None):
		if baseOffset is None:
			self.dataBytes.store(field.offset,
					     field.bitSize, value)
		else:
			self.dataBytes.store(baseOffset + field.offset,
					     field.bitSize, value)

	def getFieldDataByName(self, name, arrayIndex=None):
		return self.getFieldData(self.struct.getField(name, arrayIndex))

	def setFieldDataByName(self, name, arrayIndex, value):
		self.setFieldData(self.struct.getField(name, arrayIndex), value)

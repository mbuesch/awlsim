# -*- coding: utf-8 -*-
#
# AWL simulator - data structs
#
# Copyright 2013-2015 Michael Buesch <m@bues.ch>
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

from awlsim.common.datatypehelpers import * #+cimport
from awlsim.common.exceptions import *

from awlsim.core.util import *
from awlsim.core.identifier import *
from awlsim.core.memory import * #+cimport
from awlsim.core.offset import * #+cimport


__all__ = [
	"AwlStructField",
	"AwlStruct",
	"AwlStructInstance",
]


class AwlStructField(object): #+cdef
	"""Data structure field.
	"""

	__slots__ = (
		"name",
		"offset",
		"dataType",
		"dataTypeId",
		"initBytes",
		"override",
		"finalOverride",
		"bitSize",
		"byteSize",
		"compound",
		"callByRef",
	)

	# name => Field name string
	# offset => Field offset as AwlOffset
	# dataType => AwlDataType (or data type declaration string)
	# initBytes => bytes or bytearray of initialization data
	# override => Optional: Another AwlStructField that overrides this one.
	#             May be None, if unused.
	def __init__(self, name, offset, dataType, initBytes=None, override=None):
		from awlsim.core.datatypes import AwlDataType

		if isString(dataType):
			dataType = AwlDataType.makeByName(dataType)

		self.name = name
		self.offset = offset
		self.dataType = dataType
		self.initBytes = initBytes
		self.override = override
		self.finalOverride = None # Not known, yet.

		self.bitSize = self.dataType.width
		self.byteSize = intDivRoundUp(self.bitSize, 8)

		self.compound = bool(dataType.compound)

		from awlsim.core.blockinterface import BlockInterface
		self.callByRef = bool(dataType.type in AwlDataType.callByRefTypes)

		if self.initBytes is not None:
			assert(len(self.initBytes) == self.byteSize)

	def __eq__(self, other): #@nocy
#@cy	cdef __eq(self, other):
		return (self is other) or (\
			isinstance(other, AwlStructField) and\
			self.name == other.name and\
			self.offset == other.offset and\
			self.dataType == other.dataType and\
			self.initBytes == other.initBytes and\
			self.override == other.override\
		)

	def __ne__(self, other):		#@nocy
		return not self.__eq__(other)	#@nocy

#@cy	def __richcmp__(self, object other, int op):
#@cy		if op == 2: # __eq__
#@cy			return self.__eq(other)
#@cy		elif op == 3: # __ne__
#@cy			return not self.__eq(other)
#@cy		return False

	# Return the final AwlStructField override in the chain.
	def getFinalOverride(self):
		if self.override:
			return self.override.getFinalOverride()
		return self

	def __repr__(self):
		s = "AwlStructField(\"%s\", P#%s, %s (%d bit), init=%s)" %\
			(str(self.name),
			 str(self.offset),
			 str(self.dataType),
			 self.bitSize,
			 str(self.initBytes))
		if self.override:
			s += " as "
			s += str(self.override)
		return s

class AwlStruct(object): #+cdef
	"""Data structure.
	This is a generic class holding information about data structures
	in an AWL program. That might be an actual STRUCT or the internal
	low level representation of an UDT, DB, etc...
	"""

	__slots__ = (
		"fields",
		"name2field",
	)

	def __init__(self):
		self.fields = []
		self.name2field = {}

	def __eq__(self, other): #@nocy
#@cy	cdef __eq(self, other):
		return (self is other) or (\
			isinstance(other, AwlStruct) and\
			self.fields == other.fields\
		)

	def __ne__(self, other):		#@nocy
		return not self.__eq__(other)	#@nocy

#@cy	def __richcmp__(self, object other, int op):
#@cy		if op == 2: # __eq__
#@cy			return self.__eq(other)
#@cy		elif op == 3: # __ne__
#@cy			return not self.__eq(other)
#@cy		return False

	# Return aligned size, in bytes.
	def getSize(self):
		size = self.getUnalignedSize()
		if size % 2:
			size += 1
		return size

	# Return unaligned size, in bytes.
	def getUnalignedSize(self):
		if not self.fields:
			return 0
		# Get the offset of the last field and
		# add its size.
		lastField = self.fields[-1].getFinalOverride()
		return lastField.offset.byteOffset + lastField.byteSize

	def __registerField(self, field):
		self.fields.append(field)
		if field.name:
			self.name2field[field.name] = field

	# Add zero-length field.
	def addDummyField(self, name=None):
		offset = make_AwlOffset(self.getUnalignedSize(), 0)
		field = AwlStructField(name, offset, "VOID")
		self.__registerField(field)

	# Merge another struct 'otherStruct' into this struct 'self'.
	# 'otherStructName' is the name string of the other struct.
	# 'otherStructDataType' is the AwlDataType of the other struct.
	def merge(self, otherStruct, otherStructName=None, otherStructDataType=None):
		if not otherStructDataType:
			otherStructDataType = "VOID"
		# First add a field with the sub-structure's name.
		# This field is used for retrieval of a pointer to the sub-struct,
		# for alignment and for informational purposes only.
		baseOffset = make_AwlOffset(self.getUnalignedSize(), 0)
		baseField = AwlStructField(otherStructName,
				baseOffset, otherStructDataType,
				override = AwlStructField(otherStructName,
							  baseOffset, "VOID"))
		self.__registerField(baseField)
		# Add all fields from the other struct.
		baseOffset = make_AwlOffset(self.getUnalignedSize(), 0)
		for otherField in otherStruct.fields:
			if otherStructName and otherField.name:
				if otherField.name.startswith('[') and\
				   otherField.name.endswith(']'):
					newName = otherStructName + otherField.name
				else:
					newName = otherStructName + "." + otherField.name
			else:
				newName = None
			field = AwlStructField(name = newName,
					       offset = baseOffset + otherField.offset,
					       dataType = otherField.dataType,
					       initBytes = otherField.initBytes,
					       override = otherField.override)
			self.__registerField(field)
		# Add a zero-length sub-struct-end guard field,
		# to enforce alignment of following fields.
		self.addDummyField()
		return baseField

	def addField(self, cpu, name, dataType, initBytes=None):
		from awlsim.core.datatypes import AwlDataType

		initMem = AwlMemory()
		initMem.dataBytes = initBytes

		if dataType.type == dataType.TYPE_UDT_X:
			# Add an UDT.
			try:
				udt = cpu.udts[dataType.index]
			except KeyError:
				assert(0) # Should never happen
			assert(not initBytes)
			# Assign the struct to the UDT data type, if
			# not already done so.
			assert(dataType._struct is None or
			       dataType._struct is udt._struct)
			dataType.setStruct(udt._struct)
			# Merge the UDT struct with this struct.
			return self.merge(udt._struct, name, dataType)

		if dataType.width < 0:
			raise AwlSimError("Width of data structure field '%s : %s' "
				"is undefined. This probably means that its data "
				"type is unsupported." %\
				(name, str(dataType)))

		if dataType.type == dataType.TYPE_STRUCT or\
		   dataType.type == dataType.TYPE_STRING:
			# Add a STRUCT (or STRING, which is represented as struct).
			# The struct is represented by the data types struct.
			# Merge the data type struct into this struct.
			assert(dataType._struct)
			baseField = self.merge(dataType._struct, name, dataType)
			baseField.override = AwlStructField(baseField.name,
							    baseField.offset,
							    "VOID")
			baseField.initBytes = initBytes

		if dataType.type == dataType.TYPE_ARRAY:
			# Add an ARRAY.
			# First add a field with the array's name.
			# It has the data type 'ARRAY' and is informational only.
			offset = make_AwlOffset(self.getUnalignedSize(), 0)
			baseField = AwlStructField(name, offset, dataType,
					override = AwlStructField(name, offset,
								  "VOID"))
			self.__registerField(baseField)
			# Add fields for each ARRAY entry.
			initOffset = make_AwlOffset(0, 0)
			childIdent = AwlDataIdent(name,
					[ d[0] for d in dataType.arrayDimensions ],
					doValidateName = False)
			childType = dataType.arrayElementType
			if not childType.allowedInArray:
				raise AwlSimError("Data type '%s' not allowed in ARRAY" %\
					str(childType))
			for i in range(dataType.arrayGetNrElements()):
				try:
					if not initBytes:
						raise ValueError
					fieldInitMem = AwlMemory(intDivRoundUp(childType.width, 8))
					fieldInitData = fieldInitMem.dataBytes
					fieldInitMem.store(make_AwlOffset(0, 0), childType.width,
							    initMem.fetch(initOffset,
									  childType.width))
				except (AwlSimError, ValueError) as e:
					fieldInitData = None
				self.addField(cpu, str(childIdent), childType,
					      fieldInitData)
				initOffset += make_AwlOffset_fromLongBitOffset(childType.width)
				childIdent.advanceToNextArrayElement(dataType.arrayDimensions)
				if childType.width > 8 and\
				   intDivRoundUp(childType.width, 8) % 2 != 0:
					# Align each element to 2-byte-boundary, if word or bigger.
					self.addField(cpu, None, AwlDataType.makeByName("BYTE"))
			# Add a zero-length array-end guard field,
			# to enforce alignment of following fields.
			self.addDummyField()

		if dataType.type not in {dataType.TYPE_ARRAY,
					 dataType.TYPE_STRUCT,
					 dataType.TYPE_STRING}:
			# Add a single data type.
			if dataType.width == 1 and self.fields and\
			   self.fields[-1].bitSize == 1 and\
			   self.fields[-1].offset.bitOffset < 7:
				# Consecutive bitfields are merged into one byte
				offset = make_AwlOffset(self.fields[-1].offset.byteOffset,
						   self.fields[-1].offset.bitOffset + 1)
			else:
				offset = make_AwlOffset(self.getUnalignedSize(), 0)
			baseField = AwlStructField(name, offset, dataType, initBytes)
			self.__registerField(baseField)
		return baseField

	def addFieldAligned(self, cpu, name, dataType, byteAlignment, initBytes=None):
		from awlsim.core.datatypes import AwlDataType

		padding = byteAlignment - self.getUnalignedSize() % byteAlignment
		if padding == byteAlignment:
			padding = 0
		while padding:
			self.addField(cpu, None, AwlDataType.makeByName("BYTE"), None)
			padding -= 1
		return self.addField(cpu, name, dataType, initBytes)

	def addFieldNaturallyAligned(self, cpu, name, dataType, initBytes=None):
		if dataType.naturalAlignment == dataType.ALIGN_WORD:
			alignment = 2
		else:
			alignment = 1
		return self.addFieldAligned(cpu, name, dataType, alignment, initBytes)

	def getField(self, name):
		try:
			return self.name2field[name]
		except KeyError:
			raise AwlSimError("Data structure field '%s' not found" % name)

	def __repr__(self):
		return "\n".join(str(field) for field in self.fields)

class AwlStructInstance(object): #+cdef
	"""Data structure instance.
	This represents an instance that corresponds to an AwlStruct() object.
	"""

	__slots__ = (
		"_struct",
		"memory",
	)

	def __init__(self, _struct):
		# Store a reference to the data structure
		self._struct = _struct
		# Allocate self.memory
		self.memory = AwlMemory(self._struct.getSize())
		# Initialize the data structure
		for field in self._struct.fields:
			if not field.initBytes:
				continue
			try:
				self.memory.store(field.offset, field.bitSize,
						  field.initBytes)
			except AwlSimError as e:
				raise AwlSimError("Data structure field '%s' "
					"initialization is out of range." %\
					str(field))

	def getFieldData(self, field, baseOffset): #@nocy
#@cy	cdef object getFieldData(self, AwlStructField field, AwlOffset baseOffset):
		if baseOffset is None:
			return self.memory.fetch(field.offset, field.bitSize)
		return self.memory.fetch(baseOffset + field.offset, field.bitSize)

	def setFieldData(self, field, value, baseOffset): #@nocy
#@cy	cdef setFieldData(self, AwlStructField field, object value, AwlOffset baseOffset):
		if baseOffset is None:
			self.memory.store(field.offset,
					  field.bitSize, value)
		else:
			self.memory.store(baseOffset + field.offset,
					  field.bitSize, value)

	def getFieldDataByName(self, name):
		return self.getFieldData(self._struct.getField(name), None)

	def setFieldDataByName(self, name, value):
		self.setFieldData(self._struct.getField(name), value, None)

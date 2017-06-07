# -*- coding: utf-8 -*-
#
# AWL simulator - Central memory abstraction
#
# Copyright 2012-2017 Michael Buesch <m@bues.ch>
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

from awlsim.common.util import *
from awlsim.common.datatypehelpers import * #+cimport
from awlsim.common.exceptions import *

from awlsim.core.datatypes import *
from awlsim.core.offset import * #+cimport


__all__ = [
	"Pointer",
	"PointerConst",
	"DBPointer",
	"SymbolicDBPointer",
	"ANYPointer",
	"ANYPointerConst",
	"Accu",
	"Addressregister",
	"AwlMemory",
]


class GenericInteger(object): #+cdef

	__slots__ = (
		"value",
		"mask",
	)

	def __init__(self, value, width): #@nocy
#@cy	def __init__(self, int64_t value, uint8_t width):
#@cy		cdef uint64_t one

		assert(width > 0 and width <= 32)
		self.value = value
		one = 1
		self.mask = int(((one << width) - 1) & 0xFFFFFFFF)

	def copyFrom(self, other): #@nocy
#@cy	cdef void copyFrom(self, GenericInteger other):
		self.value = other.value & self.mask

	def reset(self): #@nocy
#@cy	cdef void reset(self):
		self.value = 0

	def set(self, value): #@nocy
#@cy	cdef void set(self, int64_t value):
		self.value = value & self.mask

	def setByte(self, value):				#@nocy
		self.value = (((self.value & 0xFFFFFF00) |	#@nocy
			       (value & 0xFF)) &		#@nocy
			      self.mask)			#@nocy
#@cy	cdef void setByte(self, int64_t value):
#@cy		self.value = (((self.value & 0xFFFFFF00u) |
#@cy			       <uint8_t>value) &
#@cy			      self.mask)

	def setWord(self, value):				#@nocy
		self.value = (((self.value & 0xFFFF0000) |	#@nocy
			       (value & 0xFFFF)) &		#@nocy
			      self.mask)			#@nocy
#@cy	cdef void setWord(self, int64_t value):
#@cy		self.value = (((self.value & 0xFFFF0000u) |
#@cy			       <uint16_t>value) &
#@cy			      self.mask)

	def setDWord(self, value):				#@nocy
		self.value = value & 0xFFFFFFFF & self.mask	#@nocy
#@cy	cdef void setDWord(self, int64_t value):
#@cy		self.value = <uint32_t>value & self.mask

	def setPyFloat(self, pyfl): #@nocy
#@cy	cdef setPyFloat(self, pyfl):
		self.value = pyFloatToDWord(pyfl)

	def get(self): #@nocy
#@cy	cdef uint32_t get(self):
		return self.value

	def getByte(self):			#@nocy
		return self.value & 0xFF	#@nocy
#@cy	cdef uint8_t getByte(self):
#@cy		return self.value & 0xFFu

	def getWord(self):			#@nocy
		return self.value & 0xFFFF	#@nocy
#@cy	cdef uint16_t getWord(self):
#@cy		return self.value & 0xFFFFu

	def getDWord(self):			#@nocy
		return self.value & 0xFFFFFFFF	#@nocy
#@cy	cdef uint32_t getDWord(self):
#@cy		return self.value & 0xFFFFFFFFu

	def getSignedByte(self): #@nocy
#@cy	cdef int8_t getSignedByte(self):
		return byteToSignedPyInt(self.value)

	def getSignedWord(self): #@nocy
#@cy	cdef int16_t getSignedWord(self):
		return wordToSignedPyInt(self.value)

	def getSignedDWord(self): #@nocy
#@cy	cdef int32_t getSignedDWord(self):
		return dwordToSignedPyInt(self.value)

	def getPyFloat(self): #@nocy
#@cy	cdef getPyFloat(self):
		return dwordToPyFloat(self.value)

	def setBit(self, bitNumber): #@nocy
#@cy	cdef void setBit(self, uint8_t bitNumber):
		self.value = (self.value | (1 << bitNumber)) & self.mask

	def clearBit(self, bitNumber): #@nocy
#@cy	cdef void clearBit(self, uint8_t bitNumber):
		self.value &= ~(1 << bitNumber)

	def setBitValue(self, bitNumber, value): #@nocy
#@cy	cdef void setBitValue(self, uint8_t bitNumber, _Bool value):
		if value:
			self.setBit(bitNumber)
		else:
			self.clearBit(bitNumber)

	def getBit(self, bitNumber): #@nocy
#@cy	cdef unsigned char getBit(self, uint8_t bitNumber):
		return (self.value >> bitNumber) & 1

	def toHex(self):
		if self.mask == 0xFF:
			return "%02X" % self.value
		elif self.mask == 0xFFFF:
			return "%04X" % self.value
		elif self.mask == 0xFFFFFFFF:
			return "%08X" % self.value
		else:
			assert(0)

class GenericWord(GenericInteger): #+cdef
	__slots__ = ()

	def __init__(self, value=0):
		GenericInteger.__init__(self, value, 16)

class GenericDWord(GenericInteger): #+cdef
	__slots__ = ()

	def __init__(self, value=0):
		GenericInteger.__init__(self, value, 32)

class __PointerConstClass(object): #+cdef
	__slots__ = (
		"AREA_SHIFT",
		"AREA_MASK",
		"AREA_MASK_S",
		"AREA_NONE",
		"AREA_P",
		"AREA_E",
		"AREA_A",
		"AREA_M",
		"AREA_DB",
		"AREA_DI",
		"AREA_L",
		"AREA_VL",
		"AREA_NONE_S",
		"AREA_P_S",
		"AREA_E_S",
		"AREA_A_S",
		"AREA_M_S",
		"AREA_DB_S",
		"AREA_DI_S",
		"AREA_L_S",
		"AREA_VL_S",
		"area2str",
	)

	def __init__(self):
		# Area code position
		self.AREA_SHIFT		= 24
		self.AREA_MASK		= 0xFF
		self.AREA_MASK_S	= self.AREA_MASK << self.AREA_SHIFT

		# Area codes
		self.AREA_NONE		= 0x00
		self.AREA_P		= 0x80	# Peripheral area
		self.AREA_E		= 0x81	# Input
		self.AREA_A		= 0x82	# Output
		self.AREA_M		= 0x83	# Flags
		self.AREA_DB		= 0x84	# Global datablock
		self.AREA_DI		= 0x85	# Instance datablock
		self.AREA_L		= 0x86	# Localstack
		self.AREA_VL		= 0x87	# Parent localstack

		# Area codes (shifted to the pointer location)
		self.AREA_NONE_S	= self.AREA_NONE << self.AREA_SHIFT
		self.AREA_P_S		= self.AREA_P << self.AREA_SHIFT
		self.AREA_E_S		= self.AREA_E << self.AREA_SHIFT
		self.AREA_A_S		= self.AREA_A << self.AREA_SHIFT
		self.AREA_M_S		= self.AREA_M << self.AREA_SHIFT
		self.AREA_DB_S		= self.AREA_DB << self.AREA_SHIFT
		self.AREA_DI_S		= self.AREA_DI << self.AREA_SHIFT
		self.AREA_L_S		= self.AREA_L << self.AREA_SHIFT
		self.AREA_VL_S		= self.AREA_VL << self.AREA_SHIFT

		# Convert an area code to string
		self.area2str = {
			self.AREA_P	: "P",
			self.AREA_E	: "E",
			self.AREA_A	: "A",
			self.AREA_M	: "M",
			self.AREA_DB	: "DBX",
			self.AREA_DI	: "DIX",
			self.AREA_L	: "L",
			self.AREA_VL	: "V",
		}

PointerConst = __PointerConstClass() #+cdef-public-__PointerConstClass

class Pointer(GenericDWord): #+cdef
	"""Pointer value.
	The basic data type (GenericDWord) holds the pointer value
	and the area code."""

	# Width, in bits.
	width = 32

	__slots__ = ()

	def __init__(self, ptrValue = 0):
		GenericDWord.__init__(self, ptrValue)

	# Get the pointer (32 bit).
	def toPointer(self): #@nocy
#@cy	cpdef toPointer(self):
		return Pointer(self.toPointerValue())

	# Get the 32 bit pointer value.
	toPointerValue = GenericDWord.get #@nocy
#@cy	cpdef uint32_t toPointerValue(self):
#@cy		return self.get()

	# Get the pointer as DB-pointer (48 bit).
	def toDBPointer(self): #@nocy
#@cy	cpdef toDBPointer(self):
		return DBPointer(self.toPointerValue())

	# Get the DB-pointer value (48 bit).
	def toDBPointerValue(self): #@nocy
#@cy	cpdef uint64_t toDBPointerValue(self):
		return self.toDBPointer().toDBPointerValue()

	# Get the pointer as ANY-pointer (80 bit).
	def toANYPointer(self): #@nocy
#@cy	cpdef ANYPointer toANYPointer(self):
		return ANYPointer(self.toPointerValue())

	# Get the ANY-pointer value (80 bit).
	def toANYPointerValue(self): #@nocy
#@cy	cpdef object toANYPointerValue(self):
		return self.toANYPointer().toANYPointerValue()

	# Get the native pointer value for this type.
	toNativePointerValue = toPointerValue #@nocy
#@cy	cpdef object toNativePointerValue(self):
#@cy		return self.toPointerValue()

	# Get the area code, as byte.
	def getArea(self): #@nocy
#@cy	cpdef uint8_t getArea(self):
		return (self.toPointerValue() >> 24) & 0xFF

	# Set the area code, as byte.
	def setArea(self, newArea): #@nocy
#@cy	cpdef setArea(self, uint8_t newArea):
		self.set((self.get() & 0x00FFFFFF) | (newArea << 24))

	# Get the byte offset, as word.
	def getByteOffset(self): #@nocy
#@cy	cpdef uint16_t getByteOffset(self):
		return (self.toPointerValue() >> 3) & 0xFFFF

	# Get the bit offset, as byte.
	def getBitOffset(self): #@nocy
#@cy	cpdef uint8_t getBitOffset(self):
		return self.toPointerValue() & 7

	# Get a P#... string for this pointer.
	def toPointerString(self):
		area = self.getArea()
		if area:
			if area == PointerConst.AREA_P:
				prefix = "P "
			elif area == PointerConst.AREA_E:
				prefix = "E "
			elif area == PointerConst.AREA_A:
				prefix = "A "
			elif area == PointerConst.AREA_M:
				prefix = "M "
			elif area == PointerConst.AREA_DB:
				prefix = "DBX "
			elif area == PointerConst.AREA_DI:
				prefix = "DIX "
			elif area == PointerConst.AREA_L:
				prefix = "L "
			elif area == PointerConst.AREA_VL:
				prefix = "V "
			else:
				prefix = "(%02X) " % area
		else:
			prefix = ""
		return "P#%s%d.%d" % (prefix, self.getByteOffset(),
				      self.getBitOffset())

	def __repr__(self):
		return self.toPointerString()

class DBPointer(Pointer): #+cdef
	"""DB-Pointer value.
	The basic data type (Pointer) holds the pointer value
	and the area code. The DB number is stored separately in 'dbNr'."""

	__slots__ = (
		"dbNr",
	)

	# Width, in bits.
	width = 48

	def __init__(self, ptrValue = 0, dbNr = 0):
		Pointer.__init__(self, ptrValue)
		if not dbNr or dbNr < 0:
			dbNr = 0
		self.dbNr = dbNr

	# Get the pointer as DB-pointer (48 bit).
	def toDBPointer(self): #@nocy
#@cy	cpdef toDBPointer(self):
		return DBPointer(self.toPointerValue(), self.dbNr)

	# Get the DB-pointer value (48 bit).
	def toDBPointerValue(self): #@nocy
		return (self.dbNr << 32) | self.toPointerValue() #@nocy
#@cy	cpdef uint64_t toDBPointerValue(self):
#@cy		cdef uint64_t dbNr
#@cy		dbNr = self.dbNr
#@cy		return (dbNr << 32) | self.toPointerValue()

	# Get the pointer as ANY-pointer (80 bit).
	def toANYPointer(self): #@nocy
#@cy	cpdef ANYPointer toANYPointer(self):
		return ANYPointer(self.toPointerValue(), self.dbNr)

	# Get the native pointer value for this type.
	toNativePointerValue = toDBPointerValue #@nocy
#@cy	cpdef object toNativePointerValue(self):
#@cy		return self.toDBPointerValue()

	# Get a P#... string for this pointer.
	def toPointerString(self):
		if self.dbNr:
			assert(self.dbNr > 0 and self.dbNr <= 0xFFFF)
			if self.getArea() == PointerConst.AREA_DB:
				prefix = "DB%d.DBX " % self.dbNr
			else:
				prefix = "DB%d.(%02X) " % (self.dbNr, self.getArea())
		else:
			return Pointer.toPointerString(self)
		return "P#%s%d.%d" % (prefix, self.getByteOffset(),
				      self.getBitOffset())

class SymbolicDBPointer(DBPointer): #+cdef
	"""Symbolic DB-Pointer value.
	This is a non-standard awlsim extension.
	Example:
		P#DB100.ARRAYVAR[1].ELEMENT
	Example with symbolic DB:
		P#"MyData".ARRAYVAR[1].ELEMENT
	"""

	__slots__ = (
		"identChain",
		"dbSymbol",
	)

	# Width, in bits.
	width = -1	# Unknown width

	def __init__(self, ptrValue = 0, dbNr = 0,
		     identChain = None, dbSymbol = None):
		DBPointer.__init__(self, ptrValue, dbNr)
		self.identChain = identChain
		self.dbSymbol = dbSymbol

	# Get a P#... string for this pointer.
	def toPointerString(self):
		if self.dbSymbol or self.dbNr:
			if self.dbSymbol:
				prefix = '"%s".' % self.dbSymbol
			else:
				prefix = "DB%d." % self.dbNr
			if self.identChain:
				return "P#%s%s" % (prefix,
					self.identChain.getString())
			else:
				if self.getArea() == PointerConst.AREA_DB:
					prefix += "DBX "
				else:
					prefix += "(%02X) " % self.getArea()
				return "P#%s%d.%d" % (prefix,
					self.getByteOffset(), self.getBitOffset())
		else:
			assert(not self.identChain)
			return Pointer.toPointerString(self)

class __ANYPointerConstClass(object): #+cdef
	__slots__ = (
		"MAGIC",
		"typeId2typeCode",
		"typeCode2typeId",
	)

	def __init__(self):
		# ANY pointer magic value.
		self.MAGIC = 0x10

		# AwlDataType to ANY-Pointer type code.
		self.typeId2typeCode = {
			AwlDataType.TYPE_NIL		: 0x00,
			AwlDataType.TYPE_BOOL		: 0x01,
			AwlDataType.TYPE_BYTE		: 0x02,
			AwlDataType.TYPE_CHAR		: 0x03,
			AwlDataType.TYPE_WORD		: 0x04,
			AwlDataType.TYPE_INT		: 0x05,
			AwlDataType.TYPE_DWORD		: 0x06,
			AwlDataType.TYPE_DINT		: 0x07,
			AwlDataType.TYPE_REAL		: 0x08,
			AwlDataType.TYPE_DATE		: 0x09,
			AwlDataType.TYPE_TOD		: 0x0A,
			AwlDataType.TYPE_TIME		: 0x0B,
			AwlDataType.TYPE_S5T		: 0x0C,
			AwlDataType.TYPE_DT		: 0x0E,
			AwlDataType.TYPE_STRING		: 0x13,
			AwlDataType.TYPE_BLOCK_FB	: 0x17,
			AwlDataType.TYPE_BLOCK_FC	: 0x18,
			AwlDataType.TYPE_BLOCK_DB	: 0x19,
			AwlDataType.TYPE_BLOCK_SDB	: 0x1A,
			AwlDataType.TYPE_COUNTER	: 0x1C,
			AwlDataType.TYPE_TIMER		: 0x1D,
		}
		# ANY-Pointer type code to AwlDataType.
		self.typeCode2typeId = pivotDict(self.typeId2typeCode)

ANYPointerConst = __ANYPointerConstClass() #+cdef-public-__ANYPointerConstClass

class ANYPointer(DBPointer): #+cdef
	"""ANY-Pointer value.
	The basic data type (DBPointer) holds the pointer value,
	the area code and the DB number.
	The data type is stored in 'dataType' as AwlDataType object.
	The count is stored in 'count'."""

	__slots__ = (
		"dataType",
		"count",
	)

	# Width, in bits.
	width = 80

	# Make an ANYPointer instance based on the data area width (in bits).
	# Automatically selects an appropriate data type and count.
	@classmethod
	def makeByTypeWidth(cls, bitWidth, ptrValue = 0, dbNr = 0):
		if dbNr < 0:
			dbNr = 0
		if bitWidth % 32 == 0:
			dataType = AwlDataType.makeByName("DWORD")
			count = bitWidth // 32
		elif bitWidth % 16 == 0:
			dataType = AwlDataType.makeByName("WORD")
			count = bitWidth // 16
		elif bitWidth % 8 == 0:
			dataType = AwlDataType.makeByName("BYTE")
			count = bitWidth // 8
		else:
			dataType = AwlDataType.makeByName("BOOL")
			count = bitWidth
		return cls(ptrValue = ptrValue,
			   dbNr = dbNr,
			   dataType = dataType,
			   count = count)

	# Create an ANY pointer to a typed data field.
	# Select the right ANY data type automatically.
	@classmethod
	def makeByAutoType(cls, dataType, ptrValue = 0, dbNr = 0):
		if dbNr < 0:
			dbNr = 0
		if dataType.type == AwlDataType.TYPE_ARRAY and\
		   cls.dataTypeIsSupported(dataType.arrayElementType):
			return cls(ptrValue = ptrValue,
				   dbNr = dbNr,
				   dataType = dataType.arrayElementType,
				   count = dataType.arrayGetNrElements())
		elif cls.dataTypeIsSupported(dataType):
			return cls(ptrValue = ptrValue,
				   dbNr = dbNr,
				   dataType = dataType,
				   count = 1)
		else:
			return cls.makeByTypeWidth(bitWidth = dataType.width,
						   ptrValue = ptrValue,
						   dbNr = dbNr)

	# Check whether ANY supports the data type.
	@classmethod
	def dataTypeIsSupported(cls, dataType):
		return dataType and\
		       dataType.type in ANYPointerConst.typeId2typeCode

	def __init__(self, ptrValue = 0, dbNr = 0, dataType = None, count = 1):
		DBPointer.__init__(self, ptrValue, dbNr)
		if not dataType:
			dataType = AwlDataType.makeByName("NIL")
		if not self.dataTypeIsSupported(dataType):
			raise AwlSimError("Data type '%s' is not allowed "
				"in ANY pointers." % str(dataType))
		self.dataType = dataType
		self.count = count

	# Get the pointer as ANY-pointer (80 bit).
	def toANYPointer(self): #@nocy
#@cy	cpdef ANYPointer toANYPointer(self):
		return ANYPointer(self.toPointerValue(), self.dbNr,
				  self.dataType, self.count)

	# Get the ANY-pointer value (80 bit).
	def toANYPointerValue(self): #@nocy
#@cy	cpdef object toANYPointerValue(self):
		# Byte layout: 0x10, typeCode,
		#              countHi, countLo,
		#              dbHi, dbLo,
		#              area, ptrHi, ptrMid, ptrLo
		try:
			count = self.count
			dbNr = self.dbNr
			ptr = self.toPointerValue()
			return bytearray((ANYPointerConst.MAGIC,
					  ANYPointerConst.typeId2typeCode[self.dataType.type],
					  (count >> 8) & 0xFF,
					  count & 0xFF,
					  (dbNr >> 8) & 0xFF,
					  dbNr & 0xFF,
					  (ptr >> 24) & 0xFF,
					  (ptr >> 16) & 0xFF,
					  (ptr >> 8) & 0xFF,
					  ptr & 0xFF))
		except KeyError as e:
			raise AwlSimError("Can not convert data type '%s' to "
				"ANY pointer." %\
				str(self.dataType))

	# Get the native pointer value for this type.
	toNativePointerValue = toANYPointerValue #@nocy
#@cy	cpdef object toNativePointerValue(self):
#@cy		return self.toANYPointerValue()

	# Get a P#... string for this pointer.
	def toPointerString(self):
		dbStr = ""
		if self.dbNr:
			dbStr = "DB%d." % self.dbNr
		try:
			areaStr = PointerConst.area2str[self.getArea()]
		except KeyError as e:
			areaStr = "(%02X)" % self.getArea()
		return "P#%s%s %d.%d %s %d" %\
			(dbStr, areaStr,
			 self.getByteOffset(),
			 self.getBitOffset(),
			 str(self.dataType),
			 self.count)

class Accu(GenericDWord): #+cdef
	"Accumulator register"

	__slots__ = ()

	def __init__(self):
		GenericDWord.__init__(self)

class Addressregister(Pointer): #+cdef
	"Address register"

	__slots__ = ()

	def __init__(self):
		Pointer.__init__(self)

class AwlMemory(object): #+cdef
	"""Generic memory representation."""

	__slots__ = (
		"dataBytes",
	)

	def __init__(self, init=0):
		self.dataBytes = bytearray(init)

	# Memory fetch operation.
	# This method returns the data (bit, byte, word, dword, etc...) for
	# a given memory region of this byte array.
	# offset => An AwlOffset() that specifies the region to fetch from.
	# width => An integer specifying the width (in bits) to fetch.
	# Returns an int for small widths (<= 32 bits) and a memoryview
	# for larger widths.
	def fetch(self, offset, width): #@nocy
#@cy	cdef object fetch(self, AwlOffset offset, uint32_t width):
#@cy		cdef uint32_t byteOffset
#@cy		cdef bytearray dataBytes
#@cy		cdef uint64_t nrBytes
#@cy		cdef uint64_t end

		dataBytes = self.dataBytes
		try:
			byteOffset = offset.byteOffset
			if width == 1:
				return (dataBytes[byteOffset] >> offset.bitOffset) & 1	#@nocy
#@cy				return (<uint8_t>(dataBytes[byteOffset]) >> offset.bitOffset) & 1u
			elif width == 8:
				return dataBytes[byteOffset] & 0xFF			#@nocy
#@cy				return <uint8_t>(dataBytes[byteOffset])
			elif width == 16:
				return (((dataBytes[byteOffset] << 8) |			#@nocy
				         dataBytes[byteOffset + 1]) & 0xFFFF)		#@nocy
#@cy				return (((<uint8_t>(dataBytes[byteOffset]) << 8) |
#@cy				         <uint8_t>(dataBytes[byteOffset + 1])) & 0xFFFFu)
			elif width == 32:
				return (((dataBytes[byteOffset] << 24) |		#@nocy
				         (dataBytes[byteOffset + 1] << 16) |		#@nocy
				         (dataBytes[byteOffset + 2] << 8) |		#@nocy
				         dataBytes[byteOffset + 3]) & 0xFFFFFFFF)	#@nocy
#@cy				return (((<uint8_t>(dataBytes[byteOffset]) << 24) |
#@cy				         (<uint8_t>(dataBytes[byteOffset + 1]) << 16) |
#@cy				         (<uint8_t>(dataBytes[byteOffset + 2]) << 8) |
#@cy				         <uint8_t>(dataBytes[byteOffset + 3])) & 0xFFFFFFFFu)
			else:
				assert(not offset.bitOffset) #@nocy
				nrBytes = intDivRoundUp(width, 8)
				end = byteOffset + nrBytes
				if end > len(dataBytes):
					raise IndexError
				return dataBytes[byteOffset : end]
		except IndexError as e:
			raise AwlSimError("fetch: Operator offset '%s' out of range" %\
					  str(offset))

	# Memory store operation.
	# This method stores data (bit, byte, word, dword, etc...) to
	# a given memory region of this byte array.
	# offset => An AwlOffset() that specifies the region to store to.
	# width => An integer specifying the width (in bits) to store.
	# value => The value to store.
	#          May be an int, bytearray, bytes or compatible.
	def store(self, offset, width, value): #@nocy
#@cy	cdef store(self, AwlOffset offset, uint32_t width, object value):
#@cy		cdef uint32_t byteOffset
#@cy		cdef bytearray dataBytes
#@cy		cdef uint64_t value_uint64
#@cy		cdef uint64_t nrBytes
#@cy		cdef uint64_t end

		dataBytes = self.dataBytes
		try:
			byteOffset = offset.byteOffset
#@cy2			if isinstance(value, int) or isinstance(value, long):
#@cy3			if isinstance(value, int):
			if isInteger(value): #@nocy
#@cy				value_uint64 = <uint64_t>(<int64_t>value)
				if width == 1:
					if value: #@nocy
#@cy					if value_uint64:
						dataBytes[byteOffset] |= 1 << offset.bitOffset
					else:
						dataBytes[byteOffset] &= ~(1 << offset.bitOffset)
				else:
					while width:
						width -= 8
						dataBytes[byteOffset] = (value >> width) & 0xFF #@nocy
#@cy						dataBytes[byteOffset] = (value_uint64 >> width) & 0xFF
						byteOffset += 1
			else:
				if width == 1:
					if value[0] & 1:
						dataBytes[byteOffset] |= 1 << offset.bitOffset
					else:
						dataBytes[byteOffset] &= ~(1 << offset.bitOffset)
				else:
					nrBytes = intDivRoundUp(width, 8)
					assert(nrBytes == len(value)) #@nocy
					end = byteOffset + nrBytes
					if end > len(dataBytes):
						raise IndexError
					dataBytes[byteOffset : end] = value
		except IndexError as e:
			raise AwlSimError("store: Operator offset '%s' out of range" %\
					  str(offset))

	def __len__(self):
		return len(self.dataBytes)

	def __bool__(self):			#@cy3
		return bool(self.dataBytes)	#@cy3

	def __nonzero__(self):			#@cy2
		return bool(self.dataBytes)	#@cy2

	def __repr__(self):
#@cy		cdef list ret
#@cy		cdef uint64_t i

		ret = [ 'AwlMemory(b"', ]
		for i in range(len(self.dataBytes)):
			ret.append("\\x%02X" % self.dataBytes[i])
		ret.append('")')
		return "".join(ret)

	def __str__(self):
		return self.__repr__()

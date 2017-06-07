# -*- coding: utf-8 -*-
#
# AWL data types
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

from awlsim.common.datatypehelpers import * #+cimport
from awlsim.common.immutable import *
from awlsim.common.enumeration import *
from awlsim.common.exceptions import *

from awlsim.core.util import *
from awlsim.core.timers import * #+cimport
from awlsim.core.offset import * #+cimport
from awlsim.core.identifier import *

#from awlsim.core.memory cimport * #@cy

import datetime


__all__ = [
	"AwlDataType",
]


class AwlDataType(OptionalImmutable):
	# Data type IDs
	EnumGen.start
	TYPE_VOID	= EnumGen.item
	TYPE_NIL	= EnumGen.item
	TYPE_BOOL	= EnumGen.item
	TYPE_BYTE	= EnumGen.item
	TYPE_WORD	= EnumGen.item
	TYPE_DWORD	= EnumGen.item
	TYPE_INT	= EnumGen.item
	TYPE_DINT	= EnumGen.item
	TYPE_REAL	= EnumGen.item
	TYPE_S5T	= EnumGen.item
	TYPE_TIME	= EnumGen.item
	TYPE_DATE	= EnumGen.item
	TYPE_DT		= EnumGen.item
	TYPE_TOD	= EnumGen.item
	TYPE_CHAR	= EnumGen.item
	TYPE_ARRAY	= EnumGen.item
	TYPE_STRUCT	= EnumGen.item
	TYPE_STRING	= EnumGen.item
	TYPE_TIMER	= EnumGen.item
	TYPE_COUNTER	= EnumGen.item
	TYPE_POINTER	= EnumGen.item
	TYPE_ANY	= EnumGen.item
	TYPE_BLOCK_DB	= EnumGen.item # DB number type
	TYPE_BLOCK_SDB	= EnumGen.item # SDB number type
	TYPE_BLOCK_FB	= EnumGen.item # FB number type
	TYPE_BLOCK_FC	= EnumGen.item # FC number type
	TYPE_DB_X	= EnumGen.item # DBx type
	TYPE_OB_X	= EnumGen.item # OBx type
	TYPE_FC_X	= EnumGen.item # FCx type
	TYPE_SFC_X	= EnumGen.item # SFCx type
	TYPE_FB_X	= EnumGen.item # FBx type
	TYPE_SFB_X	= EnumGen.item # SFBx type
	TYPE_UDT_X	= EnumGen.item # UDTx type
	TYPE_VAT_X	= EnumGen.item # VATx type
	EnumGen.end

	__name2id = {
		"VOID"		: TYPE_VOID,
		"NIL"		: TYPE_NIL,
		"BOOL"		: TYPE_BOOL,
		"BYTE"		: TYPE_BYTE,
		"WORD"		: TYPE_WORD,
		"DWORD"		: TYPE_DWORD,
		"INT"		: TYPE_INT,
		"DINT"		: TYPE_DINT,
		"REAL"		: TYPE_REAL,
		"S5TIME"	: TYPE_S5T,
		"TIME"		: TYPE_TIME,
		"DATE"		: TYPE_DATE,
		"DATE_AND_TIME"	: TYPE_DT,
		"TIME_OF_DAY"	: TYPE_TOD,
		"CHAR"		: TYPE_CHAR,
		"ARRAY"		: TYPE_ARRAY,
		"STRUCT"	: TYPE_STRUCT,
		"STRING"	: TYPE_STRING,
		"TIMER"		: TYPE_TIMER,
		"COUNTER"	: TYPE_COUNTER,
		"POINTER"	: TYPE_POINTER,
		"ANY"		: TYPE_ANY,
		"BLOCK_DB"	: TYPE_BLOCK_DB,
		"BLOCK_SDB"	: TYPE_BLOCK_SDB,
		"BLOCK_FB"	: TYPE_BLOCK_FB,
		"BLOCK_FC"	: TYPE_BLOCK_FC,
		"DB"		: TYPE_DB_X,
		"OB"		: TYPE_OB_X,
		"FC"		: TYPE_FC_X,
		"SFC"		: TYPE_SFC_X,
		"FB"		: TYPE_FB_X,
		"SFB"		: TYPE_SFB_X,
		"UDT"		: TYPE_UDT_X,
		"VAT"		: TYPE_VAT_X,
	}
	__id2name = pivotDict(__name2id)

	# Width table for types
	# -1 => Type width must be calculated
	typeWidths = {
		TYPE_VOID	: 0,
		TYPE_NIL	: 0,
		TYPE_BOOL	: 1,
		TYPE_BYTE	: 8,
		TYPE_WORD	: 16,
		TYPE_DWORD	: 32,
		TYPE_INT	: 16,
		TYPE_DINT	: 32,
		TYPE_REAL	: 32,
		TYPE_S5T	: 16,
		TYPE_TIME	: 32,
		TYPE_DATE	: 16,
		TYPE_DT		: 64,
		TYPE_TOD	: 32,
		TYPE_CHAR	: 8,
		TYPE_ARRAY	: -1,
		TYPE_STRUCT	: -1,
		TYPE_STRING	: -1,
		TYPE_TIMER	: 16,
		TYPE_COUNTER	: 16,
		TYPE_POINTER	: 48,
		TYPE_ANY	: 80,
		TYPE_BLOCK_DB	: 16,
		TYPE_BLOCK_SDB	: 16,
		TYPE_BLOCK_FB	: 16,
		TYPE_BLOCK_FC	: 16,
		TYPE_DB_X	: -1,
		TYPE_OB_X	: 0,
		TYPE_FC_X	: 0,
		TYPE_SFC_X	: 0,
		TYPE_FB_X	: -1,
		TYPE_SFB_X	: -1,
		TYPE_UDT_X	: -1,
		TYPE_VAT_X	: 0,
	}

	# Table of trivial types with sign
	__signedTypes = {
		TYPE_INT,
		TYPE_DINT,
		TYPE_REAL,
	}

	# Table of compound types
	__compoundTypes = {
		TYPE_DT,
		TYPE_ARRAY,
		TYPE_STRUCT,
		TYPE_STRING,
		TYPE_UDT_X,

		# No TYPE_POINTER here.
		# Technically POINTER is compound, too, but we use this
		# table to decide whether we need to create POINTERs.
		# Adding TYPE_POINTER here would create an infinite loop.
	}

	# Table of types allowed inside of STRUCT.
	__allowedInStructTypes = {
		TYPE_BOOL,
		TYPE_BYTE,
		TYPE_WORD,
		TYPE_DWORD,
		TYPE_INT,
		TYPE_DINT,
		TYPE_REAL,
		TYPE_S5T,
		TYPE_TIME,
		TYPE_DATE,
		TYPE_DT,
		TYPE_TOD,
		TYPE_CHAR,
		TYPE_ARRAY,
		TYPE_STRUCT,
		TYPE_STRING,
		TYPE_UDT_X,
	}

	# Table of types allowed as ARRAY element.
	__allowedInArrayTypes = __allowedInStructTypes

	# Table of types allowed as block interface element.
	__allowedInInterfaceTypes = __allowedInStructTypes | {
		TYPE_TIMER,
		TYPE_COUNTER,
		TYPE_POINTER,
		TYPE_ANY,
		TYPE_BLOCK_DB,
		TYPE_BLOCK_FB,
		TYPE_BLOCK_FC,
		TYPE_FB_X,
		TYPE_SFB_X,
	}

	# Data-types that must be passed "by-reference" to FCs/FBs.
	callByRefTypes = {
		TYPE_TIMER,
		TYPE_COUNTER,
		TYPE_BLOCK_DB,
		TYPE_BLOCK_FB,
		TYPE_BLOCK_FC,
	}

	# Convert a list of array dimensions into a number of elements.
	@classmethod
	def arrayDimensionsToNrElements(cls, dimensions):
		assert(dimensions is not None)
		assert(len(dimensions) >= 1 and len(dimensions) <= 6)
		nrElems = reduce(lambda a, b: a * (b[1] - b[0] + 1),
				 dimensions, 1)
		return nrElems

	@classmethod
	def _name2typeid(cls, nameTokens):
		nameTokens = toList(nameTokens)
		try:
			return cls.__name2id[nameTokens[0].upper()]
		except (KeyError, IndexError) as e:
			raise AwlSimError("Invalid data type name: " +\
					  nameTokens[0] if len(nameTokens) else "None")

	# Dict of simple types that were already contructed
	# and can be re-used.
	# All types herein are forced immutable.
	__staticTypes = {
		TYPE_VOID	: None,
		TYPE_BOOL	: None,
		TYPE_BYTE	: None,
		TYPE_WORD	: None,
		TYPE_DWORD	: None,
		TYPE_INT	: None,
		TYPE_DINT	: None,
		TYPE_REAL	: None,
		TYPE_S5T	: None,
		TYPE_TIME	: None,
		TYPE_DATE	: None,
		TYPE_DT		: None,
		TYPE_TOD	: None,
		TYPE_CHAR	: None,
		TYPE_TIMER	: None,
		TYPE_COUNTER	: None,
		TYPE_POINTER	: None,
		TYPE_ANY	: None,
		TYPE_BLOCK_DB	: None,
		TYPE_BLOCK_SDB	: None,
		TYPE_BLOCK_FB	: None,
		TYPE_BLOCK_FC	: None,
	}

	@classmethod
	def makeByName(cls, nameTokens, arrayDimensions=None):
		"""Make an AwlDataType instance by type name.
		nameTokens -> a list of tokens for the type name.
		arrayDimensions -> List of possible array dimensions, or None.
		                   Each list element is a tuple of (start, end)
				   with the start and end array index for that dimension."""

		nameTokens = toList(nameTokens)
		type = cls._name2typeid(nameTokens)

		# Check if we already had such a type and use that.
		if not arrayDimensions:
			dataType = cls.__staticTypes.get(type)
			if dataType:
				assert(dataType.isImmutable())
				return dataType

		if type == cls.TYPE_STRING:
			# Construct a data structure for the STRING layout.
			strLen = -1
			if len(nameTokens) == 1:
				# Extension: No dimensions means [254]
				strLen = 254
			elif len(nameTokens) == 4 and\
			     nameTokens[1] == '[' and nameTokens[3] == ']' and\
			     isdecimal(nameTokens[2]):
				strLen = int(nameTokens[2], 10)
			if strLen < 0 or strLen > 254:
				raise AwlSimError("Invalid STRING length definition "
					"in '%s'" % "".join(nameTokens))
			byteType = cls.makeByName("BYTE")
			import awlsim.core.datastructure as datastructure
			struct = datastructure.AwlStruct()
			struct.addField(cpu = None, name = None, dataType = byteType,
					initBytes = bytearray((strLen,)))
			struct.addField(cpu = None, name = None, dataType = byteType)
			for i in range(strLen):
				struct.addField(cpu = None, name = "[%s]" % (i + 1),
						dataType = byteType)
		else:
			struct = None

		index = None
		if type == cls.TYPE_ARRAY:
			raise AwlSimError("Nested ARRAYs are not allowed")
		elif type in (cls.TYPE_DB_X,
			      cls.TYPE_OB_X,
			      cls.TYPE_FC_X,
			      cls.TYPE_SFC_X,
			      cls.TYPE_FB_X,
			      cls.TYPE_SFB_X,
			      cls.TYPE_UDT_X):
			if len(nameTokens) < 2:
				raise AwlSimError("Invalid '%s' block data type" %\
					nameTokens[0])
			blockNumber = cls.tryParseImmediate_INT(nameTokens[1])
			if blockNumber is None:
				raise AwlSimError("Invalid '%s' block data type "\
					"index" % nameTokens[0])
			index = blockNumber

		if arrayDimensions:
			# An ARRAY is to be constructed.
			elementType = cls.makeByName(nameTokens)
			dataType = cls(type = cls.TYPE_ARRAY,
				       index = index,
				       arrayDimensions = arrayDimensions,
				       arrayElementType = elementType)
		else:
			dataType = cls(type = type,
				       index = index,
				       struct = struct)

			# Store the data type instance for later re-use, if it is
			# in the simple-types dict.
			# Force it immutable, so it cannot change anymore.
			if type in cls.__staticTypes:
				dataType.setImmutable()
				assert(dataType.index is None)
				assert(dataType.arrayDimensions is None)
				assert(dataType.arrayElementType is None)
				assert(dataType._struct is None)
				assert(cls.__staticTypes[type] is None)
				cls.__staticTypes[type] = dataType

		return dataType

	__slots__ = (
		"type",
		"index",
		"arrayDimensions",
		"arrayElementType",
		"_struct",
		"__widthOverride",
	)

	def __init__(self, type,
		     index=None,
		     arrayDimensions=None,
		     arrayElementType=None,
		     struct=None):
		super(AwlDataType, self).__init__()
		self.type = type		# The TYPE_... for this datatype
		self.index = index		# The Index number, if any. May be None
		self.arrayDimensions = arrayDimensions # The ARRAY's dimensions
		self.arrayElementType = arrayElementType # AwlDataType for the array elements.
		self.setStruct(struct)		# AwlStruct instance. Only for STRUCT type.
		self.__widthOverride = None

	def __eq__(self, other):
		return (self is other) or (\
			isinstance(other, AwlDataType) and\
			self.type == other.type and\
			self.index == other.index and\
			self.arrayDimensions == other.arrayDimensions and\
			self.arrayElementType == other.arrayElementType and\
			self._struct == other._struct and\
			self.__widthOverride == other.__widthOverride\
		)

	def __ne__(self, other):
		return not self.__eq__(other)

	# Set the AwlStruct that defines the structure of this STRUCT type.
	def setStruct(self, struct):
		assert(struct is None or
		       self.type == self.TYPE_STRUCT or
		       self.type == self.TYPE_UDT_X or
		       self.type == self.TYPE_STRING)
		self._struct = struct

	# Get the type element structure.
	# This is the element's struct for ARRAYs and the struct
	# of this type for STRUCTs/UDTs.
	# None for others.
	@property
	def itemStruct(self):
		if self.type == self.TYPE_ARRAY:
			return self.arrayElementType._struct
		return self._struct

	# Returns the width of this data type, in bits.
	@property
	def width(self):
		if self.__widthOverride is not None:
			return self.__widthOverride
		if self.type == self.TYPE_ARRAY:
			nrElements = self.arrayGetNrElements()
			if self.arrayElementType.type == self.TYPE_STRUCT:
				if self.arrayElementType._struct:
					oneElemWidth = self.arrayElementType._struct.getSize() * 8
					width = nrElements * oneElemWidth
				else:
					width = -1
			else:
				oneElemWidth = self.arrayElementType.width
				width = nrElements * oneElemWidth
		elif self.type == self.TYPE_STRUCT or\
		     self.type == self.TYPE_UDT_X:
			if self._struct:
				width = self._struct.getSize() * 8
			else:
				width = -1
		elif self.type == self.TYPE_STRING:
			width = self._struct.getUnalignedSize() * 8
		else:
			width = self.typeWidths[self.type]
		return width

	# Override the width calculation.
	@width.setter
	def width(self, widthOverride):
		self.__widthOverride = widthOverride

	# Returns True, if this is a compound data type.
	# Does not return True for TYPE_POINTER.
	@property
	def compound(self):
		return self.type in self.__compoundTypes

	# Returns True, if this is a signed type.
	@property
	def isSigned(self):
		return self.type in self.__signedTypes

	# Returns True, if this type is allowed in STRUCTs.
	@property
	def allowedInStruct(self):
		return self.type in self.__allowedInStructTypes

	# Returns True, if this type is allowed as ARRAY element.
	@property
	def allowedInArray(self):
		return self.type in self.__allowedInArrayTypes

	# Returns True, if this type is allowed in block interfaces.
	@property
	def allowedInInterface(self):
		return self.type in self.__allowedInInterfaceTypes

	# Possible values for 'naturalAlignment'.
	EnumGen.start
	ALIGN_BIT	= EnumGen.item
	ALIGN_BYTE	= EnumGen.item
	ALIGN_WORD	= EnumGen.item
	EnumGen.end

	# Get the natural alignment of this type.
	@property
	def naturalAlignment(self):
		if self.width == 1:
			return self.ALIGN_BIT
		if self.width == 8:
			return self.ALIGN_BYTE
		if self.type == self.TYPE_ARRAY or\
		   self.type == self.TYPE_STRUCT or\
		   self.type == self.TYPE_UDT_X or\
		   self.width > 8:
			return self.ALIGN_WORD
		assert(0)

	# Convert array indices into a one dimensional index for this array.
	# 'indices' is a list of index integers as written in the AWL operator
	# from left to right.
	def arrayIndicesCollapse(self, indices):
		if not indices:
			return None
		if len(indices) < 1 or len(indices) > 6:
			raise AwlSimError("Invalid number of array indices")
		assert(self.type == self.TYPE_ARRAY)
		signif = self.arrayIndexSignificances()
		assert(len(indices) == len(signif))
		assert(len(indices) == len(self.arrayDimensions))
		resIndex = 0
		for i, idx in enumerate(indices):
			startIdx, endIdx = self.arrayDimensions[i]
			if idx < startIdx or idx > endIdx:
				raise AwlSimError("Array index '%d' is out of bounds "
					"for array range '%d .. %d'." %\
					(idx, startIdx, endIdx))
			resIndex += (idx - startIdx) * signif[i]
		return resIndex

	# Get the array dimension sizes. Returns a tuple of integers.
	def arrayDimSizes(self):
		assert(self.type == self.TYPE_ARRAY)
		return tuple(end - start + 1
			     for start, end in self.arrayDimensions)

	# Get the array index significances. Returns a tuple of integers.
	def arrayIndexSignificances(self):
		assert(self.type == self.TYPE_ARRAY)
		sizes = self.arrayDimSizes()
		signif = [ 1, ]
		for size in list(sizes)[::-1][:-1]:
			signif.append(size * signif[-1])
		return tuple(signif[::-1])

	# Get the number of array elements
	def arrayGetNrElements(self):
		assert(self.type == self.TYPE_ARRAY)
		return self.arrayDimensionsToNrElements(self.arrayDimensions)

	# Parse an immediate, constrained by our datatype.
	def parseMatchingImmediate(self, tokens):
		typeId = self.type
		typeWidth = self.width
		if typeId == self.TYPE_ARRAY:
			typeId = self.arrayElementType.type
			typeWidth = self.arrayElementType.width

		value = None
		if tokens is None:
			value = 0
		elif len(tokens) == 9:
			if typeId == self.TYPE_DWORD:
				value, fields = self.tryParseImmediate_ByteArray(
							tokens)
		elif len(tokens) == 5:
			if typeId == self.TYPE_WORD:
				value, fields = self.tryParseImmediate_ByteArray(
							tokens)
			elif typeId == self.TYPE_DT:
				value = self.tryParseImmediate_DT(tokens)
			elif typeId == self.TYPE_TOD:
				value = self.tryParseImmediate_TOD(tokens)
		elif len(tokens) == 2:
			if typeId == self.TYPE_TIMER:
				if tokens[0].upper() == "T":
					value = self.tryParseImmediate_INT(tokens[1])
			elif typeId == self.TYPE_COUNTER:
				if tokens[0].upper() in ("C", "Z"):
					value = self.tryParseImmediate_INT(tokens[1])
			elif typeId == self.TYPE_BLOCK_DB:
				if tokens[0].upper() == "DB":
					value = self.tryParseImmediate_INT(tokens[1])
			elif typeId == self.TYPE_BLOCK_FB:
				if tokens[0].upper() == "FB":
					value = self.tryParseImmediate_INT(tokens[1])
			elif typeId == self.TYPE_BLOCK_FC:
				if tokens[0].upper() == "FC":
					value = self.tryParseImmediate_INT(tokens[1])
		elif len(tokens) == 1:
			if typeId == self.TYPE_BOOL:
				value = self.tryParseImmediate_BOOL(
						tokens[0])
			elif typeId == self.TYPE_BYTE:
				value = self.tryParseImmediate_HexByte(
						tokens[0])
			elif typeId == self.TYPE_WORD:
				value = self.tryParseImmediate_Bin(
						tokens[0])
				if value is None:
					value = self.tryParseImmediate_HexWord(
							tokens[0])
				if value is None:
					value = self.tryParseImmediate_BCD_word(
							tokens[0])
			elif typeId == self.TYPE_DWORD:
				value = self.tryParseImmediate_Bin(
						tokens[0])
				if value is None:
					value = self.tryParseImmediate_HexDWord(
							tokens[0])
			elif typeId == self.TYPE_INT:
				value = self.tryParseImmediate_INT(
						tokens[0])
			elif typeId == self.TYPE_DINT:
				value = self.tryParseImmediate_DINT(
						tokens[0])
			elif typeId == self.TYPE_REAL:
				value = self.tryParseImmediate_REAL(
						tokens[0])
			elif typeId == self.TYPE_S5T:
				value = self.tryParseImmediate_S5T(
						tokens[0])
			elif typeId == self.TYPE_TIME:
				value = self.tryParseImmediate_TIME(
						tokens[0])
			elif typeId == self.TYPE_CHAR:
				value = self.tryParseImmediate_CHAR(
						tokens[0])
			elif typeId == self.TYPE_STRING:
				value = self.tryParseImmediate_STRING(
						tokens[0])
				typeStrLen = intDivRoundUp(typeWidth, 8) - 2
				immStrLen = len(value) - 2
				assert(typeStrLen >= 0 and immStrLen >= 0)
				if immStrLen > typeStrLen:
					raise AwlSimError("String immediate is "
						"too long. Length is %d characters, "
						"but maximum is %d characters." %\
						immStrLen, typeStrLen)
				# Expand the string to type length.
				if immStrLen < typeStrLen:
					value[0] = typeStrLen
					value.extend(b'\x00' * (typeStrLen - immStrLen))
			elif typeId == self.TYPE_DATE:
				value = self.tryParseImmediate_DATE(
						tokens[0])
		if value is None:
			raise AwlSimError("Immediate value '%s' does "
				"not match data type '%s'" %\
				(" ".join(tokens), str(self)))
		return value

	def __repr__(self):
		if self.type == self.TYPE_ARRAY:
			return "ARRAY" #TODO
		elif self.type == self.TYPE_STRING:
			return "STRING[%d]" % (self.width // 8 - 2)
		elif self.type in (self.TYPE_DB_X,
				   self.TYPE_OB_X,
				   self.TYPE_FC_X,
				   self.TYPE_SFC_X,
				   self.TYPE_FB_X,
				   self.TYPE_SFB_X,
				   self.TYPE_UDT_X):
			return "%s %d" % (
				self.__id2name[self.type],
				self.index,
			)
		try:
			return self.__id2name[self.type]
		except KeyError:
			raise AwlSimError("Invalid data type: " +\
					  str(type))

	@classmethod
	def tryParseImmediate_BOOL(cls, token):
		token = token.upper().strip()
		if token == "TRUE":
			return 1
		elif token == "FALSE":
			return 0
		return None

	@classmethod
	def tryParseImmediate_INT(cls, token):
		try:
			immediate = int(token, 10)
			if immediate > 32767 or immediate < -32768:
				raise AwlSimError("16-bit immediate overflow")
		except ValueError:
			return None
		return immediate

	@classmethod
	def tryParseImmediate_DINT(cls, token):
		token = token.upper()
		if not token.startswith("L#"):
			return None
		try:
			immediate = int(token[2:], 10)
			if immediate > 2147483647 or immediate < -2147483648: #@nocy
#@cy			if immediate > 2147483647LL or immediate < -2147483648LL:
				raise AwlSimError("32-bit immediate overflow")
			immediate &= 0xFFFFFFFF
		except ValueError as e:
			raise AwlSimError("Invalid immediate")
		return immediate

	@classmethod
	def tryParseImmediate_BCD_word(cls, token):
		token = token.upper()
		if not token.startswith("C#"):
			return None
		try:
			cnt = token[2:]
			if len(cnt) < 1 or len(cnt) > 3:
				raise ValueError
			a, b, c = 0, 0, 0
			if cnt:
				a = int(cnt[-1], 10)
				cnt = cnt[:-1]
			if cnt:
				b = int(cnt[-1], 10)
				cnt = cnt[:-1]
			if cnt:
				c = int(cnt[-1], 10)
				cnt = cnt[:-1]
			immediate = a | (b << 4) | (c << 8)
		except ValueError as e:
			raise AwlSimError("Invalid C# immediate")
		return immediate

	@classmethod
	def tryParseImmediate_REAL(cls, token):
		try:
			immFloat = float(token)
			immWord = pyFloatToDWord(immFloat)
		except ValueError:
			return None
		return immWord

	@classmethod
	def __parseGenericTime(cls, token, allowNegative):
		# Parse T# or S5T# time formats.
		# The prefix is already stripped.
		if not token:
			raise AwlSimError("Invalid time")
		token = token.upper()
		p = token
		isNegative = False
		if p.startswith("-"):
			if not allowNegative:
				raise AwlSimError("Negative time now allowed")
			isNegative = True
			p = p[1:]
		seconds = 0.0
		while p:
			if p.endswith("MS"):
				mult = 0.001
				p = p[:-2]
			elif p.endswith("S"):
				mult = 1.0
				p = p[:-1]
			elif p.endswith("M"):
				mult = 60.0
				p = p[:-1]
			elif p.endswith("H"):
				mult = 3600.0
				p = p[:-1]
			elif p.endswith("D"):
				mult = 86400.0
				p = p[:-1]
			else:
				raise AwlSimError("Invalid time")
			if not p:
				raise AwlSimError("Invalid time")
			num = ""
			while p and p[-1] in "0123456789":
				num = p[-1] + num
				p = p[:-1]
			if not num:
				raise AwlSimError("Invalid time")
			num = int(num, 10)
			seconds += num * mult
		if isNegative:
			seconds *= -1.0
		return seconds

	@classmethod
	def formatTime(cls, seconds, leadingZeros=False):
		# Format a seconds value into time format.
		d = int(seconds // 86400)
		seconds -= d * 86400
		h = int(seconds // 3600)
		seconds -= h * 3600
		m = int(seconds // 60)
		seconds -= m * 60
		s = int(seconds)
		seconds -= s
		ms = int(seconds * 1000.0)
		ret = []
		for v, b, d in ((d, "d", 1), (h, "h", 2), (m, "m", 2),
				(s, "s", 2), (ms, "ms", 3)):
			if not v:
				continue
			if leadingZeros:
				fmt = "%0" + str(d) + "d%s"
				ret.append(fmt % (v, b))
			else:
				ret.append("%d%s" % (v, b))
		if not ret:
			return "0ms"
		return "".join(ret)

	@classmethod
	def __tryParseImmediate_STRING(cls, token, maxLen=254):
		if not token.startswith("'") or\
		   not token.endswith("'"):
			return None
		token = token[1:-1]
		if len(token) > maxLen:
			raise AwlSimError("String too long (>%d characters)" % maxLen)
		from awlsim.common.sources import AwlSource
		try:
			# Strings are supposed to be traditional
			# "latin1" encoding compatible and the resulting
			# bytes are "latin1" encoded bytes.
			data = token.encode(AwlSource.COMPAT_ENCODING)
			data = bytearray(data)
			if len(data) != len(token):
				raise ValueError
		except (UnicodeError, ValueError) as e:
			raise AwlSimError("Invalid characters in string '%s'. "
				"Please make sure the string is "
				"%s encoding compatible." % (
				token, AwlSource.COMPAT_ENCODING))
		return data

	@classmethod
	def tryParseImmediate_STRING(cls, token):
		data = cls.__tryParseImmediate_STRING(token)
		if data is None:
			return None
		# Add max-length and actual-length bytes.
		data = bytearray((len(data), len(data))) + data
		return data

	@classmethod
	def tryParseImmediate_CHAR(cls, token):
		data = cls.__tryParseImmediate_STRING(token, 1)
		if data is None:
			return None
		# Return it as integer.
		return data[0]

	@classmethod
	def tryParseImmediate_S5T(cls, token):
		token = token.upper()
		if not token.startswith("S5T#"):
			return None
		seconds = cls.__parseGenericTime(token[4:],
						 allowNegative=False)
		s5t = Timer_seconds_to_s5t(seconds)
		return s5t

	@classmethod
	def tryParseImmediate_TIME(cls, token):
		token = token.upper()
		if not token.startswith("T#") and\
		   not token.startswith("TIME#"):
			return None
		token = token[token.find("#") + 1 : ] # Remove prefix
		seconds = cls.__parseGenericTime(token,
						 allowNegative=True)
		msec = int(seconds * 1000)
		if msec > 0x7FFFFFFF:
			raise AwlSimError("T# time too big")
		return msec

	@classmethod
	def tryParseImmediate_TOD(cls, tokens):
		token = "".join(tokens)
		if not token.startswith("TOD#") and\
		   not token.startswith("TIME_OF_DAY#"):
			return None
		token = token[token.find("#") + 1 : ] # Remove prefix
		try:
			time = token.split(":")
			if len(time) != 3:
				raise ValueError
			hours, minutes, fseconds = int(time[0]), int(time[1]), float(time[2])
			seconds = int(fseconds)
			msecs = int(round(fseconds * 1000.0)) - (seconds * 1000)
			if hours < 0 or hours > 23 or\
			   minutes < 0 or minutes > 59 or\
			   seconds < 0 or seconds > 59 or\
			   msecs < 0 or msecs > 999:
				raise ValueError
			val = hours * 60 * 60 * 1000 +\
			      minutes * 60 * 1000 +\
			      seconds * 1000 +\
			      msecs
			return val
		except ValueError:
			raise AwlSimError("Invalid TIME_OF_DAY immediate")

	@classmethod
	def tryParseImmediate_DATE(cls, token):
		token = token.upper()
		if not token.startswith("D#") and\
		   not token.startswith("DATE#"):
			return None
		token = token[token.find("#") + 1 : ] # Remove prefix
		try:
			date = token.split("-")
			if len(date) != 3:
				raise ValueError
			year, month, day = int(date[0]), int(date[1]), int(date[2])
			delta = datetime.date(year, month, day) -\
				datetime.date(1990, 1, 1)
			days = delta.days
			if days < 0 or days > 65378:
				raise ValueError
			return days
		except ValueError:
			raise AwlSimError("Invalid DATE immediate")

	dateAndTimeWeekdayMap = {
		0	: 2,	# monday
		1	: 3,	# tuesday
		2	: 4,	# wednesday
		3	: 5,	# thursday
		4	: 6,	# friday
		5	: 7,	# saturday
		6	: 1,	# sunday
	}

	@classmethod
	def tryParseImmediate_DT(cls, tokens):
		token = "".join(tokens)
		if not token.startswith("DT#") and\
		   not token.startswith("DATE_AND_TIME#"):
			return None
		token = token[token.find("#") + 1 : ] # Remove prefix
		try:
			idx = token.rfind("-")
			date = token[ : idx]
			time = token[idx + 1 : ]
			date = date.split("-")
			time = time.split(":")
			if len(date) != 3 or len(time) != 3:
				raise ValueError
			year, month, day = int(date[0]), int(date[1]), int(date[2])
			weekday = datetime.date(year, month, day).weekday()
			weekday = cls.dateAndTimeWeekdayMap[weekday]
			if year >= 100:
				year -= 1900
				if year > 99:
					year -= 100
			if year < 0 or year > 99 or\
			   month < 1 or month > 12 or\
			   day < 1 or day > 31:
				raise ValueError
			year = (year % 10) | (((year // 10) % 10) << 4)
			month = (month % 10) | (((month // 10) % 10) << 4)
			day = (day % 10) | (((day // 10) % 10) << 4)
			hour, minute, fsecond = int(time[0]), int(time[1]), float(time[2])
			second = int(fsecond)
			msec = int(fsecond * 1000) - (second * 1000)
			if hour < 0 or hour > 23 or\
			   minute < 0 or minute > 59 or\
			   second < 0 or second > 59 or\
			   msec < 0 or msec > 999:
				raise ValueError
			hour = (hour % 10) | (((hour // 10) % 10) << 4)
			minute = (minute % 10) | (((minute // 10) % 10) << 4)
			second = (second % 10) | (((second // 10) % 10) << 4)
			msec = (msec % 10) | (((msec // 10) % 10) << 4) |\
			       (((msec // 100) % 10) << 8)
			data = bytearray( (year, month, day, hour, minute, second,
					   (msec >> 4) & 0xFF,
					   ((msec & 0xF) << 4) | weekday) )
		except ValueError:
			raise AwlSimError("Invalid DATE_AND_TIME immediate")
		return data

	@classmethod
	def __parsePtrOffset(cls, string):
		try:
			values = string.split(".")
			if len(values) != 2:
				raise ValueError
			byteOffset = int(values[0], 10)
			bitOffset = int(values[1], 10)
			if bitOffset < 0 or bitOffset > 7 or\
			   byteOffset < 0 or byteOffset > 0xFFFF:
				raise ValueError
			return (byteOffset << 3) | bitOffset
		except ValueError:
			raise AwlSimError("Invalid pointer offset: " + string)

	@classmethod
	def tryParseImmediate_Pointer(cls, tokens):
#@cy		cdef Pointer pointer

		prefix = tokens[0]
		if not prefix.upper().startswith("P#"):
			return None, None

		from awlsim.core.memory import Pointer, DBPointer, SymbolicDBPointer

		prefix = prefix[2:] # Strip P#

		pointer = None
		dotIdx = prefix.find(".")
		if dotIdx >= 3 and prefix[:dotIdx].upper().startswith("DB") and\
		   isdecimal(prefix[2:dotIdx]):
			# Parse DB number prefix
			dbNr = int(prefix[2:dotIdx])
			prefix = prefix[dotIdx+1:]
			pointer = DBPointer(0, dbNr)
		elif dotIdx >= 3 and prefix.startswith('"'):
			endIdx = prefix[1:].find('".') + 1
			if endIdx >= 2:
				# Parse symbolic DB name prefix
				dbSymbol = prefix[1:endIdx]
				prefix = prefix[endIdx+2:]
				pointer = SymbolicDBPointer(dbSymbol = dbSymbol)

		if pointer is None:
			# There is no DB number.
			pointer = Pointer(0)

		prefix = prefix.upper()
		try:
			def matchPrefix(prefix, template):
				try:
					return prefix == template or\
					       (prefix.startswith(template) and\
						isdecimal(prefix[len(template)]))
				except IndexError as e:
					return False

			try:
				valueToken = tokens[1]
				nrTokens = 2
			except IndexError as e:
				valueToken = ""
				nrTokens = 1

			if matchPrefix(prefix, "P"):
				ptr = cls.__parsePtrOffset(prefix[1:] + valueToken) |\
					0x80000000
				pointer.setDWord(ptr)
			elif matchPrefix(prefix, "E") or matchPrefix(prefix, "I"):
				ptr = cls.__parsePtrOffset(prefix[1:] + valueToken) |\
					0x81000000
				pointer.setDWord(ptr)
			elif matchPrefix(prefix, "A") or matchPrefix(prefix, "Q"):
				ptr = cls.__parsePtrOffset(prefix[1:] + valueToken) |\
					0x82000000
				pointer.setDWord(ptr)
			elif matchPrefix(prefix, "M"):
				ptr = cls.__parsePtrOffset(prefix[1:] + valueToken) |\
					0x83000000
				pointer.setDWord(ptr)
			elif matchPrefix(prefix, "DBX"):
				ptr = cls.__parsePtrOffset(prefix[3:] + valueToken) |\
					0x84000000
				pointer.setDWord(ptr)
			elif matchPrefix(prefix, "DIX"):
				ptr = cls.__parsePtrOffset(prefix[3:] + valueToken) |\
					0x85000000
				pointer.setDWord(ptr)
			elif matchPrefix(prefix, "L"):
				ptr = cls.__parsePtrOffset(prefix[1:] + valueToken) |\
					0x86000000
				pointer.setDWord(ptr)
			else:
				if isinstance(pointer, DBPointer) and\
				   prefix and not isdecimal(prefix[0]):
					# This is a named DB variable pointer.
					# (awlsim extension).
					if not isinstance(pointer, SymbolicDBPointer):
						pointer = SymbolicDBPointer(pointer.toPointerValue(),
									    pointer.dbNr)
					tokens = [ prefix ] + tokens[1:]
					tokens, nrTokens = AwlDataIdentChain.expandTokens(tokens)
					pointer.identChain = AwlDataIdentChain.parseTokens(tokens)
					return pointer, nrTokens
				# Area-internal pointer
				ptr = cls.__parsePtrOffset(prefix)
				pointer.setDWord(ptr)
				nrTokens = 1
		except IndexError:
			raise AwlSimError("Invalid pointer immediate")

		# Check if this is an ANY pointer immediate.
		if len(tokens) >= nrTokens + 2:
			typeToken = tokens[nrTokens]
			countToken = tokens[nrTokens + 1]

			# Is this a possible ANY pointer?
			# Try to look up the data type name.
			try:
				cls._name2typeid(typeToken)
				isAnyPtr = True
			except AwlSimError as e:
				isAnyPtr = False

			if isAnyPtr:
				# Parse the data type and repetition count.
				dataType = AwlDataType.makeByName(typeToken)
				try:
					count = int(countToken, 10)
					if count < 1 or count > 65535 or\
					   count * (dataType.width // 8) > 65535:
						raise ValueError
				except ValueError as e:
					raise AwlSimError("ANY pointer: "
						"Invalid repetition count.")

				# Convert pointer to ANY
				pointer = pointer.toANYPointer()
				pointer.dataType = dataType
				pointer.count = count

				nrTokens += 2

		return pointer, nrTokens

	@classmethod
	def tryParseImmediate_Bin(cls, token):
		token = token.upper()
		if not token.startswith("2#"):
			return None
		try:
			string = token[2:].replace('_', '')
			immediate = int(string, 2)
			if immediate > 0xFFFFFFFF:
				raise ValueError
		except ValueError as e:
			raise AwlSimError("Invalid immediate")
		return immediate

	@classmethod
	def tryParseImmediate_ByteArray(cls, tokens):
		tokens = [ t.upper() for t in tokens ]
		if not tokens[0].startswith("B#("):
			return None, None
		try:
			if len(tokens) >= 5 and\
			   tokens[2] == ',' and\
			   tokens[4] == ')':
				fields = 5
				a, b = int(tokens[1], 10),\
				       int(tokens[3], 10)
				if a < 0 or a > 0xFF or\
				   b < 0 or b > 0xFF:
					raise ValueError
				immediate = (a << 8) | b
			elif len(tokens) >= 9 and\
			     tokens[2] == ',' and\
			     tokens[4] == ',' and\
			     tokens[6] == ',' and\
			     tokens[8] == ')':
				fields = 9
				a, b, c, d = int(tokens[1], 10),\
					     int(tokens[3], 10),\
					     int(tokens[5], 10),\
					     int(tokens[7], 10)
				if a < 0 or a > 0xFF or\
				   b < 0 or b > 0xFF or\
				   c < 0 or c > 0xFF or\
				   d < 0 or d > 0xFF:
					raise ValueError
				immediate = (a << 24) | (b << 16) |\
					    (c << 8) | d
			else:
				raise ValueError
		except ValueError as e:
			raise AwlSimError("Invalid immediate")
		return immediate, fields

	@classmethod
	def tryParseImmediate_HexByte(cls, token):
		token = token.upper()
		if not token.startswith("B#16#"):
			return None
		try:
			immediate = int(token[5:], 16)
			if immediate > 0xFF:
				raise ValueError
		except ValueError as e:
			raise AwlSimError("Invalid immediate")
		return immediate

	@classmethod
	def tryParseImmediate_HexWord(cls, token):
		token = token.upper()
		if not token.startswith("W#16#"):
			return None
		try:
			immediate = int(token[5:], 16)
			if immediate > 0xFFFF:
				raise ValueError
		except ValueError as e:
			raise AwlSimError("Invalid immediate")
		return immediate

	@classmethod
	def tryParseImmediate_HexDWord(cls, token):
		token = token.upper()
		if not token.startswith("DW#16#"):
			return None
		try:
			immediate = int(token[6:], 16)
			if immediate > 0xFFFFFFFF:
				raise ValueError
		except ValueError as e:
			raise AwlSimError("Invalid immediate")
		return immediate

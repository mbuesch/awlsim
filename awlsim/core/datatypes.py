# -*- coding: utf-8 -*-
#
# AWL data types
#
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
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
from awlsim.core.timers import *
from awlsim.core.datatypehelpers import *


class AwlOffset(object):
	"Memory area offset"

	def __init__(self, byteOffset, bitOffset=0, dbNumber=None):
		self.byteOffset = byteOffset
		self.bitOffset = bitOffset
		self.dbNumber = dbNumber

	def dup(self):
		return AwlOffset(self.byteOffset,
				 self.bitOffset,
				 self.dbNumber)

	@classmethod
	def fromPointerValue(cls, value):
		return cls((value & 0x00FFFFF8) >> 3,
			   (value & 0x7))

	def toPointerValue(self):
		return ((self.byteOffset << 3) & 0x00FFFFF8) |\
		       (self.bitOffset & 0x7)

	def __repr__(self):
		if self.dbNumber is not None:
			return "DB%d(%d.%d)" % (self.dbNumber,
						self.byteOffset,
						self.bitOffset)
		return "%d.%d" % (self.byteOffset, self.bitOffset)

class AwlDataType(object):
	# Data type IDs
	EnumGen.start
	TYPE_VOID	= EnumGen.item
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
	TYPE_TIMER	= EnumGen.item
	TYPE_COUNTER	= EnumGen.item
	TYPE_BLOCK_DB	= EnumGen.item # DB number type
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
		"TIMER"		: TYPE_TIMER,
		"COUNTER"	: TYPE_COUNTER,
		"BLOCK_DB"	: TYPE_BLOCK_DB,
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
	type2width = {
		TYPE_VOID	: 0,
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
		TYPE_TIMER	: 16,
		TYPE_COUNTER	: 16,
		TYPE_BLOCK_DB	: 16,
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
	signedTypes = (
		TYPE_INT,
		TYPE_DINT,
		TYPE_REAL,
	)

	@classmethod
	def _name2typeid(cls, nameTokens):
		nameTokens = toList(nameTokens)
		try:
			return cls.__name2id[nameTokens[0].upper()]
		except (KeyError, IndexError) as e:
			raise AwlSimError("Invalid data type name: " +\
					  nameTokens[0] if len(nameTokens) else "None")

	@classmethod
	def makeByName(cls, nameTokens):
		type = cls._name2typeid(nameTokens)
		index = None
		subType = None
		if type == cls.TYPE_ARRAY:
			raise AwlSimError("ARRAYs not supported, yet") #TODO
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
		return cls(type = type,
			   width = cls.type2width[type],
			   isSigned = (type in cls.signedTypes),
			   index = index,
			   subType = subType)

	def __init__(self, type, width, isSigned,
		     index=None, subType=None):
		self.type = type
		self.width = width
		self.isSigned = isSigned
		self.index = index
		self.subType = subType		#TODO

	# Parse an immediate, constrained by our datatype.
	def parseMatchingImmediate(self, tokens):
		value = None
		if len(tokens) == 9:
			if self.type == self.TYPE_DWORD:
				value, fields = self.tryParseImmediate_ByteArray(
							tokens)
		elif len(tokens) == 5:
			if self.type == self.TYPE_WORD:
				value, fields = self.tryParseImmediate_ByteArray(
							tokens)
		elif len(tokens) == 2:
			if self.type == self.TYPE_TIMER:
				if tokens[0].upper() == "T":
					value = self.tryParseImmediate_INT(tokens[1])
			elif self.type == self.TYPE_COUNTER:
				if tokens[0].upper() in ("C", "Z"):
					value = self.tryParseImmediate_INT(tokens[1])
			elif self.type == self.TYPE_BLOCK_DB:
				if tokens[0].upper() == "DB":
					value = self.tryParseImmediate_INT(tokens[1])
			elif self.type == self.TYPE_BLOCK_FB:
				if tokens[0].upper() == "FB":
					value = self.tryParseImmediate_INT(tokens[1])
			elif self.type == self.TYPE_BLOCK_FC:
				if tokens[0].upper() == "FC":
					value = self.tryParseImmediate_INT(tokens[1])
		elif len(tokens) == 1:
			if self.type == self.TYPE_BOOL:
				value = self.tryParseImmediate_BOOL(
						tokens[0])
			elif self.type == self.TYPE_BYTE:
				value = self.tryParseImmediate_HexByte(
						tokens[0])
			elif self.type == self.TYPE_WORD:
				value = self.tryParseImmediate_Bin(
						tokens[0])
				if value is None:
					value = self.tryParseImmediate_HexWord(
							tokens[0])
				if value is None:
					value = self.tryParseImmediate_BCD(
							tokens[0])
			elif self.type == self.TYPE_DWORD:
				value = self.tryParseImmediate_Bin(
						tokens[0])
				if value is None:
					value = self.tryParseImmediate_HexDWord(
							tokens[0])
			elif self.type == self.TYPE_INT:
				value = self.tryParseImmediate_INT(
						tokens[0])
			elif self.type == self.TYPE_DINT:
				value = self.tryParseImmediate_DINT(
						tokens[0])
			elif self.type == self.TYPE_REAL:
				value = self.tryParseImmediate_REAL(
						tokens[0])
			elif self.type == self.TYPE_S5T:
				value = self.tryParseImmediate_S5T(
						tokens[0])
			elif self.type == self.TYPE_TIME:
				value = self.tryParseImmediate_TIME(
						tokens[0])
			elif self.type == self.TYPE_DATE:
				pass#TODO
			elif self.type == self.TYPE_DT:
				pass#TODO
			elif self.type == self.TYPE_TOD:
				pass#TODO
			elif self.type == self.TYPE_CHAR:
				value = self.tryParseImmediate_CHAR(
						tokens[0])
		if value is None:
			raise AwlSimError("Immediate value '%s' does "
				"not match data type '%s'" %\
				(" ".join(tokens), str(self)))
		return value

	def __repr__(self):
		if self.type == self.TYPE_ARRAY:
			return "ARRAY" #TODO
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
			if immediate > 2147483647 or\
			   immediate < -2147483648:
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
			immediate = float(token)
			immediate = pyFloatToDWord(immediate)
		except ValueError:
			return None
		return immediate

	@classmethod
	def __parseGenericTime(cls, token):
		token = token.upper()
		p = token
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
		return seconds

	@classmethod
	def __tryParseImmediate_STRING(cls, token, maxLen):
		if not token.startswith("'") or\
		   not token.endswith("'"):
			return None
		token = token[1:-1]
		if len(token) > maxLen:
			raise AwlSimError("String too long (>%d characters)" % maxLen)
		value = 0
		for c in token:
			value <<= 8
			value |= ord(c)
		return value

	@classmethod
	def tryParseImmediate_STRING(cls, token):
		return cls.__tryParseImmediate_STRING(token, 4)

	@classmethod
	def tryParseImmediate_CHAR(cls, token):
		return cls.__tryParseImmediate_STRING(token, 1)

	@classmethod
	def tryParseImmediate_S5T(cls, token):
		token = token.upper()
		if not token.startswith("S5T#"):
			return None
		seconds = cls.__parseGenericTime(token[4:])
		s5t = Timer.seconds_to_s5t(seconds)
		return s5t

	@classmethod
	def tryParseImmediate_TIME(cls, token):
		token = token.upper()
		if not token.startswith("T#"):
			return None
		seconds = cls.__parseGenericTime(token[2:])
		msec = int(seconds * 1000)
		if msec > 0x7FFFFFFF:
			raise AwlSimError("T# time too big")
		return msec

	@classmethod
	def tryParseImmediate_TOD(cls, token):
		token = token.upper()
		if not token.startswith("TOD#") and\
		   not token.startswith("TIME_OF_DAY#"):
			return None
		raise AwlSimError("TIME_OF_DAY# not implemented, yet")#TODO

	@classmethod
	def tryParseImmediate_Date(cls, token):
		token = token.upper()
		if not token.startswith("D#"):
			return None
		raise AwlSimError("D# not implemented, yet")#TODO

	@classmethod
	def tryParseImmediate_DT(cls, token):
		token = token.upper()
		if not token.startswith("DT#") and\
		   not token.startswith("DATE_AND_TIME#"):
			return None
		raise AwlSimError("DATE_AND_TIME# not implemented, yet")#TODO

	@classmethod
	def __parsePtrOffset(cls, string):
		try:
			values = string.split(".")
			if len(values) != 2:
				raise ValueError
			byteOffset = int(values[0], 10)
			bitOffset = int(values[1], 10)
			if bitOffset < 0 or bitOffset > 7 or\
			   byteOffset < 0 or byteOffset > 0x1FFFFF:
				raise ValueError
			return (byteOffset << 3) | bitOffset
		except ValueError:
			raise AwlSimError("Invalid pointer offset")

	@classmethod
	def tryParseImmediate_Pointer(cls, tokens):
		prefix = tokens[0].upper()
		if not prefix.startswith("P#"):
			return None, None
		prefix = prefix[2:] # Strip P#
		try:
			if prefix == "P":
				ptr = cls.__parsePtrOffset(tokens[1]) |\
					0x80000000
				return ptr, 2
			elif prefix in ("E", "I"):
				ptr = cls.__parsePtrOffset(tokens[1]) |\
					0x81000000
				return ptr, 2
			elif prefix in ("A", "Q"):
				ptr = cls.__parsePtrOffset(tokens[1]) |\
					0x82000000
				return ptr, 2
			elif prefix == "M":
				ptr = cls.__parsePtrOffset(tokens[1]) |\
					0x83000000
				return ptr, 2
			elif prefix == "DBX":
				ptr = cls.__parsePtrOffset(tokens[1]) |\
					0x84000000
				return ptr, 2
			elif prefix == "DIX":
				ptr = cls.__parsePtrOffset(tokens[1]) |\
					0x85000000
				return ptr, 2
			elif prefix == "L":
				ptr = cls.__parsePtrOffset(tokens[1]) |\
					0x86000000
				return ptr, 2
			else:
				# Area-internal pointer
				ptr = cls.__parsePtrOffset(prefix)
				return ptr, 1
		except IndexError:
			raise AwlSimError("Invalid pointer immediate")

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

class GenericInteger(object):
	def __init__(self, value, width):
		assert(width > 0 and width <= 32)
		self.value = value
		self.mask = int(((1 << width) - 1) & 0xFFFFFFFF)

	def copyFrom(self, other):
		self.value = other.value & self.mask

	def set(self, value):
		self.value = value & self.mask

	def setByte(self, value):
		self.value = ((self.value & 0xFFFFFF00) |\
			      (value & 0xFF)) &\
			     self.mask

	def setWord(self, value):
		self.value = ((self.value & 0xFFFF0000) |\
			      (value & 0xFFFF)) &\
			     self.mask

	def setDWord(self, value):
		self.value = value & 0xFFFFFFFF & self.mask

	def setPyFloat(self, pyfl):
		self.value = pyFloatToDWord(pyfl)

	def get(self):
		return self.value

	def getByte(self):
		return self.value & 0xFF

	def getWord(self):
		return self.value & 0xFFFF

	def getDWord(self):
		return self.value & 0xFFFFFFFF

	def getSignedByte(self):
		return byteToSignedPyInt(self.value)

	def getSignedWord(self):
		return wordToSignedPyInt(self.value)

	def getSignedDWord(self):
		return dwordToSignedPyInt(self.value)

	def getPyFloat(self):
		return dwordToPyFloat(self.value)

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

class GenericWord(GenericInteger):
	def __init__(self, value=0):
		GenericInteger.__init__(self, value, 16)

class GenericDWord(GenericInteger):
	def __init__(self, value=0):
		GenericInteger.__init__(self, value, 32)

class ByteArray(bytearray):
	def fetch(self, offset, width):
		byteOffset = offset.byteOffset
		try:
			if width == 1:
				return (self[byteOffset] >> offset.bitOffset) & 1
			elif width == 8:
				return self[byteOffset]
			elif width == 16:
				return (self[byteOffset] << 8) |\
				       self[byteOffset + 1]
			elif width == 32:
				return (self[byteOffset] << 24) |\
				       (self[byteOffset + 1] << 16) |\
				       (self[byteOffset + 2] << 8) |\
				       self[byteOffset + 3]
		except IndexError as e:
			raise AwlSimError("fetch: Operator offset out of range")
		assert(0)

	def store(self, offset, width, value):
		byteOffset = offset.byteOffset
		try:
			if width == 1:
				if value:
					self[byteOffset] |= 1 << offset.bitOffset
				else:
					self[byteOffset] &= ~(1 << offset.bitOffset)
			elif width == 8:
				self[byteOffset] = value & 0xFF
			elif width == 16:
				self[byteOffset] = (value >> 8) & 0xFF
				self[byteOffset + 1] = value & 0xFF
			elif width == 32:
				self[byteOffset] = (value >> 24) & 0xFF
				self[byteOffset + 1] = (value >> 16) & 0xFF
				self[byteOffset + 2] = (value >> 8) & 0xFF
				self[byteOffset + 3] = value & 0xFF
			else:
				assert(0)
		except IndexError as e:
			raise AwlSimError("store: Operator offset out of range")

class Accu(GenericDWord):
	"Accumulator register"

	def __init__(self):
		GenericDWord.__init__(self)

class Adressregister(GenericDWord):
	"Address register"

	def __init__(self):
		GenericDWord.__init__(self)

	def toPointerString(self):
		value = self.getDWord()
		area = (value >> 24) & 0xFF
		if area:
			if area == 0x81:
				prefix = "E"
			elif area == 0x82:
				prefix = "A"
			elif area == 0x83:
				prefix = "M"
			elif area == 0x86:
				prefix = "L"
			else:
				prefix = "(%02X)" % area
			prefix += " "
		else:
			prefix = ""
		byteOffset = (value & 0x00FFFFFF) >> 3
		bitOffset = value & 7
		return "P#%s%d.%d" % (prefix, byteOffset, bitOffset)

# -*- coding: utf-8 -*-
#
# AWL data types
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from util import *
from awltimers import *


class AwlDataType(object):
	# Data type IDs
	TYPE_BOOL	= 0
	TYPE_BYTE	= 1
	TYPE_WORD	= 2
	TYPE_DWORD	= 3
	TYPE_INT	= 4
	TYPE_DINT	= 5
	TYPE_REAL	= 6
	TYPE_S5T	= 7
	TYPE_TIME	= 8
	TYPE_DATE	= 9
	TYPE_TOD	= 10
	TYPE_CHAR	= 11

	__name2id = {
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
		"TIME_OF_DAY"	: TYPE_TOD,
		"CHAR"		: TYPE_CHAR,
	}

	type2width = {
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
		TYPE_TOD	: 32,
		TYPE_CHAR	: 8,
	}

	type2signed = {
		TYPE_BOOL	: False,
		TYPE_BYTE	: False,
		TYPE_WORD	: False,
		TYPE_DWORD	: False,
		TYPE_INT	: True,
		TYPE_DINT	: True,
		TYPE_REAL	: False,
		TYPE_S5T	: False,
		TYPE_TIME	: False,
		TYPE_DATE	: False,
		TYPE_TOD	: False,
		TYPE_CHAR	: False,
	}

	@classmethod
	def name2type(cls, nameString):
		try:
			return cls.__name2id[nameString.upper()]
		except KeyError:
			raise AwlSimError("Invalid data type name: " +\
					  nameString)

	@classmethod
	def make(cls, type):
		return cls(type, cls.type2width[type],
			   cls.type2signed[type])

	@classmethod
	def makeByName(cls, nameString):
		return cls.make(cls.name2type(nameString))

	def __init__(self, type, width, signed):
		self.type = type
		self.width = width
		self.signed = signed

	def parseImmediate(self, string):
		if self.type == self.TYPE_BOOL:
			value = self.tryParseImmediate_BOOL(string)
		elif self.type == self.TYPE_BYTE:
			value = self.tryParseImmediate_HexByte(string)
		elif self.type == self.TYPE_WORD:
			value = self.tryParseImmediate_Bin(string)
			if value is None:
				value = self.tryParseImmediate_HexWord(string)
			if value is None:
				value = self.tryParseImmediate_BCD(string)
			if value is None:
				value = self.tryParseImmediate_ByteArray(string)
				if value > 0xFFFF:
					raise AwlSimError("Word-byte-array "
						"bigger than 16 bit")
		elif self.type == self.TYPE_DWORD:
			value = self.tryParseImmediate_Bin(string)
			if value is None:
				value = self.tryParseImmediate_HexDWord(string)
			if value is None:
				value = self.tryParseImmediate_ByteArray(string)
		elif self.type == self.TYPE_INT:
			value = self.tryParseImmediate_INT(string)
		elif self.type == self.TYPE_DINT:
			value = self.tryParseImmediate_DINT(string)
		elif self.type == self.TYPE_REAL:
			value = self.tryParseImmediate_REAL(string)
		elif self.type == self.TYPE_S5T:
			value = self.tryParseImmediate_S5T(string)
		elif self.type == self.TYPE_TIME:
			value = None
			pass#TODO
		elif self.type == self.TYPE_DATE:
			value = None
			pass#TODO
		elif self.type == self.TYPE_TOD:
			value = None
			pass#TODO
		elif self.type == self.TYPE_CHAR:
			value = None
			pass#TODO
		else:
			assert(0)
		if value is None:
			raise AwlSimError("Immediate value does "
				"not match data type")
		return value

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
			immediate = float(token[0])
			immediate = pyFloatToDWord(immediate)
		except ValueError:
			return None
		return immediate

	@classmethod
	def tryParseImmediate_S5T(cls, token):
		token = token.upper()
		if not token.startswith("S5T#"):
			return None
		p = token[4:]
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
		s5t = Timer.seconds_to_s5t(seconds)
		return s5t

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
		if isinstance(tokens, str):
			assert(0)#TODO
		tokens = [ t.upper() for t in tokens ]
		if not tokens[0].startswith("B#("):
			return None, None
		try:
			if len(tokens) >= 5 and\
			   tokens[2] == ',' and\
			   tokens[4] == ')':
				size, fields = 16, 5
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
				size, fields = 32, 9
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
	def __init__(self, value, mask):
		self.value = value
		self.mask = mask
		assert(mask <= 0xFFFFFFFF)

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

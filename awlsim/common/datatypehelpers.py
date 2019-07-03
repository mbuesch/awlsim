# -*- coding: utf-8 -*-
#
# AWL data types helper functions
#
# Copyright 2013-2019 Michael Buesch <m@bues.ch>
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
#from awlsim.common.cython_support cimport * #@cy
from awlsim.common.compat import *

from awlsim.common.util import *
from awlsim.common.exceptions import *

import struct #@nocy


__all__ = [
	"swapEndianWord",
	"swapEndianDWord",
	"byteToSignedPyInt",
	"wordToSignedPyInt",
	"dwordToSignedPyInt",
	"qwordToSignedPyInt",
	"pyFloatToDWord",
	"dwordToPyFloat",
	"floatConst",
	"isNaN",
	"isInf",
	"isPosNegZero",
	"isDenormalPyFloat",
	"pyFloatEqual",
	"floatEqual",
	"roundUp",
	"intDivRoundUp",
	"getMSB",
	"isInteger",
	"isString",
	"len_u32",
	"len_u16",
	"len_u8",
	"len_s32",
	"len_s16",
	"len_s8",
	"u32_to_s32",
	"u32_to_s16",
	"u32_to_s8",
	"s32_to_u32",
	"s32_to_u16",
	"s32_to_u8",
]


__floatStruct = struct.Struct(str('>f'))				#@nocy
__wordStruct = struct.Struct(str('>H'))					#@nocy
__leWordStruct = struct.Struct(str('<H'))				#@nocy
__dwordStruct = struct.Struct(str('>I'))				#@nocy
__leDWordStruct = struct.Struct(str('<I'))				#@nocy


# Swap the endianness of an S7 word.
# The Cython variant of this function is defined in .pxd.in
def swapEndianWord(word,						#@nocy
		   __be=__wordStruct,					#@nocy
		   __le=__leWordStruct):				#@nocy
	return __le.unpack(__be.pack(word))[0]				#@nocy

# Swap the endianness of an S7 dword.
# The Cython variant of this function is defined in .pxd.in
def swapEndianDWord(dword,						#@nocy
		   __be=__dwordStruct,					#@nocy
		   __le=__leDWordStruct):				#@nocy
	return __le.unpack(__be.pack(dword))[0]				#@nocy


# Convert a S7 byte to a signed Python int.
# This applies the two's complement, if the byte is negative
# so that the resulting Python int will have the correct sign.
# The Cython variant of this function is defined in .pxd.in
def byteToSignedPyInt(byte):						#@nocy
	if byte & 0x80:							#@nocy
		return -((~byte + 1) & 0xFF)				#@nocy
	return byte & 0xFF						#@nocy


# Convert a S7 word to a signed Python int.
# This applies the two's complement, if the word is negative
# so that the resulting Python int will have the correct sign.
# The Cython variant of this function is defined in .pxd.in
def wordToSignedPyInt(word):						#@nocy
	if word & 0x8000:						#@nocy
		return -((~word + 1) & 0xFFFF)				#@nocy
	return word & 0xFFFF						#@nocy


# Convert a S7 dword to a signed Python int.
# This applies the two's complement, if the dword is negative
# so that the resulting Python int will have the correct sign.
# The Cython variant of this function is defined in .pxd.in
def dwordToSignedPyInt(dword):						#@nocy
	if dword & 0x80000000:						#@nocy
		return -((~dword + 1) & 0xFFFFFFFF)			#@nocy
	return dword & 0xFFFFFFFF					#@nocy

# Convert a quad-word (64 bit) to a signed Python int.
# This applies the two's complement, if the qword is negative
# so that the resulting Python int will have the correct sign.
# The Cython variant of this function is defined in .pxd.in
def qwordToSignedPyInt(qword):						#@nocy
	if qword & 0x8000000000000000:					#@nocy
		return -((~qword + 1) & 0xFFFFFFFFFFFFFFFF)		#@nocy
	return qword & 0xFFFFFFFFFFFFFFFF				#@nocy


# Convert a Python float to an S7 dword.
def pyFloatToDWord(pyfl,						#@nocy
		   __f=__floatStruct,					#@nocy
		   __d=__dwordStruct):					#@nocy
#cdef uint32_t pyFloatToDWord(double pyfl):				#@cy
#	cdef _floatCastUnion u						#@cy
#	cdef uint32_t dword						#@cy

	try:								#@nocy
		dword = __d.unpack(__f.pack(pyfl))[0]			#@nocy
	except OverflowError:						#@nocy
		if pyfl < 0.0:						#@nocy
			dword = floatConst.minNormNegFloat32DWord	#@nocy
		else:							#@nocy
			dword = floatConst.maxNormPosFloat32DWord	#@nocy

#	u.fvalue = <float>pyfl;						#@cy
#	dword = u.value32						#@cy

	if isDenormalPyFloat(pyfl):
		# Denormal floats are equal to zero on the S7 CPU.
		# OV and OS flags are set in the StatusWord handler.
		dword = 0x00000000
	elif (dword & 0x7FFFFFFF) > 0x7F800000:
		# NaNs are always all-ones on the S7 CPU.
		dword = 0xFFFFFFFF
	return dword


# Convert an S7 dword to a Python float.
# The Cython variant of this function is defined in .pxd.in
def dwordToPyFloat(dword,						#@nocy
		   __f=__floatStruct,					#@nocy
		   __d=__dwordStruct):					#@nocy
	return __f.unpack(__d.pack(dword))[0]				#@nocy


class FloatConst(object): #+cdef
	__slots__ = (
		"minNormPosFloat32DWord",
		"minNormPosFloat32",
		"minNormNegFloat32DWord",
		"minNormNegFloat32",
		"maxNormNegFloat32DWord",
		"maxNormNegFloat32",
		"maxNormPosFloat32DWord",
		"maxNormPosFloat32",
		"posInfDWord",
		"posInfFloat",
		"negInfDWord",
		"negInfFloat",
		"pNaNDWord",
		"nNaNDWord",
		"nNaNFloat",
		"negZeroDWord",
		"epsilonFloat",
	)

	def __init__(self):
		# The smallest normalized positive 32-bit float.
		self.minNormPosFloat32DWord = 0x00000001
		self.minNormPosFloat32 = dwordToPyFloat(self.minNormPosFloat32DWord)

		# The smallest normalized negative 32-bit float.
		self.minNormNegFloat32DWord = 0xFF7FFFFF
		self.minNormNegFloat32 = dwordToPyFloat(self.minNormNegFloat32DWord)

		# The biggest normalized negative 32-bit float.
		self.maxNormNegFloat32DWord = 0x80000001
		self.maxNormNegFloat32 = dwordToPyFloat(self.maxNormNegFloat32DWord)

		# The biggest normalized positive 32-bit float.
		self.maxNormPosFloat32DWord = 0x7F7FFFFF
		self.maxNormPosFloat32 = dwordToPyFloat(self.maxNormPosFloat32DWord)

		# Positive infinity
		self.posInfDWord = 0x7F800000
		self.posInfFloat = dwordToPyFloat(self.posInfDWord)

		# Negative infinity
		self.negInfDWord = 0xFF800000
		self.negInfFloat = dwordToPyFloat(self.negInfDWord)

		# Positive NaN
		self.pNaNDWord = 0x7FFFFFFF

		# Negative NaN
		self.nNaNDWord = 0xFFFFFFFF
		self.nNaNFloat = dwordToPyFloat(self.nNaNDWord)

		# Negative zero
		self.negZeroDWord = 0x80000000

		# Compare threshold
		self.epsilonFloat = 0.0000001

floatConst = FloatConst() #+cdef-FloatConst


# Check if dword is positive or negative NaN
# The Cython variant of this function is defined in .pxd.in
def isNaN(dword):							#@nocy
	return (dword & 0x7FFFFFFF) > 0x7F800000			#@nocy

# Check if dword is positive or negative infinity.
# The Cython variant of this function is defined in .pxd.in
def isInf(dword):							#@nocy
	return (dword & 0x7FFFFFFF) == 0x7F800000			#@nocy

# Check if dword is positive or negative zero in IEEE float encoding.
# The Cython variant of this function is defined in .pxd.in
def isPosNegZero(dword):						#@nocy
	return (dword & 0x7FFFFFFF) == 0				#@nocy

# Check if a Python float is in the denormalized range.
# The Cython variant of this function is defined in .pxd.in
def isDenormalPyFloat(pyfl,						#@nocy
		      __min=floatConst.minNormPosFloat32,		#@nocy
		      __max=floatConst.maxNormNegFloat32):		#@nocy
	return ((pyfl > 0.0 and pyfl < __min) or			#@nocy
	        (pyfl < 0.0 and pyfl > __max))				#@nocy


# Check if two Python floats are equal.
def pyFloatEqual(pyfl0, pyfl1):						#@nocy
	return abs(pyfl0 - pyfl1) < floatConst.epsilonFloat		#@nocy


# Check if two Python floats or S7 dword are equal.
def floatEqual(fl0, fl1):						#@nocy
#cdef _Bool floatEqual(object fl0, object fl1):				#@cy
	if not isinstance(fl0, float):
		fl0 = dwordToPyFloat(fl0)
	if not isinstance(fl1, float):
		fl1 = dwordToPyFloat(fl1)
	return pyFloatEqual(fl0, fl1)


# Round up integer 'n' to a multiple of integer 's'
# The Cython variant of this function is defined in .pxd.in
def roundUp(n, s):				#@nocy
	return ((n + s - 1) // s) * s		#@nocy


# Divide integer 'n' by 'd' and round up to the next integer
# The Cython variant of this function is defined in .pxd.in
def intDivRoundUp(n, d):			#@nocy
	return (n + d - 1) // d			#@nocy

# Get the most significant bit set in a 32 bit integer
# and return an integer with only that bit set.
# If the value is bigger than 0xFFFFFFFF the behavior is undefined.
def getMSB(value): #@nocy
#cdef uint32_t getMSB(uint32_t value): #@cy
	value |= value >> 1
	value |= value >> 2
	value |= value >> 4
	value |= value >> 8
	value |= value >> 16
	return value ^ (value >> 1)

def __isInteger_python2(value):				#@nocy #@nocov
	return isinstance(value, (int, long))		#@nocy

def __isInteger_python3(value):				#@nocy #@nocov
	return isinstance(value, int)			#@nocy

isInteger = py23(__isInteger_python2,			#@nocy
		 __isInteger_python3)			#@nocy

def __isString_python2(value):				#@nocy #@nocov
	return isinstance(value, (unicode, str))	#@nocy

def __isString_python3(value):				#@nocy #@nocov
	return isinstance(value, str)			#@nocy

isString = py23(__isString_python2,			#@nocy
		__isString_python3)			#@nocy

# Get the len() of obj and restrict to uint32_t.
# The Cython variant of this function is defined in .pxd.in
def len_u32(obj):					#@nocy
	return min(len(obj), 0xFFFFFFFF)		#@nocy

# Get the len() of obj and restrict to uint16_t.
# The Cython variant of this function is defined in .pxd.in
def len_u16(obj):					#@nocy
	return min(len(obj), 0xFFFF)			#@nocy

# Get the len() of obj and restrict to uint8_t.
# The Cython variant of this function is defined in .pxd.in
def len_u8(obj):					#@nocy
	return min(len(obj), 0xFF)			#@nocy

# Get the len() of obj and restrict to int32_t.
# The Cython variant of this function is defined in .pxd.in
def len_s32(obj):					#@nocy
	return min(len(obj), 0x7FFFFFFF)		#@nocy

# Get the len() of obj and restrict to int16_t.
# The Cython variant of this function is defined in .pxd.in
def len_s16(obj):					#@nocy
	return min(len(obj), 0x7FFF)			#@nocy

# Get the len() of obj and restrict to int8_t.
# The Cython variant of this function is defined in .pxd.in
def len_s8(obj):					#@nocy
	return min(len(obj), 0x7F)			#@nocy

# Restrict an uint32_t to int32_t range.
# The Cython variant of this function is defined in .pxd.in
def u32_to_s32(value):					#@nocy
	return min(value, 0x7FFFFFFF)			#@nocy

# Restrict an uint32_t to int16_t range.
# The Cython variant of this function is defined in .pxd.in
def u32_to_s16(value):					#@nocy
	return min(value, 0x7FFF)			#@nocy

# Restrict an uint32_t to int8_t range.
# The Cython variant of this function is defined in .pxd.in
def u32_to_s8(value):					#@nocy
	return min(value, 0x7F)				#@nocy

# Restrict an int32_t to uint32_t range.
# The Cython variant of this function is defined in .pxd.in
def s32_to_u32(value):					#@nocy
	return min(max(value, 0), 0x7FFFFFFF)		#@nocy

# Restrict an int32_t to uint16_t range.
# The Cython variant of this function is defined in .pxd.in
def s32_to_u16(value):					#@nocy
	return min(max(value, 0), 0xFFFF)		#@nocy

# Restrict an int32_t to uint8_t range.
# The Cython variant of this function is defined in .pxd.in
def s32_to_u8(value):					#@nocy
	return min(max(value, 0), 0xFF)			#@nocy

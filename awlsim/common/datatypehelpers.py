# -*- coding: utf-8 -*-
#
# AWL data types helper functions
#
# Copyright 2013-2017 Michael Buesch <m@bues.ch>
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

import struct


__all__ = [
	"swapEndianWord",
	"swapEndianDWord",
	"byteToSignedPyInt",
	"wordToSignedPyInt",
	"dwordToSignedPyInt",
	"pyFloatToDWord",
	"dwordToPyFloat",
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
	"isNaN",
	"isDenormalPyFloat",
	"pyFloatEqual",
	"floatEqual",
	"roundUp",
	"intDivRoundUp",
]


__floatStruct = struct.Struct(str('>f'))
__wordStruct = struct.Struct(str('>H'))
__leWordStruct = struct.Struct(str('<H'))
__dwordStruct = struct.Struct(str('>I'))
__leDWordStruct = struct.Struct(str('<I'))


# Swap the endianness of an S7 word.
def swapEndianWord(word,						#@nocy
		   __be=__wordStruct,					#@nocy
		   __le=__leWordStruct):				#@nocy
	return __le.unpack(__be.pack(word))[0]				#@nocy
#cdef uint16_t swapEndianWord(uint16_t word):				#@cy
#	return __leWordStruct.unpack(__wordStruct.pack(word))[0]	#@cy

assert(swapEndianWord(0x1234) == 0x3412)
assert(swapEndianWord(swapEndianWord(0x1234)) == 0x1234)


# Swap the endianness of an S7 dword.
def swapEndianDWord(dword,						#@nocy
		   __be=__dwordStruct,					#@nocy
		   __le=__leDWordStruct):				#@nocy
	return __le.unpack(__be.pack(dword))[0]				#@nocy
#cdef uint32_t swapEndianDWord(uint32_t dword):				#@cy
#	return __leDWordStruct.unpack(__dwordStruct.pack(dword))[0]	#@cy

assert(swapEndianDWord(0x12345678) == 0x78563412)
assert(swapEndianDWord(swapEndianDWord(0x12345678)) == 0x12345678)


# Convert a S7 byte to a signed Python int.
# This applies the two's complement, if the dword is negative
# so that the resulting Python int will have the correct sign.
def byteToSignedPyInt(byte):						#@nocy
	if byte & 0x80:							#@nocy
		return -((~byte + 1) & 0xFF)				#@nocy
	return byte & 0xFF						#@nocy
#cdef int32_t byteToSignedPyInt(uint8_t byte):				#@cy
#	return <int32_t>(<int8_t>byte)					#@cy


# Convert a S7 word to a signed Python int.
# This applies the two's complement, if the dword is negative
# so that the resulting Python int will have the correct sign.
def wordToSignedPyInt(word):						#@nocy
	if word & 0x8000:						#@nocy
		return -((~word + 1) & 0xFFFF)				#@nocy
	return word & 0xFFFF						#@nocy
#cdef int32_t wordToSignedPyInt(uint16_t word):				#@cy
#	return <int32_t>(<int16_t>word)					#@cy


# Convert a S7 dword to a signed Python int.
# This applies the two's complement, if the dword is negative
# so that the resulting Python int will have the correct sign.
def dwordToSignedPyInt(dword):						#@nocy
	if dword & 0x80000000:						#@nocy
		return -((~dword + 1) & 0xFFFFFFFF)			#@nocy
	return dword & 0xFFFFFFFF					#@nocy
#cdef int32_t dwordToSignedPyInt(uint32_t dword):			#@cy
#	return <int32_t>dword						#@cy


# Convert a Python float to an S7 dword.
def pyFloatToDWord(pyfl,						#@nocy
		   __f=__floatStruct,					#@nocy
		   __d=__dwordStruct):					#@nocy
	dword = __d.unpack(__f.pack(pyfl))[0]				#@nocy
#cdef uint32_t pyFloatToDWord(double pyfl):				#@cy
#	cdef uint32_t dword						#@cy
#	dword = __dwordStruct.unpack(__floatStruct.pack(pyfl))[0]	#@cy
	if isDenormalPyFloat(pyfl):
		# Denormal floats are equal to zero on the S7 CPU.
		# OV and OS flags are set in the StatusWord handler.
		dword = 0x00000000
	elif (dword & 0x7FFFFFFF) > 0x7F800000:
		# NaNs are always all-ones on the S7 CPU.
		dword = 0xFFFFFFFF
	return dword


# Convert an S7 dword to a Python float.
def dwordToPyFloat(dword,						#@nocy
		   __f=__floatStruct,					#@nocy
		   __d=__dwordStruct):					#@nocy
	return __f.unpack(__d.pack(dword))[0]				#@nocy
#cdef double dwordToPyFloat(uint32_t dword):				#@cy
#	return __floatStruct.unpack(__dwordStruct.pack(dword))[0]	#@cy


# The smallest normalized positive 32-bit float.
minNormPosFloat32DWord = 0x00000001					#+cdef-public-uint32_t
minNormPosFloat32 = dwordToPyFloat(minNormPosFloat32DWord)		#+cdef-public-double

# The smallest normalized negative 32-bit float.
minNormNegFloat32DWord = 0xFF7FFFFF					#+cdef-public-uint32_t
minNormNegFloat32 = dwordToPyFloat(minNormNegFloat32DWord)		#+cdef-public-double

# The biggest normalized negative 32-bit float.
maxNormNegFloat32DWord = 0x80000001					#+cdef-public-uint32_t
maxNormNegFloat32 = dwordToPyFloat(maxNormNegFloat32DWord)		#+cdef-public-double

# The biggest normalized positive 32-bit float.
maxNormPosFloat32DWord = 0x7F7FFFFF					#+cdef-public-uint32_t
maxNormPosFloat32 = dwordToPyFloat(maxNormPosFloat32DWord)		#+cdef-public-double

# Positive infinity
posInfDWord = 0x7F800000						#+cdef-public-uint32_t
posInfFloat = dwordToPyFloat(posInfDWord)				#+cdef-public-double

# Negative infinity
negInfDWord = 0xFF800000						#+cdef-public-uint32_t
negInfFloat = dwordToPyFloat(negInfDWord)				#+cdef-public-double

# Positive NaN
pNaNDWord = 0x7FFFFFFF							#+cdef-public-uint32_t

# Negative NaN
nNaNDWord = 0xFFFFFFFF							#+cdef-public-uint32_t
nNaNFloat = dwordToPyFloat(nNaNDWord)					#+cdef-public-double


# Check if dword is positive or negative NaN
def isNaN(dword):							#@nocy
#cdef _Bool isNaN(uint32_t dword):					#@cy
	return (dword & 0x7FFFFFFF) > 0x7F800000


# Check if a Python float is in the denormalized range.
def isDenormalPyFloat(pyfl,						#@nocy
		      __min=minNormPosFloat32,				#@nocy
		      __max=maxNormNegFloat32):				#@nocy
	return ((pyfl > 0.0 and pyfl < __min) or			#@nocy
	        (pyfl < 0.0 and pyfl > __max))				#@nocy
#cdef _Bool isDenormalPyFloat(double pyfl):				#@cy
#	return ((pyfl > 0.0 and pyfl < minNormPosFloat32) or		#@cy
#	        (pyfl < 0.0 and pyfl > maxNormNegFloat32))		#@cy


# Check if two Python floats are equal.
def pyFloatEqual(pyfl0, pyfl1):						#@nocy
#cdef _Bool pyFloatEqual(double pyfl0, double pyfl1):			#@cy
	return abs(pyfl0 - pyfl1) < 0.000001


# Check if two Python floats or S7 dword are equal.
def floatEqual(fl0, fl1):						#@nocy
#cdef _Bool floatEqual(object fl0, object fl1):				#@cy
	if not isinstance(fl0, float):
		fl0 = dwordToPyFloat(fl0)
	if not isinstance(fl1, float):
		fl1 = dwordToPyFloat(fl1)
	return pyFloatEqual(fl0, fl1)


# Constant value sanity checks.
assert(pyFloatToDWord(minNormPosFloat32) == minNormPosFloat32DWord)
assert(pyFloatToDWord(minNormNegFloat32) == minNormNegFloat32DWord)
assert(pyFloatToDWord(maxNormNegFloat32) == maxNormNegFloat32DWord)
assert(pyFloatToDWord(maxNormPosFloat32) == maxNormPosFloat32DWord)
assert(pyFloatToDWord(posInfFloat) == posInfDWord)
assert(pyFloatToDWord(negInfFloat) == negInfDWord)
assert(pyFloatToDWord(nNaNFloat) == nNaNDWord)


# Round up integer 'n' to a multiple of integer 's'
def roundUp(n, s):							#@nocy
#cdef uint32_t roundUp(uint32_t n, uint32_t s):				#@cy
	return ((n + s - 1) // s) * s


# Divide integer 'n' by 'd' and round up to the next integer
def intDivRoundUp(n, d):						#@nocy
#cdef uint32_t intDivRoundUp(uint32_t n, uint32_t d):			#@cy
	return (n + d - 1) // d

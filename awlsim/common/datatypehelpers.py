# -*- coding: utf-8 -*-
#
# AWL data types helper functions
#
# Copyright 2013-2016 Michael Buesch <m@bues.ch>
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


__floatStruct = struct.Struct(str('>f'))
__wordStruct = struct.Struct(str('>H'))
__leWordStruct = struct.Struct(str('<H'))
__dwordStruct = struct.Struct(str('>I'))
__leDWordStruct = struct.Struct(str('<I'))


# Swap the endianness of an S7 word.
def swapEndianWord(word,
		   __be=__wordStruct,
		   __le=__leWordStruct):
	return __le.unpack(__be.pack(word))[0]

assert(swapEndianWord(0x1234) == 0x3412)
assert(swapEndianWord(swapEndianWord(0x1234)) == 0x1234)

# Swap the endianness of an S7 dword.
def swapEndianDWord(dword,
		   __be=__dwordStruct,
		   __le=__leDWordStruct):
	return __le.unpack(__be.pack(dword))[0]

assert(swapEndianDWord(0x12345678) == 0x78563412)
assert(swapEndianDWord(swapEndianDWord(0x12345678)) == 0x12345678)

# Convert a S7 byte to a signed Python int.
# This applies the two's complement, if the dword is negative
# so that the resulting Python int will have the correct sign.
def byteToSignedPyInt(byte):
	if byte & 0x80:
		return -((~byte + 1) & 0xFF)
	return byte & 0xFF

# Convert a S7 word to a signed Python int.
# This applies the two's complement, if the dword is negative
# so that the resulting Python int will have the correct sign.
def wordToSignedPyInt(word):
	if word & 0x8000:
		return -((~word + 1) & 0xFFFF)
	return word & 0xFFFF

# Convert a S7 dword to a signed Python int.
# This applies the two's complement, if the dword is negative
# so that the resulting Python int will have the correct sign.
def dwordToSignedPyInt(dword):
	if dword & 0x80000000:
		return -((~dword + 1) & 0xFFFFFFFF)
	return dword & 0xFFFFFFFF

# Convert a Python float to an S7 dword.
def pyFloatToDWord(pyfl,
		   __f=__floatStruct,
		   __d=__dwordStruct):
	dword = __d.unpack(__f.pack(pyfl))[0]
	if isDenormalPyFloat(pyfl):
		# Denormal floats are equal to zero on the S7 CPU.
		# OV and OS flags are set in the StatusWord handler.
		dword = 0x00000000
	elif (dword & 0x7FFFFFFF) > 0x7F800000:
		# NaNs are always all-ones on the S7 CPU.
		dword = 0xFFFFFFFF
	return dword

# Convert an S7 dword to a Python float.
def dwordToPyFloat(dword,
		   __f=__floatStruct,
		   __d=__dwordStruct):
	return __f.unpack(__d.pack(dword))[0]

# The smallest normalized positive 32-bit float.
minNormPosFloat32DWord = 0x00000001
minNormPosFloat32 = dwordToPyFloat(minNormPosFloat32DWord)

# The smallest normalized negative 32-bit float.
minNormNegFloat32DWord = 0xFF7FFFFF
minNormNegFloat32 = dwordToPyFloat(minNormNegFloat32DWord)

# The biggest normalized negative 32-bit float.
maxNormNegFloat32DWord = 0x80000001
maxNormNegFloat32 = dwordToPyFloat(maxNormNegFloat32DWord)

# The biggest normalized positive 32-bit float.
maxNormPosFloat32DWord = 0x7F7FFFFF
maxNormPosFloat32 = dwordToPyFloat(maxNormPosFloat32DWord)

# Positive infinity
posInfDWord = 0x7F800000
posInfFloat = dwordToPyFloat(posInfDWord)

# Negative infinity
negInfDWord = 0xFF800000
negInfFloat = dwordToPyFloat(negInfDWord)

# Positive NaN
pNaNDWord = 0x7FFFFFFF

# Negative NaN
nNaNDWord = 0xFFFFFFFF
nNaNFloat = dwordToPyFloat(nNaNDWord)

# Check if dword is positive or negative NaN
def isNaN(dword):
	return (dword & 0x7FFFFFFF) > 0x7F800000

# Check if a Python float is in the denormalized range.
def isDenormalPyFloat(pyfl,
		      __min=minNormPosFloat32,
		      __max=maxNormNegFloat32):
	return (pyfl > 0.0 and pyfl < __min) or\
	       (pyfl < 0.0 and pyfl > __max)

# Check if two Python floats are equal.
def pyFloatEqual(pyfl0, pyfl1):
	return abs(pyfl0 - pyfl1) < 0.000001

# Check if two Python floats or S7 dword are equal.
def floatEqual(fl0, fl1):
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
def roundUp(n, s):
	return ((n + s - 1) // s) * s

# Divide integer 'n' by 'd' and round up to the next integer
def intDivRoundUp(n, d):
	return (n + d - 1) // d

# -*- coding: utf-8 -*-
#
# AWL data types helper functions
# Copyright 2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from awlsim.util import *


def swapEndianWord(word):
	return ((word & 0x00FF) << 8) |\
	       ((word & 0xFF00) >> 8)

def swapEndianDWord(dword):
	return ((dword & 0x000000FF) << 24) |\
	       ((dword & 0x0000FF00) << 8) |\
	       ((dword & 0x00FF0000) >> 8) |\
	       ((dword & 0xFF000000) >> 24)

def byteToSignedPyInt(byte):
	if byte & 0x80:
		return -((~byte + 1) & 0xFF)
	return byte & 0xFF

def wordToSignedPyInt(word):
	if word & 0x8000:
		return -((~word + 1) & 0xFFFF)
	return word & 0xFFFF

def dwordToSignedPyInt(dword):
	if dword & 0x80000000:
		return -((~dword + 1) & 0xFFFFFFFF)
	return dword & 0xFFFFFFFF

def __rawPyFloatToDWord_python2(pyfl):
	buf = struct.pack('>f', pyfl)
	return (ord(buf[0]) << 24) |\
	       (ord(buf[1]) << 16) |\
	       (ord(buf[2]) << 8) |\
	       ord(buf[3])

def __rawPyFloatToDWord_python3(pyfl):
	buf = struct.pack('>f', pyfl)
	return (buf[0] << 24) |\
	       (buf[1] << 16) |\
	       (buf[2] << 8) |\
	       buf[3]

rawPyFloatToDWord = py23(__rawPyFloatToDWord_python2,
			 __rawPyFloatToDWord_python3)

def pyFloatToDWord(pyfl):
	dword = rawPyFloatToDWord(pyfl)
	if isDenormalPyFloat(pyfl):
		# Denormal floats are equal to zero on the S7 CPU.
		# OV and OS flags are set in the StatusWord handler.
		dword = 0x00000000
	elif (dword & 0x7FFFFFFF) > 0x7F800000:
		# NaNs are always all-ones on the S7 CPU.
		dword = 0xFFFFFFFF
	return dword

def __dwordToPyFloat_python2(dword):
	return struct.unpack('>f',
		chr((dword >> 24) & 0xFF) +\
		chr((dword >> 16) & 0xFF) +\
		chr((dword >> 8) & 0xFF) +\
		chr(dword & 0xFF)
	)[0]

def __dwordToPyFloat_python3(dword):
	return struct.unpack('>f',
		bytes( ((dword >> 24) & 0xFF,
			(dword >> 16) & 0xFF,
			(dword >> 8) & 0xFF,
			dword & 0xFF)
		)
	)[0]

dwordToPyFloat = py23(__dwordToPyFloat_python2,
		      __dwordToPyFloat_python3)

# The smallest normalized positive 32-bit float.
minNormPosFloat32 = dwordToPyFloat(0x00000001)
# The smallest normalized negative 32-bit float.
minNormNegFloat32 = dwordToPyFloat(0xFF7FFFFF)
# The biggest normalized negative 32-bit float.
maxNormNegFloat32 = dwordToPyFloat(0x80000001)
# The biggest normalized positive 32-bit float.
maxNormPosFloat32 = dwordToPyFloat(0x7F7FFFFF)

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

def isDenormalPyFloat(pyfl):
	return (pyfl > 0.0 and pyfl < minNormPosFloat32) or\
	       (pyfl < 0.0 and pyfl > maxNormNegFloat32)

def pyFloatEqual(pyfl0, pyfl1):
	return abs(pyfl0 - pyfl1) < 0.000001

def floatEqual(fl0, fl1):
	if not isinstance(fl0, float):
		fl0 = dwordToPyFloat(fl0)
	if not isinstance(fl1, float):
		fl1 = dwordToPyFloat(fl1)
	return pyFloatEqual(fl0, fl1)

def intDivRoundUp(n, d):
	return (n + d - 1) // d

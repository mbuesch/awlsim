from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim_tstlib import *

from awlsim.common.datatypehelpers import *


def test_swapEndianWord():
	assert_eq(swapEndianWord(0x1234), 0x3412)
	assert_eq(swapEndianWord(swapEndianWord(0x1234)), 0x1234)

def test_swapEndianDWord():
	assert_eq(swapEndianDWord(0x12345678), 0x78563412)
	assert_eq(swapEndianDWord(swapEndianDWord(0x12345678)), 0x12345678)

def test_floatConst():
	assert_eq(pyFloatToDWord(floatConst.minNormPosFloat32), floatConst.minNormPosFloat32DWord)
	assert_eq(pyFloatToDWord(floatConst.minNormNegFloat32), floatConst.minNormNegFloat32DWord)
	assert_eq(pyFloatToDWord(floatConst.maxNormNegFloat32), floatConst.maxNormNegFloat32DWord)
	assert_eq(pyFloatToDWord(floatConst.maxNormPosFloat32), floatConst.maxNormPosFloat32DWord)
	assert_eq(pyFloatToDWord(floatConst.posInfFloat), floatConst.posInfDWord)
	assert_eq(pyFloatToDWord(floatConst.negInfFloat), floatConst.negInfDWord)
	assert_eq(pyFloatToDWord(floatConst.nNaNFloat), floatConst.nNaNDWord)

def test_getMSB():
	assert_eq(getMSB(0), 0)
	assert_eq(getMSB(0xFFFFFFFF), 0x80000000)
	assert_eq(getMSB(0x57C31), 0x40000)
	assert_eq(getMSB(0xA6B204), 0x800000)
	mask0 = 0xAAAAAAAA
	mask1 = 0x55555555
	for i in range(32):
		assert_eq(getMSB(1 << i), 1 << i)
		assert_eq(getMSB(mask0), 1 << (31 - i))
		assert_eq(getMSB(mask1), (1 << (31 - i)) >> 1)
		mask0 >>= 1
		mask1 >>= 1

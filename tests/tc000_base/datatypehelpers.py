from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim_tstlib import *
initTest(__file__)

from awlsim.common.datatypehelpers import * #+cimport


class Test_DataTypeHelpers(TestCase):
	def test_swapEndianWord(self):
		self.assertEqual(swapEndianWord(0x1234), 0x3412)
		self.assertEqual(swapEndianWord(swapEndianWord(0x1234)), 0x1234)

	def test_swapEndianDWord(self):
		self.assertEqual(swapEndianDWord(0x12345678), 0x78563412)
		self.assertEqual(swapEndianDWord(swapEndianDWord(0x12345678)), 0x12345678)

	def test_floatConst(self):
		self.assertEqual(pyFloatToDWord(floatConst.minNormPosFloat32), floatConst.minNormPosFloat32DWord)
		self.assertEqual(pyFloatToDWord(floatConst.minNormNegFloat32), floatConst.minNormNegFloat32DWord)
		self.assertEqual(pyFloatToDWord(floatConst.maxNormNegFloat32), floatConst.maxNormNegFloat32DWord)
		self.assertEqual(pyFloatToDWord(floatConst.maxNormPosFloat32), floatConst.maxNormPosFloat32DWord)
		self.assertEqual(pyFloatToDWord(floatConst.posInfFloat), floatConst.posInfDWord)
		self.assertEqual(pyFloatToDWord(floatConst.negInfFloat), floatConst.negInfDWord)
		self.assertEqual(pyFloatToDWord(floatConst.nNaNFloat), floatConst.nNaNDWord)

	def test_getMSB(self):
		self.assertEqual(getMSB(0), 0)
		self.assertEqual(getMSB(0xFFFFFFFF), 0x80000000)
		self.assertEqual(getMSB(0x57C31), 0x40000)
		self.assertEqual(getMSB(0xA6B204), 0x800000)
		mask0 = 0xAAAAAAAA
		mask1 = 0x55555555
		for i in range(32):
			self.assertEqual(getMSB(1 << i), 1 << i)
			self.assertEqual(getMSB(mask0), 1 << (31 - i))
			self.assertEqual(getMSB(mask1), (1 << (31 - i)) >> 1)
			mask0 >>= 1
			mask1 >>= 1

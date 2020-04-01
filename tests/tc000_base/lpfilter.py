from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim_tstlib import *
initTest(__file__)

from awlsim.common.lpfilter import * #+cimport
from awlsim.common.exceptions import *


class Test_LPFilter(TestCase):
	def test_case_0(self):
		f = LPFilter(4)
		for i in range(10):
			self.assertEqual(f.run(0.0), 0.0)

	def test_case_1(self):
		f = LPFilter(1)
		self.assertAlmostEqual(f.run(10.0), 10.0, places=3)
		self.assertAlmostEqual(f.run(10.0), 10.0, places=3)
		self.assertAlmostEqual(f.run(20.0), 20.0, places=3)
		self.assertAlmostEqual(f.run(20.0), 20.0, places=3)
		self.assertAlmostEqual(f.run(30.0), 30.0, places=3)
		self.assertAlmostEqual(f.run(30.0), 30.0, places=3)
		self.assertAlmostEqual(f.run(-10.0), -10.0, places=3)
		self.assertAlmostEqual(f.run(-10.0), -10.0, places=3)

	def test_case_2(self):
		f = LPFilter(2)
		self.assertAlmostEqual(f.run(10.0), 5.0000, places=3)
		self.assertAlmostEqual(f.run(10.0), 7.5000, places=3)
		self.assertAlmostEqual(f.run(10.0), 8.7500, places=3)
		self.assertAlmostEqual(f.run(10.0), 9.3750, places=3)
		self.assertAlmostEqual(f.run(10.0), 9.6875, places=3)

	def test_case_3(self):
		f = LPFilter(4)
		for i in range(100):
			r = f.run(8.0)
			if i == 0:
				self.assertAlmostEqual(r, 2.0, places=3)
			if i == 99:
				self.assertAlmostEqual(r, 8.0, places=3)

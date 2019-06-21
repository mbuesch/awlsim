from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim_tstlib import *
initTest(__file__)

from awlsim.common.movingavg import * #+cimport
from awlsim.common.exceptions import *


class Test_MovingAvg(TestCase):
	def test_case_0(self):
		m = MovingAvg(3)
		for i in range(10):
			self.assertEqual(m.calculate(0.0), 0.0)

	def test_case_1(self):
		m = MovingAvg(1)
		for i in range(10):
			self.assertAlmostEqual(m.calculate(float(i)), float(i))

	def test_case_2(self):
		m = MovingAvg(1)
		for i in range(0, -10, -1):
			self.assertAlmostEqual(m.calculate(float(i)), float(i))

	def test_case_3(self):
		self.assertRaises(AwlSimError, lambda: MovingAvg(0))
		self.assertRaises(AwlSimError, lambda: MovingAvg(-1))

	def test_case_4(self):
		m = MovingAvg(3)
		self.assertAlmostEqual(m.calculate(1.0), 1.0, places=3)
		self.assertAlmostEqual(m.calculate(2.0), 1.5, places=3)
		self.assertAlmostEqual(m.calculate(2.0), 1.6666, places=3)
		self.assertAlmostEqual(m.calculate(2.0), 2.0, places=3)
		self.assertAlmostEqual(m.calculate(3.0), 2.3333, places=3)
		self.assertAlmostEqual(m.calculate(10.0), 5.0, places=3)
		self.assertAlmostEqual(m.calculate(20.0), 11.0, places=3)
		self.assertAlmostEqual(m.calculate(300.0), 110.0, places=3)
		self.assertAlmostEqual(m.calculate(1.2), 107.0666, places=3)
		self.assertAlmostEqual(m.calculate(1.2), 100.8, places=3)
		self.assertAlmostEqual(m.calculate(1.2), 1.2, places=3)

	def test_case_5(self):
		m = MovingAvg(5)
		self.assertAlmostEqual(m.calculate(-1.0), -1.0, places=3)
		self.assertAlmostEqual(m.calculate(-1.0), -1.0, places=3)
		self.assertAlmostEqual(m.calculate(-7.7), -3.2333, places=3)
		self.assertAlmostEqual(m.calculate(-6.1), -3.95, places=3)
		self.assertAlmostEqual(m.calculate(-6.1), -4.38, places=3)
		self.assertAlmostEqual(m.calculate(-11.5), -6.48, places=3)
		self.assertAlmostEqual(m.calculate(-12.2), -8.72, places=3)
		self.assertAlmostEqual(m.calculate(1000.0), 192.82, places=3)

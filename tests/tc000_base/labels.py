from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim_tstlib import *
initTest(__file__)

from awlsim.core.labels import * #+cimport


class Test_AwlLabels(TestCase):
	def test_generateLabelName(self):
		self.assertRaises(ValueError, lambda: AwlLabel.generateLabelName(-1))
		self.assertEqual(AwlLabel.generateLabelName(0),         "AAAA")
		self.assertEqual(AwlLabel.generateLabelName(26**1 - 1), "AAAZ")
		self.assertEqual(AwlLabel.generateLabelName(26**1),     "AABA")
		self.assertEqual(AwlLabel.generateLabelName(26**2 - 1), "AAZZ")
		self.assertEqual(AwlLabel.generateLabelName(26**2),     "ABAA")
		self.assertEqual(AwlLabel.generateLabelName(26**3 - 1), "AZZZ")
		self.assertEqual(AwlLabel.generateLabelName(26**3),     "BAAA")
		self.assertEqual(AwlLabel.generateLabelName(26**4 - 1), "ZZZZ")
		self.assertRaises(ValueError, lambda: AwlLabel.generateLabelName(26**4))

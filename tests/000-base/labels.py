from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim_tstlib import *

from awlsim.core.labels import *


class Test_AwlLabels(object):
	def test_generateLabelName(self):
		assert_raises(ValueError, lambda: AwlLabel.generateLabelName(-1))
		assert_eq(AwlLabel.generateLabelName(0),         "AAAA")
		assert_eq(AwlLabel.generateLabelName(26**1 - 1), "AAAZ")
		assert_eq(AwlLabel.generateLabelName(26**1),     "AABA")
		assert_eq(AwlLabel.generateLabelName(26**2 - 1), "AAZZ")
		assert_eq(AwlLabel.generateLabelName(26**2),     "ABAA")
		assert_eq(AwlLabel.generateLabelName(26**3 - 1), "AZZZ")
		assert_eq(AwlLabel.generateLabelName(26**3),     "BAAA")
		assert_eq(AwlLabel.generateLabelName(26**4 - 1), "ZZZZ")
		assert_raises(ValueError, lambda: AwlLabel.generateLabelName(26**4))

from __future__ import division, absolute_import, print_function, unicode_literals

from unittest import TestCase

def initTest(testCaseFile):
	from os.path import basename
	print("(test case file: %s)" % basename(testCaseFile))

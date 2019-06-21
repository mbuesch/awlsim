from __future__ import division, absolute_import, print_function, unicode_literals

from unittest import TestCase

__all__ = [
	"TestCase",
	"initTest",
]

def initTest(testCaseFile):
	from os.path import basename
	print("(test case file: %s)" % basename(testCaseFile))

# Run code coverage metrics, if enabled.
import awlsim_loader.coverage_helper

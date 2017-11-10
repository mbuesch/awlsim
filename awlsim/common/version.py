from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim.common.compat import *


__all__ = [
	"VERSION_MAJOR",
	"VERSION_MINOR",
	"VERSION_STRING",
]


VERSION_MAJOR = 0
VERSION_MINOR = 58
VERSION_EXTRA = ""

VERSION_STRING = "%d.%d%s" % (VERSION_MAJOR, VERSION_MINOR, VERSION_EXTRA)

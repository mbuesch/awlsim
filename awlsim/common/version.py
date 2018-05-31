from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim.common.compat import *

import binascii


__all__ = [
	"VERSION_MAJOR",
	"VERSION_MINOR",
	"VERSION_STRING",
	"VERSION_ID",
]


VERSION_MAJOR = 0
VERSION_MINOR = 64
VERSION_EXTRA = "-pre"

VERSION_STRING = "%d.%d%s" % (VERSION_MAJOR, VERSION_MINOR, VERSION_EXTRA)
VERSION_ID = binascii.crc32(VERSION_STRING.encode("UTF-8")) & 0x7FFFFFFF

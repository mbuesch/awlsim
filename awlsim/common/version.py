from __future__ import division, absolute_import, print_function, unicode_literals
#from awlsim.common.cython_support cimport * #@cy
from awlsim.common.compat import *

from binascii import crc32


__all__ = [
	"VERSION_MAJOR",
	"VERSION_MINOR",
	"VERSION_BUGFIX",
	"VERSION_STRING",
	"VERSION_ID",
]


VERSION_MAJOR	= 0
VERSION_MINOR	= 75
VERSION_BUGFIX	= 0
VERSION_EXTRA	= ""



if osIsWindows and VERSION_EXTRA: #@nocov
	# pywin32 does not like non-numbers in the version string.
	# Convert the VERSION_EXTRA into a dot-number string.
	VERSION_EXTRA = ".0000%d0000" % (crc32(VERSION_EXTRA.encode("UTF-8")) & 0xFFFF)

# Create a string from the version information.
VERSION_STRING = "%d.%d.%d%s" % (VERSION_MAJOR, VERSION_MINOR,
				 VERSION_BUGFIX, VERSION_EXTRA)

# Create a 31 bit ID number from the version information.
VERSION_ID = crc32(VERSION_STRING.encode("UTF-8")) & 0x7FFFFFFF

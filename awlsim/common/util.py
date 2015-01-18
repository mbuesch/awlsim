# -*- coding: utf-8 -*-
#
# AWL simulator - common utility functions
#
# Copyright 2012-2014 Michael Buesch <m@bues.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim.common.compat import *

from awlsim.common.enumeration import *
from awlsim.common.exceptions import *

import sys
import os
import random
import base64
import binascii


class Logging(object):
	EnumGen.start
	LOG_NONE	= EnumGen.item
	LOG_ERROR	= EnumGen.item
	LOG_WARNING	= EnumGen.item
	LOG_INFO	= EnumGen.item
	LOG_VERBOSE	= EnumGen.item
	LOG_DEBUG	= EnumGen.item
	EnumGen.end

	loglevel = LOG_INFO
	prefix = ""

	@classmethod
	def setLoglevel(cls, loglevel):
		if loglevel not in (cls.LOG_NONE,
				    cls.LOG_ERROR,
				    cls.LOG_WARNING,
				    cls.LOG_INFO,
				    cls.LOG_VERBOSE,
				    cls.LOG_DEBUG):
			raise AwlSimError("Invalid log level '%d'" % loglevel)
		cls.loglevel = loglevel

	@classmethod
	def setPrefix(cls, prefix):
		cls.prefix = prefix

	@classmethod
	def __print(cls, stream, text):
		try:
			if cls.prefix:
				stream.write(cls.prefix)
			stream.write(text)
			stream.write("\n")
			stream.flush()
		except RuntimeError:
			pass #Ignore

	@classmethod
	def printDebug(cls, text):
		if cls.loglevel >= cls.LOG_DEBUG:
			cls.__print(sys.stdout, text)

	@classmethod
	def printVerbose(cls, text):
		if cls.loglevel >= cls.LOG_VERBOSE:
			cls.__print(sys.stdout, text)

	@classmethod
	def printInfo(cls, text):
		if cls.loglevel >= cls.LOG_INFO:
			cls.__print(sys.stdout, text)

	@classmethod
	def printWarning(cls, text):
		if cls.loglevel >= cls.LOG_WARNING:
			cls.__print(sys.stderr, text)

	@classmethod
	def printError(cls, text):
		if cls.loglevel >= cls.LOG_ERROR:
			cls.__print(sys.stderr, text)

def printDebug(text):
	Logging.printDebug(text)

def printVerbose(text):
	Logging.printVerbose(text)

def printInfo(text):
	Logging.printInfo(text)

def printWarning(text):
	Logging.printWarning(text)

def printError(text):
	Logging.printError(text)

def awlFileRead(filename, encoding="latin_1"):
	try:
		fd = open(filename, "rb")
		data = fd.read()
		if encoding != "binary":
			data = data.decode(encoding)
		fd.close()
	except (IOError, UnicodeError) as e:
		raise AwlParserError("Failed to read '%s': %s" %\
			(filename, str(e)))
	return data

def awlFileWrite(filename, data, encoding="latin_1"):
	if encoding != "binary":
		data = "\r\n".join(data.splitlines()) + "\r\n"
	for count in range(1000):
		tmpFile = "%s-%d-%d.tmp" %\
			(filename, random.randint(0, 0xFFFF), count)
		if not os.path.exists(tmpFile):
			break
	else:
		raise AwlParserError("Could not create temporary file")
	try:
		fd = open(tmpFile, "wb")
		if encoding != "binary":
			data = data.encode(encoding)
		fd.write(data)
		fd.flush()
		fd.close()
		if not osIsPosix:
			# Can't use safe rename on non-POSIX.
			# Must unlink first.
			try:
				os.unlink(filename)
			except OSError as e:
				pass
		os.rename(tmpFile, filename)
	except (IOError, OSError, UnicodeError) as e:
		raise AwlParserError("Failed to write file:\n" + str(e))
	finally:
		try:
			os.unlink(tmpFile)
		except (IOError, OSError):
			pass

# Call a callable and suppress all exceptions,
# except for really fatal coding exceptions.
def CALL_NOEX(_callable, *args, **kwargs):
	try:
		return _callable(*args, **kwargs)
	except (SyntaxError, NameError, AttributeError) as e:
		raise
	except ValueError as e:
		import re
		if re.match(r'.*takes exactly \d+ argument \(\d+ given\).*', str(e)) or\
		   re.match(r'.*missing \d+ required positional argument.*', str(e)) or\
		   re.match(r'.*takes \d+ positional argument but \d+ were given.*', str(e)):
			raise
	except Exception as e:
		pass
	return None

def strToBase64(string, ignoreErrors=False):
	"""Convert a string to a base64 encoded ascii string.
	Throws ValueError on errors, if ignoreErrors is False."""

	try:
		b = string.encode("utf-8", "ignore" if ignoreErrors else "strict")
		return base64.b64encode(b).decode("ascii")
	except (UnicodeError, binascii.Error, TypeError) as e:
		if ignoreErrors:
			return ""
		raise ValueError

def base64ToStr(b64String, ignoreErrors=False):
	"""Convert a base64 encoded ascii string to utf-8 string.
	Throws ValueError on errors, if ignoreErrors is False."""

	try:
		b = b64String.encode("ascii",
			"ignore" if ignoreErrors else "strict")
		return base64.b64decode(b).decode("utf-8",
			"ignore" if ignoreErrors else "strict")
	except (UnicodeError, binascii.Error, TypeError) as e:
		if ignoreErrors:
			return ""
		raise ValueError

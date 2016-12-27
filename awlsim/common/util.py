# -*- coding: utf-8 -*-
#
# AWL simulator - common utility functions
#
# Copyright 2012-2016 Michael Buesch <m@bues.ch>
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
import errno
import random
import base64
import binascii
import functools
import itertools


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
		with contextlib.suppress(RuntimeError):
			if stream:
				if cls.prefix:
					stream.write(cls.prefix)
				stream.write(text)
				stream.write("\n")
				stream.flush()

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

def fileExists(filename):
	"""Returns True, if the file exists.
	Returns False, if the file does not exist.
	Returns None, if another error occurred.
	"""
	try:
		os.stat(filename)
	except OSError as e:
		if e.errno == errno.ENOENT:
			return False
		return None
	return True

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
			with contextlib.suppress(OSError):
				os.unlink(filename)
		os.rename(tmpFile, filename)
	except (IOError, OSError, UnicodeError) as e:
		raise AwlParserError("Failed to write file:\n" + str(e))
	finally:
		with contextlib.suppress(IOError, OSError):
			os.unlink(tmpFile)

def str2bool(string, default=False):
	"""Convert a human readable string to a boolean.
	"""
	s = string.lower().strip()
	if s in {"true", "yes", "on", "enable", "enabled"}:
		return True
	if s in {"false", "no", "off", "disable", "disabled"}:
		return False
	try:
		return bool(int(s, 10))
	except ValueError:
		return default

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

def bytesToHexStr(_bytes):
	"""Convert bytes to a hex-string.
	"""
	if _bytes is None:
		return None
	return binascii.b2a_hex(_bytes).decode("ascii")

def envClearLang(env, lang = "C"):
	"""Reset the language settings of an environment dict
	to some expected value and return the result.
	"""
	env = dict(env)
	env["LANG"] = lang
	for i in {"LANGUAGE", "LC_CTYPE", "LC_NUMERIC",
		  "LC_TIME", "LC_COLLATE", "LC_MONETARY",
		  "LC_MESSAGES", "LC_PAPER", "LC_NAME",
		  "LC_ADDRESS", "LC_TELEPHONE", "LC_MEASUREMENT",
		  "LC_IDENTIFICATION",}:
		env.pop(i, None)
	return env

def __isInteger_python2(value):
	return isinstance(value, int) or\
	       isinstance(value, long)

def __isInteger_python3(value):
	return isinstance(value, int)

isInteger = py23(__isInteger_python2,
		 __isInteger_python3)

def __isString_python2(value):
	return isinstance(value, unicode) or\
	       isinstance(value, str)

def __isString_python3(value):
	return isinstance(value, str)

isString = py23(__isString_python2,
		__isString_python3)

def isiterable(obj):
	"""Check if an object is iterable.
	"""
	try:
		iter(obj)
		return True
	except TypeError:
		pass
	return False

def getfirst(iterable, exception=KeyError):
	"""Get the first item from an iterable.
	This also works for generators.
	If the iterable is empty, exception is raised.
	If exception is None, None is returned instead.
	Warning: If iterable is not indexable (for example a set),
		 an arbitrary item is returned instead.
	"""
	try:
		return next(iter(iterable))
	except StopIteration:
		if exception:
			raise exception
		return None

# Get an arbitrary item from an iterable.
# If the iterable is empty, exception is raised.
# If exception is None, None is returned instead.
getany = getfirst

def toList(value):
	"""Returns value, if value is a list.
	Returns a list with the elements of value, if value is a set.
	Returns a list with the elements of value, if value is an iterable, but not a string.
	Otherwise returns a list with value as element.
	"""
	if isinstance(value, list):
		return value
	if isinstance(value, set):
		return sorted(value)
	if not isString(value):
		if isiterable(value):
			return list(value)
	return [ value, ]

class nopContextManager(object):
	"""No-operation context manager.
	"""

	def __enter__(self):
		return None

	def __exit__(self, exctype, excinst, exctb):
		return False
nopContext = nopContextManager()

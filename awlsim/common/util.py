# -*- coding: utf-8 -*-
#
# AWL simulator - common utility functions
#
# Copyright 2012-2017 Michael Buesch <m@bues.ch>
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


__all__ = [
	"functools",
	"itertools",
	"Logging",
	"printDebug",
	"printVerbose",
	"printInfo",
	"printWarning",
	"printError",
	"fileExists",
	"safeFileRead",
	"safeFileWrite",
	"strPartitionFull",
	"str2bool",
	"strToBase64",
	"base64ToStr",
	"bytesToHexStr",
	"toUnixEol",
	"toDosEol",
	"isInteger",
	"isString",
	"strEqual",
	"isiterable",
	"getfirst",
	"getany",
	"toList",
	"toSet",
	"pivotDict",
	"listIndex",
	"listToHumanStr",
	"listExpand",
	"clamp",
	"math_gcd",
	"math_lcm",
	"nopContext",
	"RelPath",
	"shortUUID",
]


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

def safeFileRead(filename):
	try:
		with open(filename, "rb") as fd:
			data = fd.read()
			fd.close()
	except IOError as e:
		raise AwlSimError("Failed to read '%s': %s" %\
			(filename, str(e)))
	return data

def safeFileWrite(filename, data):
	for count in range(1000):
		tmpFile = "%s-%d-%d.tmp" %\
			(filename, random.randint(0, 0xFFFF), count)
		if not os.path.exists(tmpFile):
			break
	else:
		raise AwlSimError("Could not create temporary file")
	try:
		with open(tmpFile, "wb") as fd:
			fd.write(data)
			fd.flush()
			fd.close()
		if not osIsPosix:
			# Can't use safe rename on non-POSIX.
			# Must unlink first.
			with contextlib.suppress(OSError):
				os.unlink(filename)
		os.rename(tmpFile, filename)
	except (IOError, OSError) as e:
		raise AwlSimError("Failed to write file:\n" + str(e))
	finally:
		with contextlib.suppress(IOError, OSError):
			os.unlink(tmpFile)

# Fully partition a string by separator 'sep'.
# Returns a list of strings:
# [ "first-element", sep, "second-element", sep, ... ]
# If 'keepEmpty' is True, empty elements are kept.
def strPartitionFull(string, sep, keepEmpty=True):
	first, ret = True, []
	for elem in string.split(sep):
		if not first:
			ret.append(sep)
		if elem or keepEmpty:
			ret.append(elem)
		first = False
	return ret

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

def toUnixEol(string):
	"""Convert a string to UNIX line endings,
	no matter what line endings (mix) the input string is.
	"""
	return string.replace("\r\n", "\n")\
		     .replace("\r", "\n")

def toDosEol(string):
	"""Convert a string to DOS line endings,
	no matter what line endings (mix) the input string is.
	"""
	return toUnixEol(string).replace("\n", "\r\n")

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

def strEqual(string0, string1, caseSensitive=True):
	"""Compare string0 to string1.
	If caseSensitive is False, case is ignored.
	Returns True, if both strings are equal.
	"""
	if not caseSensitive:
		if hasattr(string0, "casefold"):
			string0, string1 = string0.casefold(), string1.casefold()
		else:
			string0, string1 = string0.lower(), string1.lower()
	return string0 == string1

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
	Returns a list with the elements of value, if value is a frozenset.
	Returns a list with the elements of value, if value is an iterable, but not a string.
	Otherwise returns a list with value as element.
	"""
	if isinstance(value, list):
		return value
	if isinstance(value, set):
		return sorted(value)
	if isinstance(value, frozenset):
		return sorted(value)
	if not isString(value):
		if isiterable(value):
			return list(value)
	return [ value, ]

# Returns value, if value is a set.
# Returns a set, if value is a frozenset.
# Returns a set with the elements of value, if value is a tuple.
# Returns a set with the elements of value, if value is a list.
# Otherwise returns a set with value as single element.
def toSet(value):
	if isinstance(value, set):
		return value
	if isinstance(value, frozenset):
		return set(value)
	if isinstance(value, list) or\
	   isinstance(value, tuple):
		return set(value)
	return { value, }

def pivotDict(inDict):
	outDict = {}
	for key, value in dictItems(inDict):
		if value in outDict:
			raise KeyError("Ambiguous key in pivot dict")
		outDict[value] = key
	return outDict

# Returns the index of a list element, or -1 if not found.
# If translate if not None, it should be a callable that translates
# a list entry. Arguments are index, entry.
def listIndex(_list, value, start=0, stop=-1, translate=None):
	if stop < 0:
		stop = len(_list)
	if translate:
		for i, ent in enumerate(_list[start:stop], start):
			if translate(i, ent) == value:
				return i
		return -1
	try:
		return _list.index(value, start, stop)
	except ValueError:
		return -1

# Convert an integer list to a human readable string.
# Example: [1, 2, 3]  ->  "1, 2 or 3"
def listToHumanStr(lst, lastSep="or"):
	if not lst:
		return ""
	lst = toList(lst)
	string = ", ".join(str(i) for i in lst)
	# Replace last comma with 'lastSep'
	string = string[::-1].replace(",", lastSep[::-1] + " ", 1)[::-1]
	return string

# Expand the elements of a list.
# 'expander' is the expansion callback. 'expander' takes
# one list element as argument. It returns a list.
def listExpand(lst, expander):
	ret = []
	for item in lst:
		ret.extend(expander(item))
	return ret

def clamp(value, minValue, maxValue):
	"""Clamp value to the range minValue-maxValue.
	ValueError is raised, if minValue is bigger than maxValue.
	"""
	if minValue > maxValue:
		raise ValueError
	return max(min(value, maxValue), minValue)

# Get "Greatest Common Divisor"
def math_gcd(*args):
	return reduce(compat_gcd, args)

# Get "Least Common Multiple"
def math_lcm(*args):
	return reduce(lambda x, y: x * y // math_gcd(x, y),
		      args)

class nopContextManager(object):
	"""No-operation context manager.
	"""

	def __enter__(self):
		return None

	def __exit__(self, exctype, excinst, exctb):
		return False
nopContext = nopContextManager()

class RelPath(object):
	def __init__(self, relativeToDir):
		self.__relativeToDir = relativeToDir

	def toRelative(self, path):
		"""Generate an OS-independent relative string from a path."""
		path = os.path.relpath(path, self.__relativeToDir)
		if os.path.splitdrive(path)[0]:
			raise AwlSimError("Failed to strip the drive letter from a path, "
				"because the base and the path don't reside on the "
				"same drive. Please make sure the base and the path "
				"reside on the same drive.\n"
				"Base: %s\n"
				"Path: %s" % (
				self.__relativeToDir, path))
		path = path.replace(os.path.sep, "/")
		return path

	def fromRelative(self, path):
		"""Generate a path from an OS-independent relative string."""
		path = path.replace("/", os.path.sep)
		path = os.path.join(self.__relativeToDir, path)
		return path

def shortUUID(uuidStr):
	"""Shorten an uuid string.
	"""
	uuidStr = str(uuidStr).strip()
	if len(uuidStr) == 36 and\
	   uuidStr[8] == '-' and\
	   uuidStr[13] == '-' and\
	   uuidStr[18] == '-' and\
	   uuidStr[23] == '-':
		uuidStr = uuidStr[0:8] + ".." + uuidStr[-6:-1]
	return uuidStr

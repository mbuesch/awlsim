# -*- coding: utf-8 -*-
#
# AWL simulator - utility functions
#
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
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
from awlsim.core.compat import *

from awlsim.core.exceptions import *
from awlsim.core.enumeration import *

import sys
import os
import random
import struct


class Logging(object):
	EnumGen.start
	LOG_NONE	= EnumGen.item
	LOG_ERROR	= EnumGen.item
	LOG_INFO	= EnumGen.item
	LOG_DEBUG	= EnumGen.item
	EnumGen.end

	_loglevel = LOG_INFO

	@classmethod
	def setLoglevel(cls, loglevel):
		if loglevel not in (cls.LOG_NONE,
				    cls.LOG_ERROR,
				    cls.LOG_INFO,
				    cls.LOG_DEBUG):
			raise AwlSimError("Invalid log level '%d'" % loglevel)
		cls._loglevel = loglevel

	@classmethod
	def getLoglevel(cls):
		return cls._loglevel

	@classmethod
	def printDebug(cls, text):
		if cls._loglevel >= cls.LOG_DEBUG:
			sys.stdout.write(text)
			sys.stdout.write("\n")
			sys.stdout.flush()

	@classmethod
	def printInfo(cls, text):
		if cls._loglevel >= cls.LOG_INFO:
			sys.stdout.write(text)
			sys.stdout.write("\n")
			sys.stdout.flush()

	@classmethod
	def printError(cls, text):
		if cls._loglevel >= cls.LOG_ERROR:
			sys.stderr.write(text)
			sys.stderr.write("\n")
			sys.stderr.flush()

def printDebug(text):
	Logging.printDebug(text)

def printInfo(text):
	Logging.printInfo(text)

def printError(text):
	Logging.printError(text)

# Warning message helper
printWarning = printError

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
		if os.name.lower() != "posix":
			# Can't use safe rename on non-POSIX.
			# Must unlink first.
			os.unlink(filename)
		os.rename(tmpFile, filename)
	except (IOError, OSError, UnicodeError) as e:
		raise AwlParserError("Failed to write file:\n" + str(e))
	finally:
		try:
			os.unlink(tmpFile)
		except (IOError, OSError):
			pass

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
	string = ", ".join(str(i) for i in lst)
	# Replace last comma with 'lastSep'
	string = string[::-1].replace(",", lastSep[::-1] + " ", 1)[::-1]
	return string

def str2bool(string, default=False):
	s = string.lower()
	if s in ("true", "yes", "on", "enable", "enabled"):
		return True
	if s in ("false", "no", "off", "disable", "disabled"):
		return False
	try:
		return bool(int(s, 10))
	except ValueError:
		return default

# Returns value, if value is a list.
# Otherwise returns a list with value as element.
def toList(value):
	if isinstance(value, list):
		return value
	if isinstance(value, tuple):
		return list(value)
	return [ value, ]

def pivotDict(inDict):
	outDict = {}
	for key, value in inDict.items():
		if value in outDict:
			raise KeyError("Ambiguous key in pivot dict")
		outDict[value] = key
	return outDict

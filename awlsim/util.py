# -*- coding: utf-8 -*-
#
# AWL simulator - utility functions
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

import sys
import os
import random
import struct


class AwlSimError(Exception):
	pass

class AwlParserError(Exception):
	pass

# isPyPy is True, if the interpreter is PyPy.
isPyPy = "PyPy" in sys.version

# isPy3Compat is True, if the interpreter is Python 3 compatible.
isPy3Compat = sys.version_info[0] == 3

# isPy2Compat is True, if the interpreter is Python 2 compatible.
isPy2Compat = sys.version_info[0] == 2

# Python 2/3 helper selection
def py23(py2, py3):
	if isPy3Compat:
		return py3
	if isPy2Compat:
		return py2
	raise AwlSimError("Failed to detect Python version")

# Always map input() to text input
if isPy2Compat:
	input = raw_input

# Info message helper
def printInfo(text):
	sys.stdout.write(text)
	sys.stdout.write("\n")
	sys.stdout.flush()

# Error message helper
def printError(text):
	sys.stderr.write(text)
	sys.stderr.write("\n")
	sys.stderr.flush()

# Warning message helper
printWarning = printError

def awlFileRead(filename):
	try:
		fd = open(filename, "rb")
		data = fd.read()
		data = data.decode("latin_1")
		fd.close()
	except (IOError, UnicodeError) as e:
		raise AwlParserError("Failed to read '%s': %s" %\
			(filename, str(e)))
	return data

def awlFileWrite(filename, data):
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
		fd.write(data.encode("latin_1"))
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
def listIndex(_list, value, start=0, stop=-1):
	if stop < 0:
		stop = len(_list)
	try:
		return _list.index(value, start, stop)
	except ValueError:
		return -1

def str2bool(string, default=False):
	s = string.lower()
	if s in ("true", "yes", "on"):
		return True
	if s in ("false", "no", "off"):
		return False
	try:
		return bool(int(s, 10))
	except ValueError:
		return default

# Convert an integer list to a human readable string.
# Example: [1, 2, 3]  ->  "1, 2 or 3"
def intListToHumanStr(ilist, lastSep="or"):
	if not ilist:
		return ""
	string = ", ".join(("%d" % i) for i in ilist)
	# Replace last comma with 'lastSep'
	string = string[::-1].replace(",", lastSep[::-1] + " ", 1)[::-1]
	return string

class EnumerationHelper(object):
	"Enumeration helper"

	def __init__(self):
		self.__num = None

	@property
	def start(self):
		assert(self.__num is None)
		self.__num = 0
		return None

	@start.setter
	def start(self, startNumber):
		assert(self.__num is None)
		self.__num = startNumber

	@property
	def end(self):
		self.__num = None
		return None

	@property
	def item(self):
		number = self.itemNoInc
		self.__num += 1
		return number

	@property
	def itemNoInc(self):
		assert(self.__num is not None)
		return self.__num

	def itemAt(self, number):
		assert(self.__num is not None)
		self.__num = number + 1
		return number

	def __repr__(self):
		return "enum(%s)" % str(self.__num)

enum = EnumerationHelper()

def pivotDict(inDict):
	outDict = {}
	for key, value in inDict.items():
		if value in outDict:
			raise KeyError("Ambiguous key in pivot dict")
		outDict[value] = key
	return outDict

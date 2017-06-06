# -*- coding: utf-8 -*-
#
# AWL simulator - utility functions
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

import sys
import os
import os.path
import time
import fractions
import math
import contextlib


__all__ = [
	"sys",
	"os",
	"contextlib",
	"osIsWindows",
	"osIsPosix",
	"standaloneServerExe",
	"isPyPy",
	"isJython",
	"isIronPython",
	"isCython",
	"isMicroPython",
	"isWinStandalone",
	"isPy3Compat",
	"isPy2Compat",
	"py23",
	"pythonInterpreter",
	"input",
	"range",
	"reduce",
	"queue",
	"monotonic_time",
	"perf_monotonic_time",
	"BlockingIOError",
	"ConnectionError",
	"StringIO",
	"isalnum",
	"isdecimal",
	"compat_gcd",
	"contextlib",
	"dictItems",
	"dictKeys",
	"dictValues",
]


# Convenient operating system identifiers
if os.name == "java":
	import java.lang.System
	__osName = java.lang.System.getProperty("os.name").lower()
	osIsWindows = __osName.startswith("windows")
	osIsPosix = not osIsWindows
else:
	osIsWindows = os.name == "nt" or os.name == "ce"
	osIsPosix = os.name == "posix"

# Executable name of the standalone server.
standaloneServerExe = "awlsim-server-module.exe"

# isPyPy is True, if the interpreter is PyPy.
isPyPy = "PyPy" in sys.version

# isJython is True, if the interpreter is Jython.
isJython = sys.platform.lower().startswith("java")

# isIronPython is True, if the interpreter is IronPython
isIronPython = "IronPython" in sys.version

# isCython is True, if the interpreter is Cython
isCython = False #@nocy
#isCython = True #@cy

# isMicroPython is True, if the interpreter is MicroPython
isMicroPython = hasattr(sys, "implementation") and\
		sys.implementation.name.lower() == "micropython"

# isWinStandalone is True, if this is a Windows standalone package (py2exe/cx_Freeze)
isWinStandalone = osIsWindows and\
		  (sys.executable.endswith("awlsim-gui.exe") or\
		   sys.executable.endswith("awlsim-client.exe") or\
		   sys.executable.endswith("awlsim-server.exe") or\
		   sys.executable.endswith(standaloneServerExe) or\
		   sys.executable.endswith("awlsim-symtab.exe") or\
		   sys.executable.endswith("awlsim-test.exe"))

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
	raise Exception("Failed to detect Python version")

# Python interpreter name, as string.
if isCython:
	pythonInterpreter = "Cython"
elif isPyPy:
	pythonInterpreter = "PyPy"
elif isJython:
	pythonInterpreter = "Jython"
elif isIronPython:
	pythonInterpreter = "IronPython"
elif isMicroPython:
	pythonInterpreter = "MicroPython"
elif isWinStandalone:
	pythonInterpreter = "CPython (frozen)"
else:
	pythonInterpreter = "CPython"

# input() compatibility.
# Force Python3 behavior
if isPy2Compat:
	input = raw_input
else:
	input = input

# range() compatibility.
# Force Python3 behavior
if isPy2Compat:
	range = xrange
else:
	range = range

# reduce() compatibility.
# Force Python2 behavior
if isPy3Compat:
	from functools import reduce
else:
	reduce = reduce

# queue compatibility
# Force Python3 behavior
if isPy2Compat:
	import Queue as queue
else:
	import queue

# Monotonic time. Returns a float second count.
monotonic_time = getattr(time, "monotonic", time.clock)
# Performance counter time (if available).
perf_monotonic_time = getattr(time, "perf_counter", time.time)

# BlockingIOError dummy
try:
	BlockingIOError
except NameError:
	class BlockingIOError(BaseException): pass
BlockingIOError = BlockingIOError

# ConnectionError dummy
try:
	ConnectionError
except NameError:
	ConnectionError = OSError
ConnectionError = ConnectionError

# Import StringIO
if isIronPython and isPy2Compat:
	# Workaround for IronPython's buggy io.StringIO
	from StringIO import StringIO
else:
	from io import StringIO
StringIO = StringIO
from io import BytesIO

# str.isalnum() compatibility
# This defines a global function: isalnum(string) ==> bool
if hasattr(str, "isalnum"):
	isalnum = lambda s: s.isalnum()
else:
	isalnum = lambda s: all(c.isalpha() or c.isdigit() for c in s)

# str.isdecimal() compatibility
# This defines a global function: isdecimal(string) ==> bool
if hasattr(str, "isdecimal"):
	isdecimal = lambda s: s.isdecimal()
else:
	isdecimal = lambda s: all(c in "0123456789" for c in s)

# gcd() compatibility
# This defines a global function: compat_gcd(a, b) ==> int
if hasattr(math, "gcd"):
	compat_gcd = math.gcd
elif hasattr(fractions, "gcd"):
	compat_gcd = fractions.gcd
else:
	def compat_gcd(a, b):
		while b:
			(a, b) = (b, a % b)
		return a

# contextlib.suppress compatibility
if not hasattr(contextlib, "suppress"):
	class _suppress(object):
		def __init__(self, *excs):
			self._excs = excs
		def __enter__(self):
			pass
		def __exit__(self, exctype, excinst, exctb):
			return exctype is not None and issubclass(exctype, self._excs)
	contextlib.suppress = _suppress

# Dict items(), keys(), values() compatibility.
# Use Python3 behavior.
dictItems = py23(lambda d: d.viewitems(),
		 lambda d: d.items())
dictKeys = py23(lambda d: d.viewkeys(),
		lambda d: d.keys())
dictValues = py23(lambda d: d.viewvalues(),
		  lambda d: d.values())

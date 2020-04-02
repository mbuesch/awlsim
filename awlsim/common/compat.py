# -*- coding: utf-8 -*-
#
# AWL simulator - Python interpreter compatibility
#
# Copyright 2012-2020 Michael Buesch <m@bues.ch>
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

import contextlib
import fractions
import functools
import math
import os
import os.path # micropython needs explicit import of os.path
import re
import select
import socket
import sys
import time


__all__ = [
	"sys",
	"os",
	"contextlib",
	"osIsWindows",
	"osIsPosix",
	"osIsLinux",
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
	"BlockingIOError",
	"IOError",
	"ConnectionError",
	"StringIO",
	"isalnum",
	"isdecimal",
	"compat_gcd",
	"dictItems",
	"dictKeys",
	"dictValues",
	"bit_length",
	"excErrno",
]


# Convenient operating system identifiers
if os.name == "java": #@nocov
	import java.lang.System
	__osName = java.lang.System.getProperty("os.name").lower()
	osIsWindows = __osName.startswith("windows")
	osIsPosix = not osIsWindows
else: #@nocov
	osIsWindows = os.name == "nt" or os.name == "ce"
	osIsPosix = os.name == "posix"
osIsLinux = osIsPosix and "linux" in sys.platform.lower()

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
def py23(py2, py3): #@nocov
	if isPy3Compat:
		return py3
	if isPy2Compat:
		return py2
	raise Exception("Failed to detect Python version") #@nocov

# Python interpreter name, as string.
if isCython:
	pythonInterpreter = "Cython"			#@nocov
elif isPyPy:
	pythonInterpreter = "PyPy"			#@nocov
elif isJython:
	pythonInterpreter = "Jython"			#@nocov
elif isIronPython:
	pythonInterpreter = "IronPython"		#@nocov
elif isMicroPython:
	pythonInterpreter = "MicroPython"		#@nocov
elif isWinStandalone:
	pythonInterpreter = "CPython (frozen)"		#@nocov
else:
	pythonInterpreter = "CPython"			#@nocov

# input() compatibility.
# Force Python3 behavior
if isPy2Compat: #@nocov
	input = raw_input
else: #@nocov
	input = input

# range() compatibility.
# Force Python3 behavior
if isPy2Compat: #@nocov
	range = xrange
else: #@nocov
	range = range

# reduce() compatibility.
# Force Python2 behavior
if isPy3Compat: #@nocov
	from functools import reduce
else: #@nocov
	reduce = reduce

# queue compatibility
# Force Python3 behavior
if isPy2Compat: #@nocov
	import Queue as queue
else: #@nocov
	import queue

# BlockingIOError dummy
try: #@nocov
	BlockingIOError
except NameError: #@nocov
	class BlockingIOError(BaseException): pass
BlockingIOError = BlockingIOError

# IOError dummy
try: #@nocov
	IOError
except NameError: #@nocov
	IOError = OSError
IOError = IOError

# ConnectionError dummy
try: #@nocov
	ConnectionError
except NameError: #@nocov
	ConnectionError = OSError
ConnectionError = ConnectionError

# Import StringIO
if isIronPython and isPy2Compat: #@nocov
	# Workaround for IronPython's buggy io.StringIO
	from StringIO import StringIO
else: #@nocov
	from io import StringIO
StringIO = StringIO
from io import BytesIO

# str.isalnum() compatibility
# This defines a global function: isalnum(string) ==> bool
if hasattr(str, "isalnum"): #@nocov
	isalnum = lambda s: s.isalnum()
else: #@nocov
	isalnum = lambda s: all(c.isalpha() or c.isdigit() for c in s)

# str.isdecimal() compatibility
# This defines a global function: isdecimal(string) ==> bool
if hasattr(str, "isdecimal"): #@nocov
	isdecimal = lambda s: s.isdecimal()
else: #@nocov
	isdecimal = lambda s: all(c in "0123456789" for c in s)

# gcd() compatibility
# This defines a global function: compat_gcd(a, b) ==> int
if hasattr(math, "gcd"): #@nocov
	compat_gcd = math.gcd
elif hasattr(fractions, "gcd"): #@nocov
	compat_gcd = fractions.gcd
else: #@nocov
	def compat_gcd(a, b):
		while b:
			(a, b) = (b, a % b)
		return a

# contextlib.suppress compatibility
if not hasattr(contextlib, "suppress"): #@nocov
	class _suppress(object):
		def __init__(self, *excs):
			self._excs = excs
		def __enter__(self):
			pass
		def __exit__(self, exctype, excinst, exctb):
			return exctype is not None and issubclass(exctype, self._excs)
	contextlib.suppress = _suppress

# contextlib.nullcontext compatibility
if not hasattr(contextlib, "nullcontext"): #@nocov
	class _nullcontext(object):
		def __init__(self, enter_result=None):
			self.enter_result = enter_result
		def __enter__(self):
			return self.enter_result
		def __exit__(self, *unused):
			pass
	contextlib.nullcontext = _nullcontext

# Dict items(), keys(), values() compatibility.
# Use Python3 behavior.
dictItems = py23(lambda d: d.viewitems(),
		 lambda d: d.items())
dictKeys = py23(lambda d: d.viewkeys(),
		lambda d: d.keys())
dictValues = py23(lambda d: d.viewvalues(),
		  lambda d: d.values())

# select.select substitute
# Micropython doesn't have select.select.
if not hasattr(select, "select"): #@nocov
	select.select = None # Dummy

# Python 2 compat: log2
if not hasattr(math, "log2"): #@nocov
	math.log2 = lambda x: math.log(x, 2)

# Python 2 compat: isfinite
if not hasattr(math, "isfinite"): #@nocov
	math.isfinite = lambda x: not math.isnan(x) and not math.isinf(x)

# int.bit_length substitute
# Micropython doesn't have int.bit_length.
def bit_length(value): #@nocov
	assert isinstance(value, (int, long) if isPy2Compat else int)
	if hasattr(value, "bit_length"):
		return value.bit_length()
	return int(math.ceil(math.log2(value)))

# functools.cmp_to_key substitute
# Micropython doesn't have functools.cmp_to_key.
if not hasattr(functools, "cmp_to_key"): #@nocov
	def cmp_to_key(f):
		class Key(object):
			__hash__ = None
			def __init__(s, x): s.x = x
			def __eq__(s, o): return f(s.x, o.x) == 0
			def __lt__(s, o): return f(s.x, o.x) < 0
			def __ge__(s, o): return f(s.x, o.x) >= 0
			def __gt__(s, o): return f(s.x, o.x) > 0
			def __le__(s, o): return f(s.x, o.x) <= 0
		return Key
	functools.cmp_to_key = cmp_to_key

# functools.lru_cache substitute
# Python2 does not have functools.lru_cache.
if not hasattr(functools, "lru_cache"): #@nocov
	def _no_lru_cache(*a, **k):
		def decorator(f):
			def wrapper(*aa, **kk):
				return f(*aa, **kk)
			return wrapper
		return decorator
	functools.lru_cache = _no_lru_cache

# socket.AF_UNSPEC substitute
# Micropython doesn't have socket.AF_UNSPEC.
if not hasattr(socket, "AF_UNSPEC"): #@nocov
	socket.AF_UNSPEC = 0

# socket.timeout substitute
# Micropython doesn't have socket.timeout.
if not hasattr(socket, "timeout"): #@nocov
	socket.timeout = OSError

# OSError.errno substitute
# Micropython doesn't have OSError.errno.
def excErrno(exc):
	if hasattr(exc, "errno"):
		return exc.errno
	if isMicroPython and isinstance(exc, OSError):
		m = re.match(r"\[Errno (\d+)\]", str(exc))
		if m:
			return int(m.group(1))
	return -1

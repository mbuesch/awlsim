# -*- coding: utf-8 -*-
#
# AWL simulator - Monotonic timer
#
# Copyright 2018 Michael Buesch <m@bues.ch>
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
#from awlsim.common.cython_support cimport * #@cy
from awlsim.common.compat import *

from awlsim.common.util import *

import time


__all__ = [
	"monotonic_time",
]


class _MONOTONIC_RAW_factory(object): #+cdef
	"""CLOCK_MONOTONIC_RAW wrapper base class.
	"""

	def probe(self):
		"""Probe this timer.
		Returns True, if this timer works correctly.
		"""
		raise NotImplementedError

	def monotonic_raw(self):
		"""Returns the timer as float.
		"""
		raise NotImplementedError

	def _sanityCheck(self):
		"""Check if CLOCK_MONOTONIC_RAW works correctly.
		"""
		try:
			a = self.monotonic_raw()
			time.sleep(1e-3)
			b = self.monotonic_raw()
			if b - a <= 0.0 or b - a > 1.0:
				raise RuntimeError
		except Exception as e: #@nocov
			return False
		return True

class _MONOTONIC_RAW_timemodule_factory(_MONOTONIC_RAW_factory): #+cdef
	"""CLOCK_MONOTONIC_RAW time module wrapper.
	"""

	def probe(self):
		if not hasattr(time, "clock_gettime") or\
		   not hasattr(time, "CLOCK_MONOTONIC_RAW"):
			return False #@nocov

		self.__clock_gettime = time.clock_gettime
		self.__id_CLOCK_MONOTONIC_RAW = time.CLOCK_MONOTONIC_RAW

		if not self._sanityCheck(): #@nocov
			printWarning("CLOCK_MONOTONIC_RAW (time module) does not work "
				     "correctly on this system. Falling "
				     "back to an alternative.")
			return False
		return True

	def monotonic_raw(self):
		return self.__clock_gettime(self.__id_CLOCK_MONOTONIC_RAW)

class _MONOTONIC_RAW_CFFI_factory(_MONOTONIC_RAW_factory): #+cdef
	"""CLOCK_MONOTONIC_RAW CFFI wrapper.
	"""

	def probe(self):
		if not osIsLinux:
			printInfo("CLOCK_MONOTONIC_RAW is only available on Linux.")
			return False

		try:
			from cffi import FFI
		except ImportError as e:
			if not isMicroPython:
				printWarning("Failed to import CFFI: %s\n"
					     "Cannot use CLOCK_MONOTONIC_RAW via CFFI." % (
					     str(e)))
			return False

		self.__id_CLOCK_MONOTONIC_RAW = 4

		self.__ffi = FFI()
		# Use getattr to avoid Cython cdef compile error.
		getattr(self.__ffi, "cdef")("""
			typedef int clockid_t;
			struct timespec {
				long tv_sec;
				long tv_nsec;
			};
			int clock_gettime(clockid_t clk_id, struct timespec *tp);
		""")
		self.__c = self.__ffi.dlopen(None)
		self.__ts = self.__ffi.new("struct timespec *")

		if not self._sanityCheck():
			printWarning("CLOCK_MONOTONIC_RAW (CFFI) does not work "
				     "correctly on this system. Falling "
				     "back to an alternative.")
			return False
		return True

	def monotonic_raw(self):
		ts = self.__ts
		if self.__c.clock_gettime(self.__id_CLOCK_MONOTONIC_RAW, ts):
			raise OSError("CLOCK_MONOTONIC_RAW failed.")
		return float(ts.tv_sec) + (float(ts.tv_nsec) / 1e9)

def _monotonic_time_init():
	"""Initialize _monotonicTimeHandler.
	This will be called on the first call to monotonic_time().
	"""
	global _monotonicTimeHandler

	# Probe time.clock_gettime(CLOCK_MONOTONIC_RAW)
	factory = _MONOTONIC_RAW_timemodule_factory()
	if factory.probe():
		printVerbose("Using CLOCK_MONOTONIC_RAW (time module) as monotonic timer.")
		_monotonicTimeHandler = factory.monotonic_raw
		return _monotonicTimeHandler()

	# Probe CFFI clock_gettime(CLOCK_MONOTONIC_RAW)
	factory = _MONOTONIC_RAW_CFFI_factory()
	if factory.probe():
		printVerbose("Using CLOCK_MONOTONIC_RAW (CFFI) as monotonic timer.")
		_monotonicTimeHandler = factory.monotonic_raw
		return _monotonicTimeHandler()

	# Probe time.perf_counter
	_monotonicTimeHandler = getattr(time, "perf_counter", None)
	if _monotonicTimeHandler:
		printInfo("Using time.perf_counter() as monotonic timer.")
		return _monotonicTimeHandler()

	# Probe time.monotonic
	_monotonicTimeHandler = getattr(time, "monotonic", None)
	if _monotonicTimeHandler:
		printInfo("Using time.monotonic() as monotonic timer.")
		return _monotonicTimeHandler()

	# Out of luck. Use non-monotonic time.time
	printWarning("Falling back to non-monotonic time.time() timer.")
	_monotonicTimeHandler = time.time
	return _monotonicTimeHandler()

#cdef object _monotonicTimeHandler #@cy
_monotonicTimeHandler = _monotonic_time_init

#cdef double _prevMonotonicTime #@cy
_prevMonotonicTime = 0.0

# Get a monotonic time count, as float second count.
# The reference is undefined, so this can only be used for relative times.
def monotonic_time(): #@nocy
#cdef double monotonic_time(): #@cy
#@cy	cdef double t
	global _monotonicTimeHandler
	global _prevMonotonicTime

	try:
		t = _prevMonotonicTime = _monotonicTimeHandler()
	except Exception as e: #@nocov
		t = _prevMonotonicTime
	return t

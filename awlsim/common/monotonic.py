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
from awlsim.common.compat import *

from awlsim.common.util import *

from cffi import FFI
import time


__all__ = [
	"monotonic_time",
]


class _monotonic_raw_factory(object): #+cdef
	"""CLOCK_MONOTONIC_RAW CFFI wrapper.
	"""

	def make(self):
		"""Returns the CLOCK_MONOTONIC_RAW function
		or None on failure.
		"""
		if not osIsLinux:
			printInfo("CLOCK_MONOTONIC_RAW is only available on Linux.")
			return None

		self.__id_CLOCK_MONOTONIC_RAW = 4

		self.__ffi = FFI()
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
		self.__previous = -1.0

		# Sanity check
		try:
			a = self.__monotonic_raw()
			time.sleep(1e-3)
			b = self.__monotonic_raw()
			if a < 0.0 or b < 0.0 or\
			   b - a <= 0.0 or b - a > 1.0:
				raise RuntimeError
		except Exception as e:
			printWarning("CLOCK_MONOTONIC_RAW does not work "
				     "correctly on this system. Falling "
				     "back to an alternative.")
			return None

		return self.__monotonic_raw

	def __monotonic_raw(self):
#@cy		cdef double t

		ts = self.__ts
		if self.__c.clock_gettime(self.__id_CLOCK_MONOTONIC_RAW, ts):
			printError("CLOCK_MONOTONIC_RAW failed.")
			t = self.__previous
		else:
			self.__previous = t = float(ts.tv_sec) + (float(ts.tv_nsec) / 1e9)
		return t

def _monotonic_time_init():
	"""Initialize _monotonic_time_handler.
	This will be called on the first call to monotonic_time().
	"""
	global _monotonic_time_handler

	_monotonic_time_handler = _monotonic_raw_factory().make()
	if _monotonic_time_handler:
		printVerbose("Using CLOCK_MONOTONIC_RAW as monotonic timer.")
		return _monotonic_time_handler()

	_monotonic_time_handler = getattr(time, "perf_counter", None)
	if _monotonic_time_handler:
		printInfo("Using time.perf_counter() as monotonic timer.")
		return _monotonic_time_handler()

	_monotonic_time_handler = getattr(time, "monotonic", None)
	if _monotonic_time_handler:
		printInfo("Using time.monotonic() as monotonic timer.")
		return _monotonic_time_handler()

	printWarning("Falling back to non-monotonic time.time() timer.")
	_monotonic_time_handler = time.time
	return _monotonic_time_handler()

_monotonic_time_handler = _monotonic_time_init

# Get a monotonic time count, as float second count.
# The zero reference is undefined.
def monotonic_time(): #@nocy
#cdef double monotonic_time(): #@cy
	global _monotonic_time_handler
	return _monotonic_time_handler()

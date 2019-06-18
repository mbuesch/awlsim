# -*- coding: utf-8 -*-
#
# AWL simulator - mlock support
#
# Copyright 2019 Michael Buesch <m@bues.ch>
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
from awlsim.common.env import *
from awlsim.common.exceptions import *

import platform
import os


__all__ = [
	"MLockWrapper",
	"AwlSimMLock",
]


class MLockWrapper(object):
	"""OS mlock wrapper.
	"""

	singleton = None

	if platform.machine().lower() in (
			"alpha",
			"ppc", "ppc64", "ppcle", "ppc64le",
			"sparc", "sparc64" ):
		MCL_CURRENT	= 0x2000
		MCL_FUTURE	= 0x4000
		MCL_ONFAULT	= 0x8000
	else:
		MCL_CURRENT	= 0x1
		MCL_FUTURE	= 0x2
		MCL_ONFAULT	= 0x4

	def __init__(self):
		self.__ffi = None
		self.__libc = None

		if not osIsLinux:
			printDebug("mlock() is only available on Linux.")
			return

		try:
			from cffi import FFI
		except ImportError as e:
			printWarning("Failed to import CFFI: %s\n"
				     "Cannot use mlock() via CFFI." % (
				     str(e)))
			return

		self.__ffi = FFI()
		# Use getattr to avoid Cython cdef compile error.
		getattr(self.__ffi, "cdef")("""
			int mlock(const void *addr, size_t len);
			int mlock2(const void *addr, size_t len, int flags);
			int munlock(const void *addr, size_t len);
			int mlockall(int flags);
			int munlockall(void);
		""")
		self.__libc = self.__ffi.dlopen(None)

	@classmethod
	def get(cls):
		s = cls.singleton
		if not s:
			s = cls.singleton = cls()
		return s

	@classmethod
	def mlockall(cls, flags):
		error = "mlockall() is not supported on this operating system."
		s = cls.get()
		if s.__libc:
			ret = s.__libc.mlockall(flags)
			printDebug("mlockall(%X) = %d" % (flags, ret))
			error = os.strerror(s.__ffi.errno) if ret else ""
		return error

	@classmethod
	def munlockall(cls):
		error = "munlockall() is not supported on this operating system."
		s = cls.get()
		if s.__libc:
			ret = s.__libc.munlockall()
			printDebug("munlockall() = %d" % (ret, ))
			error = os.strerror(s.__ffi.errno) if ret else ""
		return error

class AwlSimMLock(MLockWrapper):
	"""Awlsim memory locking handler.
	"""

	@classmethod
	def lockMemory(cls, lock=True):
		mlockMode = AwlSimEnv.getMLock()
		if mlockMode == AwlSimEnv.MLOCK_OFF:
			pass # Do nothing.
		elif mlockMode in (AwlSimEnv.MLOCK_ALL,
				   AwlSimEnv.MLOCK_FORCEALL):
			if lock:
				flags = cls.MCL_CURRENT | cls.MCL_FUTURE
				error = cls.mlockall(flags)
				if error:
					msg = ("Failed to mlockall(): %s. "
					       "Check AWLSIM_MLOCK environment variable.") % error
					if mlockMode == AwlSimEnv.MLOCK_FORCEALL:
						raise AwlSimError(msg)
					printError(msg)
			else:
				cls.munlockall()
		else:
			assert(0)

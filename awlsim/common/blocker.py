# -*- coding: utf-8 -*-
#
# AWL simulator - 'with'-statement based single threaded action blocker
#
# Copyright 2014 Michael Buesch <m@bues.ch>
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


__all__ = [
	"Blocker",
]


class Blocker(object):
	"""'with'-statement based single threaded blocker.
	This is _not_ a multi-thread lock."""

	def __init__(self, initialCount = 0):
		self.__count = initialCount
		assert(self.__count >= 0)

	def __enter__(self):
		"""Enter the blocking context."""
		assert(self.__count >= 0)
		self.__count += 1

	def __exit__(self, exc_type, exc_value, traceback):
		"""Exit the blocking context."""
		self.__count -= 1
		assert(self.__count >= 0)

	def __bool__(self):
		"""Returns 'True', if the action is blocked."""
		return self.__count > 0

	__nonzero__ = __bool__ # Python 2 compat

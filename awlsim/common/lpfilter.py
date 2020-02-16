# -*- coding: utf-8 -*-
#
# AWL simulator - Low pass filter
#
# Copyright 2020 Michael Buesch <m@bues.ch>
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

#cimport cython #@cy

from math import isfinite #@nocy
#from libc.math cimport isfinite #@cy


class LPFilter(object): #+cdef
	"""Low pass filter.
	"""

	__slots__ = (
		"__div",
		"__state",
		"__initial",
	)

	def __init__(self, div, state=0.0):
		self.__div = float(div)
		if self.__div <= 0.0:
			self.__div = 1.0
		self.__initial = float(state)
		self.reset()

	def reset(self): #@nocy
#@cy	cdef void reset(self):
		self.__state = self.__initial

	def run(self, value): #@nocy
#@cy	@cython.cdivision(True)
#@cy	cdef double run(self, double value):
#@cy		cdef double div
#@cy		cdef double state
#@cy		cdef double newState

		div = self.__div
		state = self.__state
		newState = (state - (state / div)) + value
		if not isfinite(newState):
			newState = state
		self.__state = newState
		return newState / div

# -*- coding: utf-8 -*-
#
# AWL simulator - Generic moving average
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

from awlsim.common.datatypehelpers import * #+cimport
from awlsim.common.exceptions import *

#from cpython.mem cimport PyMem_Malloc, PyMem_Free #@cy

#cimport cython #@cy


__all__ = [
	"MovingAvg",
]


class MovingAvg(object): #+cdef
	__slots__ = (
		"__size",
		"__items",
		"__nrItems",
		"__beginPtr",
		"__endPtr",
		"__avgSum",
	)

	def __init__(self, size):
		if size <= 0:
			raise AwlSimError("MovingAvg: Invalid size")
		self.__size = size
		self.__items = [0.0] * self.__size #@nocy
#@cy		self.__items = <double *>PyMem_Malloc(self.__size * sizeof(double))
#@cy		if not self.__items:
#@cy			raise AwlSimError("MovingAvg: Out of memory")
		self.__nrItems = 0
		self.__beginPtr = 0
		self.__endPtr = 0
		self.__avgSum = 0

#@cy	def __dealloc__(self):
#@cy		PyMem_Free(self.__items)
#@cy		self.__items = NULL

	def calculate(self, value): #@nocy
#@cy	@cython.cdivision(True)
#@cy	cdef double calculate(self, double value):
#@cy		cdef uint32_t size
#@cy		cdef uint32_t nrItems
#@cy		cdef uint32_t endPtr
#@cy		cdef uint32_t beginPtr
#@cy		cdef double first
#@cy		cdef double avgSum

		size = self.__size
		nrItems = self.__nrItems

		if nrItems >= size: #+likely
			# Get and remove the first element from the list.
			beginPtr = self.__beginPtr
			first = self.__items[beginPtr]
			beginPtr += 1
			if beginPtr >= size:
				beginPtr = 0
			self.__beginPtr = beginPtr

		# Append the new value to the list.
		endPtr = self.__endPtr
		self.__items[endPtr] = value
		endPtr += 1
		if endPtr >= size:
			endPtr = 0
		self.__endPtr = endPtr

		avgSum = self.__avgSum
		if nrItems >= size: #+likely
			# Subtract the removed value from the sum
			# and add the new value.
			avgSum -= first
			avgSum += value
		else:
			# The list is not fully populated, yet.
			avgSum += value
			self.__nrItems = nrItems = nrItems + 1
		self.__avgSum = avgSum

		return avgSum / nrItems

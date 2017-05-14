# -*- coding: utf-8 -*-
#
# AWL simulator - L-stack handling
#
# Copyright 2014-2017 Michael Buesch <m@bues.ch>
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

from awlsim.common.exceptions import *
from awlsim.common.datatypehelpers import * #+cimport
from awlsim.common.util import *

from awlsim.core.datatypes import *
from awlsim.core.memory import * #+cimport
from awlsim.core.offset import * #+cimport


class LStackAllocator(object): #+cdef
	"""Memory allocator for the L-stack
	"""

	def __init__(self, maxSize): #@nocy
#@cy	def __init__(self, uint32_t maxSize):
		# maxSize -> max size of the L-stack, in bytes.
		self.localdata = AwlMemory(maxSize)
		self.reset(maxSize)

	# Reset all allocations on the L-stack.
	# Sets the maximum possible allocation to maxAllocBytes.
	# maxAllocBytes must be smaller or equal to self.localdata size.
	def reset(self, maxAllocBytes, curAllocBytes=0): #@nocy
#@cy	cdef reset(self, uint32_t maxAllocBytes, uint32_t curAllocBytes=0):
		self.__maxAllocBytes = maxAllocBytes
		self.__curAllocBytes = curAllocBytes
		self.__curAllocBits = 0

	# Allocate a number of bits on the L-stack.
	# Returns an AwlOffset as the offset the bits are allocated on.
	def alloc(self, nrBits): #@nocy
#@cy	cdef AwlOffset alloc(self, uint32_t nrBits):
#@cy		cdef uint32_t curAllocBytes
#@cy		cdef uint32_t curAllocBits
#@cy		cdef uint32_t nrBytes
#@cy		cdef AwlOffset offset

		curAllocBytes, curAllocBits =\
			self.__curAllocBytes, self.__curAllocBits

		if nrBits == 1:
			# Bit-aligned allocation
			offset = AwlOffset(curAllocBytes,
					   curAllocBits)
			curAllocBits += 1
			if curAllocBits >= 8:
				curAllocBytes += 1
				curAllocBits = 0
		else:
			# Byte-aligned allocation
			if curAllocBits > 0:
				curAllocBytes += 1
				curAllocBits = 0
			nrBytes = intDivRoundUp(nrBits, 8)
			offset = AwlOffset(curAllocBytes, 0)
			curAllocBytes += nrBytes

		if curAllocBytes >= self.__maxAllocBytes:
			raise AwlSimError(
				"Cannot allocate another %d bits on L-stack. "
				"The L-stack is exhausted." %\
				nrBits)

		self.__curAllocBytes, self.__curAllocBits =\
			curAllocBytes, curAllocBits
		return offset

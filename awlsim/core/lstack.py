# -*- coding: utf-8 -*-
#
# AWL simulator - L-stack handling
#
# Copyright 2014-2018 Michael Buesch <m@bues.ch>
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

from awlsim.common.exceptions import *
from awlsim.common.datatypehelpers import * #+cimport
from awlsim.common.util import *

from awlsim.core.datatypes import *
from awlsim.core.memory import * #+cimport
from awlsim.core.offset import * #+cimport

#from libc.stdlib cimport abort #@cy
#from cpython.mem cimport PyMem_Malloc, PyMem_Free #@cy


class LStackFrame(object):		#@nocy
	offset = None			#@nocy
	allocBits = 0			#@nocy
	prevFrame = None		#@nocy

class LStackAllocator(object): #+cdef
	"""Memory allocator for the L-stack.
	This class manages the L-stack of one OB instance.
	"""

	__frameFreeSet = set() #@nocy

#@cy	def __dealloc__(self):
#@cy		cdef LStackFrame *frame
#@cy		cdef LStackFrame *oldFrame
#@cy		frame = self.topFrame
#@cy		while frame:
#@cy			oldFrame = frame
#@cy			frame = frame.prevFrame
#@cy			PyMem_Free(oldFrame)

	def __init__(self, maxSize): #@nocy
#@cy	def __init__(self, uint32_t maxSize):
		# maxSize -> max size of the L-stack, in bytes.

		self.topFrame = None #+NoneToNULL
		self.resize(maxSize)

	# Reset all allocations on the L-stack.
	# Sets the maximum possible allocation to maxAllocBytes.
	# maxAllocBytes must be smaller or equal to self.memory size.
	def resize(self, maxAllocBytes): #@nocy
#@cy	cdef resize(self, uint32_t maxAllocBytes):
		self.memory = AwlMemory(maxAllocBytes)
		self.maxAllocBits = maxAllocBytes * 8

	def reset(self): #@nocy
#@cy	cdef void reset(self):
#@cy		cdef LStackFrame *frame
#@cy		cdef LStackFrame *oldFrame

		self.globAllocBits = 0

		frame = self.topFrame
		while frame:
			oldFrame = frame
			self.topFrame = frame = frame.prevFrame

			oldFrame.prevFrame = None		#+NoneToNULL
			self.__frameFreeSet.add(oldFrame)	#@nocy
#@cy			PyMem_Free(oldFrame)

	def enterStackFrame(self): #@nocy
#@cy	cdef void enterStackFrame(self):
#@cy		cdef LStackFrame *frame
#@cy		cdef uint32_t globAllocBits
#@cy		cdef uint32_t prevAllocBits

		prevAllocBits = self.globAllocBits
		self.globAllocBits = globAllocBits = (((prevAllocBits + 7) >> 3) << 3)	#+suffix-u
		globAllocBytes = globAllocBits // 8					#+suffix-u

		# Allocate a new stack frame.
		try:						#@nocy
			frame = self.__frameFreeSet.pop()	#@nocy
		except KeyError:				#@nocy
			frame = LStackFrame()			#@nocy
#@cy		frame = <LStackFrame *>PyMem_Malloc(sizeof(LStackFrame))
#@cy		if frame == NULL:
#@cy			printError("enterStackFrame: Out of memory")
#@cy			abort()

		frame.byteOffset = globAllocBytes
		# Account the rounded-up bits to the new frame.
		frame.allocBits = globAllocBits - prevAllocBits

		frame.prevFrame = self.topFrame
		self.topFrame = frame
		self.topFrameOffset = make_AwlOffset(globAllocBytes, 0)

	def exitStackFrame(self): #@nocy
#@cy	cdef void exitStackFrame(self):
#@cy		cdef LStackFrame *frame
#@cy		cdef LStackFrame *topFrame
#@cy		cdef uint32_t globAllocBits

		frame = self.topFrame
		topFrame = self.topFrame = frame.prevFrame

		self.globAllocBits = globAllocBits = self.globAllocBits - frame.allocBits
		if topFrame:
			self.topFrameOffset = make_AwlOffset_fromLongBitOffset(
					globAllocBits - topFrame.allocBits)
		else:
			self.topFrameOffset = make_AwlOffset(0, 0)

		frame.prevFrame = None		#+NoneToNULL
		self.__frameFreeSet.add(frame)	#@nocy
#@cy		PyMem_Free(frame)

	# Allocate a number of bits on the L-stack.
	# Returns an AwlOffset as the offset the bits are allocated on.
	def alloc(self, nrBits): #@nocy
#@cy	cdef AwlOffset alloc(self, uint32_t nrBits):
#@cy		cdef LStackFrame *frame
#@cy		cdef uint32_t globAllocBits
#@cy		cdef uint32_t roundBits
#@cy		cdef AwlOffset offset

		frame = self.topFrame
		globAllocBits = self.globAllocBits

		# Calculate the number of bits to actually allocate and
		# calculate the AwlOffset to this allocation.
		roundBits = 0
		if nrBits == 1:
			# Bit-aligned allocation
			offset = make_AwlOffset(globAllocBits // 8 - frame.byteOffset,	#+suffix-u
						globAllocBits % 8)			#+suffix-u
		else:
			# Byte-aligned allocation
			if globAllocBits & 7:						#+suffix-u
				# Round up to the next byte boundary.
				roundBits = 8 - (globAllocBits & 7)			#+suffix-u
				globAllocBits += roundBits
			offset = make_AwlOffset(globAllocBits // 8 - frame.byteOffset,	#+suffix-u
						0)
		globAllocBits += nrBits

		if (((globAllocBits + 7) >> 3) << 3) >= self.maxAllocBits:		#+suffix-u
			raise AwlSimError(
				"Cannot allocate another %d+%d bits on the L-stack. "
				"The L-stack is exhausted. Maximum size = %d bits." % (
				nrBits, roundBits, self.maxAllocBits))

		# Actually allocate the bits.
		self.globAllocBits = globAllocBits
		frame.allocBits += nrBits + roundBits

		return offset

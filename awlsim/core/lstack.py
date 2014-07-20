# -*- coding: utf-8 -*-
#
# AWL simulator - L-stack handling
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
from awlsim.core.compat import *

from awlsim.core.util import *
from awlsim.core.datatypes import *


class LStackAllocator(object):
	"Memory allocator for the L-stack"

	def __init__(self, size):
		# size -> size of the L-stack, in bytes.
		self.localdata = ByteArray(size)

		# 'allocation' is the current number of allocated bytes
		self.allocation = 0

	# Allocate a number of bits on the L-stack.
	# Returns an AwlOffset as the offset the bits are allocated on.
	def alloc(self, nrBits):
		#FIXME handle alignment.
		#      For now we just alloc unaligned full bytes.
		nrBytes = intDivRoundUp(nrBits, 8)

		#FIXME honor direct L-stack accesses in the code
		#      and adjust the offset accordingly.
		offset = self.allocation
		self.allocation += nrBytes
		if self.allocation >= len(self.localdata):
			raise AwlSimError("Cannot allocate data on L-stack: "
				"overflow")
		return AwlOffset(offset)

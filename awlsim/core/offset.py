# -*- coding: utf-8 -*-
#
# AWL data offset
#
# Copyright 2012-2018 Michael Buesch <m@bues.ch>
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
from awlsim.common.util import *

#cimport cython #@cy


__all__ = [ "AwlOffset",
	    "make_AwlOffset",
	    "make_AwlOffset_fromPointerValue",
	    "make_AwlOffset_fromLongBitOffset",
]


class AwlOffset(object): #+cdef
	"""Memory area offset
	"""

	# A DB-number for fully qualified access, or -1.
	dbNumber = -1 #@nocy

	# A symbolic DB-name for fully qualified access, or None.
	dbName = None #@nocy

	# An AwlDataIdentChain, or None.
	# Used for fully qualified (DBx.VAR) or named local (#VAR)
	# global symbolic ("VAR") accesses.
	# For global symbols the chain only has one element.
	identChain = None #@nocy

	# A (S)FB-number for multi-instance calls, or -1.
	fbNumber = -1 #@nocy

	# Additional sub-offset that is added to this offset, or None.
	# This is used for arrays and structs.
	subOffset = None #@nocy

	def __eq__(self, other): #@nocy
#@cy	cpdef __eq(self, object other):
		"""Equality operator.
		This does only compare byte and bit offset and
		does _not_ check dynAttrs.
		"""
		return (self is other) or (\
			isinstance(other, AwlOffset) and\
			self.byteOffset == other.byteOffset and\
			self.bitOffset == other.bitOffset\
		)

#@cy	def __richcmp__(self, object other, int op):
#@cy		if op == 2: # __eq__
#@cy			return self.__eq(other)
#@cy		elif op == 3: # __ne__
#@cy			return not self.__eq(other)
#@cy		return False

	def __ne__(self, other):		#@nocy
		return not self.__eq__(other)	#@nocy

	def dup(self): #@nocy
#@cy	cpdef AwlOffset dup(self):
#@cy		cdef AwlOffset offset

		offset = make_AwlOffset(self.byteOffset,
					self.bitOffset)
		offset.dbNumber = self.dbNumber
		return offset

	def toPointerValue(self): #@nocy
#@cy	cpdef uint32_t toPointerValue(self):
		return ((self.byteOffset << 3) & 0x0007FFF8) |\
		       (self.bitOffset & 0x7)

	def toLongBitOffset(self):				#@nocy
#@cy	cpdef uint64_t toLongBitOffset(self):
#@cy		return <int64_t>self.byteOffset * <int64_t>8 + <int64_t>self.bitOffset
		return self.byteOffset * 8 + self.bitOffset	#@nocy

	def __add__(self, other): #@nocy
#@cy	def __add__(AwlOffset self, AwlOffset other):
		return self.add(other)

	def add(self, other): #@nocy
#@cy	cdef AwlOffset add(self, AwlOffset other):
		return self.addInt(other.byteOffset, other.bitOffset)

	def addInt(self, byteOffset, bitOffset): #@nocy
#@cy	@cython.cdivision(True)
#@cy	cdef AwlOffset addInt(self, int64_t byteOffset, int32_t bitOffset):
#@cy		cdef int64_t sumOffset

		sumOffset = ((self.byteOffset + byteOffset) * 8 +	#@nocy
			     self.bitOffset + bitOffset)		#@nocy
#@cy		sumOffset = ((<int64_t>self.byteOffset + <int64_t>byteOffset) * <int64_t>8 +
#@cy			     <int64_t>self.bitOffset + <int64_t>bitOffset)
		return make_AwlOffset(sumOffset // 8, sumOffset % 8)

	def __iadd__(self, other): #@nocy
#@cy	def __iadd__(self, AwlOffset other):
		self.iadd(other)
		return self

	def iadd(self, other): #@nocy
#@cy	cdef void iadd(self, AwlOffset other):
		self.iaddInt(other.byteOffset, other.bitOffset)

	def iaddInt(self, byteOffset, bitOffset): #@nocy
#@cy	@cython.cdivision(True)
#@cy	cdef void iaddInt(self, int64_t byteOffset, int32_t bitOffset):
#@cy		cdef int64_t sumOffset

		sumOffset = ((self.byteOffset + byteOffset) * 8 +	#@nocy
			     self.bitOffset + bitOffset)		#@nocy
#@cy		sumOffset = ((<int64_t>self.byteOffset + <int64_t>byteOffset) * <int64_t>8 +
#@cy			     <int64_t>self.bitOffset + <int64_t>bitOffset)
		self.byteOffset = sumOffset // 8
		self.bitOffset = sumOffset % 8

	# Round the offset to a multiple of 'byteBase' bytes.
	# Returns an AwlOffset.
	def roundUp(self, byteBase):
#@cy		cdef int64_t byteOffset

		byteOffset = self.byteOffset
		if self.bitOffset:
			byteOffset += 1
		byteOffset = roundUp(byteOffset, byteBase)
		return make_AwlOffset(byteOffset, 0)

	def __repr__(self):
		prefix = ""
		if self.dbNumber >= 0:
			prefix = "DB%d" % self.dbNumber
		if self.dbName is not None:
			prefix = '"%s"' % self.dbName
		if self.identChain is not None:
			if prefix:
				return prefix + "." + self.identChain.getString()
			return "#" + self.identChain.getString()
		else:
			if prefix:
				prefix = prefix + ".DBX "
			return "%s%d.%d" % (prefix,
					    self.byteOffset,
					    self.bitOffset)

#
# make_AwlOffset() - Construct an AwlOffset instance.
# For Cython performance reasons we don't use __init__ with arguments.
#
def make_AwlOffset(byteOffset, bitOffset, AwlOffset=AwlOffset):		#@nocy
#cdef AwlOffset make_AwlOffset(int64_t byteOffset, int32_t bitOffset):	#@cy
#@cy	cdef AwlOffset offset

	offset = AwlOffset()
#@cy	offset.dbNumber = -1
#@cy	offset.dbName = None
#@cy	offset.identChain = None
#@cy	offset.fbNumber = -1
#@cy	offset.subOffset = None
	offset.byteOffset = byteOffset
	offset.bitOffset = bitOffset

	return offset

#
# make_AwlOffset_fromPointerValue() - Construct an AwlOffset from a S7 pointer value.
# The Cython variant of this function is defined in .pxd.in
#
def make_AwlOffset_fromPointerValue(value, make_AwlOffset=make_AwlOffset):	#@nocy
	return make_AwlOffset((value & 0x0007FFF8) >> 3,			#@nocy
			      (value & 0x7))					#@nocy

#
# make_AwlOffset_fromLongBitOffset() - Construct an AwlOffset from a bit offset.
# The Cython variant of this function is defined in .pxd.in
#
def make_AwlOffset_fromLongBitOffset(bitOffset, make_AwlOffset=make_AwlOffset): #@nocy
	return make_AwlOffset(bitOffset // 8, bitOffset % 8)			#@nocy

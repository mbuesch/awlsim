# -*- coding: utf-8 -*-
#
# AWL simulator - Word packer
#
# Copyright 2013-2014 Michael Buesch <m@bues.ch>
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

import struct


__all__ = [
	"WordPacker",
]


class _WordPacker:
	"""Pack/unpack bytes/words/dwords into/from a byte stream."""

	_wordStruct = struct.Struct(str(">H"))
	_dwordStruct = struct.Struct(str(">I"))

	def __fromBytes_1(self, buf, byteOffset):
		return buf[byteOffset] & 0x01

	def __fromBytes_8(self, buf, byteOffset):
		return buf[byteOffset]

	def __fromBytes_16(self, buf, byteOffset):
		return _WordPacker._wordStruct.unpack_from(
			buf, byteOffset
		)[0]

	def __fromBytes_32(self, buf, byteOffset):
		return _WordPacker._dwordStruct.unpack_from(
			buf, byteOffset
		)[0]

	__fromBytesHandlers = {
		1	: __fromBytes_1,
		8	: __fromBytes_8,
		16	: __fromBytes_16,
		32	: __fromBytes_32,
	}

	def __toBytes_1(self, buf, byteOffset, value):
		buf[byteOffset] = value & 0x01

	def __toBytes_8(self, buf, byteOffset, value):
		buf[byteOffset] = value & 0xFF

	def __toBytes_16(self, buf, byteOffset, value):
		if byteOffset + 2 > len(buf):
			raise IndexError
		buf[byteOffset : byteOffset + 2] =\
			_WordPacker._wordStruct.pack(value & 0xFFFF)

	def __toBytes_32(self, buf, byteOffset, value):
		if byteOffset + 4 > len(buf):
			raise IndexError
		buf[byteOffset : byteOffset + 4] =\
			_WordPacker._dwordStruct.pack(value & 0xFFFFFFFF)

	__toBytesHandlers = {
		1	: __toBytes_1,
		8	: __toBytes_8,
		16	: __toBytes_16,
		32	: __toBytes_32,
	}

	def fromBytes(self, byteBuffer, bitWidth, byteOffset=0):
		# byteBuffer should not be 'bytes' for Py2 compoatibility reasons.
		# 'bytes' indexing returns different results on Py3 (int vs. str).
		assert(not isinstance(byteBuffer, bytes))
		if bitWidth > 32:
			return byteBuffer
		try:
			handler = self.__fromBytesHandlers[bitWidth]
			return handler(self, byteBuffer, byteOffset)
		except (IndexError, KeyError, struct.error) as e:
			raise AwlSimError("Failed to unpack %d bits from buffer" % bitWidth)

	def toBytes(self, byteBuffer, bitWidth, byteOffset=0, value=0):
		if bitWidth > 32:
			return value
		try:
			handler = self.__toBytesHandlers[bitWidth]
			handler(self, byteBuffer, byteOffset, value)
		except (IndexError, KeyError, struct.error) as e:
			raise AwlSimError("Failed to pack %d bits into buffer" % bitWidth)
		return byteBuffer

WordPacker = _WordPacker()

# -*- coding: utf-8 -*-
#
# AWL simulator - Block infos
#
# Copyright 2015 Michael Buesch <m@bues.ch>
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

from awlsim.common.enumeration import *
from awlsim.common.util import *
from awlsim.common.exceptions import *


__all__ = [
	"BlockInfo",
]


class BlockInfo(object):
	"""Compiled-block information."""

	# Block-info type identifier.
	EnumGen.start
	TYPE_OB		= EnumGen.item
	TYPE_FC		= EnumGen.item
	TYPE_FB		= EnumGen.item
	TYPE_DB		= EnumGen.item
	EnumGen.end

	def __init__(self, blockType, blockIndex, identHash = None):
		self.blockType = blockType
		self.blockIndex = blockIndex
		self.identHash = identHash

	@property
	def identHashStr(self):
		return bytesToHexStr(self.identHash)

	@property
	def blockName(self):
		try:
			type2name = {
				self.TYPE_OB	: "OB",
				self.TYPE_FC	: "FC",
				self.TYPE_FB	: "FB",
				self.TYPE_DB	: "DB",
			}
			blkName = type2name[self.blockType]
		except KeyError as e:
			blkName = "TYPE_%d" % self.blockType
		return "%s %d" % (blkName, self.blockIndex)

	def __eq__(self, other):
		return self.blockType == other.blockType and\
		       self.blockIndex == other.blockIndex and\
		       self.identHash == other.identHash

	def __ne__(self, other):
		return not self.__eq__(other)

	def __repr__(self):
		return "BlockInfo(%d, %d, '%s')" % (
			self.blockType,
			self.blockIndex,
			self.identHashStr
		)

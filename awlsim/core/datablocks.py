# -*- coding: utf-8 -*-
#
# AWL simulator - datablocks
#
# Copyright 2012-2017 Michael Buesch <m@bues.ch>
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

from awlsim.common.blockinfo import *
from awlsim.common.enumeration import *
from awlsim.common.exceptions import *

from awlsim.core.util import *
from awlsim.core.operators import * #+cimport
from awlsim.core.datatypes import *
from awlsim.core.memory import * #+cimport
from awlsim.core.datastructure import * #+cimport
from awlsim.core.blocks import * #+cimport
from awlsim.core.offset import * #+cimport


class DB(Block): #+cdef
	EnumGen.start
	PERM_READ	= EnumGen.bitmask
	PERM_WRITE	= EnumGen.bitmask
	EnumGen.end

	def __init__(self, index, codeBlock=None,
		     permissions=(PERM_READ|PERM_WRITE)):
		Block.__init__(self, index)
		self._PERM_READ = self.PERM_READ
		self._PERM_WRITE = self.PERM_WRITE

		self.setPermissions(permissions)

		self.codeBlock = codeBlock	# The FB, if this is an instance-DB.
		if self.codeBlock:
			# The data structure is declared by the interface.
			self.__struct = None
		else:
			self.__struct = AwlStruct()
		self.structInstance = None

	def setPermissions(self, newPermissions):
		self.permissions = newPermissions

	@property
	def struct(self):
		if self.codeBlock:
			return self.codeBlock.interface._struct
		return self.__struct

	def isInstanceDB(self):
		return bool(self.codeBlock)

	def allocate(self):
		self.structInstance = AwlStructInstance(self.struct)

	def fetch(self, operator, baseOffset): #@nocy
#@cy	cdef object fetch(self, AwlOperator operator, AwlOffset baseOffset):
		if self.permissions & self._PERM_READ:
			if baseOffset is None:
				return self.structInstance.memory.fetch(
						operator.offset,
						operator.width)
			else:
				return self.structInstance.memory.fetch(
						baseOffset + operator.offset,
						operator.width)
		raise AwlSimError("Fetch from read protected DB %d" % self.index)

	def store(self, operator, value, baseOffset): #@nocy
#@cy	cdef store(self, AwlOperator operator, object value, AwlOffset baseOffset):
		if self.permissions & self._PERM_WRITE:
			if baseOffset is None:
				self.structInstance.memory.store(
						operator.offset,
						operator.width,
						value)
			else:
				self.structInstance.memory.store(
						baseOffset + operator.offset,
						operator.width,
						value)
		else:
			raise AwlSimError("Store to write protected DB %d" % self.index)

	def getBlockInfo(self):
		"""Get a BlockInfo instance for this block.
		"""
		return BlockInfo(blockType = BlockInfo.TYPE_DB,
				 blockIndex = self.index,
				 identHash = self.identHash)

	def __repr__(self):
		if self.index == 0:
			return "DB --"
		return "DB %d" % self.index

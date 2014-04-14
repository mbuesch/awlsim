# -*- coding: utf-8 -*-
#
# AWL simulator - datablocks
#
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
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
from awlsim.core.operators import *
from awlsim.core.datatypes import *
from awlsim.core.datastructure import *


class DB(object):
	PERM_READ	= 1 << 0
	PERM_WRITE	= 1 << 1

	def __init__(self, index, codeBlock=None,
		     permissions=(PERM_READ|PERM_WRITE)):
		self.setPermissions(permissions)
		self.index = index
		self.codeBlock = codeBlock	# The FB or FC, if this is an instance/bounce-DB.
		if self.codeBlock:
			# The data structure is declared by the interface.
			self.__struct = None
		else:
			self.__struct = AwlStruct()
		self.structInstance = None

	def setPermissions(self, newPermissions):
		self.permissions = newPermissions
		if self.permissions & self.PERM_READ:
			self.fetch = self.__fetch
		else:
			self.fetch = self.__fetch_noPermission
		if self.permissions & self.PERM_WRITE:
			self.store = self.__store
		else:
			self.store = self.__store_noPermission

	@property
	def struct(self):
		if self.codeBlock:
			return self.codeBlock.interface.struct
		return self.__struct

	def isInstanceDB(self):
		return bool(self.codeBlock)

	def allocate(self):
		self.structInstance = AwlStructInstance(self.struct)

	def __fetch(self, operator):
		return self.structInstance.dataBytes.fetch(operator.value, operator.width)

	def __fetch_noPermission(self, operator):
		raise AwlSimError("Fetch from read protected DB %d" % self.index)

	fetch = __fetch

	def __store(self, operator, value):
		self.structInstance.dataBytes.store(operator.value, operator.width, value)

	def __store_noPermission(self, operator, value):
		raise AwlSimError("Store to write protected DB %d" % self.index)

	store = __store

	def __repr__(self):
		if self.index == 0:
			return "DB --"
		return "DB %d" % self.index

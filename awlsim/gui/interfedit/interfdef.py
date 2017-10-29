# -*- coding: utf-8 -*-
#
# AWL simulator - Block interface definition
#
# Copyright 2016-2017 Michael Buesch <m@bues.ch>
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

from awlsim.common.util import *

import uuid


class AwlInterfFieldDef(object):
	@classmethod
	def newUUID(cls):
		"""Generate a new unique identifier string.
		"""
		return str(uuid.uuid4())

	def __init__(self, name="", typeStr="", initValueStr="", comment="", uuid=None):
		self.name = name
		self.typeStr = typeStr
		self.initValueStr = initValueStr
		self.comment = comment
		self.uuid = uuid or self.newUUID()

	def isValid(self):
		return self.name and self.typeStr

class AwlInterfDef(object):
	def __init__(self):
		self.clear()

	def clear(self):
		self.inFields = []
		self.outFields = []
		self.inOutFields = []
		self.statFields = []
		self.tempFields = []
		self.retValField = None

	def isEmpty(self):
		"""Returns True, if the interface is empty.
		That is if it does not contain fields and RET_VAL is VOID.
		"""
		retEmpty = not self.retValField or (
			   self.retValField.typeStr.upper().strip() == "VOID" and\
			   not self.retValField.initValueStr.strip() and\
			   not self.retValField.comment.strip())
		return not self.inFields and\
		       not self.outFields and\
		       not self.inOutFields and\
		       not self.statFields and\
		       not self.tempFields and\
		       retEmpty

	@property
	def allFields(self):
		"""Get all fields.
		"""
		for field in itertools.chain(self.inFields,
					     self.outFields,
					     self.inOutFields,
					     self.statFields,
					     self.tempFields,
					     [self.retValField]):
			if field:
				yield field

	def findByName(self, name, caseSensitive=False, strip=True):
		"""Find a field by its name.
		caseSensitive => Do a case sensitive match
		strip => Strip the name and remove leading #
		"""
		if strip:
			name = name.strip() # Strip leading and trailing white space
			if name.startswith("#"):
				name = name[1:] # Strip #-prefix
		for field in self.allFields:
			fieldName = field.name
			if not caseSensitive:
				fieldName = fieldName.upper()
				name = name.upper()
			if fieldName == name:
				return field # Found it
		return None

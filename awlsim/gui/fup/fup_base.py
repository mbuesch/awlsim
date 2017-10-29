# -*- coding: utf-8 -*-
#
# AWL simulator - FUP - Abstract base classes
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


__all__ = [
	"FupBaseClass",
]


class FupBaseClass(object):
	"""Abstract FUP/FBD base class"""

	factory = None

	__slots__ = (
		"__uuid",
	)

	@classmethod
	def newUUID(cls):
		"""Generate a new unique identifier string.
		"""
		return str(uuid.uuid4())

	def __init__(self, uuid=None):
		self.uuid = uuid

	@property
	def uuid(self):
		return self.__uuid

	@uuid.setter
	def uuid(self, uuid):
		self.__uuid = uuid or self.newUUID()

	def __eq__(self, other):
		return self is other

	def __ne__(self, other):
		return self is not other

	def __hash__(self):
		return id(self)

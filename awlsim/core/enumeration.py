# -*- coding: utf-8 -*-
#
# AWL simulator - utility functions
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


class MagicEnumerationGenerator(object):
	"Magic enumeration generator"

	def __init__(self):
		self.__num = None

	@property
	def start(self):
		assert(self.__num is None)
		self.__num = 0
		return None

	@start.setter
	def start(self, startNumber):
		assert(self.__num is None)
		self.__num = startNumber

	@property
	def end(self):
		self.__num = None
		return None

	@property
	def item(self):
		number = self.itemNoInc
		self.__num += 1
		return number

	@property
	def itemNoInc(self):
		assert(self.__num is not None)
		return self.__num

	def itemAt(self, number):
		assert(self.__num is not None)
		self.__num = number + 1
		return number

	def __repr__(self):
		return "EnumGen(num = %s)" % str(self.__num)

EnumGen = MagicEnumerationGenerator()

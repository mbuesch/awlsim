# -*- coding: utf-8 -*-
#
# AWL simulator - Dynamic attributes base class
#
# Copyright 2014-2016 Michael Buesch <m@bues.ch>
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

#from awlsim.core.dynattrs cimport * #@cy


class DynAttrs(object): #+cdef
	"""Dynamic attributes base class.
	The specified attributes are automatically initialized
	to their initial values on the first read access."""

	# Dict of dynamic attributes.
	# Key is the attribute name.
	# Value is the initial attribute value.
	# If value is a callable, it is called with (self, name) as arguments
	# to retrieve the actual value.
	dynAttrs = {}

	def __getattr__(self, name):
		# Create the attribute, if it is in the dynAttrs dict.
		if name in self.dynAttrs:
			value = self.dynAttrs[name]
			if callable(value):
				value = value(self, name)
			setattr(self, name, value)
			return value
		# Fail for all other attributes
		raise AttributeError(name)

	def __eq__(self, other): #@nocy
#@cy	cdef __eq(self, object other):
		if self is other:
			return True
		if not isinstance(other, DynAttrs):
			return False
		for attrName in self.dynAttrs:
			if not hasattr(self, attrName) and\
			   not hasattr(other, attrName):
				continue
			if getattr(self, attrName) != getattr(other, attrName):
				return False
		return True

#@cy	def __richcmp__(self, object other, int op):
#@cy		if op == 2: # __eq__
#@cy			return self.__eq(other)
#@cy		elif op == 3: # __ne__
#@cy			return not self.__eq(other)
#@cy		return False

	def __ne__(self, other):		#@nocy
		return not self.__eq__(other)	#@nocy

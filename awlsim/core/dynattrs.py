# -*- coding: utf-8 -*-
#
# AWL simulator - Dynamic attributes base class
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


class DynAttrs(object):
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
		raise AttributeError

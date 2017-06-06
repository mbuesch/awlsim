# -*- coding: utf-8 -*-
#
# AWL simulator - Instance write protection
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


__all__ = [
	"OptionalImmutable",
]


__useDummy = False
if isMicroPython:
	__useDummy = True


if __useDummy:
	class OptionalImmutable(object):
		"""Optional instance write protection.
		Dummy implementation.
		"""

		_immutable = False

		def isImmutable(self):
			return self._immutable

		def setImmutable(self):
			self._immutable = True
else:
	class OptionalImmutable(object):
		"""Optional instance write protection.
		By default, instances are not write protected (not immutable).
		If setImmutable() is called, assignment to instance attributes
		and deletion of attributes is restricted.
		This cannot be reverted.
		Subclass this class to use this mechanism."""

		__slots__ = (
			"_immutable",
		)

		def __new__(cls, *args, **kwargs):
			self = super(OptionalImmutable, cls).__new__(cls)
			super(OptionalImmutable, self).__setattr__("_immutable", False)
			return self

		def isImmutable(self):
			"""Returns True, if self is immutable."""
			return self._immutable

		def setImmutable(self):
			"""Make self immutable. This is not reversible."""
			self._immutable = True

		def __setattr__(self, name, value):
			if self._immutable:
				raise AttributeError("Assignment to '%s' "
					"of immutable %s." %\
					(name, str(type(self))))
			super(OptionalImmutable, self).__setattr__(name, value)

		def __delattr__(self, name):
			if self._immutable:
				raise AttributeError("Deletion of '%s' "
					"from immutable %s." %\
					(name, str(type(self))))
			super(OptionalImmutable, self).__delattr__(name)

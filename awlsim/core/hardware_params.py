# -*- coding: utf-8 -*-
#
# AWL simulator - Hardware module parameters
#
# Copyright 2013-2017 Michael Buesch <m@bues.ch>
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


__all__ = [ "HwParamDesc",
	    "HwParamDesc_pyobject",
	    "HwParamDesc_str",
	    "HwParamDesc_int",
	    "HwParamDesc_bool",
]


class HwParamDesc(object):
	"""Abstract hardware parameter descriptor."""

	class ParseError(Exception):
		pass

	typeStr = "<NoType>"
	userEditable = True
	defaultValue = None

	def __init__(self, name, description="", mandatory=False):
		self.name = name
		self.description = description
		self.mandatory = mandatory

	def parse(self, value):
		"""Parse a value string.
		This must be overridden.
		"""
		raise NotImplementedError

	def match(self, matchName):
		"""Match a name string.
		The default implementation just compares the string to self.name.
		The parameter must not be 'mandatory', if this method is overridden.
		"""
		return self.name == matchName

class HwParamDesc_pyobject(HwParamDesc):
	"""Generic object parameter descriptor."""

	typeStr = "PyObject"
	userEditable = False

	def __init__(self, name, description="", mandatory=False):
		HwParamDesc.__init__(self, name, description, mandatory)

	def parse(self, value):
		return value

class HwParamDesc_str(HwParamDesc):
	"""String hardware parameter descriptor."""

	typeStr = "string"

	def __init__(self, name, defaultValue="", description="", mandatory=False):
		HwParamDesc.__init__(self, name, description, mandatory)
		self.defaultValue = defaultValue

	def parse(self, value):
		return value

class HwParamDesc_int(HwParamDesc):
	"""Integer hardware parameter descriptor."""

	typeStr = "integer"

	def __init__(self, name,
		     defaultValue=0, minValue=None, maxValue=None,
		     description="", mandatory=False):
		HwParamDesc.__init__(self, name, description, mandatory)
		self.defaultValue = defaultValue
		self.minValue = minValue
		self.maxValue = maxValue

	def parse(self, value):
		try:
			value = int(value)
		except ValueError:
			raise self.ParseError("Value '%s' is not a valid integer." %\
					      str(value))
		if self.minValue is not None:
			if value < self.minValue:
				raise self.ParseError("Value '%d' is too small." % value)
		if self.maxValue is not None:
			if value > self.maxValue:
				raise self.ParseError("Value '%d' is too big." % value)
		return value

class HwParamDesc_bool(HwParamDesc):
	"""Boolean hardware parameter descriptor."""

	typeStr = "boolean"

	def __init__(self, name, defaultValue=False,
		     description="", mandatory=False):
		HwParamDesc.__init__(self, name, description, mandatory)
		self.defaultValue = defaultValue

	def parse(self, value):
		value = value.strip()
		if value.lower() in ("true", "yes", "on"):
			return True
		if value.lower() in ("false", "no", "off"):
			return False
		try:
			value = int(value, 10)
		except ValueError:
			raise self.ParseError("Value '%s' is not a valid boolean." %\
				str(value))
		return bool(value)

# -*- coding: utf-8 -*-
#
# AWL simulator - Hardware module parameters
#
# Copyright 2013-2018 Michael Buesch <m@bues.ch>
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
from awlsim.common.exceptions import *


__all__ = [ "HwParamDesc",
	    "HwParamDesc_pyobject",
	    "HwParamDesc_str",
	    "HwParamDesc_int",
	    "HwParamDesc_bool",
	    "HwParamDesc_outAddr",
	    "HwParamDesc_inAddr",
]


class HwParamDesc(object):
	"""Abstract hardware parameter descriptor."""

	class ParseError(Exception):
		pass

	typeStr = "<NoType>"
	userEditable = True
	defaultValue = None

	def __init__(self, name, description="", mandatory=False, hidden=False):
		self.name = name
		self.description = description
		self.mandatory = mandatory
		self.hidden = hidden

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

	def __init__(self, name, description="", mandatory=False, hidden=False):
		HwParamDesc.__init__(self, name, description, mandatory, hidden)

	def parse(self, value):
		return value

class HwParamDesc_str(HwParamDesc):
	"""String hardware parameter descriptor."""

	typeStr = "string"

	def __init__(self, name, defaultValue="", description="", mandatory=False, hidden=False):
		HwParamDesc.__init__(self, name, description, mandatory, hidden)
		self.defaultValue = defaultValue

	def parse(self, value):
		return value

class HwParamDesc_int(HwParamDesc):
	"""Integer hardware parameter descriptor."""

	typeStr = "integer"

	def __init__(self, name,
		     defaultValue=0, minValue=None, maxValue=None,
		     description="", mandatory=False, hidden=False):
		HwParamDesc.__init__(self, name, description, mandatory, hidden)
		self.defaultValue = defaultValue
		self.minValue = minValue
		self.maxValue = maxValue

	def parse(self, value):
		if not value.strip():
			return self.defaultValue
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
		     description="", mandatory=False, hidden=False):
		HwParamDesc.__init__(self, name, description, mandatory, hidden)
		self.defaultValue = defaultValue

	def parse(self, value):
		value = value.strip()
		if not value:
			return self.defaultValue
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

class __HwParamDesc_addr(HwParamDesc):
	"""Address hardware parameter descriptor."""

	typeStr = None
	ADDR_PREFIXES = None

	def __init__(self, name,
		     defaultValue=None, minValue=None, maxValue=None,
		     description="", mandatory=False, hidden=False):
		HwParamDesc.__init__(self, name, description, mandatory, hidden)
		self.defaultValue = defaultValue
		self.minValue = minValue
		self.maxValue = maxValue

	def _parseAddr(self, value):
		if not value.strip():
			return self.defaultValue
		try:
			v = value.split()
			if len(v) != 2:
				raise ValueError
			if not any(strEqual(v[0], p, False) for p in self.ADDR_PREFIXES):
				raise ValueError
			o = v[1].split(".")
			if len(o) != 2:
				raise ValueError
			byteOffset, bitOffset = int(o[0], 10), int(o[1], 10)
			if byteOffset < 0 or bitOffset < 0 or bitOffset > 7:
				raise ValueError
			return byteOffset * 8 + bitOffset
		except ValueError:
			raise self.ParseError("Value '%s' is not a %s." % (
					      str(value), self.typeStr))

	def parse(self, value):
		bitOffset = self._parseAddr(value)
		if self.minValue is not None:
			minBitOffset = self._parseAddr(self.minValue)
			if bitOffset < minBitOffset:
				raise self.ParseError("Address '%s' is too small." % value)
		if self.maxValue is not None:
			maxAddr = self._parseAddr(self.maxValue)
			if bitOffset > maxBitOffset:
				raise self.ParseError("Address '%s' is too big." % value)
		return bitOffset

class HwParamDesc_outAddr(__HwParamDesc_addr):
	"""Output address hardware parameter descriptor."""

	typeStr = "outputAddress"
	ADDR_PREFIXES = ("Q", "A")

class HwParamDesc_inAddr(__HwParamDesc_addr):
	"""Input address hardware parameter descriptor."""

	typeStr = "inputAddress"
	ADDR_PREFIXES = ("I", "E")

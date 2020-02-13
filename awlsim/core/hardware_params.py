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
#from awlsim.common.cython_support cimport * #@cy
from awlsim.common.compat import *

from awlsim.common.enumeration import *
from awlsim.common.util import *
from awlsim.common.exceptions import *
from awlsim.common.cpuconfig import *

from awlsim.core.operatortypes import * #+cimport

from awlsim.awlcompiler.optrans import *

import re


__all__ = [ "HwParamDesc",
	    "HwParamDesc_str",
	    "HwParamDesc_int",
	    "HwParamDesc_float",
	    "HwParamDesc_bool",
	    "HwParamDesc_oper",
]


class HwParamDesc(object):
	"""Abstract hardware parameter descriptor."""

	class ParseError(Exception):
		pass

	typeStr = "<NoType>"
	userEditable = True
	defaultValue = None	# Default value; represented as parsed value
	defaultValueStr = None	# Default value; represented as parser input string

	def __init__(self, name,
		     description="",
		     mandatory=False,
		     hidden=False,
		     deprecated=False,
		     compatReplacement="",
		     replacement=""):
		"""
		name: The parameter name string.
		description: The parameter description string.
		mandatory: If True, then this parameter must be specified.
		hidden: If True, then this parameter will not be shown by default.
		deprecated: If True, then the use of this parameter is discouraged.
		compatReplacement: Optional name of a fully compatible parameter
		                   that replaces this one. (Also see 'deprecated').
		replacement: Optional name of an incompatible parameter
		             that replaces this one. (Also see 'deprecated').
		"""
		self.name = name
		self.description = description
		self.mandatory = mandatory
		self.hidden = hidden
		self.deprecated = deprecated
		self.compatReplacement = compatReplacement
		self.replacement = replacement

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

class HwParamDesc_str(HwParamDesc):
	"""String hardware parameter descriptor."""

	typeStr = "string"

	def __init__(self, name, defaultValue="", **kwargs):
		HwParamDesc.__init__(self, name, **kwargs)
		self.defaultValue = defaultValue
		self.defaultValueStr = defaultValue

	def parse(self, value):
		if not value.strip():
			return self.defaultValue
		return value

class HwParamDesc_int(HwParamDesc):
	"""Integer hardware parameter descriptor."""

	typeStr = "integer"

	def __init__(self, name,
		     defaultValue=0, minValue=None, maxValue=None, **kwargs):
		HwParamDesc.__init__(self, name, **kwargs)
		self.defaultValue = defaultValue
		self.defaultValueStr = None if defaultValue is None else str(defaultValue)
		self.minValue = minValue
		self.maxValue = maxValue

	def parse(self, value):
		value = value.strip()
		if not value:
			return self.defaultValue

		valueUpper = value.upper()
		if valueUpper.startswith("B#16#") or\
		   valueUpper.startswith("W#16#"):
			value = "0x" + value[5:]
		elif valueUpper.startswith("DW#16#"):
			value = "0x" + value[6:]
		elif valueUpper.startswith("L#"):
			value = value[2:] # Strip L# prefix

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

class HwParamDesc_float(HwParamDesc):
	"""Float hardware parameter descriptor."""

	typeStr = "float"

	def __init__(self, name,
		     defaultValue=0.0, minValue=None, maxValue=None, **kwargs):
		HwParamDesc.__init__(self, name, **kwargs)
		self.defaultValue = defaultValue
		self.defaultValueStr = None if defaultValue is None else str(defaultValue)
		self.minValue = minValue
		self.maxValue = maxValue

	def parse(self, value):
		if not value.strip():
			return self.defaultValue
		try:
			value = float(value)
		except ValueError:
			raise self.ParseError("Value '%s' is not a valid floating point number." %\
					      str(value))
		if self.minValue is not None:
			if value < self.minValue:
				raise self.ParseError("Value '%f' is too small." % value)
		if self.maxValue is not None:
			if value > self.maxValue:
				raise self.ParseError("Value '%f' is too big." % value)
		return value

class HwParamDesc_bool(HwParamDesc):
	"""Boolean hardware parameter descriptor."""

	typeStr = "boolean"

	def __init__(self, name, defaultValue=False, **kwargs):
		HwParamDesc.__init__(self, name, **kwargs)
		self.defaultValue = None if defaultValue is None else bool(defaultValue)
		self.defaultValueStr = None if defaultValue is None else str(bool(defaultValue))

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

class HwParamDesc_oper(HwParamDesc):
	"""Hardware parameter descriptor for operators.
	"""

	typeStr = "operator"

	def __init__(self, name,
		     allowedOperTypes=(),
		     allowedOperWidths=(),
		     **kwargs):
		HwParamDesc.__init__(self, name, **kwargs)
		self.allowedOperTypes = allowedOperTypes
		self.allowedOperWidths = allowedOperWidths

	numRe = re.compile(r'^\-?\d+$', re.DOTALL)

	def __tryParse(self, value, mnemonics):
		# Add a L# prefix, if this is a constant long integer.
		if self.numRe.match(value):
			try:
				v = int(value, 10)
				if (v > 32767 and v <= 2147483647) or\
				   (v < -32768 and v >= -2147483648):
					value = "L#" + value
			except ValueError as e:
				pass
		# Parse value as operator.
		try:
			trans = AwlOpTranslator(mnemonics=mnemonics)
			opDesc = trans.translateFromString(value)
			oper = opDesc.operator
		except AwlSimError as e:
			oper = None
		return oper

	def parse(self, value):
		if not value.strip():
			return None
		oper = self.__tryParse(value, S7CPUConfig.MNEMONICS_EN)
		if not oper:
			oper = self.__tryParse(value, S7CPUConfig.MNEMONICS_DE)
			if not oper:
				raise self.ParseError("Operator '%s' "
					"is not valid." % value)
		if self.allowedOperTypes:
			if oper.operType not in self.allowedOperTypes:
				raise self.ParseError("Operator '%s' "
					"does not have a valid type." % value)
		if self.allowedOperWidths:
			if oper.width not in self.allowedOperWidths:
				raise self.ParseError("Operator '%s' "
					"does not have a valid bit width. "
					"Valid widths are: %s bits." % (
					value, listToHumanStr(self.allowedOperWidths)))
		return oper

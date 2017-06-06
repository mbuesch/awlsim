# -*- coding: utf-8 -*-
#
# AWL simulator - name validation and limitation
#
# Copyright 2016 Michael Buesch <m@bues.ch>
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

import re


__all__ = [
	"AwlName",
]


class AwlName(object):
	labelRe = re.compile(r'^[_a-zA-Z][_0-9a-zA-Z]{0,3}$')
	alpha_lower = "abcdefghijklmnopqrstuvwxyz"
	alpha_upper = alpha_lower.upper()
	alpha = alpha_lower + alpha_upper
	space = " \t"
	special = "\0\a\b\v\f"
	newlines = "\r\n"
	num = "0123456789"
	alpha_under = alpha + "_"
	alpha_num_under = alpha + num + "_"

	@classmethod
	def isValidLabel(cls, labelString):
		"""Checks if string is a valid label or
		label reference (without colons).
		"""
		return bool(cls.labelRe.match(labelString))

	@classmethod
	def isValidVarName(cls, name, checkMaxLength=True):
		"""Checks if a string is a valid variable name.
		"""
		return name and\
		       all(c in cls.alpha_num_under for c in name) and\
		       name[0] in cls.alpha_under and\
		       name[-1] != "_" and\
		       name.find("__") < 0 and\
		       (not checkMaxLength or len(name) <= 24)

	@classmethod
	def mayBeValidType(cls, typeString, checkMaxLength=True):
		"""Check if a string looks like a valid type.
		This does NOT check whether this actually is a valid type.
		It does just check if there are no obvious
		non-type-like characters in the string.
		"""
		return (typeString and\
		        all(c in cls.alpha_num_under or c in cls.space
		            for c in typeString) and\
		        typeString[0] != "_" and\
		        typeString[-1] != "_") or\
		       cls.isValidSymbolName(typeString.strip(), checkMaxLength)

	@classmethod
	def isValidSymbolName(cls, symName, checkMaxLength=True):
		"""Check if a string is a valid symbol name (with quotes).
		"""
		return len(symName) >= 3 and\
		       symName[0] == '"' and\
		       symName[-1] == '"' and\
		       symName[1:-1].find('"') < 0 and\
		       all(c not in cls.newlines and c not in cls.special
		           for c in symName) and\
		       (not checkMaxLength or len(symName) <= 24 + 2)

	@classmethod
	def mayBeValidValue(cls, valueString):
		"""Check if a string looks like a valid variable value.
		This does NOT check whether this actually is valid data.
		It does just check if there are no obvious
		non-value-like characters in the string.
		"""
		return valueString.strip() and\
		       all(c not in cls.newlines and c not in cls.special
			   for c in valueString)

	@classmethod
	def isValidComment(cls, commentString):
		"""Check if a string is a valid AWL comment string.
		The string shall not start with the // comment characters.
		"""
		return all(c not in cls.newlines and c not in cls.special
			   for c in commentString)

	@classmethod
	def stripChars(cls, string,
		       replaceWith="",
		       notStripChars="",
		       stripAlpha=True,
		       stripNum=True,
		       stripSpace=True,
		       stripNewline=True,
		       stripSpecial=True):
		"""Strip characters from a string based in the character type.
		"""
		ret = []
		for c in string:
			valid = True
			if c not in notStripChars:
				if c in cls.alpha:
					if stripAlpha:
						valid = False
				elif c in cls.num:
					if stripNum:
						valid = False
				elif c.isspace():
					if stripSpace:
						valid = False
				elif c in cls.newlines:
					if stripNewline:
						valid = False
				elif c in cls.special:
					if stripSpecial:
						valid = False
				else:
					valid = False
			if valid:
				ret.append(c)
			else:
				ret.append(replaceWith)
		return "".join(ret)

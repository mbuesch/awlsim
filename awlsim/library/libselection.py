# -*- coding: utf-8 -*-
#
# AWL simulator - Library entry selection
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
from awlsim.common.compat import *

from awlsim.common.enumeration import *


class AwlLibEntrySelection(object):
	"""AWL library entry selection."""

	# Library entry type.
	# This enumeration is awlsim-coreserver API!
	EnumGen.start
	TYPE_UNKNOWN	= EnumGen.item
	TYPE_FC		= EnumGen.item
	TYPE_FB		= EnumGen.item
	EnumGen.end

	def __init__(self, libName="",
		     entryType=TYPE_UNKNOWN,
		     entryIndex=-1, effectiveEntryIndex=-1):
		self.setLibName(libName)
		self.setEntryType(entryType)
		self.setEntryIndex(entryIndex)
		self.setEffectiveEntryIndex(effectiveEntryIndex)

	def setLibName(self, libName):
		self.__libName = libName.strip()

	def getLibName(self):
		return self.__libName

	def setEntryType(self, entryType):
		if entryType not in (self.TYPE_UNKNOWN,
				     self.TYPE_FC,
				     self.TYPE_FB):
			raise AwlSimError("Library selection: "
				"Invalid entry type %d." %\
				entryType)
		self.__entryType = entryType

	def getEntryType(self):
		return self.__entryType

	def getEntryTypeStr(self):
		return {
			self.TYPE_UNKNOWN	: "UNKNOWN",
			self.TYPE_FC		: "FC",
			self.TYPE_FB		: "FB",
		}[self.getEntryType()]

	def setEntryIndex(self, entryIndex):
		if entryIndex < -1 or entryIndex > 0xFFFF:
			raise AwlSimError("Library selection: "
				"Invalid entry index %d." %\
				entryIndex)
		self.__entryIndex = entryIndex

	def getEntryIndex(self):
		return self.__entryIndex

	def setEffectiveEntryIndex(self, effectiveEntryIndex):
		if effectiveEntryIndex < -1 or effectiveEntryIndex > 0xFFFF:
			raise AwlSimError("Library selection: "
				"Invalid effective entry index %d." %\
				effectiveEntryIndex)
		self.__effectiveEntryIndex = effectiveEntryIndex

	def getEffectiveEntryIndex(self):
		return self.__effectiveEntryIndex

	def isValid(self):
		return self.__libName and\
		       self.__entryType in (self.TYPE_FC, self.TYPE_FB) and\
		       self.__entryIndex >= 0 and\
		       self.__entryIndex <= 0xFFFF and\
		       self.__effectiveEntryIndex >= 0 and\
		       self.__effectiveEntryIndex <= 0xFFFF

	def __repr__(self):
		return "%s - %s %d (=> %s %d)" % (
			self.getLibName(),
			self.getEntryTypeStr(),
			self.getEntryIndex(),
			self.getEntryTypeStr(),
			self.getEffectiveEntryIndex(),
		)

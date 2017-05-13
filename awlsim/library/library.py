# -*- coding: utf-8 -*-
#
# AWL simulator - Library
#
# Copyright 2014-2017 Michael Buesch <m@bues.ch>
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
from awlsim.common.dynamic_import import *


__all__ = [
	"AwlLib",
]


class AwlLib(object):
	"""AWL library."""

	__awlLibs = {}

	@classmethod
	def register(cls, libName, description):
		"""Register an AWL library."""

		libName = libName.lower()
		if libName in cls.__awlLibs:
			raise AwlSimError("Trying to register library '%s', "
				"but it does already exist.")
		cls.__awlLibs[libName] = cls(libName, description)

	@classmethod
	def registerEntry(cls, entryClass):
		"""Register an entry-class for an already registered library."""

		libName = entryClass.libraryName.lower()
		if libName not in cls.__awlLibs:
			raise AwlSimError("Trying to register element '%s' "
				"for unknown library '%s'." %\
				(str(entryClass), entryClass.libraryName))
		cls.__awlLibs[libName].entryClasses.add(entryClass)

	@classmethod
	def getByName(cls, libName):
		"""Get a library, by name."""

		libName = libName.lower()

		# Name sanity check
		try:
			if not libName.strip():
				raise ValueError
			for c in libName:
				if not isalnum(c) and c != "_":
					raise ValueError
		except ValueError:
			raise AwlSimError("Library name '%s' "
				"is invalid." % libName)

		# Get the module and return the class
		try:
			importModule("awlsim.library.%s" % libName)
			return cls.__awlLibs[libName]
		except (ImportError, KeyError) as e:
			raise AwlSimError("Library '%s' was not found "
				"in the standard library catalog." %\
				libName)

	@classmethod
	def getEntryBySelection(cls, selection):
		"""Get a library entry class by AwlLibEntrySelection().
		selection -> An AwlLibEntrySelection instance."""

		return cls.getByName(selection.getLibName()).getEntry(selection)

	def __init__(self, name, description):
		self.name = name
		self.description = description
		self.entryClasses = set()

	def entries(self):
		"""Returns a sorted iterator over
		all entry classes."""

		def sortKey(cls):
			return cls.staticIndex +\
			       0x10000 if cls._isFB else 0

		for cls in sorted(self.entryClasses, key=sortKey):
			yield cls

	def getEntry(self, selection):
		"""Get a library entry class by AwlLibEntrySelection().
		selection -> An AwlLibEntrySelection instance."""

		for cls in self.entryClasses:
			if selection.getEntryType() == selection.TYPE_FC:
				if not cls._isFC:
					continue
			else:
				if not cls._isFB:
					continue
			if cls.staticIndex != selection.getEntryIndex():
				continue
			return cls
		raise AwlSimError("The selected library entry '%s' was "
			"not found." % str(selection))

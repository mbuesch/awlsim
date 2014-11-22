# -*- coding: utf-8 -*-
#
# AWL simulator - Library entry
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

from awlsim.common.exceptions import *
from awlsim.common.dynamic_import import *

from awlsim.core.blocks import *

from awlsim.library.libselection import *


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
		for c in libName:
			if not c.isalnum() and c != "_":
				raise AwlSimError("Library name '%s' "
					"is invalid." % libName)

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
			       0x10000 if cls.isFB else 0

		for cls in sorted(self.entryClasses, key=sortKey):
			yield cls

	def getEntry(self, selection):
		"""Get a library entry class by AwlLibEntrySelection().
		selection -> An AwlLibEntrySelection instance."""

		for cls in self.entryClasses:
			if selection.getEntryType() == selection.TYPE_FC:
				if not cls.isFC:
					continue
			else:
				if not cls.isFB:
					continue
			if cls.staticIndex != selection.getEntryIndex():
				continue
			return cls
		raise AwlSimError("The selected library entry '%s' was "
			"not found." % str(selection))

class AwlLibEntry(StaticCodeBlock):
	"""AWL library entry base class."""

	# The entry identification.
	# To be overridden by the subclass.
	libraryName = ""	# The name of the library this entry belongs to
	staticIndex = -1	# The static block index number
	symbolName = ""		# The FC/FB symbol name string
	description = ""	# Short description string

	# The subclass should override this with a string
	# defining the AWL code that implements this library entry.
	# The code does only include the FC/FB code body.
	# No interface definitions here.
	awlCode = ""

	isLibraryBlock = True

	def __init__(self, index, interface):
		if index is None:
			index = self.staticIndex
		StaticCodeBlock.__init__(self, [], index, interface)

	def _generateInterfaceCode(self, special_RET_VAL=False):
		code = []
		retValType = None
		for ftype, fields in sorted(self.interfaceFields.items(),
					    key=lambda i: i[0]):
			decl = {
				BlockInterfaceField.FTYPE_IN	: "VAR_INPUT",
				BlockInterfaceField.FTYPE_OUT	: "VAR_OUTPUT",
				BlockInterfaceField.FTYPE_INOUT	: "VAR_IN_OUT",
				BlockInterfaceField.FTYPE_STAT	: "VAR",
				BlockInterfaceField.FTYPE_TEMP	: "VAR_TEMP",
			}[ftype]
			variables = []
			for field in fields:
				if ftype == BlockInterfaceField.FTYPE_OUT and\
				   field.name.upper() == "RET_VAL" and\
				   special_RET_VAL:
					# This is special 'RET_VAL', which specifies
					# the FC return type.
					retValType = str(field.dataType)
				else:
					variables.append("\t%s : %s;" %\
						(field.name,
						 str(field.dataType)))
			if not variables:
				continue
			code.append(decl)
			code.extend(variables)
			code.append("END_VAR")
		code.append("")
		return "\n".join(code), retValType

	def getCode(self):
		"""Get the AWL code."""

		raise NotImplementedError

	def makeSelection(self):
		"""Get an AwlLibEntrySelection for this entry."""

		return AwlLibEntrySelection(libName = self.libraryName,
					    entryIndex = self.staticIndex,
					    effectiveEntryIndex = self.index)

	def __repr__(self):
		return "AwlLibEntry %d" % self.index

class AwlLibFC(AwlLibEntry):
	"""Base class for library FCs."""

	isFC = True

	def __init__(self, index=None):
		AwlLibEntry.__init__(self, index, AwlLibFCInterface())

	def getCode(self, symbolic=False):
		"""Get the AWL code."""

		interfCode, retValType = self._generateInterfaceCode(True)
		code = []
		if symbolic:
			code.append("FUNCTION \"%s\" : %s\n" %\
				    (self.symbolName, retValType))
		else:
			code.append("FUNCTION FC %d : %s\n" %\
				    (self.index, retValType))
		code.append(interfCode)
		code.append("BEGIN\n")
		code.append(self.awlCode.strip("\n"))
		code.append("\nEND_FUNCTION\n")
		return "".join(code)

	def makeSelection(self):
		"""Get an AwlLibEntrySelection for this entry."""

		sel = AwlLibEntry.makeSelection(self)
		sel.setEntryType(sel.TYPE_FC)
		return sel

class AwlLibFCInterface(FCInterface):
	pass

class AwlLibFB(AwlLibEntry):
	"""Base class for library FBs."""

	isFB = True

	def __init__(self, index=None):
		AwlLibEntry.__init__(self, index, AwlLibFBInterface())

	def getCode(self, symbolic=False):
		"""Get the AWL code."""

		interfCode, retValType = self._generateInterfaceCode(False)
		code = []
		if symbolic:
			code.append("FUNCTION_BLOCK \"%s\"\n" % self.symbolName)
		else:
			code.append("FUNCTION_BLOCK FB %d\n" % self.index)
		code.append(interfCode)
		code.append("BEGIN\n")
		code.append(self.awlCode.strip("\n"))
		code.append("\nEND_FUNCTION_BLOCK\n")
		return "".join(code)

	def makeSelection(self):
		"""Get an AwlLibEntrySelection for this entry."""

		sel = AwlLibEntry.makeSelection(self)
		sel.setEntryType(sel.TYPE_FB)
		return sel

class AwlLibFBInterface(FBInterface):
	pass

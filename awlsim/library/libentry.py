# -*- coding: utf-8 -*-
#
# AWL simulator - Library entry
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
from awlsim.common.blockinfo import *

from awlsim.core.blocks import * #+cimport
from awlsim.core.blockinterface import *
from awlsim.core.datatypes import *

from awlsim.library.library import *
from awlsim.library.libselection import *
from awlsim.library.libinterface import *


class AwlLibEntry(StaticCodeBlock): #+cdef
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

	# The license information for the AWL code in 'awlCode'.
	# That license may be different from the license of this
	# file's Python code.
	# These fields _must_ be overridden by the subclass.
	awlCodeCopyright = None
	awlCodeLicense = None

	# Set this to True in the subclass, if this is a STANDARD block.
	awlCodeIsStandard = False

	# The AWL code version number.
	# Override this in the subclass.
	awlCodeVersion = "0.1"

	# Mark this block as a library block.
	_isLibraryBlock = True

	def __init__(self, index, interface):
		if index is None:
			index = self.staticIndex
		StaticCodeBlock.__init__(self, [], index, interface)

	def _generateInterfaceCode(self, special_RET_VAL=False):
		code = []
		retValType = None
		for ftype, fields in sorted(dictItems(self.interfaceFields),
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

	# Table for license-short-name to license-text translation.
	__licenseTranslation = {
		"BSD-2-clause"		: \
			"All rights reserved.\n"\
			"\n"\
			"Redistribution and use in source and binary forms, with or without\n"\
			"modification, are permitted provided that the following conditions are met:\n"\
			"\n"\
			"1. Redistributions of source code must retain the above copyright notice, this\n"\
			"   list of conditions and the following disclaimer.\n"\
			"2. Redistributions in binary form must reproduce the above copyright notice,\n"\
			"   this list of conditions and the following disclaimer in the documentation\n"\
			"   and/or other materials provided with the distribution.\n"\
			"\n"\
			"THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS \"AS IS\" AND\n"\
			"ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED\n"\
			"WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE\n"\
			"DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR\n"\
			"ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES\n"\
			"(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;\n"\
			"LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND\n"\
			"ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT\n"\
			"(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS\n"\
			"SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.\n"
	}

	def getCodeLicense(self):
		"""Get the AWL code license information."""

		if not self.awlCodeCopyright:
			raise AwlSimError("Library entry %s/%s does not define "
				"copyright information." % (
				self.libraryName, self.symbolName))
		if not self.awlCodeLicense:
			raise AwlSimError("Library entry %s/%s does not define "
				"license information." % (
				self.libraryName, self.symbolName))

		try:
			license = self.__licenseTranslation[self.awlCodeLicense]
		except KeyError:
			license = self.awlCodeLicense

		code = [ "", ]
		code.extend(self.awlCodeCopyright.splitlines())
		code.extend(license.splitlines())
		code.append("")
		code = [ ("  // " + l).rstrip() for l in code ]

		return "\n".join(code)

	def getCodeTitle(self):
		"""Get the AWL code title."""

		return "TITLE = %s" % self.description

	def getCodeAuthor(self):
		"""Get the AWL code author header."""

		names = []
		for n in self.awlCodeCopyright.splitlines():
			idx = n.find("<")
			if idx >= 0: # Strip E-Mail
				n = n[:idx]
			names.append(n.strip())
		return "AUTHOR : %s" % " / ".join(names)

	def getCodeFamily(self):
		"""Get the AWL code family header."""

		return "FAMILY : %s" % self.libraryName

	def getCodeName(self):
		"""Get the AWL code name header."""

		return "NAME : %s" % self.symbolName

	def getCodeVersion(self):
		"""Get the AWL code version header."""

		return "VERSION : %s" % self.awlCodeVersion

	def getCodeHeaders(self):
		"""Get AWL code headers."""

		hdrs = [ self.getCodeTitle(),
			 self.getCodeAuthor(),
			 self.getCodeFamily(),
			 self.getCodeName(), ]
		if self.awlCodeIsStandard:
			hdrs.append("STANDARD")
		hdrs.append(self.getCodeVersion())
		hdrs.append(self.getCodeLicense())

		return "\n".join(hdrs)

	def makeSelection(self):
		"""Get an AwlLibEntrySelection for this entry."""

		return AwlLibEntrySelection(libName = self.libraryName,
					    entryIndex = self.staticIndex,
					    effectiveEntryIndex = self.index)

	def __repr__(self):
		return "AwlLibEntry %d" % self.index

class AwlLibFC(AwlLibEntry): #+cdef
	"""Base class for library FCs."""

	_isFC = True

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
		code.append(self.getCodeHeaders() + "\n")
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

	def getBlockInfo(self):
		"""Get a BlockInfo instance for this block.
		"""
		return BlockInfo(blockType = BlockInfo.TYPE_FC,
				 blockIndex = self.index,
				 identHash = self.identHash)

	def __repr__(self):
		return "FC %d" % self.index

class AwlLibFB(AwlLibEntry):
	"""Base class for library FBs."""

	_isFB = True

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
		code.append(self.getCodeHeaders() + "\n")
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

	def getBlockInfo(self):
		"""Get a BlockInfo instance for this block.
		"""
		return BlockInfo(blockType = BlockInfo.TYPE_FB,
				 blockIndex = self.index,
				 identHash = self.identHash)

	def __repr__(self):
		return "FB %d" % self.index

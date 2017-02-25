# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - Boolean element
#
# Copyright 2016-2017 Michael Buesch <m@bues.ch>
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

from awlsim.fupcompiler.fupcompiler_elem import *
from awlsim.fupcompiler.fupcompiler_elemoper import *

#from awlsim.core.instructions.all_insns cimport * #@cy
from awlsim.core.instructions.all_insns import * #@nocy


class FupCompiler_ElemBool(FupCompiler_Elem):
	"""FUP compiler - Boolean element.
	"""

	EnumGen.start
	SUBTYPE_AND		= EnumGen.item
	SUBTYPE_OR		= EnumGen.item
	SUBTYPE_XOR		= EnumGen.item
	EnumGen.end

	str2subtype = {
		"and"		: SUBTYPE_AND,
		"or"		: SUBTYPE_OR,
		"xor"		: SUBTYPE_XOR,
	}

	@classmethod
	def parse(cls, grid, x, y, subType, content):
		try:
			subType = cls.str2subtype[subType]
			if subType == cls.SUBTYPE_AND:
				return FupCompiler_ElemBoolAnd(grid=grid,
							       x=x, y=y,
							       content=content)
			elif subType == cls.SUBTYPE_OR:
				return FupCompiler_ElemBoolOr(grid=grid,
							      x=x, y=y,
							      content=content)
			elif subType == cls.SUBTYPE_XOR:
				return FupCompiler_ElemBoolXor(grid=grid,
							       x=x, y=y,
							       content=content)
		except KeyError:
			pass
		return None

	def __init__(self, grid, x, y, subType, content):
		FupCompiler_Elem.__init__(self, grid=grid, x=x, y=y,
					  elemType=FupCompiler_Elem.TYPE_BOOLEAN,
					  subType=subType, content=content)

	def _doCompileBool(self, insnClass, insnBranchClass):
		insns = []
		# Walk down each input connection of this element.
		for conn in sorted(self.connections, key=lambda c: c.pos):
			if not conn.dirIn:
				continue
			# For each element that is connected to this element's
			# input connection via its output connection.
			for otherElem in conn.getConnectedElems(viaOut=True):
				if otherElem.elemType == self.TYPE_OPERAND and\
				   otherElem.subType == FupCompiler_ElemOper.SUBTYPE_LOAD:
					# The other element is a LOAD operand.
					# Compile the boolean (load) instruction.
					try:
						otherElem.setInsnClass(insnClass)
						insns.extend(otherElem.compile())
					finally:
						otherElem.setInsnClass(None)
				elif otherElem.elemType == self.TYPE_BOOLEAN:
					# The other element we get the signal from
					# is a boolean element. Compile this to get its
					# resulting VKE.
					if otherElem.compileState == self.NOT_COMPILED:
						insns.append(insnBranchClass(cpu=None))
						insns.extend(otherElem.compile())
						# Store result to a TEMP variable, if required.
						insns.extend(otherElem._mayStoreToTemp())
						insns.append(AwlInsn_BEND(cpu=None))
					else:
						# Get the stored result from TEMP.
						insns.extend(otherElem._loadFromTemp(insnClass))
				else:
					raise AwlSimError("FUP compiler: Invalid "
						"element '%s' connected to '%s'." % (
						str(otherElem), str(self)))
		return insns

class FupCompiler_ElemBoolAnd(FupCompiler_ElemBool):
	"""FUP compiler - Boolean AND element.
	"""

	def __init__(self, grid, x, y, content):
		FupCompiler_ElemBool.__init__(self, grid=grid, x=x, y=y,
					      subType=FupCompiler_ElemBool.SUBTYPE_AND,
					      content=content)

	def _doCompile(self):
		return self._doCompileBool(AwlInsn_U, AwlInsn_UB)

class FupCompiler_ElemBoolOr(FupCompiler_ElemBool):
	"""FUP compiler - Boolean OR element.
	"""

	def __init__(self, grid, x, y, content):
		FupCompiler_ElemBool.__init__(self, grid=grid, x=x, y=y,
					      subType=FupCompiler_ElemBool.SUBTYPE_OR,
					      content=content)

	def _doCompile(self):
		return self._doCompileBool(AwlInsn_O, AwlInsn_OB)

class FupCompiler_ElemBoolXor(FupCompiler_ElemBool):
	"""FUP compiler - Boolean XOR element.
	"""

	def __init__(self, grid, x, y, content):
		FupCompiler_ElemBool.__init__(self, grid=grid, x=x, y=y,
					      subType=FupCompiler_ElemBool.SUBTYPE_XOR,
					      content=content)

	def _doCompile(self):
		return self._doCompileBool(AwlInsn_X, AwlInsn_XB)

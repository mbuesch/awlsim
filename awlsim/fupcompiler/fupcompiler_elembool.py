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

from awlsim.core.operators import * #+cimport
from awlsim.core.operatortypes import * #+cimport

from awlsim.core.instructions.all_insns import * #+cimport


class FupCompiler_ElemBool(FupCompiler_Elem):
	"""FUP compiler - Boolean element.
	"""

	ELEM_NAME = "BOOL"

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

	def __init__(self, grid, x, y, subType, content, **kwargs):
		FupCompiler_Elem.__init__(self, grid=grid, x=x, y=y,
					  elemType=FupCompiler_Elem.TYPE_BOOLEAN,
					  subType=subType, content=content,
					  **kwargs)

	def __getOutConn(self):
		outConnections = list(self.outConnections)
		if len(outConnections) != 1:
			raise FupElemError("Boolean elements only support one output.", self)
		return outConnections[0]

	def _doCompileBool(self, insnClass):
		insns = []
		# Walk down each input connection of this element.
		for conn in sorted(self.inConnections, key=lambda c: c.pos):
			# For each element that is connected to this element's
			# input connection via its output connection.
			otherConn = conn.getConnectedConn(getOutput=True)
			otherElem = otherConn.elem
			if otherElem.isType(self.TYPE_OPERAND,
					    FupCompiler_ElemOper.SUBTYPE_LOAD):
				# The other element is a LOAD operand.
				# Compile the boolean (load) instruction.
				# This generates:  U #oper , O #oper or something similar.
				insns.extend(otherElem.compileOperLoad(
						insnClass,
						{ FupCompiler_Conn.TYPE_VKE, },
						inverted=conn.inverted))
			elif otherElem.isType(self.TYPE_BOOLEAN):
				# The other element we get the signal from
				# is a boolean element. Compile this to get its
				# resulting VKE.
				insns.extend(otherElem.compileToVKE(insnClass=insnClass,
								    inverted=conn.inverted))
			else:
				insns.extend(otherConn.compileConn(targetInsnClass=insnClass,
								   inverted=conn.inverted))
		outConn = self.__getOutConn()
		if outConn.inverted:
			insns.append(self.newInsn(AwlInsn_NOT))
		return insns

	def compileToVKE(self, insnClass, inverted=False):
		"""Compile this boolean operation in a way that after the last
		instruction returned by this method the result of this element
		resides in the VKE.
		insnClass => The AwlInsn class used to load to VKE.
		Returns a list of AwlInsn instances.
		"""
		insns = []
		if self.needCompile:
			insnBranchClass = self.compiler.branchInsnClass[insnClass]
			if inverted:
				insnBranchClass = self.compiler.invertedInsnClass[insnBranchClass]
			insns.append(self.newInsn(insnBranchClass))
			insns.extend(self.compile())
			# Store result to a TEMP variable, if required.
			if len(tuple(self.__getOutConn().getConnectedConns(getInputs=True))) > 1:
				insns.extend(self._storeToTemp("BOOL", AwlInsn_ASSIGN))
			insns.append(self.newInsn(AwlInsn_BEND))
		else:
			# Get the stored result from TEMP.
			if inverted:
				insnClass = self.compiler.invertedInsnClass[insnClass]
			insns.extend(self._loadFromTemp(insnClass))
		return insns

class FupCompiler_ElemBoolAnd(FupCompiler_ElemBool):
	"""FUP compiler - Boolean AND element.
	"""

	ELEM_NAME = "AND"

	def __init__(self, grid, x, y, content, **kwargs):
		FupCompiler_ElemBool.__init__(self, grid=grid, x=x, y=y,
					      subType=FupCompiler_ElemBool.SUBTYPE_AND,
					      content=content,
					      **kwargs)

	def _doCompile(self):
		return self._doCompileBool(AwlInsn_U)

class FupCompiler_ElemBoolOr(FupCompiler_ElemBool):
	"""FUP compiler - Boolean OR element.
	"""

	ELEM_NAME = "OR"

	def __init__(self, grid, x, y, content, **kwargs):
		FupCompiler_ElemBool.__init__(self, grid=grid, x=x, y=y,
					      subType=FupCompiler_ElemBool.SUBTYPE_OR,
					      content=content,
					      **kwargs)

	def _doCompile(self):
		return self._doCompileBool(AwlInsn_O)

class FupCompiler_ElemBoolXor(FupCompiler_ElemBool):
	"""FUP compiler - Boolean XOR element.
	"""

	ELEM_NAME = "XOR"

	def __init__(self, grid, x, y, content, **kwargs):
		FupCompiler_ElemBool.__init__(self, grid=grid, x=x, y=y,
					      subType=FupCompiler_ElemBool.SUBTYPE_XOR,
					      content=content,
					      **kwargs)

	def _doCompile(self):
		return self._doCompileBool(AwlInsn_X)

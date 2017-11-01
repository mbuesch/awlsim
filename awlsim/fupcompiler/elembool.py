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

from awlsim.fupcompiler.elem import *
from awlsim.fupcompiler.elemoper import *

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
	SUBTYPE_S		= EnumGen.item
	SUBTYPE_R		= EnumGen.item
	SUBTYPE_SR		= EnumGen.item
	SUBTYPE_RS		= EnumGen.item
	SUBTYPE_FP		= EnumGen.item
	SUBTYPE_FN		= EnumGen.item
	EnumGen.end

	str2subtype = {
		"and"		: SUBTYPE_AND,
		"or"		: SUBTYPE_OR,
		"xor"		: SUBTYPE_XOR,
		"s"		: SUBTYPE_S,
		"r"		: SUBTYPE_R,
		"sr"		: SUBTYPE_SR,
		"rs"		: SUBTYPE_RS,
		"fp"		: SUBTYPE_FP,
		"fn"		: SUBTYPE_FN,
	}

	@classmethod
	def parse(cls, grid, x, y, subType, content):
		try:
			subType = cls.str2subtype[subType]
			type2class = {
				cls.SUBTYPE_AND		: FupCompiler_ElemBoolAnd,
				cls.SUBTYPE_OR		: FupCompiler_ElemBoolOr,
				cls.SUBTYPE_XOR		: FupCompiler_ElemBoolXor,
				cls.SUBTYPE_S		: FupCompiler_ElemBoolS,
				cls.SUBTYPE_R		: FupCompiler_ElemBoolR,
				cls.SUBTYPE_SR		: FupCompiler_ElemBoolSR,
				cls.SUBTYPE_RS		: FupCompiler_ElemBoolRS,
				cls.SUBTYPE_FP		: FupCompiler_ElemBoolFP,
				cls.SUBTYPE_FN		: FupCompiler_ElemBoolFN,
			}
			elemClass = None
			with contextlib.suppress(KeyError):
				elemClass = type2class[subType]
			if elemClass:
				return elemClass(grid=grid,
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

	def _getBodyOper(self):
		"""Get the body operand.
		"""
		if len(self.subElems) != 1:
			raise FupElemError("Invalid body operator in '%s'" % (
				str(self)),
				self)
		subElem = getany(self.subElems)
		if not subElem.isType(FupCompiler_Elem.TYPE_OPERAND,
				      FupCompiler_ElemOper.SUBTYPE_EMBEDDED):
			raise FupElemError("Body operator element '%s' "
				"is of invalid type." % (
				str(subElem)),
				self)
		return subElem

	def getOutConn(self):
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
				insns.extend(otherConn.compileConn(
						targetInsnClass=insnClass,
						inverted=conn.inverted))
			elif otherElem.isType(self.TYPE_BOOLEAN):
				# The other element we get the signal from
				# is a boolean element. Compile this to get its
				# resulting VKE.
				insns.extend(otherElem.__compileToVKE(insnClass=insnClass,
								    inverted=conn.inverted))
			else:
				insnBranchClass = self.compiler.branchInsnClass[insnClass]
				insns.append(self.newInsn(insnBranchClass, parentFupConn=conn))
				insns.extend(otherConn.compileConn(targetInsnClass=insnClass,
								   inverted=conn.inverted))
				insns.append(self.newInsn(AwlInsn_BEND, parentFupConn=conn))
		outConn = self.getOutConn()
		if outConn.inverted:
			insns.append(self.newInsn(AwlInsn_NOT, parentFupConn=outConn))
		return insns

	def __compileToVKE(self, insnClass, inverted=False):
		"""Compile this boolean operation in a way that after the last
		instruction returned by this method the result of this element
		resides in the VKE.
		insnClass => The AwlInsn class used to load to VKE.
		Returns a list of AwlInsn instances.
		"""
		insns = []
		outConn = self.getOutConn()
		if self.needCompile:
			insnBranchClass = self.compiler.branchInsnClass[insnClass]
			if inverted:
				insnBranchClass = self.compiler.invertedInsnClass[insnBranchClass]
			insns.append(self.newInsn(insnBranchClass, parentFupConn=outConn))
			insns.extend(self.compile())
			# Store result to a TEMP variable, if required.
			if len(tuple(outConn.getConnectedConns(getInputs=True))) > 1:
				insns.extend(self._storeToTemp("BOOL", AwlInsn_ASSIGN,
							       { outConn,
							         self.MAIN_RESULT }))
			insns.append(self.newInsn(AwlInsn_BEND, parentFupConn=outConn))
		else:
			# Get the stored result from TEMP.
			if inverted:
				insnClass = self.compiler.invertedInsnClass[insnClass]
			insns.extend(self._loadFromTemp(insnClass, conn=outConn))
		return insns

	def compileConn(self, conn, desiredTarget, inverted=False):
		self._compileConn_checkTarget(conn, desiredTarget, inverted,
					      targetExpectVKE=True,
					      allowInversion=True)
		insnClass = FupCompiler_Conn.targetToInsnClass(desiredTarget,
							       toLoad=conn.dirOut,
							       inverted=inverted)
		return self.__compileToVKE(insnClass)

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

class FupCompiler_ElemBoolSR(FupCompiler_ElemBool):
	"""FUP compiler - Boolean SR element.
	"""

	ELEM_NAME	= "SR"
	SUBTYPE		= FupCompiler_ElemBool.SUBTYPE_SR
	HAVE_S		= True
	HAVE_R		= True
	HIGH_PRIO_R	= True
	OPTIONAL_CONNS	= { "R", "Q", }

	def __init__(self, grid, x, y, content, **kwargs):
		FupCompiler_ElemBool.__init__(self, grid=grid, x=x, y=y,
					      subType=self.SUBTYPE,
					      content=content,
					      **kwargs)

	def __compileSR(self, bodyOper, connName, insnClass):
		conn = self.getUniqueConnByText(connName, searchInputs=True)
		if not conn or not conn.isConnected:
			return []
		otherConn = conn.getConnectedConn(getOutput=True)
		insns = otherConn.compileConn(targetInsnClass=AwlInsn_U,
					      inverted=conn.inverted)
		insns.extend(bodyOper.compileAs(insnClass))
		return insns

	def __compileS(self, bodyOper):
		if not self.HAVE_S:
			return []
		return self.__compileSR(bodyOper, "S", AwlInsn_S)

	def __compileR(self, bodyOper):
		if not self.HAVE_R:
			return []
		return self.__compileSR(bodyOper, "R", AwlInsn_R)

	@property
	def isCompileEntryPoint(self):
		# We are a compilation entry, if Q is not connected.
		conn = self.getUniqueConnByText("Q", searchOutputs=True)
		if not conn or not conn.isConnected:
			return True
		return False

	def _doCompile(self):
		insns = []

		bodyOper = self._getBodyOper()

		# Compile S and R inputs
		if self.HIGH_PRIO_R:
			insns.extend(self.__compileS(bodyOper))
			insns.extend(self.__compileR(bodyOper))
		else:
			insns.extend(self.__compileR(bodyOper))
			insns.extend(self.__compileS(bodyOper))

		# Compile Q output
		conn_Q = self.getUniqueConnByText("Q", searchOutputs=True)
		if conn_Q and conn_Q.isConnected:
			insns.extend(bodyOper.compileAs(AwlInsn_UN if conn_Q.inverted
							else AwlInsn_U))

		return insns

	def connIsOptional(self, conn):
		return conn.hasText(self.OPTIONAL_CONNS)

class FupCompiler_ElemBoolRS(FupCompiler_ElemBoolSR):
	"""FUP compiler - Boolean RS element.
	"""

	ELEM_NAME	= "RS"
	SUBTYPE		= FupCompiler_ElemBool.SUBTYPE_RS
	HAVE_S		= True
	HAVE_R		= True
	HIGH_PRIO_R	= False
	OPTIONAL_CONNS	= { "S", "Q", }

class FupCompiler_ElemBoolS(FupCompiler_ElemBoolSR):
	"""FUP compiler - Boolean S element.
	"""

	ELEM_NAME	= "S"
	SUBTYPE		= FupCompiler_ElemBool.SUBTYPE_S
	HAVE_S		= True
	HAVE_R		= False
	HIGH_PRIO_R	= False
	OPTIONAL_CONNS	= { "Q", }

	def _doCompile(self):
		# Enforce connection names.
		# They might not be present in the project file.
		if len(list(self.inConnections)) == 1:
			getany(self.inConnections).text = self.ELEM_NAME
		if len(list(self.outConnections)) == 1:
			getany(self.outConnections).text = "Q"

		# Run the SR compiler
		return FupCompiler_ElemBoolSR._doCompile(self)

class FupCompiler_ElemBoolR(FupCompiler_ElemBoolS):
	"""FUP compiler - Boolean R element.
	"""

	ELEM_NAME	= "R"
	SUBTYPE		= FupCompiler_ElemBool.SUBTYPE_R
	HAVE_S		= False
	HAVE_R		= True
	HIGH_PRIO_R	= True
	OPTIONAL_CONNS	= { "Q", }

class FupCompiler_ElemBoolFP(FupCompiler_ElemBool):
	"""FUP compiler - Boolean FP element.
	"""

	ELEM_NAME	= "FP"
	SUBTYPE		= FupCompiler_ElemBool.SUBTYPE_FP
	POSITIVE	= True

	def __init__(self, grid, x, y, content, **kwargs):
		FupCompiler_ElemBool.__init__(self, grid=grid, x=x, y=y,
					      subType=self.SUBTYPE,
					      content=content,
					      **kwargs)

	def _doCompile(self):
		insns = []

		bodyOper = self._getBodyOper()

		inConns = list(self.inConnections)
		if len(inConns) != 1:
			raise FupElemError("Invalid number of input connections",
				self)
		inConn = inConns[0]

		outConns = list(self.outConnections)
		if len(outConns) != 1:
			raise FupElemError("Invalid number of output connections",
				self)
		outConn = outConns[0]

		otherConn = inConn.getConnectedConn(getOutput=True)
		insns.extend(otherConn.compileConn(targetInsnClass=AwlInsn_U,
						   inverted=inConn.inverted))
		insns.extend(bodyOper.compileAs(AwlInsn_FP if self.POSITIVE
						else AwlInsn_FN))
		if outConn.inverted:
			insns.append(self.newInsn(AwlInsn_NOT, parentFupConn=outConn))

		return insns

class FupCompiler_ElemBoolFN(FupCompiler_ElemBoolFP):
	"""FUP compiler - Boolean FN element.
	"""

	ELEM_NAME	= "FN"
	SUBTYPE		= FupCompiler_ElemBool.SUBTYPE_FN
	POSITIVE	= False

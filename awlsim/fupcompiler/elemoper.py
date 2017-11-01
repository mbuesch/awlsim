# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - Operand element
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

from awlsim.core.operators import * #+cimport
from awlsim.core.operatortypes import * #+cimport

from awlsim.core.instructions.all_insns import * #+cimport


class FupCompiler_ElemOper(FupCompiler_Elem):
	"""FUP compiler - Operand element.
	"""

	ELEM_NAME		= "operator"
	IS_LOAD_OPER		= False
	IS_EMBEDDED_OPER	= False

	EnumGen.start
	SUBTYPE_LOAD		= EnumGen.item
	SUBTYPE_ASSIGN		= EnumGen.item
	SUBTYPE_EMBEDDED	= EnumGen.item
	EnumGen.end

	str2subtype = {
		"load"		: SUBTYPE_LOAD,
		"assign"	: SUBTYPE_ASSIGN,
		"embedded"	: SUBTYPE_EMBEDDED,
	}

	@classmethod
	def parse(cls, grid, x, y, subType, content):
		try:
			subType = cls.str2subtype[subType]
			type2class = {
				cls.SUBTYPE_LOAD	: FupCompiler_ElemOperLoad,
				cls.SUBTYPE_ASSIGN	: FupCompiler_ElemOperAssign,
				cls.SUBTYPE_EMBEDDED	: FupCompiler_ElemOperEmbedded,
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
					  elemType=FupCompiler_Elem.TYPE_OPERAND,
					  subType=subType, content=content,
					  **kwargs)

		# The translated operator, if any, yet.
		# This will be available after compilation of this element.
		self._operator = None
		self.__operatorWidth = None

	def _getConn(self, getInput=True):
		"""Get the one connection of this element.
		"""
		# Only one connection allowed per oper.
		if len(self.connections) != 1:
			raise FupOperError("Invalid number of "
				"connections in '%s'." % (
				str(self)),
				self)

		# The connection must be input.
		conn = getany(self.connections)
		if conn.dirIn != getInput or\
		   conn.dirOut == getInput or\
		   conn.pos != 0:
			raise FupOperError("Invalid connection "
				"properties in '%s'." % (
				str(self)),
				self)
		return conn

	def _getConnectedElem(self, viaOut=True):
		"""Get the element that is connected to this operator element.
		"""
		conn = self._getConn(getInput=viaOut)
		otherElem = conn.getConnectedElem(viaOut=viaOut)
		return otherElem

	def _translateContent(self):
		"""Translate the element content and create self._operator,
		if not already done so.
		"""
		if not self._operator:
			if not self.content.strip():
				raise FupOperError("Found empty operator: %s" % (
					str(self)),
					self)
			opDesc = self.opTrans.translateFromString(self.content)
			self._operator = opDesc.operator
		return self._operator

	@property
	def operatorWidth(self):
		if self.__operatorWidth is None:
			if self._operator:
				# Get the width of a possibly symbolic operator.
				compiler = self.grid.compiler
				width = compiler.getOperDataWidth(self._operator)
				self.__operatorWidth = width
				return width
		else:
			return self.__operatorWidth
		# Unknown width
		return 0

	def getConnType(self, conn, preferVKE=False):
		if conn in self.connections or conn is None:
			self._translateContent()
			operType = self._operator.operType
			if operType == AwlOperatorTypes.SYMBOLIC:
				pass#TODO
			if operType in {AwlOperatorTypes.MEM_T,
					AwlOperatorTypes.MEM_Z}:
				if preferVKE:
					return FupCompiler_Conn.TYPE_VKE
				return FupCompiler_Conn.TYPE_ACCU
			operWidth = self.operatorWidth
			if operWidth == 1:
				return FupCompiler_Conn.TYPE_VKE
			elif operWidth in {8, 16, 32}:
				return FupCompiler_Conn.TYPE_ACCU
		return FupCompiler_Conn.TYPE_UNKNOWN

	def compileAs(self, insnClass):
		"""Compile this operator as the specified instruction.
		This may be AwlInsn_U, AwlInsn_S or similar.
		"""
		insns = []

		self._translateContent()

		if self.IS_EMBEDDED_OPER:
			conn = None
		else:
			conn = self._getConn(not self.IS_LOAD_OPER)

		insns.append(self.newInsn(insnClass, ops=[self._operator],
					  parentFupConn=conn))

		return insns

	def compileConn(self, conn, desiredTarget, inverted=False):
		self.compileState = self.COMPILE_RUNNING

		insns = []

		assert(conn in self.connections)
		insnClass = FupCompiler_Conn.targetToInsnClass(desiredTarget,
							       toLoad=conn.dirOut,
							       inverted=inverted)
		insns.extend(self.compileAs(insnClass))

		self.compileState = self.COMPILE_DONE
		return insns

	def __str__(self):
		extra = []
		if len(self.connections) == 1:
			conn = getany(self.connections)
			elems = list(conn.getConnectedElems(viaOut=conn.dirIn,
							    viaIn=conn.dirOut))
			if elems:
				text = []
				for elem in elems:
					text.append(elem.toStr())
				extra.append("for " + " and ".join(text))
		return self.toStr(extra=extra)

class FupCompiler_ElemOperLoad(FupCompiler_ElemOper):
	"""FUP compiler - Operand LOAD element.
	"""

	ELEM_NAME		= "LOAD"
	IS_LOAD_OPER		= True
	IS_EMBEDDED_OPER	= False

	# Allow multiple compilations of LOAD operand.
	allowTrans_done2Running = True

	def __init__(self, grid, x, y, content, **kwargs):
		FupCompiler_ElemOper.__init__(self, grid=grid, x=x, y=y,
					      subType=FupCompiler_ElemOper.SUBTYPE_LOAD,
					      content=content,
					      **kwargs)

	def _doCompile(self):
		insns = []

		# Translate the operator content
		self._translateContent()

		# Infer the instruction class from the operator.
		# Note that this can't distinguish between different
		# boolean types and always uses U.
		if self.operatorWidth == 1:
			insnClass = AwlInsn_U
		elif self.operatorWidth in {8, 16, 32}:
			insnClass = AwlInsn_L
		else:
			raise FupOperError("Invalid operator width %d "
				"in load operator: %s" % (
				self.operatorWidth, str(self)),
				self)

		# Create the LOAD instruction.
		insns.extend(self.compileAs(insnClass))

		return insns

class FupCompiler_ElemOperAssign(FupCompiler_ElemOper):
	"""FUP compiler - Operand ASSIGN element.
	"""

	ELEM_NAME		= "STORE"
	IS_LOAD_OPER		= False
	IS_EMBEDDED_OPER	= False

	def __init__(self, grid, x, y, content, **kwargs):
		FupCompiler_ElemOper.__init__(self, grid=grid, x=x, y=y,
					      subType=FupCompiler_ElemOper.SUBTYPE_ASSIGN,
					      content=content,
					      **kwargs)
		self.__storeEmitted = False

	@property
	def isCompileEntryPoint(self):
		return True # This is a compilation entry point.

	def _doCompile(self):
		insns = []

		# Get the element that is connected to this operator.
		otherElem = self._getConnectedElem()

		# Translate the operator.
		# Do this before compiling the connected element so that
		# the operator is available to the element.
		self._translateContent()

		# Compile the element connected to the input.
		if otherElem.needCompile:
			insns.extend(otherElem.compile())
		else:
			if not self.__storeEmitted:
				insns.extend(otherElem._loadFromTemp(AwlInsn_U))
		if not self.__storeEmitted:
			# This assign operator has not been emitted, yet.
			# Do a VKE store now.
			insns.extend(self.emitStore_VKE())

			# Compile additional assign operators.
			# This is an optimization to avoid additional compilations
			# of the whole tree. We just assign the VKE once again.
			#FIXME this might lead to problems in evaluation order, if we have a branch with interleaved assigns and other elems.
			conn = getany(self.connections)
			for otherElem in self.sorted(conn.getConnectedElems(viaIn=True)):
				if otherElem.isType(self.TYPE_OPERAND,
						    self.SUBTYPE_ASSIGN):
					otherElem.compileState = self.COMPILE_RUNNING
					insns.extend(otherElem.compileAs(AwlInsn_ASSIGN))
					otherElem.compileState = self.COMPILE_DONE

		return insns

	def emitStore_VKE(self):
		"""Emit a VKE store instruction (=) for this operator element.
		This does not check whether the operator actually is a boolean operator.
		A list of instructions is returned.
		"""
		insns = []

		# Create the ASSIGN instruction.
		insns.extend(self.compileAs(AwlInsn_ASSIGN))
		otherElem = self._getConnectedElem()

		# If the other element connected to this operand is a boolean and has more
		# than one connected element, we need to store the VKE for them.
		if otherElem.isType(self.TYPE_BOOLEAN):
			if any(len(tuple(c.getConnectedConns(getInputs=True))) > 1
			       for c in otherElem.outConnections):
				outConn = otherElem.getOutConn()
				insns.extend(otherElem._storeToTemp("BOOL", AwlInsn_ASSIGN,
								    { outConn,
								      otherElem.MAIN_RESULT }))

		self.__storeEmitted = True
		return insns

	def emitStore_ACCU(self):
		"""Emit an ACCU store instruction (T) for this operator element.
		This does not check whether the operator actually is a non-bool operator.
		A list of instructions is returned.
		"""
		insns = []

		# Create a transfer instruction.
		insns.extend(self.compileAs(AwlInsn_T))

		self.__storeEmitted = True
		return insns

class FupCompiler_ElemOperEmbedded(FupCompiler_ElemOper):
	"""FUP compiler - Embedded operand element.
	"""

	ELEM_NAME		= "EMBEDDED"
	IS_LOAD_OPER		= False
	IS_EMBEDDED_OPER	= True

	def __init__(self, grid, x, y, content, **kwargs):
		FupCompiler_ElemOper.__init__(self, grid=grid, x=x, y=y,
					      subType=FupCompiler_ElemOper.SUBTYPE_EMBEDDED,
					      content=content,
					      **kwargs)

	def _doCompile(self):
		raise FupOperError("It's unknown how to compile "
			"the embedded operand.",
			self)

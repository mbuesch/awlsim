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

from awlsim.fupcompiler.fupcompiler_elem import *

from awlsim.core.operators import * #+cimport
from awlsim.core.operatortypes import * #+cimport

from awlsim.core.instructions.all_insns import * #+cimport


class FupCompiler_ElemOper(FupCompiler_Elem):
	"""FUP compiler - Operand element.
	"""

	ELEM_NAME = "operator"

	EnumGen.start
	SUBTYPE_LOAD		= EnumGen.item
	SUBTYPE_ASSIGN		= EnumGen.item
	EnumGen.end

	str2subtype = {
		"load"		: SUBTYPE_LOAD,
		"assign"	: SUBTYPE_ASSIGN,
	}

	@classmethod
	def parse(cls, grid, x, y, subType, content):
		try:
			subType = cls.str2subtype[subType]
			if subType == cls.SUBTYPE_LOAD:
				return FupCompiler_ElemOperLoad(grid=grid,
							        x=x, y=y,
							        content=content)
			elif subType == cls.SUBTYPE_ASSIGN:
				return FupCompiler_ElemOperAssign(grid=grid,
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

	def getConnType(self, conn):
		if conn in self.connections or conn is None:
			operWidth = self.operatorWidth
			if operWidth == 1:
				return FupCompiler_Conn.TYPE_VKE
			elif operWidth in {8, 16, 32}:
				return FupCompiler_Conn.TYPE_ACCU
		return FupCompiler_Conn.TYPE_UNKNOWN

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

	ELEM_NAME = "LOAD"

	# Allow multiple compilations of LOAD operand.
	allowTrans_done2Running = True

	def __init__(self, grid, x, y, content, **kwargs):
		FupCompiler_ElemOper.__init__(self, grid=grid, x=x, y=y,
					      subType=FupCompiler_ElemOper.SUBTYPE_LOAD,
					      content=content,
					      **kwargs)

		# Constructor class used for LOAD operand.
		self.__insnClass = None

	def setInsnClass(self, insnClass, inverted=False):
		if inverted and insnClass:
			insnClass = self.compiler.invertedInsnClass[insnClass]
		self.__insnClass = insnClass

	def compileOperLoad(self, insnClass, allowedConnTypes, inverted=False):
		"""Set the instruction class and compile this load operator.
		insnClass => The AwlInsn class that performs the load.
		allowedConnTypes => Iterable of allowed connection types.
		Returns the instruction.
		"""
		try:
			self.setInsnClass(insnClass, inverted)
			insn = self.compile()
			if self.getConnType(None) not in allowedConnTypes:
				raise FupOperError("The load operand '%s' type is not "
					"allowed here." % (
					str(self)),
					self)
			return insn
		finally:
			self.setInsnClass(None)

	def _doCompile(self):
		insns = []

		# Translate the operator
		if not self.content.strip():
			raise FupOperError("Found empty load operator: %s" % (
				str(self)),
				self)
		opDesc = self.opTrans.translateFromString(self.content)
		self._operator = opDesc.operator

		insnClass = self.__insnClass
		if not insnClass:
			# No instruction class has been set.
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
		insns.append(self.newInsn(insnClass, ops=[self._operator]))

		return insns

class FupCompiler_ElemOperAssign(FupCompiler_ElemOper):
	"""FUP compiler - Operand ASSIGN element.
	"""

	ELEM_NAME = "STORE"

	def __init__(self, grid, x, y, content, **kwargs):
		FupCompiler_ElemOper.__init__(self, grid=grid, x=x, y=y,
					      subType=FupCompiler_ElemOper.SUBTYPE_ASSIGN,
					      content=content,
					      **kwargs)
		self.__storeEmitted = False

	def _doCompile(self):
		insns = []

		# Get the element that is connected to this operator.
		otherElem = self.__getConnectedElem()

		# Translate the operator.
		# Do this before compiling the connected element so that
		# the operator is available to the element.
		self.__translateContent()

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
				if otherElem.elemType == self.TYPE_OPERAND and\
				   otherElem.subType == self.SUBTYPE_ASSIGN:
					otherElem.compileState = self.COMPILE_RUNNING
					opDesc = self.opTrans.translateFromString(otherElem.content)
					insns.append(self.newInsn(AwlInsn_ASSIGN, ops=[opDesc.operator]))
					otherElem.compileState = self.COMPILE_DONE

		return insns

	def __getConn(self):
		"""Get the one input connection of this element.
		"""
		# Only one connection allowed per ASSIGN.
		if len(self.connections) != 1:
			raise FupOperError("Invalid number of "
				"connections in '%s'." % (
				str(self)),
				self)

		# The connection must be input.
		conn = getany(self.connections)
		if not conn.dirIn or conn.dirOut or conn.pos != 0:
			raise FupOperError("Invalid connection "
				"properties in '%s'." % (
				str(self)),
				self)

		return conn

	def __getConnectedElem(self):
		"""Get the element that is connected to this operator element.
		"""
		conn = self.__getConn()
		otherElem = conn.getConnectedElem(viaOut=True)
		return otherElem

	def __translateContent(self):
		"""Translate the element content and create self._operator,
		if not already done so.
		"""
		if self._operator:
			return
		if not self.content.strip():
			raise FupOperError("Found empty assignment operator %s "
				"that is connected to %s" % (
				str(self), str(self.__getConnectedElem())),
				self)
		opDesc = self.opTrans.translateFromString(self.content)
		self._operator = opDesc.operator

	def emitStore_VKE(self):
		"""Emit a VKE store instruction (=) for this operator element.
		This does not check whether the operator actually is a boolean operator.
		A list of instructions is returned.
		"""
		insns = []

		# Translate the assign operator content, if not already done so.
		self.__translateContent()

		# Create the ASSIGN instruction.
		insns.append(self.newInsn(AwlInsn_ASSIGN, ops=[self._operator]))
		otherElem = self.__getConnectedElem()

		# If the other element connected to this operand is a boolean and has more
		# than one connected element, we need to store the VKE for them.
		if otherElem.isType(self.TYPE_BOOLEAN):
			if any(len(tuple(c.getConnectedConns(getInputs=True))) > 1
			       for c in otherElem.outConnections):
				insns.extend(otherElem._storeToTemp("BOOL", AwlInsn_ASSIGN))

		self.__storeEmitted = True
		return insns

	def emitStore_ACCU(self):
		"""Emit an ACCU store instruction (T) for this operator element.
		This does not check whether the operator actually is a non-bool operator.
		A list of instructions is returned.
		"""
		insns = []

		# Translate the assign operator content, if not already done so.
		self.__translateContent()

		# Create a transfer instruction.
		insns.append(self.newInsn(AwlInsn_T, ops=[self._operator]))

		self.__storeEmitted = True
		return insns

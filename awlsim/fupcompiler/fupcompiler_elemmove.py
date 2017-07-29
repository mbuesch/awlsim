# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - Move box
#
# Copyright 2017 Michael Buesch <m@bues.ch>
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
from awlsim.fupcompiler.fupcompiler_elembool import *

from awlsim.core.operators import * #+cimport
from awlsim.core.operatortypes import * #+cimport

from awlsim.core.instructions.all_insns import * #+cimport

import re


class FupCompiler_ElemMove(FupCompiler_Elem):
	"""FUP compiler - Move box.
	"""

	ELEM_NAME = "MOVEBOX"

	@classmethod
	def parse(cls, grid, x, y, subType, content):
		return FupCompiler_ElemMove(grid=grid,
					    x=x, y=y,
					    content=content)

	def __init__(self, grid, x, y, content, **kwargs):
		FupCompiler_Elem.__init__(self, grid=grid, x=x, y=y,
					  elemType=FupCompiler_Elem.TYPE_MOVE,
					  subType=None,
					  content=content,
					  **kwargs)

	def connIsOptional(self, conn):
		connText = conn.text.upper()
		return connText in {"EN", "ENO"}

	def getConnType(self, conn):
		if conn in self.connections:
			connText = conn.text.upper()
			if connText in {"EN", "ENO"}:
				return FupCompiler_Conn.TYPE_VKE
			return FupCompiler_Conn.TYPE_ACCU
		return FupCompiler_Conn.TYPE_UNKNOWN

	def __getConnections(self):
		conn_EN = self.getUniqueConnByText("EN", searchInputs=True)
		conn_IN = self.getUniqueConnByText("IN", searchInputs=True)
		conn_ENO = self.getUniqueConnByText("ENO", searchOutputs=True)
		if not conn_EN or not conn_IN or not conn_ENO:
			raise FupElemError("Invalid connections "
				"in FUP move box %s." % (
				str(self)),
				self)
		return conn_EN, conn_IN, conn_ENO

	def compileConn(self, conn, desiredTarget, inverted=False):
		insns = []
		assert(conn in self.connections)
		if conn.hasText("ENO"):
			if not FupCompiler_Conn.targetIsVKE(desiredTarget):
				raise FupElemError("The ENO output "
					"of FUP move box %s must only be connected "
					"to boolean inputs." % (
					str(self)),
					self)
			if self.needCompile:
				insns.extend(self.compile())
				if inverted:
					insns.append(self.newInsn(AwlInsn_NOT))
			else:
				awlInsnClass = FupCompiler_Conn.targetToInsnClass(desiredTarget,
										  toLoad=True,
										  inverted=inverted)
				insns.extend(conn.elem._loadFromTemp(awlInsnClass, conn))
		else:
			raise FupElemError("It is not known how to compile "
				"the connection '%s' of FUP move box %s." % (
				conn.text,
				str(self)),
				self)
		return insns

	def __genVirtualAND(self, leftConn, rightConn):
		# Transform this:
		#   [x]-----------------------[rightConn]
		#
		# into this:            _
		#   [x]---------------0|&|0---[rightConn]
		#   [leftConn]--------1|_|
		#
		# If leftConn is connected already (to y), the result will look like this:
		#                       _
		#   [x]---------------0|&|0---[rightConn]
		#   [leftConn]----+---1|_|
		#                 |
		#                 +----[y]
		#
		# x is at least one arbitrary connection.
		# leftConn must be an output.
		# rightConn must be an input.
		# rightConn must be connected (to x).

		assert(leftConn.dirOut)
		assert(rightConn.dirIn)
		assert(rightConn.isConnected)

		# Get the left-handed wire or create one.
		if leftConn.isConnected:
			leftWire = leftConn.wire
		else:
			leftWire = self.grid.newWire()
			leftWire.addConn(leftConn)

		# disconnect the right-handed connection from its wire.
		origWire = rightConn.wire
		origWire.removeConn(rightConn)

		# Create a new right-handed wire
		rightWire = self.grid.newWire()
		rightWire.addConn(rightConn)

		# Create a virtual AND element to connect the elements.
		virtElemAnd = FupCompiler_ElemBoolAnd(grid=self.grid,
						      x=self.x, y=self.y,
						      content=None,
						      virtual=True)
		virtElemAndIn0 = FupCompiler_Conn(elem=virtElemAnd,
						  pos=0,
						  dirIn=True, dirOut=False,
						  wireId=origWire.idNum,
						  text=None,
						  virtual=True)
		virtElemAnd.addConn(virtElemAndIn0)
		origWire.addConn(virtElemAndIn0)
		virtElemAndIn1 = FupCompiler_Conn(elem=virtElemAnd,
						  pos=1,
						  dirIn=True, dirOut=False,
						  wireId=leftWire.idNum,
						  text=None,
						  virtual=True)
		virtElemAnd.addConn(virtElemAndIn1)
		leftWire.addConn(virtElemAndIn1)
		virtElemAndOut = FupCompiler_Conn(elem=virtElemAnd,
						  pos=0,
						  dirIn=False, dirOut=True,
						  wireId=rightWire.idNum,
						  text=None,
						  virtual=True)
		virtElemAnd.addConn(virtElemAndOut)
		rightWire.addConn(virtElemAndOut)

	def _doPreprocess(self):
		conn_EN, conn_IN, conn_ENO = self.__getConnections()

		# Get the element that is connected via its output to our IN connection.
		connectedElem_IN = conn_IN.getConnectedElem(viaOut=True)

		# If the element connected to IN is not a LOAD operand, we must
		# take its ENO into account.
		# If we don't have a connection on EN, we implicitly connect
		# the IN-element's ENO to our EN here.
		# If we already have a connection on EN, we implicitly add an AND-element
		# between the IN-element's ENO and our EN.
		if not connectedElem_IN.isType(self.TYPE_OPERAND,
					       FupCompiler_ElemOper.SUBTYPE_LOAD):
			if not connectedElem_IN.isType(self.TYPE_MOVE):
				raise FupElemError("The element %s that is "
					"connected to IN of %s is not allowed here." % (
					str(connectedElem_IN), str(self)),
					self)
			otherConn_ENO = connectedElem_IN.getUniqueConnByText("ENO",
									     searchOutputs=True)
			if conn_EN.isConnected:
				self.__genVirtualAND(leftConn=otherConn_ENO,
						     rightConn=conn_EN)
			else:
				conn_EN.connectTo(otherConn_ENO)

	def _doCompile(self):
		insns = []

		conn_EN, conn_IN, conn_ENO = self.__getConnections()

		# Get the element that is connected via its output to our IN connection.
		connectedElem_IN = conn_IN.getConnectedElem(viaOut=True)

		# If the element connected to IN is not a LOAD operand, we have
		# a chained element (for example another move box).
		# Compile that first.
		if connectedElem_IN.needCompile and\
		   not connectedElem_IN.isType(self.TYPE_OPERAND,
					       FupCompiler_ElemOper.SUBTYPE_LOAD):
			insns.extend(connectedElem_IN.compile())

		# Generate a jump target label name for the EN jump.
		# This might end up being unused, though.
		endLabel = self.grid.compiler.newLabel()

		# If we have an EN input, emit the corresponding conditional jump.
		# If EN is not a plain operator, this might involve compiling
		# the connected element.
		if conn_EN.isConnected:
			otherElem = conn_EN.getConnectedElem(viaOut=True)
			if otherElem.isType(self.TYPE_OPERAND,
					    FupCompiler_ElemOper.SUBTYPE_LOAD):
				# The other element is a LOAD operand.
				# Compile the boolean (load) instruction.
				# This generates:  U #EN
				insns.extend(otherElem.compileOperLoad(
						AwlInsn_U,
						{ FupCompiler_Conn.TYPE_VKE, }))
			elif otherElem.isType(self.TYPE_BOOLEAN):
				# The other element we get the signal from
				# is a boolean element. Compile this to get its
				# resulting VKE.
				insns.extend(otherElem.compileToVKE(AwlInsn_U))
			elif otherElem.isType(self.TYPE_MOVE):
				if otherElem.needCompile:
					insns.extend(otherElem.compile())
				else:
					otherConn_ENO = otherElem.getUniqueConnByText("ENO", searchOutputs=True)
					insns.extend(otherElem._loadFromTemp(AwlInsn_U, otherConn_ENO))
			else:
				raise FupElemError("Invalid "
					"element '%s' connected to '%s'." % (
					str(otherElem), str(self)),
					self)

			# Emit the jump instruction.
			# This will evaluate the current VKE.
			oper = make_AwlOperator(AwlOperatorTypes.LBL_REF, 0, None, None)
			oper.immediateStr = endLabel
			insns.append(self.newInsn(AwlInsn_SPBNB, ops=[oper]))

		# Compile the element connected to the input.
		if connectedElem_IN.needCompile:
			insns.extend(connectedElem_IN.compile())
		else:
			insns.extend(connectedElem_IN._loadFromTemp(AwlInsn_L, self.MAIN_RESULT))
		if conn_IN.connType != FupCompiler_Conn.TYPE_ACCU:
			raise FupElemError("The IN connection "
				"of the FUP move box %s must not be connected "
				"to a bit (VKE) wire." % (
				str(self)),
				self)

		# Assign the outputs.
		storeToTempConns = set()
		for conn in self.outConnections:
			if not re.match(r"OUT\d+", conn.text, re.IGNORECASE):
				continue
			for otherElem in self.sorted(conn.getConnectedElems(viaIn=True)):
				if otherElem.isType(self.TYPE_OPERAND,
						    FupCompiler_ElemOper.SUBTYPE_ASSIGN):
					insns.extend(otherElem.emitStore_ACCU())
				else:
					storeToTempConns.add(conn)
		if storeToTempConns:
			storeToTempConns.add(self.MAIN_RESULT)
			insns.extend(self._storeToTemp("DWORD", AwlInsn_T, storeToTempConns))

		# Make sure BIE is set, if EN is not connected and ENO is connected.
		if not conn_EN.isConnected and conn_ENO.isConnected:
			# Set VKE=1 and create a dummy SPBNB to
			# set BIE=1 and /ER=0.
			# The SPBNB branch is never taken due to VKE=1.
			insns.append(self.newInsn(AwlInsn_SET))
			oper = make_AwlOperator(AwlOperatorTypes.LBL_REF, 0, None, None)
			oper.immediateStr = endLabel
			insns.append(self.newInsn(AwlInsn_SPBNB, ops=[oper]))

		# Create the jump target label for EN=0.
		# This might end up being unused, though.
		oper = make_AwlOperator(AwlOperatorTypes.IMM, 16, None, None)
		oper.immediate = 0
		insn = self.newInsn(AwlInsn_NOP, ops=[oper])
		insn.labelStr = endLabel
		insns.append(insn)

		# Handle ENO output.
		if conn_ENO.isConnected:
			# Add instruction:  U BIE
			oper = make_AwlOperator(AwlOperatorTypes.MEM_STW, 1,
						make_AwlOffset(0, 8), None)
			insns.append(self.newInsn(AwlInsn_U, ops=[oper]))

			# Add VKE assignment instruction.
			storeToTempConns = set()
			for otherElem in self.sorted(conn_ENO.getConnectedElems(viaIn=True)):
				if otherElem.isType(self.TYPE_OPERAND,
						    FupCompiler_ElemOper.SUBTYPE_ASSIGN):
					insns.extend(otherElem.emitStore_VKE())
				else:
					storeToTempConns.add(conn_ENO)
			if storeToTempConns:
				insns.extend(self._storeToTemp("BOOL", AwlInsn_ASSIGN,
							       storeToTempConns))

		return insns

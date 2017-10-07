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

from awlsim.fupcompiler.elem import *
from awlsim.fupcompiler.elemoper import *
from awlsim.fupcompiler.elembool import *
from awlsim.fupcompiler.helpers import *

from awlsim.core.operators import * #+cimport
from awlsim.core.operatortypes import * #+cimport

from awlsim.core.instructions.all_insns import * #+cimport


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
		return conn.hasText({"EN", "ENO"})

	def getConnType(self, conn, preferVKE=False):
		if conn in self.connections:
			if conn.hasText({"EN", "ENO"}):
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

		awlInsnClass = FupCompiler_Conn.targetToInsnClass(desiredTarget,
								  toLoad=True,
								  inverted=inverted)

		if conn.hasText("ENO"):
			self._compileConn_checkTarget(conn, desiredTarget, inverted,
						      targetExpectVKE=True,
						      allowInversion=True)
			if self.needCompile:
				insns.extend(self.compile())
				if inverted:
					insns.append(self.newInsn(AwlInsn_NOT))
			else:
				awlInsnClass = FupCompiler_Conn.targetToInsnClass(desiredTarget,
										  toLoad=True,
										  inverted=inverted)
				insns.extend(conn.elem._loadFromTemp(awlInsnClass, conn))
		elif conn.textMatch(r"OUT\d+"):
			self._compileConn_checkTarget(conn, desiredTarget, inverted,
						      targetExpectVKE=False,
						      allowInversion=False)
			if self.needCompile:
				insns.extend(self.compile())
			insns.extend(conn.elem._loadFromTemp(awlInsnClass, conn))
		else:
			return FupCompiler_Elem.compileConn(self, conn, desiredTarget, inverted)
		return insns

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
			FupCompiler_Helpers.genIntermediateBool(
					parentElem=self,
					elemsA=[connectedElem_IN],
					connNamesA=["ENO"],
					elemB=self,
					connNameB="EN",
					boolElemClass=FupCompiler_ElemBoolAnd)

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
			# Compile the element that drives this wire.
			otherConn = conn_EN.getConnectedConn(getOutput=True)
			insns.extend(otherConn.compileConn(targetInsnClass=AwlInsn_U,
							   inverted=False))

			# Emit the jump instruction.
			# This will evaluate the current VKE.
			insns.append(self.newInsn_JMP(AwlInsn_SPBNB, endLabel))

		# Compile the element connected to the input.
		otherConn_IN = conn_IN.getConnectedConn(getOutput=True)
		if connectedElem_IN.needCompile:
			insns.extend(connectedElem_IN.compile())
		else:
			insns.extend(otherConn_IN.compileConn(targetInsnClass=AwlInsn_L))
		if conn_IN.connType != FupCompiler_Conn.TYPE_ACCU:
			raise FupElemError("The IN connection "
				"of the FUP move box %s must not be connected "
				"to a bit (VKE) wire." % (
				str(self)),
				self)

		# Assign the outputs.
		storeToTempConns = set()
		for conn in FupCompiler_Conn.sorted(self.outConnections):
			if not conn.textMatch(r"OUT\d+"):
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
			insns.append(self.newInsn_JMP(AwlInsn_SPBNB, endLabel))

		# Create the jump target label for EN=0.
		# This might end up being unused, though.
		insns.append(self.newInsn_NOP(labelStr=endLabel))

		# Handle ENO output.
		if conn_ENO.isConnected:
			# Add instruction:  U BIE
			insns.append(self.newInsn_LOAD_BIE(AwlInsn_U))

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

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

	def __init__(self, grid, x, y, content):
		FupCompiler_Elem.__init__(self, grid=grid, x=x, y=y,
					  elemType=FupCompiler_Elem.TYPE_MOVE,
					  subType=None,
					  content=content)

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

	def _doCompile(self):
		insns = []

		conn_EN = self.getUniqueConnByText("EN", searchInputs=True)
		conn_IN = self.getUniqueConnByText("IN", searchInputs=True)
		conn_ENO = self.getUniqueConnByText("ENO", searchOutputs=True)
		if not conn_EN or not conn_IN or not conn_ENO:
			raise AwlSimError("FUP compiler: Invalid connections "
				"in FUP move box %s." % (
				str(self)))

		# Get the element that is connected via its output to our IN connection.
		connectedElem_IN = conn_IN.getConnectedElem(viaOut=True)

		# If the element connected to IN is not a LOAD operand, we have
		# a chained element (for example another move box).
		# Compile that first.
		if connectedElem_IN.compileState == self.NOT_COMPILED and\
		   (connectedElem_IN.elemType != self.TYPE_OPERAND or\
		    connectedElem_IN.subType != FupCompiler_ElemOper.SUBTYPE_LOAD):
			insns.extend(connectedElem_IN.compile())

		# Generate a jump target for the EN jump.
		endLabel = self.grid.compiler.newLabel()

		if conn_EN.isConnected:
			otherElem = conn_EN.getConnectedElem(viaOut=True)
			if otherElem.elemType == self.TYPE_OPERAND and\
			   otherElem.subType == FupCompiler_ElemOper.SUBTYPE_LOAD:
				# The other element is a LOAD operand.
				# Compile the boolean (load) instruction.
				# This generates:  U #EN
				insns.extend(otherElem.compileOperLoad(
						AwlInsn_U,
						{ FupCompiler_Conn.TYPE_VKE, }))
			elif otherElem.elemType == self.TYPE_BOOLEAN:
				# The other element we get the signal from
				# is a boolean element. Compile this to get its
				# resulting VKE.
				insns.extend(otherElem.compileToVKE(AwlInsn_U, AwlInsn_UB))
			else:
				raise AwlSimError("FUP compiler: Invalid "
					"element '%s' connected to '%s'." % (
					str(otherElem), str(self)))

			oper = make_AwlOperator(AwlOperatorTypes.LBL_REF, 0, None, None)
			oper.immediateStr = endLabel
			insns.append(AwlInsn_SPBNB(cpu=None, ops=[oper]))

		# Compile the element connected to the input.
		if connectedElem_IN.compileState == self.NOT_COMPILED:
			insns.extend(connectedElem_IN.compile())
		else:
			insns.extend(connectedElem_IN._loadFromTemp(AwlInsn_L))
		if conn_IN.connType != FupCompiler_Conn.TYPE_ACCU:
			raise AwlSimError("FUP compiler: The IN connection "
				"of the FUP move box %s must not be connected "
				"to a bit (VKE) wire." % (
				str(self)))

		# Assign the outputs.
		storeToTemp = False
		for conn in self.outConnections:
			if not re.match(r"OUT\d+", conn.text, re.IGNORECASE):
				continue
			for otherElem in self.sorted(conn.getConnectedElems(viaIn=True)):
				if otherElem.elemType == self.TYPE_OPERAND and\
				   otherElem.subType == FupCompiler_ElemOper.SUBTYPE_ASSIGN:
					insns.extend(otherElem.emitStore_ACCU())
				else:
					storeToTemp = True
		if storeToTemp:
			insns.extend(self._storeToTemp("DWORD", AwlInsn_T))

		# Make sure BIE is set, if EN is not connected and ENO is connected.
		if not conn_EN.isConnected and conn_ENO.isConnected:
			# Set VKE=1 and create a dummy SPBNB to
			# set BIE=1 and /ER=0.
			# The SPBNB branch is never taken due to VKE=1.
			insns.append(AwlInsn_SET(cpu=None, ops=[]))
			oper = make_AwlOperator(AwlOperatorTypes.LBL_REF, 0, None, None)
			oper.immediateStr = endLabel
			insns.append(AwlInsn_SPBNB(cpu=None, ops=[oper]))

		# Create the jump target label for EN=0.
		oper = make_AwlOperator(AwlOperatorTypes.IMM, 16, None, None)
		oper.immediate = 0
		insn = AwlInsn_NOP(cpu=None, ops=[oper])
		insn.labelStr = endLabel
		insns.append(insn)

		# Handle ENO output.
		if conn_ENO.isConnected:
			otherElem = conn_ENO.getConnectedElem(viaIn=True)

			# Add instruction:  U BIE
			oper = make_AwlOperator(AwlOperatorTypes.MEM_STW, 1,
						make_AwlOffset(0, 8), None)
			insns.append(AwlInsn_U(cpu=None, ops=[oper]))

			# Add VKE assignment instruction.
			insns.extend(otherElem.emitStore_VKE())

		return insns

# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - Compare operations
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


class FupCompiler_ElemCmp(FupCompiler_Elem):
	"""FUP compiler - Compare operation.
	"""

	ELEM_NAME		= "CMP"
	SUBTYPE			= None # Override this in the subclass
	CMP_INSN_CLASS		= None # Override this in the subclass

	EnumGen.start
	SUBTYPE_EQ_I		= EnumGen.item
	SUBTYPE_NE_I		= EnumGen.item
	SUBTYPE_LT_I		= EnumGen.item
	SUBTYPE_GT_I		= EnumGen.item
	SUBTYPE_LE_I		= EnumGen.item
	SUBTYPE_GE_I		= EnumGen.item
	SUBTYPE_EQ_D		= EnumGen.item
	SUBTYPE_NE_D		= EnumGen.item
	SUBTYPE_LT_D		= EnumGen.item
	SUBTYPE_GT_D		= EnumGen.item
	SUBTYPE_LE_D		= EnumGen.item
	SUBTYPE_GE_D		= EnumGen.item
	SUBTYPE_EQ_R		= EnumGen.item
	SUBTYPE_NE_R		= EnumGen.item
	SUBTYPE_LT_R		= EnumGen.item
	SUBTYPE_GT_R		= EnumGen.item
	SUBTYPE_LE_R		= EnumGen.item
	SUBTYPE_GE_R		= EnumGen.item
	EnumGen.end

	str2subtype = {
		"eq-int"	: SUBTYPE_EQ_I,
		"ne-int"	: SUBTYPE_NE_I,
		"lt-int"	: SUBTYPE_LT_I,
		"gt-int"	: SUBTYPE_GT_I,
		"le-int"	: SUBTYPE_LE_I,
		"ge-int"	: SUBTYPE_GE_I,
		"eq-dint"	: SUBTYPE_EQ_D,
		"ne-dint"	: SUBTYPE_NE_D,
		"lt-dint"	: SUBTYPE_LT_D,
		"gt-dint"	: SUBTYPE_GT_D,
		"le-dint"	: SUBTYPE_LE_D,
		"ge-dint"	: SUBTYPE_GE_D,
		"eq-real"	: SUBTYPE_EQ_R,
		"ne-real"	: SUBTYPE_NE_R,
		"lt-real"	: SUBTYPE_LT_R,
		"gt-real"	: SUBTYPE_GT_R,
		"le-real"	: SUBTYPE_LE_R,
		"ge-real"	: SUBTYPE_GE_R,
	}

	@classmethod
	def parse(cls, grid, x, y, subType, content):
		try:
			subType = cls.str2subtype[subType]
			type2class = {
				cls.SUBTYPE_EQ_I	: FupCompiler_ElemCmpEQI,
				cls.SUBTYPE_NE_I	: FupCompiler_ElemCmpNEI,
				cls.SUBTYPE_LT_I	: FupCompiler_ElemCmpLTI,
				cls.SUBTYPE_GT_I	: FupCompiler_ElemCmpGTI,
				cls.SUBTYPE_LE_I	: FupCompiler_ElemCmpLEI,
				cls.SUBTYPE_GE_I	: FupCompiler_ElemCmpGEI,
				cls.SUBTYPE_EQ_D	: FupCompiler_ElemCmpEQD,
				cls.SUBTYPE_NE_D	: FupCompiler_ElemCmpNED,
				cls.SUBTYPE_LT_D	: FupCompiler_ElemCmpLTD,
				cls.SUBTYPE_GT_D	: FupCompiler_ElemCmpGTD,
				cls.SUBTYPE_LE_D	: FupCompiler_ElemCmpLED,
				cls.SUBTYPE_GE_D	: FupCompiler_ElemCmpGED,
				cls.SUBTYPE_EQ_R	: FupCompiler_ElemCmpEQR,
				cls.SUBTYPE_NE_R	: FupCompiler_ElemCmpNER,
				cls.SUBTYPE_LT_R	: FupCompiler_ElemCmpLTR,
				cls.SUBTYPE_GT_R	: FupCompiler_ElemCmpGTR,
				cls.SUBTYPE_LE_R	: FupCompiler_ElemCmpLER,
				cls.SUBTYPE_GE_R	: FupCompiler_ElemCmpGER,
			}
			elemClass = None
			with contextlib.suppress(KeyError):
				elemClass = type2class[subType]
			if elemClass:
				return elemClass(grid=grid, x=x, y=y,
						 content=content)
		except KeyError:
			pass
		return None

	def __init__(self, grid, x, y, content, **kwargs):
		FupCompiler_Elem.__init__(self, grid=grid, x=x, y=y,
					  elemType=FupCompiler_Elem.TYPE_CMP,
					  subType=self.SUBTYPE,
					  content=content,
					  **kwargs)

	def connIsOptional(self, conn):
		return conn.hasText({ "EN", "ENO", })

	def getConnType(self, conn, preferVKE=False):
		if conn in self.connections:
			if conn.textMatch(r"(OUT\d+)|(EN)|(ENO)"):
				return FupCompiler_Conn.TYPE_VKE
			return FupCompiler_Conn.TYPE_ACCU
		return FupCompiler_Conn.TYPE_UNKNOWN

	def __getConnsEN(self):
		"""Get EN and ENO connections.
		"""
		conn_EN = self.getUniqueConnByText("EN", searchInputs=True)
		conn_ENO = self.getUniqueConnByText("ENO", searchOutputs=True)
		if not conn_EN or not conn_ENO:
			raise FupElemError("Invalid EN or ENO connections "
				"in FUP compare %s." % (
				str(self)),
				self)
		return conn_EN, conn_ENO

	def __allConnsIN(self):
		"""Get all INx connections.
		"""
		conns = []
		for conn in FupCompiler_Conn.sorted(self.inConnections):
			if conn.textMatch(r"IN\d+"):
				conns.append(conn)
		if len(conns) != 2:
			raise FupElemError("Invalid number of input connections.", self)
		return conns

	def __allConnsOUT(self):
		"""Get all OUTx connections.
		"""
		for conn in FupCompiler_Conn.sorted(self.outConnections):
			if conn.textMatch(r"OUT\d+"):
				yield conn

	def compileConn(self, conn, desiredTarget, inverted=False):
		insns = []
		assert(conn in self.connections)

		awlInsnClass = FupCompiler_Conn.targetToInsnClass(desiredTarget,
								  toLoad=True,
								  inverted=inverted)

		if conn.textMatch("(ENO)|(OUT\d+)"):
			self._compileConn_checkTarget(conn, desiredTarget, inverted,
						      targetExpectVKE=True,
						      allowInversion=True)
			if self.needCompile:
				insns.extend(self.compile())
				if inverted:
					insns.append(self.newInsn(AwlInsn_NOT))
			else:
				insns.extend(conn.elem._loadFromTemp(awlInsnClass, conn))
		else:
			return FupCompiler_Elem.compileConn(self, conn, desiredTarget, inverted)
		return insns

	def _doPreprocess(self):
		# If the element connected to IN is not a LOAD operand, we must
		# take its ENO into account.
		# If we don't have a connection on EN, we implicitly connect
		# the IN-element's ENO to our EN here.
		# If we already have a connection on EN, we implicitly add an AND-element
		# between the IN-element's ENO and our EN.
		elemsA = []
		for conn in self.__allConnsIN():
			connectedElem = conn.getConnectedElem(viaOut=True)
			if not connectedElem.isType(FupCompiler_Elem.TYPE_OPERAND,
						    FupCompiler_ElemOper.SUBTYPE_LOAD):
				elemsA.append(connectedElem)
		FupCompiler_Helpers.genIntermediateBool(
				parentElem=self,
				elemsA=elemsA,
				connNamesA=(["ENO"] * len(elemsA)),
				elemB=self,
				connNameB="EN",
				boolElemClass=FupCompiler_ElemBoolAnd)

	def _doCompile(self):
		insns = []

		conn_EN, conn_ENO = self.__getConnsEN()

		# Compile all elements connected to IN connections.
		for conn in self.__allConnsIN():
			connectedElem = conn.getConnectedElem(viaOut=True)
			# Only compile the element, if it is not a plain LOAD box.
			if connectedElem.needCompile and\
			   not connectedElem.isType(FupCompiler_Elem.TYPE_OPERAND,
						    FupCompiler_ElemOper.SUBTYPE_LOAD):
				insns.extend(connectedElem.compile())

		# If we have an ENO, store the EN state in BIE,
		# so that EN does not have to be evaluated twice.
		if conn_EN.isConnected and conn_ENO.isConnected:
			# Compile the element that drives EN.
			otherConn = conn_EN.getConnectedConn(getOutput=True)
			insns.extend(otherConn.compileConn(targetInsnClass=AwlInsn_U,
							   inverted=False))
			# Save EN to BIE.
			insns.append(self.newInsn(AwlInsn_SAVE))

		# Compile the actual operation.
		for conn in self.__allConnsIN():
			# Compile the element connected to the input.
			otherConn = conn.getConnectedConn(getOutput=True)
			if otherConn.elem.needCompile:
				insns.extend(otherConn.elem.compile())
			else:
				insns.extend(otherConn.compileConn(targetInsnClass=AwlInsn_L))
			if conn.connType != FupCompiler_Conn.TYPE_ACCU:
				raise FupElemError("The IN connection "
					"of the FUP compare box %s must not be connected "
					"to a bit (VKE) wire." % (
					str(self)),
					self)
		# Add the arithmetic operation.
		insns.append(self.newInsn(self.CMP_INSN_CLASS))

		# If we have an EN input, add an AND operation between
		# the compare result and the EN input.
		if conn_EN.isConnected:
			# If we have an ENO, the EN state has been stored in BIE.
			# Use BIE so that EN does not have to be evaluated twice.
			if conn_ENO.isConnected:
				insns.append(self.newInsn_LOAD_BIE(AwlInsn_U))
			else:
				# Compile the element that drives this wire.
				otherConn = conn_EN.getConnectedConn(getOutput=True)
				insns.extend(otherConn.compileConn(targetInsnClass=AwlInsn_U,
								   inverted=False))

		# Assign the outputs.
		storeToTempConns = set()
		for conn in self.__allConnsOUT():
			for otherElem in self.sorted(conn.getConnectedElems(viaIn=True)):
				if otherElem.isType(FupCompiler_Elem.TYPE_OPERAND,
						    FupCompiler_ElemOper.SUBTYPE_ASSIGN):
					insns.extend(otherElem.emitStore_VKE())
				else:
					storeToTempConns.add(conn)
		if storeToTempConns:
			storeToTempConns.add(self.MAIN_RESULT)
			insns.extend(self._storeToTemp("BOOL", AwlInsn_ASSIGN, storeToTempConns))

		# Handle ENO output.
		if conn_ENO.isConnected:
			if conn_EN.isConnected:
				# Add instruction:  U BIE
				insns.append(self.newInsn_LOAD_BIE(AwlInsn_U))
			else:
				# Add instruction to set VKE
				insns.append(self.newInsn(AwlInsn_SET))

			# Add VKE assignment instruction.
			storeToTempConns = set()
			for otherElem in self.sorted(conn_ENO.getConnectedElems(viaIn=True)):
				if otherElem.isType(FupCompiler_Elem.TYPE_OPERAND,
						    FupCompiler_ElemOper.SUBTYPE_ASSIGN):
					insns.extend(otherElem.emitStore_VKE())
				else:
					storeToTempConns.add(conn_ENO)
			if storeToTempConns:
				insns.extend(self._storeToTemp("BOOL", AwlInsn_ASSIGN,
							       storeToTempConns))

		return insns

class FupCompiler_ElemCmpEQI(FupCompiler_ElemCmp):
	"""FUP compiler - Compare operation - ==I
	"""

	ELEM_NAME		= "==I"
	SUBTYPE			= FupCompiler_ElemCmp.SUBTYPE_EQ_I
	CMP_INSN_CLASS		= AwlInsn_EQ_I

class FupCompiler_ElemCmpNEI(FupCompiler_ElemCmp):
	"""FUP compiler - Compare operation - <>I
	"""

	ELEM_NAME		= "<>I"
	SUBTYPE			= FupCompiler_ElemCmp.SUBTYPE_NE_I
	CMP_INSN_CLASS		= AwlInsn_NE_I

class FupCompiler_ElemCmpGTI(FupCompiler_ElemCmp):
	"""FUP compiler - Compare operation - >I
	"""

	ELEM_NAME		= ">I"
	SUBTYPE			= FupCompiler_ElemCmp.SUBTYPE_GT_I
	CMP_INSN_CLASS		= AwlInsn_GT_I

class FupCompiler_ElemCmpLTI(FupCompiler_ElemCmp):
	"""FUP compiler - Compare operation - <I
	"""

	ELEM_NAME		= "<I"
	SUBTYPE			= FupCompiler_ElemCmp.SUBTYPE_LT_I
	CMP_INSN_CLASS		= AwlInsn_LT_I

class FupCompiler_ElemCmpGEI(FupCompiler_ElemCmp):
	"""FUP compiler - Compare operation - >=I
	"""

	ELEM_NAME		= ">=I"
	SUBTYPE			= FupCompiler_ElemCmp.SUBTYPE_GE_I
	CMP_INSN_CLASS		= AwlInsn_GE_I

class FupCompiler_ElemCmpLEI(FupCompiler_ElemCmp):
	"""FUP compiler - Compare operation - <=I
	"""

	ELEM_NAME		= "<=I"
	SUBTYPE			= FupCompiler_ElemCmp.SUBTYPE_LE_I
	CMP_INSN_CLASS		= AwlInsn_LE_I

class FupCompiler_ElemCmpEQD(FupCompiler_ElemCmp):
	"""FUP compiler - Compare operation - ==D
	"""

	ELEM_NAME		= "==D"
	SUBTYPE			= FupCompiler_ElemCmp.SUBTYPE_EQ_D
	CMP_INSN_CLASS		= AwlInsn_EQ_D

class FupCompiler_ElemCmpNED(FupCompiler_ElemCmp):
	"""FUP compiler - Compare operation - <>D
	"""

	ELEM_NAME		= "<>D"
	SUBTYPE			= FupCompiler_ElemCmp.SUBTYPE_NE_D
	CMP_INSN_CLASS		= AwlInsn_NE_D

class FupCompiler_ElemCmpGTD(FupCompiler_ElemCmp):
	"""FUP compiler - Compare operation - >D
	"""

	ELEM_NAME		= ">D"
	SUBTYPE			= FupCompiler_ElemCmp.SUBTYPE_GT_D
	CMP_INSN_CLASS		= AwlInsn_GT_D

class FupCompiler_ElemCmpLTD(FupCompiler_ElemCmp):
	"""FUP compiler - Compare operation - <D
	"""

	ELEM_NAME		= "<D"
	SUBTYPE			= FupCompiler_ElemCmp.SUBTYPE_LT_D
	CMP_INSN_CLASS		= AwlInsn_LT_D

class FupCompiler_ElemCmpGED(FupCompiler_ElemCmp):
	"""FUP compiler - Compare operation - >=D
	"""

	ELEM_NAME		= ">=D"
	SUBTYPE			= FupCompiler_ElemCmp.SUBTYPE_GE_D
	CMP_INSN_CLASS		= AwlInsn_GE_D

class FupCompiler_ElemCmpLED(FupCompiler_ElemCmp):
	"""FUP compiler - Compare operation - <=D
	"""

	ELEM_NAME		= "<=D"
	SUBTYPE			= FupCompiler_ElemCmp.SUBTYPE_LE_D
	CMP_INSN_CLASS		= AwlInsn_LE_D

class FupCompiler_ElemCmpEQR(FupCompiler_ElemCmp):
	"""FUP compiler - Compare operation - ==R
	"""

	ELEM_NAME		= "==R"
	SUBTYPE			= FupCompiler_ElemCmp.SUBTYPE_EQ_R
	CMP_INSN_CLASS		= AwlInsn_EQ_R

class FupCompiler_ElemCmpNER(FupCompiler_ElemCmp):
	"""FUP compiler - Compare operation - <>R
	"""

	ELEM_NAME		= "<>R"
	SUBTYPE			= FupCompiler_ElemCmp.SUBTYPE_NE_R
	CMP_INSN_CLASS		= AwlInsn_NE_R

class FupCompiler_ElemCmpGTR(FupCompiler_ElemCmp):
	"""FUP compiler - Compare operation - >R
	"""

	ELEM_NAME		= ">R"
	SUBTYPE			= FupCompiler_ElemCmp.SUBTYPE_GT_R
	CMP_INSN_CLASS		= AwlInsn_GT_R

class FupCompiler_ElemCmpLTR(FupCompiler_ElemCmp):
	"""FUP compiler - Compare operation - <R
	"""

	ELEM_NAME		= "<R"
	SUBTYPE			= FupCompiler_ElemCmp.SUBTYPE_LT_R
	CMP_INSN_CLASS		= AwlInsn_LT_R

class FupCompiler_ElemCmpGER(FupCompiler_ElemCmp):
	"""FUP compiler - Compare operation - >=R
	"""

	ELEM_NAME		= ">=R"
	SUBTYPE			= FupCompiler_ElemCmp.SUBTYPE_GE_R
	CMP_INSN_CLASS		= AwlInsn_GE_R

class FupCompiler_ElemCmpLER(FupCompiler_ElemCmp):
	"""FUP compiler - Compare operation - <=R
	"""

	ELEM_NAME		= "<=R"
	SUBTYPE			= FupCompiler_ElemCmp.SUBTYPE_LE_R
	CMP_INSN_CLASS		= AwlInsn_LE_R

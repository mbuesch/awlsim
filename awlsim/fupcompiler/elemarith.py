# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - Arithmetic operations
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


class FupCompiler_ElemArith(FupCompiler_Elem):
	"""FUP compiler - Arithmetic operation.
	"""

	ELEM_NAME		= "ARITH"
	SUBTYPE			= None # Override this in the subclass
	ARITH_INSN_CLASS	= None # Override this in the subclass
	HAVE_REMAINDER		= False # Operation has remainder?

	EnumGen.start
	SUBTYPE_ADD_I		= EnumGen.item
	SUBTYPE_SUB_I		= EnumGen.item
	SUBTYPE_MUL_I		= EnumGen.item
	SUBTYPE_DIV_I		= EnumGen.item
	SUBTYPE_ADD_D		= EnumGen.item
	SUBTYPE_SUB_D		= EnumGen.item
	SUBTYPE_MUL_D		= EnumGen.item
	SUBTYPE_DIV_D		= EnumGen.item
	SUBTYPE_MOD_D		= EnumGen.item
	SUBTYPE_ADD_R		= EnumGen.item
	SUBTYPE_SUB_R		= EnumGen.item
	SUBTYPE_MUL_R		= EnumGen.item
	SUBTYPE_DIV_R		= EnumGen.item
	EnumGen.end

	str2subtype = {
		"add-int"	: SUBTYPE_ADD_I,
		"sub-int"	: SUBTYPE_SUB_I,
		"mul-int"	: SUBTYPE_MUL_I,
		"div-int"	: SUBTYPE_DIV_I,
		"add-dint"	: SUBTYPE_ADD_D,
		"sub-dint"	: SUBTYPE_SUB_D,
		"mul-dint"	: SUBTYPE_MUL_D,
		"div-dint"	: SUBTYPE_DIV_D,
		"mod-dint"	: SUBTYPE_MOD_D,
		"add-real"	: SUBTYPE_ADD_R,
		"sub-real"	: SUBTYPE_SUB_R,
		"mul-real"	: SUBTYPE_MUL_R,
		"div-real"	: SUBTYPE_DIV_R,
	}

	@classmethod
	def parse(cls, grid, x, y, subType, content):
		try:
			subType = cls.str2subtype[subType]
			type2class = {
				cls.SUBTYPE_ADD_I	: FupCompiler_ElemArithAddI,
				cls.SUBTYPE_SUB_I	: FupCompiler_ElemArithSubI,
				cls.SUBTYPE_MUL_I	: FupCompiler_ElemArithMulI,
				cls.SUBTYPE_DIV_I	: FupCompiler_ElemArithDivI,
				cls.SUBTYPE_ADD_D	: FupCompiler_ElemArithAddD,
				cls.SUBTYPE_SUB_D	: FupCompiler_ElemArithSubD,
				cls.SUBTYPE_MUL_D	: FupCompiler_ElemArithMulD,
				cls.SUBTYPE_DIV_D	: FupCompiler_ElemArithDivD,
				cls.SUBTYPE_MOD_D	: FupCompiler_ElemArithModD,
				cls.SUBTYPE_ADD_R	: FupCompiler_ElemArithAddR,
				cls.SUBTYPE_SUB_R	: FupCompiler_ElemArithSubR,
				cls.SUBTYPE_MUL_R	: FupCompiler_ElemArithMulR,
				cls.SUBTYPE_DIV_R	: FupCompiler_ElemArithDivR,
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
					  elemType=FupCompiler_Elem.TYPE_ARITH,
					  subType=self.SUBTYPE,
					  content=content,
					  **kwargs)

	def connIsOptional(self, conn):
		return conn.hasText({ "EN", "ENO", "OV", "REM", "==0", "<>0",
				      ">0", "<0", ">=0", "<=0", "UO", })

	def getConnType(self, conn, preferVKE=False):
		if conn in self.connections:
			if conn.hasText({ "EN", "ENO", "OV", "==0", "<>0",
					  ">0", "<0", ">=0", "<=0", "UO", }):
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
				"in FUP arithmetic %s." % (
				str(self)),
				self)
		return conn_EN, conn_ENO

	def __getConnFlag(self, connName):
		conn = self.getUniqueConnByText(connName, searchOutputs=True)
		if conn and conn.isConnected:
			return conn
		return None

	def __allConnsIN(self):
		"""Get all INx connections.
		"""
		for conn in FupCompiler_Conn.sorted(self.inConnections):
			if conn.textMatch(r"IN\d+"):
				yield conn

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

		if conn.hasText("ENO"):
			self._compileConn_checkTarget(conn, desiredTarget, inverted,
						      targetExpectVKE=True,
						      allowInversion=True)
			if self.needCompile:
				insns.extend(self.compile())
				if inverted:
					insns.append(self.newInsn(AwlInsn_NOT))
			else:
				insns.extend(conn.elem._loadFromTemp(awlInsnClass, conn))
		elif conn.hasText({ "OV", "==0", "<>0", ">0",
				    "<0", ">=0", "<=0", "UO", }):
			self._compileConn_checkTarget(conn, desiredTarget, inverted,
						      targetExpectVKE=True,
						      allowInversion=False)
			if self.needCompile:
				insns.extend(self.compile())
			insns.extend(conn.elem._loadFromTemp(awlInsnClass, conn))
		elif conn.textMatch(r"(REM)|(OUT\d+)"):
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

		# Compile the actual operation.
		for i, conn in enumerate(self.__allConnsIN()):
			otherConn = conn.getConnectedConn(getOutput=True)
			otherElem = otherConn.elem

			# Compile the element connected to the input.
			if otherElem.needCompile:
				insns.extend(otherElem.compile())
			else:
				insns.extend(otherConn.compileConn(targetInsnClass=AwlInsn_L))
			if conn.connType != FupCompiler_Conn.TYPE_ACCU:
				raise FupElemError("The IN connection "
					"of the FUP arithmetic box %s must not be connected "
					"to a bit (VKE) wire." % (
					str(self)),
					self)

			# Add the arithmetic operation.
			if i > 0:
				insns.append(self.newInsn(self.ARITH_INSN_CLASS))

		# Assign the outputs.
		storeToTempConns = set()
		for conn in self.__allConnsOUT():
			for otherElem in self.sorted(conn.getConnectedElems(viaIn=True)):
				if otherElem.isType(FupCompiler_Elem.TYPE_OPERAND,
						    FupCompiler_ElemOper.SUBTYPE_ASSIGN):
					insns.extend(otherElem.emitStore_ACCU())
				else:
					storeToTempConns.add(conn)
		if storeToTempConns:
			storeToTempConns.add(self.MAIN_RESULT)
			insns.extend(self._storeToTemp("DWORD", AwlInsn_T, storeToTempConns))

		# Check if any of the flags outputs is used.
		anyFlagConnected = any(bool(self.__getConnFlag(name))
				       for name in {"OV", "==0", "<>0", ">0",
						    "<0", ">=0", "<=0", "UO"})

		# Handle REMainder output.
		if self.HAVE_REMAINDER:
			conn_REM = self.getUniqueConnByText("REM", searchOutputs=True)
			if conn_REM and conn_REM.isConnected:
				# Shift the remainder to the lower 16 bits.
				# The division result will be lost.
				# But save the status word before shifting to avoid
				# clobbering STW by SRD. This is only done, if the
				# STW is used later on for the flags outputs.
				if anyFlagConnected:
					insns.append(self.newInsn_L_STW())
					insns.append(self.newInsn(AwlInsn_TAK))
				insns.append(self.newInsn_SRD(16))
				# Store the REM output (or store to TEMP).
				storeToTempConns = set()
				for otherElem in self.sorted(conn_REM.getConnectedElems(viaIn=True)):
					if otherElem.isType(FupCompiler_Elem.TYPE_OPERAND,
							    FupCompiler_ElemOper.SUBTYPE_ASSIGN):
						insns.extend(otherElem.emitStore_ACCU())
					else:
						storeToTempConns.add(conn_REM)
				insns.extend(self._storeToTemp("WORD", AwlInsn_T, storeToTempConns))
				# Restore STW.
				if anyFlagConnected:
					insns.append(self.newInsn(AwlInsn_TAK))
					insns.append(self.newInsn_T_STW())

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

		# Compile flags outputs.
		if anyFlagConnected:
			insns.extend(FupCompiler_Helpers.genSTWOutputOper(self,
					conn=self.__getConnFlag("OV"),
					andWithBIE=conn_EN.isConnected,
					operType=AwlOperatorTypes.MEM_STW,
					bitPos=S7StatusWord.getBitnrByName("OV", S7CPUConfig.MNEMONICS_DE)))
			insns.extend(FupCompiler_Helpers.genSTWOutputOper(self,
					conn=self.__getConnFlag("==0"),
					andWithBIE=conn_EN.isConnected,
					operType=AwlOperatorTypes.MEM_STW_Z))
			insns.extend(FupCompiler_Helpers.genSTWOutputOper(self,
					conn=self.__getConnFlag("<>0"),
					andWithBIE=conn_EN.isConnected,
					operType=AwlOperatorTypes.MEM_STW_NZ))
			insns.extend(FupCompiler_Helpers.genSTWOutputOper(self,
					conn=self.__getConnFlag(">0"),
					andWithBIE=conn_EN.isConnected,
					operType=AwlOperatorTypes.MEM_STW_POS))
			insns.extend(FupCompiler_Helpers.genSTWOutputOper(self,
					conn=self.__getConnFlag("<0"),
					andWithBIE=conn_EN.isConnected,
					operType=AwlOperatorTypes.MEM_STW_NEG))
			insns.extend(FupCompiler_Helpers.genSTWOutputOper(self,
					conn=self.__getConnFlag(">=0"),
					andWithBIE=conn_EN.isConnected,
					operType=AwlOperatorTypes.MEM_STW_POSZ))
			insns.extend(FupCompiler_Helpers.genSTWOutputOper(self,
					conn=self.__getConnFlag("<=0"),
					andWithBIE=conn_EN.isConnected,
					operType=AwlOperatorTypes.MEM_STW_NEGZ))
			insns.extend(FupCompiler_Helpers.genSTWOutputOper(self,
					conn=self.__getConnFlag("UO"),
					andWithBIE=conn_EN.isConnected,
					operType=AwlOperatorTypes.MEM_STW_UO))

		# Handle ENO output.
		if conn_ENO.isConnected:
			# Add instruction:  U BIE
			insns.append(self.newInsn_LOAD_BIE(AwlInsn_U))

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

class FupCompiler_ElemArithAddI(FupCompiler_ElemArith):
	"""FUP compiler - Arithmetic operation - +I
	"""

	ELEM_NAME		= "+I"
	SUBTYPE			= FupCompiler_ElemArith.SUBTYPE_ADD_I
	ARITH_INSN_CLASS	= AwlInsn_PL_I

class FupCompiler_ElemArithSubI(FupCompiler_ElemArith):
	"""FUP compiler - Arithmetic operation - -I
	"""

	ELEM_NAME		= "-I"
	SUBTYPE			= FupCompiler_ElemArith.SUBTYPE_SUB_I
	ARITH_INSN_CLASS	= AwlInsn_MI_I

class FupCompiler_ElemArithMulI(FupCompiler_ElemArith):
	"""FUP compiler - Arithmetic operation - *I
	"""

	ELEM_NAME		= "*I"
	SUBTYPE			= FupCompiler_ElemArith.SUBTYPE_MUL_I
	ARITH_INSN_CLASS	= AwlInsn_MU_I

class FupCompiler_ElemArithDivI(FupCompiler_ElemArith):
	"""FUP compiler - Arithmetic operation - /I
	"""

	ELEM_NAME		= "/I"
	SUBTYPE			= FupCompiler_ElemArith.SUBTYPE_DIV_I
	ARITH_INSN_CLASS	= AwlInsn_DI_I
	HAVE_REMAINDER		= True

class FupCompiler_ElemArithAddD(FupCompiler_ElemArith):
	"""FUP compiler - Arithmetic operation - +D
	"""

	ELEM_NAME		= "+D"
	SUBTYPE			= FupCompiler_ElemArith.SUBTYPE_ADD_D
	ARITH_INSN_CLASS	= AwlInsn_PL_D

class FupCompiler_ElemArithSubD(FupCompiler_ElemArith):
	"""FUP compiler - Arithmetic operation - -D
	"""

	ELEM_NAME		= "-D"
	SUBTYPE			= FupCompiler_ElemArith.SUBTYPE_SUB_D
	ARITH_INSN_CLASS	= AwlInsn_MI_D

class FupCompiler_ElemArithMulD(FupCompiler_ElemArith):
	"""FUP compiler - Arithmetic operation - *D
	"""

	ELEM_NAME		= "*D"
	SUBTYPE			= FupCompiler_ElemArith.SUBTYPE_MUL_D
	ARITH_INSN_CLASS	= AwlInsn_MU_D

class FupCompiler_ElemArithDivD(FupCompiler_ElemArith):
	"""FUP compiler - Arithmetic operation - /D
	"""

	ELEM_NAME		= "/D"
	SUBTYPE			= FupCompiler_ElemArith.SUBTYPE_DIV_D
	ARITH_INSN_CLASS	= AwlInsn_DI_D

class FupCompiler_ElemArithModD(FupCompiler_ElemArith):
	"""FUP compiler - Arithmetic operation - MOD
	"""

	ELEM_NAME		= "MOD"
	SUBTYPE			= FupCompiler_ElemArith.SUBTYPE_MOD_D
	ARITH_INSN_CLASS	= AwlInsn_MOD

class FupCompiler_ElemArithAddR(FupCompiler_ElemArith):
	"""FUP compiler - Arithmetic operation - +R
	"""

	ELEM_NAME		= "+R"
	SUBTYPE			= FupCompiler_ElemArith.SUBTYPE_ADD_R
	ARITH_INSN_CLASS	= AwlInsn_PL_R

class FupCompiler_ElemArithSubR(FupCompiler_ElemArith):
	"""FUP compiler - Arithmetic operation - -R
	"""

	ELEM_NAME		= "-R"
	SUBTYPE			= FupCompiler_ElemArith.SUBTYPE_SUB_R
	ARITH_INSN_CLASS	= AwlInsn_MI_R

class FupCompiler_ElemArithMulR(FupCompiler_ElemArith):
	"""FUP compiler - Arithmetic operation - *R
	"""

	ELEM_NAME		= "*R"
	SUBTYPE			= FupCompiler_ElemArith.SUBTYPE_MUL_R
	ARITH_INSN_CLASS	= AwlInsn_MU_R

class FupCompiler_ElemArithDivR(FupCompiler_ElemArith):
	"""FUP compiler - Arithmetic operation - /R
	"""

	ELEM_NAME		= "/R"
	SUBTYPE			= FupCompiler_ElemArith.SUBTYPE_DIV_R
	ARITH_INSN_CLASS	= AwlInsn_DI_R

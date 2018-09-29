# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - S7 counter
#
# Copyright 2018 Michael Buesch <m@bues.ch>
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
#from awlsim.common.cython_support cimport * #@cy
from awlsim.common.compat import *

from awlsim.fupcompiler.elem import *
from awlsim.fupcompiler.elemoper import *
from awlsim.fupcompiler.elembool import *
from awlsim.fupcompiler.helpers import *

from awlsim.core.operators import * #+cimport
from awlsim.core.operatortypes import * #+cimport

from awlsim.core.instructions.all_insns import * #+cimport


class FupCompiler_ElemCount(FupCompiler_Elem):
	"""FUP compiler - S7 counter.
	"""

	ELEM_NAME		= "COUNT"
	SUBTYPE			= None

	EnumGen.start
	SUBTYPE_CUD		= EnumGen.item
	SUBTYPE_CU		= EnumGen.item
	SUBTYPE_CUO		= EnumGen.item
	SUBTYPE_CD		= EnumGen.item
	SUBTYPE_CDO		= EnumGen.item
	SUBTYPE_CSO		= EnumGen.item
	EnumGen.end

	str2subtype = {
		"cud"	: SUBTYPE_CUD,
		"cu"	: SUBTYPE_CU,
		"cuo"	: SUBTYPE_CUO,
		"cd"	: SUBTYPE_CD,
		"cdo"	: SUBTYPE_CDO,
		"cso"	: SUBTYPE_CSO,
	}

	@classmethod
	def parse(cls, grid, x, y, subType, content):
		try:
			subType = cls.str2subtype[subType]
			type2class = {
				cls.SUBTYPE_CUD	: FupCompiler_ElemCUD,
				cls.SUBTYPE_CU	: FupCompiler_ElemCU,
				cls.SUBTYPE_CUO	: FupCompiler_ElemCUO,
				cls.SUBTYPE_CD	: FupCompiler_ElemCD,
				cls.SUBTYPE_CDO	: FupCompiler_ElemCDO,
				cls.SUBTYPE_CSO	: FupCompiler_ElemCSO,
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
					  elemType=FupCompiler_Elem.TYPE_COUNT,
					  subType=self.SUBTYPE,
					  content=content,
					  **kwargs)

	def connIsOptional(self, conn):
		if not self.enabled:
			return True
		return conn.hasText({ "EN", "ENO", "CU", "CD", "S", "PV", "R",
				      "CV", "CVB", "Q", })

	def getConnType(self, conn, preferVKE=False):
		if self.enabled and conn in self.connections:
			if conn.hasText({ "EN", "ENO", "CU", "CD", "S", "R", "Q", }):
				return FupCompiler_Conn.TYPE_VKE
			return FupCompiler_Conn.TYPE_ACCU
		return FupCompiler_Conn.TYPE_UNKNOWN

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

	def compileConn(self, conn, desiredTarget, inverted=False):
		if not self.enabled:
			return []
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
		elif conn.hasText("Q"):
			self._compileConn_checkTarget(conn, desiredTarget, inverted,
						      targetExpectVKE=True,
						      allowInversion=True)
			if self.needCompile:
				insns.extend(self.compile())
			insns.extend(conn.elem._loadFromTemp(awlInsnClass, conn))
		elif conn.hasText("CV") or conn.hasText("CVB"):
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
		if not self.enabled:
			return
		# If any element connected to any input is not a LOAD operand, we must
		# take its ENO into account.
		# If we don't have a connection on EN, we implicitly connect
		# the IN-element's ENO to our EN here.
		# If we already have a connection on EN, we implicitly add an AND-element
		# between the IN-element's ENO and our EN.
		elemsA = []
		conn_CU = self.getUniqueConnByText("CU", searchInputs=True)
		conn_CD = self.getUniqueConnByText("CD", searchInputs=True)
		conn_S = self.getUniqueConnByText("S", searchInputs=True)
		conn_PV = self.getUniqueConnByText("PV", searchInputs=True)
		conn_R = self.getUniqueConnByText("R", searchInputs=True)
		for conn in (conn_CU, conn_CD, conn_S, conn_PV, conn_R):
			if conn and conn.isConnected:
				connectedElem = conn.getConnectedElem(viaOut=True)
				if conn is not conn_PV:
					# If a simple BOOLEAN is connected to CU, CD, S or R
					# then we do not need to connect its ENO.
					if connectedElem.isType(FupCompiler_Elem.TYPE_BOOLEAN):
						continue
				if connectedElem.isType(FupCompiler_Elem.TYPE_OPERAND,
							FupCompiler_ElemOper.SUBTYPE_LOAD):
					# No ENO connection for simple load operands.
					continue
				# For everything else, add an ENO wire.
				elemsA.append(connectedElem)
		FupCompiler_Helpers.genIntermediateBool(
				parentElem=self,
				elemsA=elemsA,
				connNamesA=(["ENO"] * len(elemsA)),
				elemB=self,
				connNameB="EN",
				boolElemClass=FupCompiler_ElemBoolAnd)

	def _doCompile(self):
		if not self.enabled:
			return []
		insns = []

		# Get all inputs.
		conn_EN = self.getUniqueConnByText("EN", searchInputs=True)
		conn_CU = self.getUniqueConnByText("CU", searchInputs=True)
		conn_CD = self.getUniqueConnByText("CD", searchInputs=True)
		conn_S = self.getUniqueConnByText("S", searchInputs=True)
		conn_PV = self.getUniqueConnByText("PV", searchInputs=True)
		conn_R = self.getUniqueConnByText("R", searchInputs=True)
		# Get all outputs.
		conn_CV = self.getUniqueConnByText("CV", searchOutputs=True)
		conn_CVB = self.getUniqueConnByText("CVB", searchOutputs=True)
		conn_Q = self.getUniqueConnByText("Q", searchOutputs=True)
		conn_ENO = self.getUniqueConnByText("ENO", searchOutputs=True)

		# Get the Zx body operator.
		bodyOperElem = self._getBodyOper()

		# Compile all elements connected to input connections (except for EN).
		for conn in (conn_CU, conn_CD, conn_S, conn_PV, conn_R):
			if not conn or not conn.isConnected:
				continue # Input is not connected.
			connectedElem = conn.getConnectedElem(viaOut=True)
			if not connectedElem.needCompile:
				continue # The element is compiled already.
			if conn is not conn_PV:
				# If a simple BOOLEAN is connected to CU, CD, S or R
				# then we do not need to compile it now.
				# It can be compiled in-line below.
				if connectedElem.isType(FupCompiler_Elem.TYPE_BOOLEAN):
					continue
			if connectedElem.isType(FupCompiler_Elem.TYPE_OPERAND,
						FupCompiler_ElemOper.SUBTYPE_LOAD):
				# A load operand will be handled below.
				continue
			# Compile the element connected to the input and store its
			# result to TEMP.
			insns.extend(connectedElem.compile())

		# Generate a jump target label name for the EN jump.
		# This might end up being unused, though.
		endLabel = self.grid.compiler.newLabel()

		# If we have an EN input, emit the corresponding conditional jump.
		# If EN is not a plain operator, this might involve compiling
		# the connected element.
		if conn_EN and conn_EN.isConnected:
			# Compile the element that drives this wire.
			otherConn = conn_EN.getConnectedConn(getOutput=True)
			insns.extend(otherConn.compileConn(targetInsnClass=AwlInsn_U,
							   inverted=False))

			# Emit the jump instruction.
			# This will evaluate the current VKE.
			insns.append(self.newInsn_JMP(AwlInsn_SPBNB, endLabel))

		def compileCounter(conn, counterInsnClass):
			if not conn or not conn.isConnected:
				return

			# Compile the element connected to the input.
			otherConn = conn.getConnectedConn(getOutput=True)
			insns.extend(otherConn.compileConn(targetInsnClass=AwlInsn_U))
			if otherConn.connType != FupCompiler_Conn.TYPE_VKE:
				raise FupElemError("The CU, CD, R and S connections "
					"of the FUP element %s must be connected "
					"to bit (VKE) wires." % (
					str(self)),
					self)

			# Add the counter instruction.
			insns.extend(bodyOperElem.compileAs(counterInsnClass))

		# Handle CU and CD counter inputs.
		compileCounter(conn_CU, AwlInsn_ZV)
		compileCounter(conn_CD, AwlInsn_ZR)

		# Handle set input.
		if conn_S and conn_S.isConnected:
			if not conn_PV or not conn_PV.isConnected:
				raise FupElemError("The S input of the FUP counter "
					"element %s is connected, but the PV input "
					"is not connected." % (
					str(self)),
					self)

			# Load the preset value PV.
			otherConn = conn_PV.getConnectedConn(getOutput=True)
			insns.extend(otherConn.compileConn(targetInsnClass=AwlInsn_L))
			if otherConn.connType != FupCompiler_Conn.TYPE_ACCU:
				raise FupElemError("The PV connection "
					"of the FUP element %s must be connected "
					"to WORD (ACCU) wires." % (
					str(self)),
					self)
			# Add the S Zx instruction.
			compileCounter(conn_S, AwlInsn_S)

		# Handle reset input.
		compileCounter(conn_R, AwlInsn_R)

		# Handle CV and CVB counter outputs.
		def compileCounterOutput(conn, bcd):
			if not conn or not conn.isConnected:
				return
			# Load the body operand into ACCU.
			insns.extend(bodyOperElem.compileAs(AwlInsn_LC if bcd
							    else AwlInsn_L))

			# Assign the outputs.
			storeToTempConns = set()
			for otherElem in self.sorted(conn.getConnectedElems(viaIn=True)):
				if otherElem.isType(FupCompiler_Elem.TYPE_OPERAND,
						    FupCompiler_ElemOper.SUBTYPE_ASSIGN):
					insns.extend(otherElem.emitStore_ACCU())
				else:
					storeToTempConns.add(conn)
			if storeToTempConns:
				if not bcd:
					storeToTempConns.add(self.MAIN_RESULT)
				insns.extend(self._storeToTemp("WORD", AwlInsn_T,
							       storeToTempConns))
		compileCounterOutput(conn_CV, bcd=False)
		compileCounterOutput(conn_CVB, bcd=True)

		# Make sure BIE is set, if EN is not connected and ENO is connected.
		if (not conn_EN or not conn_EN.isConnected) and\
		   (conn_ENO and conn_ENO.isConnected):
			# set BIE=1 and /ER=0.
			insns.extend(self.newInsns_SET_BIE_CLR_ER())

		# Create the jump target label for EN=0.
		# This might end up being unused, though.
		insns.append(self.newInsn_NOP(labelStr=endLabel))

		# Compile the Q output.
		if conn_Q and conn_Q.isConnected:
			# Load the body operand into VKE.
			insns.extend(bodyOperElem.compileAs(AwlInsn_U))

			if conn_EN and conn_EN.isConnected:
				# AND the EN input to Q, so that Q
				# output is 0 in case EN is 0.
				insns.append(self.newInsn_LOAD_BIE(AwlInsn_U))

			# Add VKE assignment instruction.
			storeToTempConns = set()
			for otherElem in self.sorted(conn_Q.getConnectedElems(viaIn=True)):
				if otherElem.isType(FupCompiler_Elem.TYPE_OPERAND,
						    FupCompiler_ElemOper.SUBTYPE_ASSIGN):
					insns.extend(otherElem.emitStore_VKE())
				else:
					storeToTempConns.add(conn_Q)
			if storeToTempConns:
				insns.extend(self._storeToTemp("BOOL", AwlInsn_ASSIGN,
							       storeToTempConns))

		# Handle ENO output.
		if conn_ENO and conn_ENO.isConnected:
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

	@property
	def isCompileEntryPoint(self):
		if not self.enabled:
			return False
		# We are a compilation entry, if no output is connected.
		conn_CV = self.getUniqueConnByText("CV", searchOutputs=True)
		conn_CVB = self.getUniqueConnByText("CVB", searchOutputs=True)
		conn_Q = self.getUniqueConnByText("Q", searchOutputs=True)
		conn_ENO = self.getUniqueConnByText("ENO", searchOutputs=True)
		if (conn_CV and conn_CV.isConnected) or\
		   (conn_CVB and conn_CVB.isConnected) or\
		   (conn_Q and conn_Q.isConnected) or\
		   (conn_ENO and conn_ENO.isConnected):
			return False
		return True

class FupCompiler_ElemCUD(FupCompiler_ElemCount):
	"""FUP compiler - S7 counter - up-down
	"""

	ELEM_NAME		= "CUD"
	SUBTYPE			= FupCompiler_ElemCount.SUBTYPE_CUD

class FupCompiler_ElemCU(FupCompiler_ElemCount):
	"""FUP compiler - S7 counter - up
	"""

	ELEM_NAME		= "CU"
	SUBTYPE			= FupCompiler_ElemCount.SUBTYPE_CU

class FupCompiler_ElemCUO(FupCompiler_ElemCount):
	"""FUP compiler - S7 counter - up-only
	"""

	ELEM_NAME		= "CUO"
	SUBTYPE			= FupCompiler_ElemCount.SUBTYPE_CUO

class FupCompiler_ElemCD(FupCompiler_ElemCount):
	"""FUP compiler - S7 counter - down
	"""

	ELEM_NAME		= "CD"
	SUBTYPE			= FupCompiler_ElemCount.SUBTYPE_CD

class FupCompiler_ElemCDO(FupCompiler_ElemCount):
	"""FUP compiler - S7 counter - down-only
	"""

	ELEM_NAME		= "CDO"
	SUBTYPE			= FupCompiler_ElemCount.SUBTYPE_CDO

class FupCompiler_ElemCSO(FupCompiler_ElemCount):
	"""FUP compiler - S7 counter - set
	"""

	ELEM_NAME		= "CSO"
	SUBTYPE			= FupCompiler_ElemCount.SUBTYPE_CSO

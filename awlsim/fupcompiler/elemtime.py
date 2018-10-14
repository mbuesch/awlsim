# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - S7 timer
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


class FupCompiler_ElemTime(FupCompiler_Elem):
	"""FUP compiler - S7 timer.
	"""

	ELEM_NAME		= "TIMER"
	SUBTYPE			= None
	AWLINSN			= None

	EnumGen.start
	SUBTYPE_SI		= EnumGen.item
	SUBTYPE_SV		= EnumGen.item
	SUBTYPE_SE		= EnumGen.item
	SUBTYPE_SS		= EnumGen.item
	SUBTYPE_SA		= EnumGen.item
	EnumGen.end

	str2subtype = {
		"si"	: SUBTYPE_SI,
		"sv"	: SUBTYPE_SV,
		"se"	: SUBTYPE_SE,
		"ss"	: SUBTYPE_SS,
		"sa"	: SUBTYPE_SA,
	}

	@classmethod
	def parse(cls, grid, x, y, subType, content):
		try:
			subType = cls.str2subtype[subType]
			type2class = {
				cls.SUBTYPE_SI	: FupCompiler_ElemTSI,
				cls.SUBTYPE_SV	: FupCompiler_ElemTSV,
				cls.SUBTYPE_SE	: FupCompiler_ElemTSE,
				cls.SUBTYPE_SS	: FupCompiler_ElemTSS,
				cls.SUBTYPE_SA	: FupCompiler_ElemTSA,
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
					  elemType=FupCompiler_Elem.TYPE_TIME,
					  subType=self.SUBTYPE,
					  content=content,
					  **kwargs)

	def connIsOptional(self, conn):
		if not self.enabled:
			return True
		return conn.hasText({ "EN", "ENO", "R", "BIN", "BCD", "Q", })

	def getConnType(self, conn, preferVKE=False):
		if self.enabled and conn in self.connections:
			if conn.hasText({ "EN", "ENO", "S", "R", "Q", }):
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
		elif conn.hasText("BIN") or conn.hasText("BCD"):
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
		conn_S = self.getUniqueConnByText("S", searchInputs=True)
		conn_TV = self.getUniqueConnByText("TV", searchInputs=True)
		conn_R = self.getUniqueConnByText("R", searchInputs=True)
		for conn in (conn_S, conn_TV, conn_R):
			if conn and conn.isConnected:
				connectedElem = conn.getConnectedElem(viaOut=True)
				if conn is not conn_TV:
					# If a simple BOOLEAN is connected to S or R
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
		conn_S = self.getUniqueConnByText("S", searchInputs=True)
		conn_TV = self.getUniqueConnByText("TV", searchInputs=True)
		conn_R = self.getUniqueConnByText("R", searchInputs=True)
		# Get all outputs.
		conn_BIN = self.getUniqueConnByText("BIN", searchOutputs=True)
		conn_BCD = self.getUniqueConnByText("BCD", searchOutputs=True)
		conn_Q = self.getUniqueConnByText("Q", searchOutputs=True)
		conn_ENO = self.getUniqueConnByText("ENO", searchOutputs=True)

		# Get the Zx body operator.
		bodyOperElem = self._getBodyOper()

		# Compile all elements connected to input connections (except for EN).
		for conn in (conn_S, conn_TV, conn_R):
			if not conn or not conn.isConnected:
				continue # Input is not connected.
			connectedElem = conn.getConnectedElem(viaOut=True)
			if not connectedElem.needCompile:
				continue # The element is compiled already.
			if conn is not conn_TV:
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

		# Compile the element connected to the S input.
		otherConn = conn_S.getConnectedConn(getOutput=True)
		insns.extend(otherConn.compileConn(targetInsnClass=AwlInsn_U))
		if otherConn.connType != FupCompiler_Conn.TYPE_VKE:
			raise FupElemError("The S connection "
				"of the FUP element %s must be connected "
				"to bit (VKE) wires." % (
				str(self)),
				self)

		# Compile the element connected to the TV input.
		otherConn = conn_TV.getConnectedConn(getOutput=True)
		insns.extend(otherConn.compileConn(targetInsnClass=AwlInsn_L))
		if otherConn.connType != FupCompiler_Conn.TYPE_ACCU:
			raise FupElemError("The TV connection "
				"of the FUP element %s must be connected "
				"to word (ACCU) wires." % (
				str(self)),
				self)

		# Add the timer instruction.
		insns.extend(bodyOperElem.compileAs(self.AWLINSN))

		# Handle reset input.
		if conn_R and conn_R.isConnected:
			otherConn = conn_R.getConnectedConn(getOutput=True)
			insns.extend(otherConn.compileConn(targetInsnClass=AwlInsn_U))
			if otherConn.connType != FupCompiler_Conn.TYPE_VKE:
				raise FupElemError("The R connection "
					"of the FUP element %s must be connected "
					"to bit (VKE) wires." % (
					str(self)),
					self)
			insns.extend(bodyOperElem.compileAs(AwlInsn_R))

		# Handle BIN and BCD counter outputs.
		def compileTimerOutput(conn, bcd):
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
		compileTimerOutput(conn_BIN, bcd=False)
		compileTimerOutput(conn_BCD, bcd=True)

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
		conn_BIN = self.getUniqueConnByText("BIN", searchOutputs=True)
		conn_BCD = self.getUniqueConnByText("BCD", searchOutputs=True)
		conn_Q = self.getUniqueConnByText("Q", searchOutputs=True)
		conn_ENO = self.getUniqueConnByText("ENO", searchOutputs=True)
		if (conn_BIN and conn_BIN.isConnected) or\
		   (conn_BCD and conn_BCD.isConnected) or\
		   (conn_Q and conn_Q.isConnected) or\
		   (conn_ENO and conn_ENO.isConnected):
			return False
		return True

class FupCompiler_ElemTSI(FupCompiler_ElemTime):
	"""FUP compiler - S7 timer - pulse
	"""

	ELEM_NAME		= "PULSE"
	SUBTYPE			= FupCompiler_ElemTime.SUBTYPE_SI
	AWLINSN			= AwlInsn_SI

class FupCompiler_ElemTSV(FupCompiler_ElemTime):
	"""FUP compiler - S7 timer - extended pulse
	"""

	ELEM_NAME		= "EXTPULSE"
	SUBTYPE			= FupCompiler_ElemTime.SUBTYPE_SV
	AWLINSN			= AwlInsn_SV

class FupCompiler_ElemTSE(FupCompiler_ElemTime):
	"""FUP compiler - S7 timer - ON delay
	"""

	ELEM_NAME		= "ONDELAY"
	SUBTYPE			= FupCompiler_ElemTime.SUBTYPE_SE
	AWLINSN			= AwlInsn_SE

class FupCompiler_ElemTSS(FupCompiler_ElemTime):
	"""FUP compiler - S7 timer - extended ON delay
	"""

	ELEM_NAME		= "EXTONDELAY"
	SUBTYPE			= FupCompiler_ElemTime.SUBTYPE_SS
	AWLINSN			= AwlInsn_SS

class FupCompiler_ElemTSA(FupCompiler_ElemTime):
	"""FUP compiler - S7 timer - OFF delay
	"""

	ELEM_NAME		= "OFFDELAY"
	SUBTYPE			= FupCompiler_ElemTime.SUBTYPE_SA
	AWLINSN			= AwlInsn_SA

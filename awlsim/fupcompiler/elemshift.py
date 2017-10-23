# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - Shift operations
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


class FupCompiler_ElemShift(FupCompiler_Elem):
	"""FUP compiler - Shift operation.
	"""

	ELEM_NAME		= "SHIFT"
	SUBTYPE			= None # Override this in the subclass
	SHIFT_INSN_CLASS	= None # Override this in the subclass

	EnumGen.start
	SUBTYPE_SSI		= EnumGen.item
	SUBTYPE_SSD		= EnumGen.item
	SUBTYPE_SLW		= EnumGen.item
	SUBTYPE_SRW		= EnumGen.item
	SUBTYPE_SLD		= EnumGen.item
	SUBTYPE_SRD		= EnumGen.item
	SUBTYPE_RRD		= EnumGen.item
	SUBTYPE_RLD		= EnumGen.item
	EnumGen.end

	str2subtype = {
		"ssi"	: SUBTYPE_SSI,
		"ssd"	: SUBTYPE_SSD,
		"slw"	: SUBTYPE_SLW,
		"srw"	: SUBTYPE_SRW,
		"sld"	: SUBTYPE_SLD,
		"srd"	: SUBTYPE_SRD,
		"rrd"	: SUBTYPE_RRD,
		"rld"	: SUBTYPE_RLD,
	}

	@classmethod
	def parse(cls, grid, x, y, subType, content):
		try:
			subType = cls.str2subtype[subType]
			type2class = {
				cls.SUBTYPE_SSI	: FupCompiler_ElemShiftSSI,
				cls.SUBTYPE_SSD	: FupCompiler_ElemShiftSSD,
				cls.SUBTYPE_SLW	: FupCompiler_ElemShiftSLW,
				cls.SUBTYPE_SRW	: FupCompiler_ElemShiftSRW,
				cls.SUBTYPE_SLD	: FupCompiler_ElemShiftSLD,
				cls.SUBTYPE_SRD	: FupCompiler_ElemShiftSRD,
				cls.SUBTYPE_RRD	: FupCompiler_ElemShiftRRD,
				cls.SUBTYPE_RLD	: FupCompiler_ElemShiftRLD,
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
					  elemType=FupCompiler_Elem.TYPE_SHIFT,
					  subType=self.SUBTYPE,
					  content=content,
					  **kwargs)

	def connIsOptional(self, conn):
		return conn.hasText({ "EN", "ENO", "LOB", })

	def getConnType(self, conn, preferVKE=False):
		if conn in self.connections:
			if conn.hasText({ "EN", "ENO", "LOB", }):
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
				"in FUP element %s." % (
				str(self)),
				self)
		return conn_EN, conn_ENO

	def __getConnsIN(self):
		"""Get IN and N connections.
		"""
		conn_IN = self.getUniqueConnByText("IN", searchInputs=True)
		conn_N = self.getUniqueConnByText("N", searchInputs=True)
		if not conn_IN or not conn_N:
			raise FupElemError("Invalid IN or N connections "
				"in FUP element %s." % (
				str(self)),
				self)
		return conn_IN, conn_N

	def __getConnFlag(self, connName):
		conn = self.getUniqueConnByText(connName, searchOutputs=True)
		if conn and conn.isConnected:
			return conn
		return None

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
		elif conn.hasText("LOB"):
			self._compileConn_checkTarget(conn, desiredTarget, inverted,
						      targetExpectVKE=True,
						      allowInversion=False)
			if self.needCompile:
				insns.extend(self.compile())
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
		# If the element connected to IN is not a LOAD operand, we must
		# take its ENO into account.
		# If we don't have a connection on EN, we implicitly connect
		# the IN-element's ENO to our EN here.
		# If we already have a connection on EN, we implicitly add an AND-element
		# between the IN-element's ENO and our EN.
		elemsA = []
		for conn in self.__getConnsIN():
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
		for conn in self.__getConnsIN():
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
		conn_IN, conn_N = self.__getConnsIN()
		for conn in (conn_N, conn_IN):
			otherConn = conn.getConnectedConn(getOutput=True)
			otherElem = otherConn.elem

			# Compile the element connected to the input.
			if otherElem.needCompile:
				insns.extend(otherElem.compile())
			else:
				insns.extend(otherConn.compileConn(targetInsnClass=AwlInsn_L))
			if conn.connType != FupCompiler_Conn.TYPE_ACCU:
				raise FupElemError("The IN connection "
					"of the FUP element %s must not be connected "
					"to a bit (VKE) wire." % (
					str(self)),
					self)
		# Add the shift operation.
		insns.append(self.newInsn(self.SHIFT_INSN_CLASS))

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
				       for name in {"LOB", })

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
					conn=self.__getConnFlag("LOB"),
					andWithBIE=conn_EN.isConnected,
					operType=AwlOperatorTypes.MEM_STW_NZ))

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

class FupCompiler_ElemShiftSSI(FupCompiler_ElemShift):
	"""FUP compiler - Shift operation - SSI
	"""

	ELEM_NAME		= "SSI"
	SUBTYPE			= FupCompiler_ElemShift.SUBTYPE_SSI
	SHIFT_INSN_CLASS	= AwlInsn_SSI

class FupCompiler_ElemShiftSSD(FupCompiler_ElemShift):
	"""FUP compiler - Shift operation - SSD
	"""

	ELEM_NAME		= "SSD"
	SUBTYPE			= FupCompiler_ElemShift.SUBTYPE_SSD
	SHIFT_INSN_CLASS	= AwlInsn_SSD

class FupCompiler_ElemShiftSLW(FupCompiler_ElemShift):
	"""FUP compiler - Shift operation - SLW
	"""

	ELEM_NAME		= "SLW"
	SUBTYPE			= FupCompiler_ElemShift.SUBTYPE_SLW
	SHIFT_INSN_CLASS	= AwlInsn_SLW

class FupCompiler_ElemShiftSRW(FupCompiler_ElemShift):
	"""FUP compiler - Shift operation - SRW
	"""

	ELEM_NAME		= "SRW"
	SUBTYPE			= FupCompiler_ElemShift.SUBTYPE_SRW
	SHIFT_INSN_CLASS	= AwlInsn_SRW

class FupCompiler_ElemShiftSLD(FupCompiler_ElemShift):
	"""FUP compiler - Shift operation - SLD
	"""

	ELEM_NAME		= "SLD"
	SUBTYPE			= FupCompiler_ElemShift.SUBTYPE_SLD
	SHIFT_INSN_CLASS	= AwlInsn_SLD

class FupCompiler_ElemShiftSRD(FupCompiler_ElemShift):
	"""FUP compiler - Shift operation - SRD
	"""

	ELEM_NAME		= "SRD"
	SUBTYPE			= FupCompiler_ElemShift.SUBTYPE_SRD
	SHIFT_INSN_CLASS	= AwlInsn_SRD

class FupCompiler_ElemShiftRLD(FupCompiler_ElemShift):
	"""FUP compiler - Shift operation - RLD
	"""

	ELEM_NAME		= "RLD"
	SUBTYPE			= FupCompiler_ElemShift.SUBTYPE_RLD
	SHIFT_INSN_CLASS	= AwlInsn_RLD

class FupCompiler_ElemShiftRRD(FupCompiler_ElemShift):
	"""FUP compiler - Shift operation - RRD
	"""

	ELEM_NAME		= "RRD"
	SUBTYPE			= FupCompiler_ElemShift.SUBTYPE_RRD
	SHIFT_INSN_CLASS	= AwlInsn_RRD

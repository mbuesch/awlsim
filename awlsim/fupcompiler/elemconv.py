# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - Value conversion boxes
#
# Copyright 2017-2018 Michael Buesch <m@bues.ch>
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


class FupCompiler_ElemConv(FupCompiler_Elem):
	"""FUP compiler - Value conversion operation.
	"""

	ELEM_NAME		= "CONV"
	SUBTYPE			= None # Override this in the subclass
	CONV_INSN_CLASS		= None # Override this in the subclass

	EnumGen.start
	SUBTYPE_BTI	= EnumGen.item
	SUBTYPE_ITB	= EnumGen.item
	SUBTYPE_BTD	= EnumGen.item
	SUBTYPE_ITD	= EnumGen.item
	SUBTYPE_DTB	= EnumGen.item
	SUBTYPE_DTR	= EnumGen.item
	SUBTYPE_INVI	= EnumGen.item
	SUBTYPE_INVD	= EnumGen.item
	SUBTYPE_NEGI	= EnumGen.item
	SUBTYPE_NEGD	= EnumGen.item
	SUBTYPE_NEGR	= EnumGen.item
	SUBTYPE_TAW	= EnumGen.item
	SUBTYPE_TAD	= EnumGen.item
	SUBTYPE_RND	= EnumGen.item
	SUBTYPE_TRUNC	= EnumGen.item
	SUBTYPE_RNDP	= EnumGen.item
	SUBTYPE_RNDN	= EnumGen.item
	EnumGen.end

	str2subtype = {
		"bti"	: SUBTYPE_BTI,
		"itb"	: SUBTYPE_ITB,
		"btd"	: SUBTYPE_BTD,
		"itd"	: SUBTYPE_ITD,
		"dtb"	: SUBTYPE_DTB,
		"dtr"	: SUBTYPE_DTR,
		"invi"	: SUBTYPE_INVI,
		"invd"	: SUBTYPE_INVD,
		"negi"	: SUBTYPE_NEGI,
		"negd"	: SUBTYPE_NEGD,
		"negr"	: SUBTYPE_NEGR,
		"taw"	: SUBTYPE_TAW,
		"tad"	: SUBTYPE_TAD,
		"rnd"	: SUBTYPE_RND,
		"trunc"	: SUBTYPE_TRUNC,
		"rndp"	: SUBTYPE_RNDP,
		"rndn"	: SUBTYPE_RNDN,
	}

	@classmethod
	def parse(cls, grid, x, y, subType, content):
		try:
			subType = cls.str2subtype[subType]
			type2class = {
				cls.SUBTYPE_BTI		: FupCompiler_ElemConvBTI,
				cls.SUBTYPE_ITB		: FupCompiler_ElemConvITB,
				cls.SUBTYPE_BTD		: FupCompiler_ElemConvBTD,
				cls.SUBTYPE_ITD		: FupCompiler_ElemConvITD,
				cls.SUBTYPE_DTB		: FupCompiler_ElemConvDTB,
				cls.SUBTYPE_DTR		: FupCompiler_ElemConvDTR,
				cls.SUBTYPE_INVI	: FupCompiler_ElemConvINVI,
				cls.SUBTYPE_INVD	: FupCompiler_ElemConvINVD,
				cls.SUBTYPE_NEGI	: FupCompiler_ElemConvNEGI,
				cls.SUBTYPE_NEGD	: FupCompiler_ElemConvNEGD,
				cls.SUBTYPE_NEGR	: FupCompiler_ElemConvNEGR,
				cls.SUBTYPE_TAW		: FupCompiler_ElemConvTAW,
				cls.SUBTYPE_TAD		: FupCompiler_ElemConvTAD,
				cls.SUBTYPE_RND		: FupCompiler_ElemConvRND,
				cls.SUBTYPE_TRUNC	: FupCompiler_ElemConvTRUNC,
				cls.SUBTYPE_RNDP	: FupCompiler_ElemConvRNDP,
				cls.SUBTYPE_RNDN	: FupCompiler_ElemConvRNDN,
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
					  elemType=FupCompiler_Elem.TYPE_CONV,
					  subType=self.SUBTYPE,
					  content=content,
					  **kwargs)

	def connIsOptional(self, conn):
		if not self.enabled:
			return True
		return conn.hasText({ "EN", "ENO", })

	def getConnType(self, conn, preferVKE=False):
		if self.enabled and conn in self.connections:
			if conn.hasText({ "EN", "ENO", }):
				return FupCompiler_Conn.TYPE_VKE
			return FupCompiler_Conn.TYPE_ACCU
		return FupCompiler_Conn.TYPE_UNKNOWN

	def __getConnsEN(self):
		"""Get EN and ENO connections.
		"""
		conn_EN = self.getUniqueConnByText("EN", searchInputs=True)
		conn_ENO = self.getUniqueConnByText("ENO", searchOutputs=True)
		return conn_EN, conn_ENO

	def __getConnIN(self):
		"""Get the IN connection.
		"""
		conn_IN = self.getUniqueConnByText("IN", searchInputs=True)
		if not conn_IN:
			raise FupElemError("No IN connection "
				"in FUP element %s." % (
				str(self)),
				self)
		return conn_IN

	def __allConnsOUT(self):
		"""Get all OUTx connections.
		"""
		for conn in FupCompiler_Conn.sorted(self.outConnections):
			if conn.textMatch(r"OUT\d+"):
				yield conn

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
		if not self.enabled:
			return
		# If the element connected to IN is not a LOAD operand, we must
		# take its ENO into account.
		# If we don't have a connection on EN, we implicitly connect
		# the IN-element's ENO to our EN here.
		# If we already have a connection on EN, we implicitly add an AND-element
		# between the IN-element's ENO and our EN.
		elemsA = []
		connectedElem = self.__getConnIN().getConnectedElem(viaOut=True)
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
		if not self.enabled:
			return []
		insns = []

		conn_EN, conn_ENO = self.__getConnsEN()
		enIsConnected = conn_EN is not None and conn_EN.isConnected
		enoIsConnected = conn_ENO is not None and conn_ENO.isConnected

		# Compile the element connected to the IN connection.
		conn_IN = self.__getConnIN()
		connectedElem = conn_IN.getConnectedElem(viaOut=True)
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
		if enIsConnected:
			# Compile the element that drives this wire.
			otherConn = conn_EN.getConnectedConn(getOutput=True)
			insns.extend(otherConn.compileConn(targetInsnClass=AwlInsn_U,
							   inverted=False))

			# Emit the jump instruction.
			# This will evaluate the current VKE.
			insns.append(self.newInsn_JMP(AwlInsn_SPBNB, endLabel))

		# Compile the actual operation.
		otherConn = conn_IN.getConnectedConn(getOutput=True)
		otherElem = otherConn.elem
		# Compile the element connected to the input.
		insns.extend(otherConn.compileConn(targetInsnClass=AwlInsn_L))
		if otherConn.connType != FupCompiler_Conn.TYPE_ACCU:
			raise FupElemError("The IN connection "
				"of the FUP conversion box %s must not be connected "
				"to a bit (VKE) wire." % (
				str(self)),
				self)
		# Append the actual operation.
		insns.append(self.newInsn(self.CONV_INSN_CLASS))

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

		# Make sure BIE is set, if EN is not connected and ENO is connected.
		if not enIsConnected and enoIsConnected:
			# set BIE=1 and /ER=0.
			insns.extend(self.newInsns_SET_BIE_CLR_ER())

		# Create the jump target label for EN=0.
		# This might end up being unused, though.
		insns.append(self.newInsn_NOP(labelStr=endLabel))

		# Handle ENO output.
		if enoIsConnected:
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

class FupCompiler_ElemConvBTI(FupCompiler_ElemConv):
	"""FUP compiler - Value conversion operation - BTI
	"""

	ELEM_NAME		= "BTI"
	SUBTYPE			= FupCompiler_ElemConv.SUBTYPE_BTI
	CONV_INSN_CLASS		= AwlInsn_BTI

class FupCompiler_ElemConvITB(FupCompiler_ElemConv):
	"""FUP compiler - Value conversion operation - ITB
	"""

	ELEM_NAME		= "ITB"
	SUBTYPE			= FupCompiler_ElemConv.SUBTYPE_ITB
	CONV_INSN_CLASS		= AwlInsn_ITB

class FupCompiler_ElemConvBTD(FupCompiler_ElemConv):
	"""FUP compiler - Value conversion operation - BTD
	"""

	ELEM_NAME		= "BTD"
	SUBTYPE			= FupCompiler_ElemConv.SUBTYPE_BTD
	CONV_INSN_CLASS		= AwlInsn_BTD

class FupCompiler_ElemConvITD(FupCompiler_ElemConv):
	"""FUP compiler - Value conversion operation - ITD
	"""

	ELEM_NAME		= "ITD"
	SUBTYPE			= FupCompiler_ElemConv.SUBTYPE_ITD
	CONV_INSN_CLASS		= AwlInsn_ITD

class FupCompiler_ElemConvDTB(FupCompiler_ElemConv):
	"""FUP compiler - Value conversion operation - DTB
	"""

	ELEM_NAME		= "DTB"
	SUBTYPE			= FupCompiler_ElemConv.SUBTYPE_DTB
	CONV_INSN_CLASS		= AwlInsn_DTB

class FupCompiler_ElemConvDTR(FupCompiler_ElemConv):
	"""FUP compiler - Value conversion operation - DTR
	"""

	ELEM_NAME		= "DTR"
	SUBTYPE			= FupCompiler_ElemConv.SUBTYPE_DTR
	CONV_INSN_CLASS		= AwlInsn_DTR

class FupCompiler_ElemConvINVI(FupCompiler_ElemConv):
	"""FUP compiler - Value conversion operation - INVI
	"""

	ELEM_NAME		= "INVI"
	SUBTYPE			= FupCompiler_ElemConv.SUBTYPE_INVI
	CONV_INSN_CLASS		= AwlInsn_INVI

class FupCompiler_ElemConvINVD(FupCompiler_ElemConv):
	"""FUP compiler - Value conversion operation - INVD
	"""

	ELEM_NAME		= "INVD"
	SUBTYPE			= FupCompiler_ElemConv.SUBTYPE_INVD
	CONV_INSN_CLASS		= AwlInsn_INVD

class FupCompiler_ElemConvNEGI(FupCompiler_ElemConv):
	"""FUP compiler - Value conversion operation - NEGI
	"""

	ELEM_NAME		= "NEGI"
	SUBTYPE			= FupCompiler_ElemConv.SUBTYPE_NEGI
	CONV_INSN_CLASS		= AwlInsn_NEGI

class FupCompiler_ElemConvNEGD(FupCompiler_ElemConv):
	"""FUP compiler - Value conversion operation - NEGD
	"""

	ELEM_NAME		= "NEGD"
	SUBTYPE			= FupCompiler_ElemConv.SUBTYPE_NEGD
	CONV_INSN_CLASS		= AwlInsn_NEGD

class FupCompiler_ElemConvNEGR(FupCompiler_ElemConv):
	"""FUP compiler - Value conversion operation - NEGR
	"""

	ELEM_NAME		= "NEGR"
	SUBTYPE			= FupCompiler_ElemConv.SUBTYPE_NEGR
	CONV_INSN_CLASS		= AwlInsn_NEGR

class FupCompiler_ElemConvTAW(FupCompiler_ElemConv):
	"""FUP compiler - Value conversion operation - TAW
	"""

	ELEM_NAME		= "TAW"
	SUBTYPE			= FupCompiler_ElemConv.SUBTYPE_TAW
	CONV_INSN_CLASS		= AwlInsn_TAW

class FupCompiler_ElemConvTAD(FupCompiler_ElemConv):
	"""FUP compiler - Value conversion operation - TAD
	"""

	ELEM_NAME		= "TAD"
	SUBTYPE			= FupCompiler_ElemConv.SUBTYPE_TAD
	CONV_INSN_CLASS		= AwlInsn_TAD

class FupCompiler_ElemConvRND(FupCompiler_ElemConv):
	"""FUP compiler - Value conversion operation - RND
	"""

	ELEM_NAME		= "RND"
	SUBTYPE			= FupCompiler_ElemConv.SUBTYPE_RND
	CONV_INSN_CLASS		= AwlInsn_RND

class FupCompiler_ElemConvTRUNC(FupCompiler_ElemConv):
	"""FUP compiler - Value conversion operation - TRUNC
	"""

	ELEM_NAME		= "TRUNC"
	SUBTYPE			= FupCompiler_ElemConv.SUBTYPE_TRUNC
	CONV_INSN_CLASS		= AwlInsn_TRUNC

class FupCompiler_ElemConvRNDP(FupCompiler_ElemConv):
	"""FUP compiler - Value conversion operation - RND+
	"""

	ELEM_NAME		= "RND+"
	SUBTYPE			= FupCompiler_ElemConv.SUBTYPE_RNDP
	CONV_INSN_CLASS		= AwlInsn_RNDP

class FupCompiler_ElemConvRNDN(FupCompiler_ElemConv):
	"""FUP compiler - Value conversion operation - RND-
	"""

	ELEM_NAME		= "RND-"
	SUBTYPE			= FupCompiler_ElemConv.SUBTYPE_RNDN
	CONV_INSN_CLASS		= AwlInsn_RNDN

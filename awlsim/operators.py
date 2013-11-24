# -*- coding: utf-8 -*-
#
# AWL simulator - operators
#
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
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

from awlsim.datatypes import *
from awlsim.statusword import *
from awlsim.util import *


class AwlOperator(object):
	enum.start	# Operator types

	IMM		= enum.item	# Immediate value (constant)
	IMM_REAL	= enum.item	# Real
	IMM_S5T		= enum.item	# S5T immediate
	IMM_TIME	= enum.item	# T# immediate
	IMM_DATE	= enum.item	# D# immediate
	IMM_TOD		= enum.item	# TOD# immediate
	IMM_DT		= enum.item	# DT# immediate
	IMM_PTR		= enum.item	# Pointer immediate

	MEM_E		= enum.item	# Input
	MEM_A		= enum.item	# Output
	MEM_M		= enum.item	# Flags
	MEM_L		= enum.item	# Localstack
	MEM_VL		= enum.item	# Parent localstack (indirect access)
	MEM_DB		= enum.item	# Global datablock
	MEM_DI		= enum.item	# Instance datablock
	MEM_T		= enum.item	# Timer
	MEM_Z		= enum.item	# Counter
	MEM_PA		= enum.item	# Peripheral output
	MEM_PE		= enum.item	# Peripheral input

	MEM_STW		= enum.item	# Status word bit read
	MEM_STW_Z	= enum.item	# Status word "==0" read
	MEM_STW_NZ	= enum.item	# Status word "<>0" read
	MEM_STW_POS	= enum.item	# Status word ">0" read
	MEM_STW_NEG	= enum.item	# Status word "<0" read
	MEM_STW_POSZ	= enum.item	# Status word ">=0" read
	MEM_STW_NEGZ	= enum.item	# Status word "<=0" read
	MEM_STW_UO	= enum.item	# Status word "UO" read

	LBL_REF		= enum.item	# Label reference

	BLKREF_FC	= enum.item	# FC reference
	BLKREF_SFC	= enum.item	# SFC reference
	BLKREF_FB	= enum.item	# FB reference
	BLKREF_SFB	= enum.item	# SFB reference
	BLKREF_DB	= enum.item	# DB reference
	BLKREF_DI	= enum.item	# DI reference

	NAMED_LOCAL	= enum.item	# Named local reference (#abc)
	NAMED_LOCAL_PTR	= enum.item	# Pointer to named local (P##abc)
	INTERF_DB	= enum.item	# Interface-DB access (translated NAMED_LOCAL)

	INDIRECT	= enum.item	# Indirect access
	UNSPEC		= enum.item	# Not (yet) specified memory region

	# Virtual operators used for debugging of the simulator
	VIRT_ACCU	= enum.item	# Accu
	VIRT_AR		= enum.item	# AR
	VIRT_DBR	= enum.item	# DB and DI registers

	enum.end	# Operator types

	# Type to string map
	type2str = {
		IMM		: "IMMEDIATE",
		IMM_REAL	: "REAL",
		IMM_S5T		: "S5T",
		IMM_TIME	: "TIME",
		IMM_DATE	: "DATE",
		IMM_TOD		: "TOD",
		IMM_DT		: "DT",
		IMM_PTR		: "P#",
	
		MEM_E		: "E",
		MEM_A		: "A",
		MEM_M		: "M",
		MEM_L		: "L",
		MEM_VL		: "VL",
		MEM_DB		: "DB",
		MEM_DI		: "DI",
		MEM_T		: "T",
		MEM_Z		: "Z",
		MEM_PA		: "PA",
		MEM_PE		: "PE",

		MEM_STW		: "STW",
		MEM_STW_Z	: "==0",
		MEM_STW_NZ	: "<>0",
		MEM_STW_POS	: ">0",
		MEM_STW_NEG	: "<0",
		MEM_STW_POSZ	: ">=0",
		MEM_STW_NEGZ	: "<=0",
		MEM_STW_UO	: "UO",

		LBL_REF		: "LABEL",
	
		BLKREF_FC	: "BLOCK_FC",
		BLKREF_SFC	: "BLOCK_SFC",
		BLKREF_FB	: "BLOCK_FB",
		BLKREF_SFB	: "BLOCK_SFB",
		BLKREF_DB	: "BLOCK_DB",
		BLKREF_DI	: "BLOCK_DI",
	
		NAMED_LOCAL	: "#LOCAL",
		INTERF_DB	: "__INTERFACE_DB",
	
		INDIRECT	: "__INDIRECT",
	
		VIRT_ACCU	: "__ACCU",
		VIRT_AR		: "__AR",
	}

	def __init__(self, type, width, value, insn=None):
		self.type = type
		self.width = width
		self.value = value
		self.labelIndex = None
		self.insn = insn
		self.isExtended = False

	# Make a deep copy, except for "insn".
	def dup(self):
		if isInteger(self.value):
			dupValue = self.value
		else:
			dupValue = self.value.dup()
		oper = AwlOperator(type = self.type,
				   width = self.width,
				   value = dupValue,
				   insn = self.insn)
		oper.setExtended(self.isExtended)
		oper.setLabelIndex(self.labelIndex)
		return oper

	def setInsn(self, newInsn):
		self.insn = newInsn

	def setExtended(self, isExtended):
		self.isExtended = isExtended

	def setLabelIndex(self, newLabelIndex):
		self.labelIndex = newLabelIndex

	def _raiseTypeError(self, actualType, expectedTypes):
		expectedTypes = [ self.type2str[t] for t in expectedTypes ]
		raise AwlSimError("Invalid operator type. Got %s, but expected %s." %\
			(self.type2str[actualType],
			 listToHumanStr(expectedTypes)),
			insn=self.insn)

	def assertType(self, types, lowerLimit=None, upperLimit=None):
		types = toList(types)
		if not self.type in types:
			self._raiseTypeError(self.type, types)
		if lowerLimit is not None:
			if self.value < lowerLimit:
				raise AwlSimError("Operator value too small",
						  insn=self.insn)
		if upperLimit is not None:
			if self.value > upperLimit:
				raise AwlSimError("Operator value too big",
						  insn=self.insn)

	def resolve(self, store=True):
		# This already is a direct operator.
		return self

	def __repr__(self):
		if self.type == self.IMM:
			if self.width == 8:
				return str(byteToSignedPyInt(self.value))
			if self.width == 16:
				return str(wordToSignedPyInt(self.value))
			elif self.width == 32:
				return "L#" + str(dwordToSignedPyInt(self.value))
		if self.type == self.IMM_REAL:
			return str(dwordToPyFloat(self.value))
		elif self.type == self.IMM_S5T:
			return "S5T#" #TODO
		elif self.type == self.IMM_TIME:
			return "T#" #TODO
		elif self.type == self.IMM_DATE:
			return "D#" #TODO
		elif self.type == self.IMM_TOD:
			return "TOD#" #TODO
		elif self.type in (self.MEM_A, self.MEM_E,
				   self.MEM_M, self.MEM_L):
			pfx = self.type2str[self.type]
			if self.width == 1:
				return "%s %d.%d" %\
					(pfx, self.value.byteOffset, self.value.bitOffset)
			elif self.width == 8:
				return "%sB %d" % (pfx, self.value.byteOffset)
			elif self.width == 16:
				return "%sW %d" % (pfx, self.value.byteOffset)
			elif self.width == 32:
				return "%sD %d" % (pfx, self.value.byteOffset)
		elif self.type == self.MEM_DB:
			if self.value.dbNumber is None:
				dbPrefix = ""
			else:
				dbPrefix = "DB%d." % self.value.dbNumber
			if self.width == 1:
				return "%sDBX %d.%d" % (dbPrefix,
							self.value.byteOffset,
							self.value.bitOffset)
			elif self.width == 8:
				return "%sDBB %d" % (dbPrefix, self.value.byteOffset)
			elif self.width == 16:
				return "%sDBW %d" % (dbPrefix, self.value.byteOffset)
			elif self.width == 32:
				return "%sDBD %d" % (dbPrefix, self.value.byteOffset)
		elif self.type == self.MEM_DI:
			if self.width == 1:
				return "DIX %d.%d" % (self.value.byteOffset, self.value.bitOffset)
			elif self.width == 8:
				return "DIB %d" % self.value.byteOffset
			elif self.width == 16:
				return "DIW %d" % self.value.byteOffset
			elif self.width == 32:
				return "DID %d" % self.value.byteOffset
		elif self.type == self.MEM_T:
			return "T %d" % self.value.byteOffset
		elif self.type == self.MEM_Z:
			return "Z %d" % self.value.byteOffset
		elif self.type == self.MEM_PA:
			if self.width == 8:
				return "PAB %d" % self.value.byteOffset
			elif self.width == 16:
				return "PAW %d" % self.value.byteOffset
			elif self.width == 32:
				return "PAD %d" % self.value.byteOffset
		elif self.type == self.MEM_PE:
			if self.width == 8:
				return "PEB %d" % self.value.byteOffset
			elif self.width == 16:
				return "PEW %d" % self.value.byteOffset
			elif self.width == 32:
				return "PED %d" % self.value.byteOffset
		elif self.type == self.MEM_STW:
			return "__STW " + S7StatusWord.nr2name[self.value.bitOffset]
		elif self.type == self.LBL_REF:
			return self.value
		elif self.type == self.BLKREF_FC:
			return "FC %d" % self.value.byteOffset
		elif self.type == self.BLKREF_SFC:
			return "SFC %d" % self.value.byteOffset
		elif self.type == self.BLKREF_FB:
			return "FB %d" % self.value.byteOffset
		elif self.type == self.BLKREF_SFB:
			return "SFB %d" % self.value.byteOffset
		elif self.type == self.BLKREF_DB:
			return "DB %d" % self.value.byteOffset
		elif self.type == self.BLKREF_DI:
			return "DI %d" % self.value.byteOffset
		elif self.type == self.NAMED_LOCAL:
			return "#%s" % self.value
		elif self.type == self.INTERF_DB:
			return "__INTERFACE_DB" #FIXME
		elif self.type == self.INDIRECT:
			assert(0) # Overloaded in AwlIndirectOp
		elif self.type == self.VIRT_ACCU:
			return "__ACCU %d" % self.value.byteOffset
		elif self.type == self.VIRT_AR:
			return "__AR %d" % self.value.byteOffset
		elif self.type == self.VIRT_DBR:
			return "__DBR %d" % self.value.byteOffset
		try:
			return self.type2str[self.type]
		except KeyError:
			assert(0)

class AwlIndirectOp(AwlOperator):
	"Indirect addressing operand"

	# Address register
	AR_NONE		= 0	# No address register
	AR_1		= 1	# Use AR1
	AR_2		= 2	# Use AR2

	# Address area mask
	ADDRESS_MASK	= 0x0000FFFFFF

	# Pointer area constants
	AREA_SHIFT	= 24
	AREA_MASK	= 0x00FF000000
	EXT_AREA_MASK	= 0xFFFF000000

	# Pointer area encodings
	AREA_NONE	= 0
	AREA_P		= 0x0080000000	# Peripheral area
	AREA_E		= 0x0081000000	# Input
	AREA_A		= 0x0082000000	# Output
	AREA_M		= 0x0083000000	# Flags
	AREA_DB		= 0x0084000000	# Global datablock
	AREA_DI		= 0x0085000000	# Instance datablock
	AREA_L		= 0x0086000000	# Localstack
	AREA_VL		= 0x0087000000	# Parent localstack

	# Extended area encodings. Only used for internal purposes.
	# These are not used in the interpreted AWL code.
	EXT_AREA_T		= 0x01FF000000	# Timer
	EXT_AREA_Z		= 0x02FF000000	# Counter
	EXT_AREA_BLKREF_DB	= 0x03FF000000	# DB block reference
	EXT_AREA_BLKREF_FB	= 0x04FF000000	# FB block reference
	EXT_AREA_BLKREF_FC	= 0x05FF000000	# FC block reference
	EXT_AREA_INTERF_DB	= 0x06FF000000	# INTERF_DB

	# Map for converting area code to operator type for fetch operations
	area2optype_fetch = {
		AREA_P			: AwlOperator.MEM_PE,
		AREA_E			: AwlOperator.MEM_E,
		AREA_A			: AwlOperator.MEM_A,
		AREA_M			: AwlOperator.MEM_M,
		AREA_DB			: AwlOperator.MEM_DB,
		AREA_DI			: AwlOperator.MEM_DI,
		AREA_L			: AwlOperator.MEM_L,
		AREA_VL			: AwlOperator.MEM_VL,
		EXT_AREA_T		: AwlOperator.MEM_T,
		EXT_AREA_Z		: AwlOperator.MEM_Z,
		EXT_AREA_BLKREF_DB	: AwlOperator.BLKREF_DB,
		EXT_AREA_BLKREF_FB	: AwlOperator.BLKREF_FB,
		EXT_AREA_BLKREF_FC	: AwlOperator.BLKREF_FC,
		EXT_AREA_INTERF_DB	: AwlOperator.INTERF_DB,
	}

	# Map for converting area code to operator type for store operations
	area2optype_store = area2optype_fetch.copy()
	area2optype_store[AREA_P] = AwlOperator.MEM_PA

	# Map for converting operator type to area code
	optype2area = pivotDict(area2optype_fetch)
	optype2area[AwlOperator.MEM_PA] = AREA_P
	optype2area[AwlOperator.UNSPEC] = AREA_NONE

	def __init__(self, area, width, addressRegister, offsetOper, insn=None):
		AwlOperator.__init__(self,
				     type = AwlOperator.INDIRECT,
				     width = width,
				     value = None,
				     insn = insn)
		assert(width in (1, 8, 16, 32))
		self.area = area
		self.addressRegister = addressRegister
		self.offsetOper = offsetOper

	# Make a deep copy, except for "insn".
	def dup(self):
		return AwlIndirectOp(area = self.area,
				     width = self.width,
				     addressRegister = self.addressRegister,
				     offsetOper = self.offsetOper.dup(),
				     insn = self.insn)

	def setInsn(self, newInsn):
		AwlOperator.setInsn(self, newInsn)
		self.offsetOper.setInsn(newInsn)

	def assertType(self, types, lowerLimit=None, upperLimit=None):
		types = toList(types)
		if not self.area2optype_fetch[self.area] in types and\
		   not self.area2optype_store[self.area] in types:
			self._raiseTypeError(self.area2optype_fetch[self.area], types)
		assert(lowerLimit is None)
		assert(upperLimit is None)

	# Possible offset oper types for indirect access
	__possibleOffsetOperTypes = (AwlOperator.MEM_M,
				     AwlOperator.MEM_L,
				     AwlOperator.MEM_DB,
				     AwlOperator.MEM_DI,
				     AwlOperator.INTERF_DB)

	# Resolve this indirect operator to a direct operator.
	def resolve(self, store=True):
		bitwiseDirectOffset = True
		offsetOper = self.offsetOper
		# Construct the pointer
		if self.addressRegister == AwlIndirectOp.AR_NONE:
			# Indirect access
			if self.area == AwlIndirectOp.AREA_NONE:
				raise AwlSimError("Area-spanning access not "
					"possible in indirect access without "
					"address register.")
			if self.area > AwlIndirectOp.AREA_MASK:
				# Is extended area
				possibleWidths = (8, 16, 32)
				bitwiseDirectOffset = False
			else:
				# Is standard area
				possibleWidths = (32,)
			if offsetOper.type not in self.__possibleOffsetOperTypes:
				raise AwlSimError("Offset operator in indirect "
					"access is not a valid memory offset.")
			if offsetOper.width not in possibleWidths:
				raise AwlSimError("Offset operator in indirect "
					"access is not of %s bit width." %\
					listToHumanStr(possibleWidths))
			offsetValue = self.insn.cpu.fetch(offsetOper)
			pointer = (self.area | (offsetValue & 0x00FFFFFF))
		else:
			# Register-indirect access
			if offsetOper.type != AwlOperator.IMM_PTR:
				raise AwlSimError("Offset operator in "
					"register-indirect access is not a "
					"pointer immediate.")
			offsetValue = self.insn.cpu.fetch(offsetOper)
			if self.area == AwlIndirectOp.AREA_NONE:
				# Area-spanning access
				pointer = (self.insn.cpu.getAR(self.addressRegister).get() +\
					   offsetValue) & 0xFFFFFFFF
			else:
				# Area-internal access
				pointer = ((self.insn.cpu.getAR(self.addressRegister).get() +
					    offsetValue) & 0x00FFFFFF) |\
					  self.area
		# Create a direct operator
		try:
			if store:
				optype = AwlIndirectOp.area2optype_store[
						pointer & AwlIndirectOp.EXT_AREA_MASK]
			else:
				optype = AwlIndirectOp.area2optype_fetch[
						pointer & AwlIndirectOp.EXT_AREA_MASK]
		except KeyError:
			raise AwlSimError("Invalid area code (%X hex) in indirect addressing" %\
				((pointer & AwlIndirectOp.EXT_AREA_MASK) >>\
				 AwlIndirectOp.AREA_SHIFT))
		if bitwiseDirectOffset:
			# 'pointer' has pointer format
			directOffset = AwlOffset.fromPointerValue(pointer)
		else:
			# 'pointer' is a byte offset
			directOffset = AwlOffset(pointer & AwlIndirectOp.ADDRESS_MASK)
		if self.width != 1 and directOffset.bitOffset:
			raise AwlSimError("Bit offset (lowest three bits) in %d-bit "
				"indirect addressing is not zero. "
				"(Computed offset is: %s)" %\
				(self.width, str(directOffset)))
		return AwlOperator(optype, self.width, directOffset, self.insn)

	def __repr__(self):
		return "__INDIRECT" #TODO

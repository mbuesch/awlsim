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

from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim.core.compat import *

from awlsim.core.datatypes import *
from awlsim.core.statusword import *
from awlsim.core.lstack import *
from awlsim.core.util import *


class AwlOperator(object):
	EnumGen.start	# Operator types

	IMM		= EnumGen.item	# Immediate value (constant)
	IMM_REAL	= EnumGen.item	# Real
	IMM_S5T		= EnumGen.item	# S5T immediate
	IMM_TIME	= EnumGen.item	# T# immediate
	IMM_DATE	= EnumGen.item	# D# immediate
	IMM_TOD		= EnumGen.item	# TOD# immediate
	IMM_DT		= EnumGen.item	# DT# immediate
	IMM_PTR		= EnumGen.item	# Pointer immediate

	MEM_E		= EnumGen.item	# Input
	MEM_A		= EnumGen.item	# Output
	MEM_M		= EnumGen.item	# Flags
	MEM_L		= EnumGen.item	# Localstack
	MEM_VL		= EnumGen.item	# Parent localstack (indirect access)
	MEM_DB		= EnumGen.item	# Global datablock
	MEM_DI		= EnumGen.item	# Instance datablock
	MEM_T		= EnumGen.item	# Timer
	MEM_Z		= EnumGen.item	# Counter
	MEM_PA		= EnumGen.item	# Peripheral output
	MEM_PE		= EnumGen.item	# Peripheral input

	MEM_STW		= EnumGen.item	# Status word bit read
	MEM_STW_Z	= EnumGen.item	# Status word "==0" read
	MEM_STW_NZ	= EnumGen.item	# Status word "<>0" read
	MEM_STW_POS	= EnumGen.item	# Status word ">0" read
	MEM_STW_NEG	= EnumGen.item	# Status word "<0" read
	MEM_STW_POSZ	= EnumGen.item	# Status word ">=0" read
	MEM_STW_NEGZ	= EnumGen.item	# Status word "<=0" read
	MEM_STW_UO	= EnumGen.item	# Status word "UO" read

	MEM_DBLG	= EnumGen.item	# DB-register: DB length
	MEM_DBNO	= EnumGen.item	# DB-register: DB number
	MEM_DILG	= EnumGen.item	# DI-register: DB length
	MEM_DINO	= EnumGen.item	# DI-register: DB number

	MEM_AR2		= EnumGen.item	# AR2 register

	BLKREF_FC	= EnumGen.item	# FC reference
	BLKREF_SFC	= EnumGen.item	# SFC reference
	BLKREF_FB	= EnumGen.item	# FB reference
	BLKREF_SFB	= EnumGen.item	# SFB reference
	BLKREF_UDT	= EnumGen.item	# UDT reference
	BLKREF_DB	= EnumGen.item	# DB reference
	BLKREF_DI	= EnumGen.item	# DI reference
	BLKREF_OB	= EnumGen.item	# OB reference (only symbol table)
	BLKREF_VAT	= EnumGen.item	# VAT reference (only symbol table)

	LBL_REF		= EnumGen.item	# Label reference
	SYMBOLIC	= EnumGen.item	# Classic symbolic reference ("xyz")
	NAMED_LOCAL	= EnumGen.item	# Named local reference (#abc)
	NAMED_LOCAL_PTR	= EnumGen.item	# Pointer to named local (P##abc)

	INDIRECT	= EnumGen.item	# Indirect access
	UNSPEC		= EnumGen.item	# Not (yet) specified memory region

	# Virtual operators used internally in awlsim, only.
	# These operators do not have standard AWL mnemonics.
	VIRT_ACCU	= EnumGen.item	# Accu
	VIRT_AR		= EnumGen.item	# AR
	VIRT_DBR	= EnumGen.item	# DB and DI registers

	EnumGen.end	# Operator types

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

		MEM_DBLG	: "DBLG",
		MEM_DBNO	: "DBNO",
		MEM_DILG	: "DILG",
		MEM_DINO	: "DINO",
		MEM_AR2		: "AR2",

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
		BLKREF_UDT	: "BLOCK_UDT",
		BLKREF_DB	: "BLOCK_DB",
		BLKREF_DI	: "BLOCK_DI",
		BLKREF_OB	: "BLOCK_OB",
		BLKREF_VAT	: "BLOCK_VAT",

		NAMED_LOCAL	: "#LOCAL",

		INDIRECT	: "__INDIRECT",

		VIRT_ACCU	: "__ACCU",
		VIRT_AR		: "__AR",
		VIRT_DBR	: "__DBR",
	}

	def __init__(self, type, width, value, insn=None):
		# type -> The operator type ID number. See "Operator types" above.
		# width -> The bit width of the access.
		# value -> The value. May be an AwlOffset or a string (depends on type).
		# insn -> The instruction this operator is used in. May be None.
		self.type = type
		self.width = width
		self.value = value
		self.labelIndex = None
		self.insn = insn
		self.isExtended = False
		# The symbol resolver may also put a "self.interfaceIndex" number in here.

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
		if self.type == AwlOperator.NAMED_LOCAL or\
		   self.type == AwlOperator.NAMED_LOCAL_PTR:
			return #FIXME we should check type for these, too.
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

	# Resolve this indirect operator to a direct operator.
	def resolve(self, store=True):
		# This already is a direct operator.
		if self.type == self.NAMED_LOCAL:
			# This is a named-local access (#abc).
			# Resolve it to an interface-operator.
			return self.insn.cpu.callStackTop.interfRefs[self.interfaceIndex].resolve()
		return self

	# Make an area-spanning pointer (32 bit) to this memory area.
	def makePointer(self):
		try:
			area = AwlIndirectOp.optype2area[self.type]
		except KeyError as e:
			raise AwlSimError("Could not transform operator '%s' "
				"into a pointer." % str(self))
		return area | self.value.toPointerValue()

	def __repr__(self):
		if self.type == self.IMM:
			if self.width == 1:
				return "TRUE" if (self.value & 1) else "FALSE"
			elif self.width == 8:
				return str(byteToSignedPyInt(self.value))
			elif self.width == 16:
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
				   self.MEM_M, self.MEM_L, self.MEM_VL):
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
		elif self.type == self.BLKREF_UDT:
			return "UDT %d" % self.value.byteOffset
		elif self.type == self.BLKREF_DB:
			return "DB %d" % self.value.byteOffset
		elif self.type == self.BLKREF_DI:
			return "DI %d" % self.value.byteOffset
		elif self.type == self.BLKREF_OB:
			return "OB %d" % self.value.byteOffset
		elif self.type == self.BLKREF_VAT:
			return "VAT %d" % self.value.byteOffset
		elif self.type == self.SYMBOLIC:
			return '"%s"' % self.value
		elif self.type == self.NAMED_LOCAL:
			return "#%s" % self.value
		elif self.type == self.NAMED_LOCAL_PTR:
			return "P##%s" % self.value
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
	ADDRESS_MASK	= 0x0000FFFFFF #FIXME should be 0x7FFFF

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
	}

	# Map for converting area code to operator type for store operations
	area2optype_store = area2optype_fetch.copy()
	area2optype_store[AREA_P] = AwlOperator.MEM_PA

	# Map for converting operator type to area code
	optype2area = pivotDict(area2optype_fetch)
	optype2area[AwlOperator.MEM_PA] = AREA_P
	optype2area[AwlOperator.UNSPEC] = AREA_NONE

	def __init__(self, area, width, addressRegister, offsetOper, insn=None):
		# area -> The area code for this indirect operation.
		#         AREA_... or EXT_AREA_...
		#         This corresponds to the area code in AWL pointer format.
		# width -> The width (in bits) of the region that is being adressed.
		# addressRegister -> One of:
		#                    AR_NONE => This is a memory-indirect access.
		#                    AR_1 => This is a register-indirect access with AR1.
		#                    AR_2 => This is a register-indirect access with AR2.
		# offsetOper -> This is the AwlOperator for the offset.
		#               For memory-indirect access, this must be an AwlOperator
		#               with "type in __possibleOffsetOperTypes".
		#               For register-indirect access, this must be an AwlOperator
		#               with "type==IMM_PTR".
		# insn -> The instruction this operator is used in. May be None.
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
				     AwlOperator.MEM_DI)

	# Resolve this indirect operator to a direct operator.
	def resolve(self, store=True):
		bitwiseDirectOffset = True
		offsetOper = self.offsetOper
		# Construct the pointer
		if self.addressRegister == AwlIndirectOp.AR_NONE:
			# Memory-indirect access
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

	def makePointer(self):
		# This is a programming error.
		# The caller should resolve() the operator first.
		raise AwlSimError("BUG: Can not transform indirect operator "
			"into a pointer. Resolve it first.")

	def __repr__(self):
		return "__INDIRECT" #TODO

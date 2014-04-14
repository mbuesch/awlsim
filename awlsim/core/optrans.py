#
# AWL simulator - Operator translator
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

import math
import re

from awlsim.core.util import *
from awlsim.core.operators import *
from awlsim.core.parameters import *
from awlsim.core.datatypes import *
from awlsim.core.parser import *
from awlsim.core.timers import *
from awlsim.core.cpuspecs import *


class OpDescriptor(object):
	"Instruction operator descriptor"

	# operator => AwlOperator or AwlIndirectOp
	# fieldCount => Number of consumed tokens
	def __init__(self, operator, fieldCount):
		self.operator = operator
		self.fieldCount = fieldCount

	# Make a deep copy
	def dup(self):
		return OpDescriptor(operator = self.operator.dup(),
				    fieldCount = self.fieldCount)

class AwlOpTranslator(object):
	"Instruction operator translator"

	__constOperTab_german = {
		"B"	: OpDescriptor(AwlOperator(AwlOperator.UNSPEC, 8,
				       AwlOffset(-1, -1)), 2),
		"W"	: OpDescriptor(AwlOperator(AwlOperator.UNSPEC, 16,
				       AwlOffset(-1, -1)), 2),
		"D"	: OpDescriptor(AwlOperator(AwlOperator.UNSPEC, 32,
				       AwlOffset(-1, -1)), 2),
		"==0"	: OpDescriptor(AwlOperator(AwlOperator.MEM_STW_Z, 1,
				       AwlOffset(0, 0)), 1),
		"<>0"	: OpDescriptor(AwlOperator(AwlOperator.MEM_STW_NZ, 1,
				       AwlOffset(0, 0)), 1),
		">0"	: OpDescriptor(AwlOperator(AwlOperator.MEM_STW_POS, 1,
				       AwlOffset(0, 0)), 1),
		"<0"	: OpDescriptor(AwlOperator(AwlOperator.MEM_STW_NEG, 1,
				       AwlOffset(0, 0)), 1),
		">=0"	: OpDescriptor(AwlOperator(AwlOperator.MEM_STW_POSZ, 1,
				       AwlOffset(0, 0)), 1),
		"<=0"	: OpDescriptor(AwlOperator(AwlOperator.MEM_STW_NEGZ, 1,
				       AwlOffset(0, 0)), 1),
		"OV"	: OpDescriptor(AwlOperator(AwlOperator.MEM_STW, 1,
				       AwlOffset(0, 5)), 1),
		"OS"	: OpDescriptor(AwlOperator(AwlOperator.MEM_STW, 1,
				       AwlOffset(0, 4)), 1),
		"UO"	: OpDescriptor(AwlOperator(AwlOperator.MEM_STW_UO, 1,
				       AwlOffset(0, 0)), 1),
		"BIE"	: OpDescriptor(AwlOperator(AwlOperator.MEM_STW, 1,
				       AwlOffset(0, 8)), 1),
		"E"	: OpDescriptor(AwlOperator(AwlOperator.MEM_E, 1,
				       AwlOffset(-1, -1)), 2),
		"EB"	: OpDescriptor(AwlOperator(AwlOperator.MEM_E, 8,
				       AwlOffset(-1, 0)), 2),
		"EW"	: OpDescriptor(AwlOperator(AwlOperator.MEM_E, 16,
				       AwlOffset(-1, 0)), 2),
		"ED"	: OpDescriptor(AwlOperator(AwlOperator.MEM_E, 32,
				       AwlOffset(-1, 0)), 2),
		"A"	: OpDescriptor(AwlOperator(AwlOperator.MEM_A, 1,
				       AwlOffset(-1, -1)), 2),
		"AB"	: OpDescriptor(AwlOperator(AwlOperator.MEM_A, 8,
				       AwlOffset(-1, 0)), 2),
		"AW"	: OpDescriptor(AwlOperator(AwlOperator.MEM_A, 16,
				       AwlOffset(-1, 0)), 2),
		"AD"	: OpDescriptor(AwlOperator(AwlOperator.MEM_A, 32,
				       AwlOffset(-1, 0)), 2),
		"L"	: OpDescriptor(AwlOperator(AwlOperator.MEM_L, 1,
				       AwlOffset(-1, -1)), 2),
		"LB"	: OpDescriptor(AwlOperator(AwlOperator.MEM_L, 8,
				       AwlOffset(-1, 0)), 2),
		"LW"	: OpDescriptor(AwlOperator(AwlOperator.MEM_L, 16,
				       AwlOffset(-1, 0)), 2),
		"LD"	: OpDescriptor(AwlOperator(AwlOperator.MEM_L, 32,
				       AwlOffset(-1, 0)), 2),
		"M"	: OpDescriptor(AwlOperator(AwlOperator.MEM_M, 1,
				       AwlOffset(-1, -1)), 2),
		"MB"	: OpDescriptor(AwlOperator(AwlOperator.MEM_M, 8,
				       AwlOffset(-1, 0)), 2),
		"MW"	: OpDescriptor(AwlOperator(AwlOperator.MEM_M, 16,
				       AwlOffset(-1, 0)), 2),
		"MD"	: OpDescriptor(AwlOperator(AwlOperator.MEM_M, 32,
				       AwlOffset(-1, 0)), 2),
		"T"	: OpDescriptor(AwlOperator(AwlOperator.MEM_T, 16,
				       AwlOffset(-1, 0)), 2),
		"Z"	: OpDescriptor(AwlOperator(AwlOperator.MEM_Z, 16,
				       AwlOffset(-1, 0)), 2),
		"FC"	: OpDescriptor(AwlOperator(AwlOperator.BLKREF_FC, 16,
				       AwlOffset(-1, 0)), 2),
		"SFC"	: OpDescriptor(AwlOperator(AwlOperator.BLKREF_SFC, 16,
				       AwlOffset(-1, 0)), 2),
		"FB"	: OpDescriptor(AwlOperator(AwlOperator.BLKREF_FB, 16,
				       AwlOffset(-1, 0)), 2),
		"SFB"	: OpDescriptor(AwlOperator(AwlOperator.BLKREF_SFB, 16,
				       AwlOffset(-1, 0)), 2),
		"UDT"	: OpDescriptor(AwlOperator(AwlOperator.BLKREF_UDT, 16,
				       AwlOffset(-1, 0)), 2),
		"DB"	: OpDescriptor(AwlOperator(AwlOperator.BLKREF_DB, 16,
				       AwlOffset(-1, 0)), 2),
		"DI"	: OpDescriptor(AwlOperator(AwlOperator.BLKREF_DI, 16,
				       AwlOffset(-1, 0)), 2),
		"OB"	: OpDescriptor(AwlOperator(AwlOperator.BLKREF_OB, 16,
				       AwlOffset(-1, 0)), 2),
		"VAT"	: OpDescriptor(AwlOperator(AwlOperator.BLKREF_VAT, 16,
				       AwlOffset(-1, 0)), 2),
		"DBX"	: OpDescriptor(AwlOperator(AwlOperator.MEM_DB, 1,
				       AwlOffset(-1, -1)), 2),
		"DBB"	: OpDescriptor(AwlOperator(AwlOperator.MEM_DB, 8,
				       AwlOffset(-1, 0)), 2),
		"DBW"	: OpDescriptor(AwlOperator(AwlOperator.MEM_DB, 16,
				       AwlOffset(-1, 0)), 2),
		"DBD"	: OpDescriptor(AwlOperator(AwlOperator.MEM_DB, 32,
				       AwlOffset(-1, 0)), 2),
		"DIX"	: OpDescriptor(AwlOperator(AwlOperator.MEM_DI, 1,
				       AwlOffset(-1, -1)), 2),
		"DIB"	: OpDescriptor(AwlOperator(AwlOperator.MEM_DI, 8,
				       AwlOffset(-1, 0)), 2),
		"DIW"	: OpDescriptor(AwlOperator(AwlOperator.MEM_DI, 16,
				       AwlOffset(-1, 0)), 2),
		"DID"	: OpDescriptor(AwlOperator(AwlOperator.MEM_DI, 32,
				       AwlOffset(-1, 0)), 2),
		"DBLG"	: OpDescriptor(AwlOperator(AwlOperator.MEM_DBLG, 32,
				       AwlOffset(0, 0)), 1),
		"DBNO"	: OpDescriptor(AwlOperator(AwlOperator.MEM_DBNO, 32,
				       AwlOffset(0, 0)), 1),
		"DILG"	: OpDescriptor(AwlOperator(AwlOperator.MEM_DILG, 32,
				       AwlOffset(0, 0)), 1),
		"DINO"	: OpDescriptor(AwlOperator(AwlOperator.MEM_DINO, 32,
				       AwlOffset(0, 0)), 1),
		"PEB"	: OpDescriptor(AwlOperator(AwlOperator.MEM_PE, 8,
				       AwlOffset(-1, 0)), 2),
		"PEW"	: OpDescriptor(AwlOperator(AwlOperator.MEM_PE, 16,
				       AwlOffset(-1, 0)), 2),
		"PED"	: OpDescriptor(AwlOperator(AwlOperator.MEM_PE, 32,
				       AwlOffset(-1, 0)), 2),
		"PAB"	: OpDescriptor(AwlOperator(AwlOperator.MEM_PA, 8,
				       AwlOffset(-1, 0)), 2),
		"PAW"	: OpDescriptor(AwlOperator(AwlOperator.MEM_PA, 16,
				       AwlOffset(-1, 0)), 2),
		"PAD"	: OpDescriptor(AwlOperator(AwlOperator.MEM_PA, 32,
				       AwlOffset(-1, 0)), 2),
		"STW"	: OpDescriptor(AwlOperator(AwlOperator.MEM_STW, 16,
				       AwlOffset(0, 0)), 1),
		"AR2"	: OpDescriptor(AwlOperator(AwlOperator.MEM_AR2, 32,
				       AwlOffset(2, 0)), 1),
		"__STW"	 : OpDescriptor(AwlOperator(AwlOperator.MEM_STW, 1,
					AwlOffset(0, -1)), 2),
		"__ACCU" : OpDescriptor(AwlOperator(AwlOperator.VIRT_ACCU, 32,
					AwlOffset(-1, 0)), 2),
		"__AR"	 : OpDescriptor(AwlOperator(AwlOperator.VIRT_AR, 32,
					AwlOffset(-1, 0)), 2),
		"__DBR"	 : OpDescriptor(AwlOperator(AwlOperator.VIRT_DBR, 16,
					AwlOffset(-1, 0)), 2),
		"__CNST_PI" : OpDescriptor(AwlOperator(AwlOperator.IMM_REAL, 32,
					   pyFloatToDWord(math.pi)), 1),
		"__CNST_E" : OpDescriptor(AwlOperator(AwlOperator.IMM_REAL, 32,
					  pyFloatToDWord(math.e)), 1),
		"__CNST_PINF" : OpDescriptor(AwlOperator(AwlOperator.IMM_REAL, 32,
					     posInfDWord), 1),
		"__CNST_NINF" : OpDescriptor(AwlOperator(AwlOperator.IMM_REAL, 32,
					     negInfDWord), 1),
		"__CNST_PNAN" : OpDescriptor(AwlOperator(AwlOperator.IMM_REAL, 32,
					     pNaNDWord), 1),
		"__CNST_NNAN" : OpDescriptor(AwlOperator(AwlOperator.IMM_REAL, 32,
					     nNaNDWord), 1),
	}

	__english2german = {
		"I"	: "E",
		"IB"	: "EB",
		"IW"	: "EW",
		"ID"	: "ED",
		"Q"	: "A",
		"QB"	: "AB",
		"QW"	: "AW",
		"QD"	: "AD",
		"C"	: "Z",
		"BR"	: "BIE",
		"PIB"	: "PEB",
		"PIW"	: "PEW",
		"PID"	: "PED",
		"PQB"	: "PAB",
		"PQW"	: "PAW",
		"PQD"	: "PAD",
	}
	__german2english = pivotDict(__english2german)

	# Create a constOperTab for english mnemonics
	__constOperTab_english = {}
	for name, type in __constOperTab_german.items():
		try:
			name = __german2english[name]
		except KeyError:
			pass
		__constOperTab_english[name] = type

	def __init__(self, insn, mnemonics=None):
		self.insn = insn
		if mnemonics is None and insn is not None:
			mnemonics = insn.getCpu().getSpecs().getMnemonics()
		assert(mnemonics is not None)
		self.mnemonics = mnemonics

	def __translateIndirectAddressing(self, opDesc, rawOps):
		# rawOps starts _after_ the opening bracket '['
		try:
			if rawOps[0].upper() in ("AR1", "AR2"):
				# Register-indirect access:  "L W [AR1, P#0.0]"
				ar = {
					"AR1"	: AwlIndirectOp.AR_1,
					"AR2"	: AwlIndirectOp.AR_2,
				}[rawOps[0].upper()]
				if rawOps[1] != ',':
					raise AwlSimError("Missing comma in register-indirect "
						"addressing operator")
				offsetPtr, fields = AwlDataType.tryParseImmediate_Pointer(rawOps[2:])
				if fields != 1:
					raise AwlSimError("Invalid offset pointer in "
						"register indirect addressing operator")
				if rawOps[3] != ']':
					raise AwlSimError("Missing closing brackets in "
						"register indirect addressing operator")
				offsetOp = AwlOperator(type = AwlOperator.IMM_PTR,
						       width = 32,
						       value = offsetPtr,
						       insn = opDesc.operator.insn)
				try:
					area = AwlIndirectOp.optype2area[opDesc.operator.type]
				except KeyError:
					raise AwlSimError("Invalid memory area type in "
						"register indirect addressing operator")
				indirectOp = AwlIndirectOp(area = area,
							   width = opDesc.operator.width,
							   addressRegister = ar,
							   offsetOper = offsetOp,
							   insn = opDesc.operator.insn)
				fieldCount = 4	# ARx + comma + P# + ]
			else:
				# Indirect access:  "L MW [MD 42]"
				# Translate the offset operator
				offsetOpDesc = self.translateOp(None, rawOps)
				if rawOps[offsetOpDesc.fieldCount] != ']':
					raise AwlSimError("Missing closing brackets in "
						"indirect addressing operator")
				offsetOp = offsetOpDesc.operator
				if offsetOp.type == AwlOperator.INDIRECT:
					raise AwlSimError("Only direct operators supported "
						"inside of indirect operator brackets.")
				try:
					area = AwlIndirectOp.optype2area[opDesc.operator.type]
				except KeyError:
					raise AwlSimError("Invalid memory area type in "
						"indirect addressing operator")
				if area == AwlIndirectOp.AREA_NONE:
					raise AwlSimError("No memory area code specified in "
						"indirect addressing operator")
				if area in (AwlIndirectOp.EXT_AREA_T,
					    AwlIndirectOp.EXT_AREA_Z,
					    AwlIndirectOp.EXT_AREA_BLKREF_DB,
					    AwlIndirectOp.EXT_AREA_BLKREF_FC,
					    AwlIndirectOp.EXT_AREA_BLKREF_FB):
					expectedOffsetOpWidth = 16
				else:
					expectedOffsetOpWidth = 32
				if offsetOp.type != AwlOperator.NAMED_LOCAL and\
				   offsetOp.width != expectedOffsetOpWidth:
					#TODO: We should also check for NAMED_LOCAL
					raise AwlSimError("Offset operator in "
						"indirect addressing operator has invalid width. "
						"Got %d bit, but expected %d bit." %\
						(offsetOp.width, expectedOffsetOpWidth))
				indirectOp = AwlIndirectOp(area = area,
							   width = opDesc.operator.width,
							   addressRegister = AwlIndirectOp.AR_NONE,
							   offsetOper = offsetOp,
							   insn = opDesc.operator.insn)
				fieldCount = offsetOpDesc.fieldCount + 1  # offsetOperator + ]
		except IndexError:
			raise AwlSimError("Invalid indirect addressing operator")
		# Adjust the operator descriptor
		opDesc.operator = indirectOp
		opDesc.fieldCount += fieldCount

	def __translateAddressOperator(self, opDesc, rawOps):
		if len(rawOps) < 1:
			raise AwlSimError("Missing address operator")
		if rawOps[0] == '[':
			# Indirect addressing
			self.__translateIndirectAddressing(opDesc, rawOps[1:])
			return
		if opDesc.operator.type == AwlOperator.UNSPEC:
			raise AwlSimError("No memory area specified in operator")
		# Direct addressing
		if opDesc.operator.width == 1:
			if opDesc.operator.value.byteOffset == 0 and\
			   opDesc.operator.value.bitOffset == -1:
				try:
					opDesc.operator.value.bitOffset = int(rawOps[0], 10)
				except ValueError as e:
					if opDesc.operator.type == AwlOperator.MEM_STW:
						opDesc.operator.value.bitOffset = S7StatusWord.getBitnrByName(rawOps[0])
					else:
						raise AwlSimError("Invalid bit address")
			else:
				assert(opDesc.operator.value.byteOffset == -1 and\
				       opDesc.operator.value.bitOffset == -1)
				offset = rawOps[0].split('.')
				if len(offset) != 2:
					raise AwlSimError("Invalid bit address")
				try:
					opDesc.operator.value.byteOffset = int(offset[0], 10)
					opDesc.operator.value.bitOffset = int(offset[1], 10)
				except ValueError as e:
					raise AwlSimError("Invalid bit address")
		elif opDesc.operator.width == 8:
			assert(opDesc.operator.value.byteOffset == -1 and\
			       opDesc.operator.value.bitOffset == 0)
			try:
				opDesc.operator.value.byteOffset = int(rawOps[0], 10)
			except ValueError as e:
				raise AwlSimError("Invalid byte address")
		elif opDesc.operator.width == 16:
			assert(opDesc.operator.value.byteOffset == -1 and\
			       opDesc.operator.value.bitOffset == 0)
			try:
				opDesc.operator.value.byteOffset = int(rawOps[0], 10)
			except ValueError as e:
				raise AwlSimError("Invalid word address")
		elif opDesc.operator.width == 32:
			assert(opDesc.operator.value.byteOffset == -1 and
			       opDesc.operator.value.bitOffset == 0)
			try:
				opDesc.operator.value.byteOffset = int(rawOps[0], 10)
			except ValueError as e:
				raise AwlSimError("Invalid doubleword address")
		else:
			assert(0)

	def __doTrans(self, rawInsn, rawOps):
		if rawInsn and rawInsn.block.hasLabel(rawOps[0]):
			# Label reference
			return OpDescriptor(AwlOperator(AwlOperator.LBL_REF, 0,
					    rawOps[0]), 1)
		try:
			# Constant operator (from table)
			if self.mnemonics == S7CPUSpecs.MNEMONICS_DE:
				return self.__constOperTab_german[rawOps[0]].dup()
			elif self.mnemonics == S7CPUSpecs.MNEMONICS_EN:
				return self.__constOperTab_english[rawOps[0]].dup()
			else:
				assert(0)
		except KeyError as e:
			pass
		token0 = rawOps[0].upper()
		# Bitwise indirect addressing
		if token0 == '[':
			# This is special case for the "U [AR1,P#0.0]" bitwise addressing.
			# Create a descriptor for the (yet) unspecified bitwise access.
			opDesc = OpDescriptor(AwlOperator(AwlOperator.UNSPEC, 1,
							  AwlOffset(-1, -1)), 1)
			# And hand over to indirect address parsing.
			self.__translateIndirectAddressing(opDesc, rawOps[1:])
			assert(opDesc.operator.type != AwlOperator.UNSPEC)
			return opDesc
		# Local variable
		if token0.startswith('#'):
			return OpDescriptor(AwlOperator(AwlOperator.NAMED_LOCAL, 0,
							rawOps[0][1:]), 1)
		# Pointer to local variable
		if token0.startswith("P##"):
			return OpDescriptor(AwlOperator(AwlOperator.NAMED_LOCAL_PTR, 0,
							rawOps[0][3:]), 1)
		# Symbolic name
		if token0.startswith('"') and token0.endswith('"'):
			return OpDescriptor(AwlOperator(AwlOperator.SYMBOLIC, 0,
							rawOps[0][1:-1]), 1)
		# Immediate integer
		immediate = AwlDataType.tryParseImmediate_INT(rawOps[0])
		if immediate is not None:
			immediate &= 0xFFFF
			return OpDescriptor(AwlOperator(AwlOperator.IMM, 16,
					    immediate), 1)
		# Immediate float
		immediate = AwlDataType.tryParseImmediate_REAL(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator(AwlOperator.IMM_REAL, 32,
					    immediate), 1)
		# S5Time immediate
		immediate = AwlDataType.tryParseImmediate_S5T(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator(AwlOperator.IMM_S5T, 16,
					    immediate), 1)
		# Time immediate
		immediate = AwlDataType.tryParseImmediate_TIME(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator(AwlOperator.IMM_TIME, 32,
					    immediate), 1)
		# TIME_OF_DAY immediate
		immediate = AwlDataType.tryParseImmediate_TOD(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator(AwlOperator.IMM_TOD, 32,
					    immediate), 1)
		# Date immediate
		immediate = AwlDataType.tryParseImmediate_Date(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator(AwlOperator.IMM_DATE, 16,
					    immediate), 1)
		# DATE_AND_TIME immediate
		immediate = AwlDataType.tryParseImmediate_DT(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator(AwlOperator.IMM_DT, 64,
					    immediate), 1)
		# Pointer immediate
		immediate, fields = AwlDataType.tryParseImmediate_Pointer(rawOps)
		if immediate is not None:
			return OpDescriptor(AwlOperator(AwlOperator.IMM_PTR, 32,
					    immediate), fields)
		# Binary immediate
		immediate = AwlDataType.tryParseImmediate_Bin(rawOps[0])
		if immediate is not None:
			size = 32 if (immediate > 0xFFFF) else 16
			return OpDescriptor(AwlOperator(AwlOperator.IMM, size,
					    immediate), 1)
		# Byte array immediate
		immediate, fields = AwlDataType.tryParseImmediate_ByteArray(rawOps)
		if immediate is not None:
			size = 32 if fields == 9 else 16
			return OpDescriptor(AwlOperator(AwlOperator.IMM, size,
					    immediate), fields)
		# Hex byte immediate
		immediate = AwlDataType.tryParseImmediate_HexByte(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator(AwlOperator.IMM, 8,
					    immediate), 1)
		# Hex word immediate
		immediate = AwlDataType.tryParseImmediate_HexWord(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator(AwlOperator.IMM, 16,
					    immediate), 1)
		# Hex dword immediate
		immediate = AwlDataType.tryParseImmediate_HexDWord(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator(AwlOperator.IMM, 32,
					    immediate), 1)
		# Long integer immediate
		immediate = AwlDataType.tryParseImmediate_DINT(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator(AwlOperator.IMM, 32,
					    immediate), 1)
		# BCD word immediate
		immediate = AwlDataType.tryParseImmediate_BCD_word(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator(AwlOperator.IMM, 16,
					    immediate), 1)
		# String immediate
		immediate = AwlDataType.tryParseImmediate_STRING(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator(AwlOperator.IMM, 32,
					    immediate), 1)
		# DBx.DB[XBWD] addressing
		match = re.match(r'^DB(\d+)\.DB([XBWD])$', rawOps[0])
		if match:
			dbNumber = int(match.group(1))
			width = {
				"X"	: 1,
				"B"	: 8,
				"W"	: 16,
				"D"	: 32,
			}[match.group(2)]
			offset = AwlOffset(-1, -1 if (width == 1) else 0,
					   dbNumber = dbNumber)
			return OpDescriptor(AwlOperator(AwlOperator.MEM_DB, width,
					    offset), 2)
		raise AwlSimError("Cannot parse operand: " +\
				str(rawOps[0]))

	def translateOp(self, rawInsn, rawOps):
		opDesc = self.__doTrans(rawInsn, rawOps)

		if not isInteger(opDesc.operator.value) and\
		   opDesc.fieldCount == 2 and\
		   (opDesc.operator.value.byteOffset == -1 or\
		    opDesc.operator.value.bitOffset == -1):
			self.__translateAddressOperator(opDesc, rawOps[1:])

		assert(opDesc.operator.type != AwlOperator.UNSPEC)
		opDesc.operator.setExtended(rawOps[0].startswith("__"))
		opDesc.operator.setInsn(self.insn)

		return opDesc

	def __translateParameterList(self, rawInsn, rawOps):
		while rawOps:
			if len(rawOps) < 3:
				raise AwlSimError("Invalid parameter assignment")
			if rawOps[1] != ':=':
				raise AwlSimError("Missing assignment operator (:=) "
					"in parameter assignment")

			# Extract l-value and r-value
			commaIdx = listIndex(rawOps, ',', 2)
			lvalueName = rawOps[0]
			if commaIdx < 0:
				rvalueTokens = rawOps[2:]
			else:
				rvalueTokens = rawOps[2:commaIdx]
			if not rvalueTokens:
				raise AwlSimError("No R-Value in parameter assignment")

			# Translate r-value
			opDesc = self.translateOp(None, rvalueTokens)

			# Create assignment
			param = AwlParamAssign(lvalueName, opDesc.operator)
			if self.insn:
				self.insn.params.append(param)

			rawOps = rawOps[opDesc.fieldCount + 2 : ]
			if rawOps:
				if rawOps[0] == ',':
					rawOps = rawOps[1:]
				else:
					raise AwlSimError("Missing comma in parameter list")

	def translateFromRawInsn(self, rawInsn):
		rawOps = rawInsn.getOperators()
		while rawOps:
			opDesc = self.translateOp(rawInsn, rawOps)

			if self.insn:
				self.insn.ops.append(opDesc.operator)

			if len(rawOps) > opDesc.fieldCount:
				if rawInsn.name.upper() == "CALL" and\
				   rawOps[opDesc.fieldCount] == '(':
					try:
						endIdx = rawOps.index(')', opDesc.fieldCount)
					except ValueError:
						raise AwlSimError("Missing closing parenthesis")
					# Translate the call parameters
					self.__translateParameterList(rawInsn,
								      rawOps[opDesc.fieldCount + 1: endIdx])
					# Consume all tokens between (and including) parenthesis.
					opDesc.fieldCount = endIdx + 1
					if len(rawOps) > opDesc.fieldCount:
						raise AwlSimError("Trailing character after closing parenthesis")
				elif rawOps[opDesc.fieldCount] == ',':
					opDesc.fieldCount += 1 # Consume comma
					if len(rawOps) <= opDesc.fieldCount:
						raise AwlSimError("Trailing comma")
				else:
					raise AwlSimError("Missing comma in operator list")

			rawOps = rawOps[opDesc.fieldCount : ]

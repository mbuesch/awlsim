#
# AWL simulator - Operator translator
# Copyright 2012 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

import math

from util import *
from awloperators import *
from awldatatypes import *
from awlparser import *
from awltimers import *


class OpDescriptor(object):
	"Instruction operator descriptor"

	def __init__(self, operType, width, offset, bitOffset, fieldCount):
		self.operType = operType
		self.width = width
		self.offset = offset
		self.bitOffset = bitOffset
		self.fieldCount = fieldCount

	def dup(self):
		return OpDescriptor(self.operType, self.width, self.offset,
				    self.bitOffset, self.fieldCount)

class AwlOpTranslator(object):
	"Instruction operator translator"

	__constOperTab = {
		"==0"	: OpDescriptor(AwlOperator.MEM_STW_Z, 1, 0, 0, 1),
		"<>0"	: OpDescriptor(AwlOperator.MEM_STW_NZ, 1, 0, 0, 1),
		">0"	: OpDescriptor(AwlOperator.MEM_STW_POS, 1, 0, 0, 1),
		"<0"	: OpDescriptor(AwlOperator.MEM_STW_NEG, 1, 0, 0, 1),
		">=0"	: OpDescriptor(AwlOperator.MEM_STW_POSZ, 1, 0, 0, 1),
		"<=0"	: OpDescriptor(AwlOperator.MEM_STW_NEGZ, 1, 0, 0, 1),
		"OV"	: OpDescriptor(AwlOperator.MEM_STW, 1, 0, 5, 1),
		"OS"	: OpDescriptor(AwlOperator.MEM_STW, 1, 0, 4, 1),
		"UO"	: OpDescriptor(AwlOperator.MEM_STW_UO, 1, 0, 0, 1),
		"BIE"	: OpDescriptor(AwlOperator.MEM_STW, 1, 0, 8, 1),
		"E"	: OpDescriptor(AwlOperator.MEM_E, 1, -1, -1, 2),
		"EB"	: OpDescriptor(AwlOperator.MEM_E, 8, -1, 0, 2),
		"EW"	: OpDescriptor(AwlOperator.MEM_E, 16, -1, 0, 2),
		"ED"	: OpDescriptor(AwlOperator.MEM_E, 32, -1, 0, 2),
		"A"	: OpDescriptor(AwlOperator.MEM_A, 1, -1, -1, 2),
		"AB"	: OpDescriptor(AwlOperator.MEM_A, 8, -1, 0, 2),
		"AW"	: OpDescriptor(AwlOperator.MEM_A, 16, -1, 0, 2),
		"AD"	: OpDescriptor(AwlOperator.MEM_A, 32, -1, 0, 2),
		"L"	: OpDescriptor(AwlOperator.MEM_L, 1, -1, -1, 2),
		"LB"	: OpDescriptor(AwlOperator.MEM_L, 8, -1, 0, 2),
		"LW"	: OpDescriptor(AwlOperator.MEM_L, 16, -1, 0, 2),
		"LD"	: OpDescriptor(AwlOperator.MEM_L, 32, -1, 0, 2),
		"M"	: OpDescriptor(AwlOperator.MEM_M, 1, -1, -1, 2),
		"MB"	: OpDescriptor(AwlOperator.MEM_M, 8, -1, 0, 2),
		"MW"	: OpDescriptor(AwlOperator.MEM_M, 16, -1, 0, 2),
		"MD"	: OpDescriptor(AwlOperator.MEM_M, 32, -1, 0, 2),
		"T"	: OpDescriptor(AwlOperator.MEM_T, 16, -1, 0, 2),
		"Z"	: OpDescriptor(AwlOperator.MEM_Z, 16, -1, 0, 2),
		"FC"	: OpDescriptor(AwlOperator.BLKREF_FC, 16, -1, 0, 2),
		"SFC"	: OpDescriptor(AwlOperator.BLKREF_SFC, 16, -1, 0, 2),
		"FB"	: OpDescriptor(AwlOperator.BLKREF_FB, 16, -1, 0, 2),
		"SFB"	: OpDescriptor(AwlOperator.BLKREF_SFB, 16, -1, 0, 2),
		"DB"	: OpDescriptor(AwlOperator.BLKREF_DB, 16, -1, 0, 2),
		"DI"	: OpDescriptor(AwlOperator.BLKREF_DI, 16, -1, 0, 2),
		"DBX"	: OpDescriptor(AwlOperator.MEM_DB, 1, -1, -1, 2),
		"DBB"	: OpDescriptor(AwlOperator.MEM_DB, 8, -1, 0, 2),
		"DBW"	: OpDescriptor(AwlOperator.MEM_DB, 16, -1, 0, 2),
		"DBD"	: OpDescriptor(AwlOperator.MEM_DB, 32, -1, 0, 2),
		"DIX"	: OpDescriptor(AwlOperator.MEM_DI, 1, -1, -1, 2),
		"DIB"	: OpDescriptor(AwlOperator.MEM_DI, 8, -1, 0, 2),
		"DIW"	: OpDescriptor(AwlOperator.MEM_DI, 16, -1, 0, 2),
		"DID"	: OpDescriptor(AwlOperator.MEM_DI, 32, -1, 0, 2),
		"PEB"	: OpDescriptor(AwlOperator.MEM_PE, 8, -1, 0, 2),
		"PEW"	: OpDescriptor(AwlOperator.MEM_PE, 16, -1, 0, 2),
		"PED"	: OpDescriptor(AwlOperator.MEM_PE, 32, -1, 0, 2),
		"PAB"	: OpDescriptor(AwlOperator.MEM_PA, 8, -1, 0, 2),
		"PAW"	: OpDescriptor(AwlOperator.MEM_PA, 16, -1, 0, 2),
		"PAD"	: OpDescriptor(AwlOperator.MEM_PA, 32, -1, 0, 2),
		"STW"	 : OpDescriptor(AwlOperator.MEM_STW, 16, 0, 0, 1),
		"__STW"	 : OpDescriptor(AwlOperator.MEM_STW, 1, 0, -1, 2),
		"__ACCU" : OpDescriptor(AwlOperator.VIRT_ACCU, 32, -1, 0, 2),
		"__AR"	 : OpDescriptor(AwlOperator.VIRT_AR, 32, -1, 0, 2),
		"__CNST_PI" : OpDescriptor(AwlOperator.IMM_REAL, 32,
					   pyFloatToDWord(math.pi), 0, 1),
		"__CNST_E" : OpDescriptor(AwlOperator.IMM_REAL, 32,
					  pyFloatToDWord(math.e), 0, 1),
		"__CNST_PINF" : OpDescriptor(AwlOperator.IMM_REAL, 32,
					     posInfDWord, 0, 1),
		"__CNST_NINF" : OpDescriptor(AwlOperator.IMM_REAL, 32,
					     negInfDWord, 0, 1),
		"__CNST_NAN" : OpDescriptor(AwlOperator.IMM_REAL, 32,
					    nanDWord, 0, 1),
	}

	def __init__(self, insn):
		self.insn = insn

	def __translateAddressOperator(self, opDesc, rawOps):
		if len(rawOps) < 1:
			raise AwlSimError("Missing address operator")
		if opDesc.width == 1:
			if opDesc.offset == 0 and opDesc.bitOffset == -1:
				try:
					opDesc.bitOffset = int(rawOps[0], 10)
				except ValueError as e:
					if opDesc.operType == AwlOperator.MEM_STW:
						opDesc.bitOffset = S7StatusWord.getBitnrByName(rawOps[0])
					else:
						raise AwlSimError("Invalid bit address")
			else:
				assert(opDesc.offset == -1 and opDesc.bitOffset == -1)
				offset = rawOps[0].split('.')
				if len(offset) != 2:
					raise AwlSimError("Invalid bit address")
				try:
					opDesc.offset = int(offset[0], 10)
					opDesc.bitOffset = int(offset[1], 10)
				except ValueError as e:
					raise AwlSimError("Invalid bit address")
		elif opDesc.width == 8:
			assert(opDesc.offset == -1 and opDesc.bitOffset == 0)
			try:
				opDesc.offset = int(rawOps[0], 10)
			except ValueError as e:
				raise AwlSimError("Invalid byte address")
		elif opDesc.width == 16:
			assert(opDesc.offset == -1 and opDesc.bitOffset == 0)
			try:
				opDesc.offset = int(rawOps[0], 10)
			except ValueError as e:
				raise AwlSimError("Invalid word address")
		elif opDesc.width == 32:
			assert(opDesc.offset == -1 and opDesc.bitOffset == 0)
			try:
				opDesc.offset = int(rawOps[0], 10)
			except ValueError as e:
				raise AwlSimError("Invalid doubleword address")
		else:
			assert(0)

	def __doTrans(self, rawInsn, rawOps):
		if rawInsn.block.hasLabel(rawOps[0]):
			# Label reference
			return OpDescriptor(AwlOperator.LBL_REF, 0, rawOps[0], 0, 1)
		try:
			# Constant operator (from table)
			return self.__constOperTab[rawOps[0]].dup()
		except KeyError as e:
			pass
		# Immediate integer
		immediate = AwlDataType.tryParseImmediate_INT(rawOps[0])
		if immediate is not None:
			immediate &= 0xFFFF
			return OpDescriptor(AwlOperator.IMM, 16,
					    immediate, 0, 1)
		# Immediate float
		immediate = AwlDataType.tryParseImmediate_REAL(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator.IMM_REAL, 32,
					    immediate, 0, 1)
		# S5Time immediate
		immediate = AwlDataType.tryParseImmediate_S5T(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator.IMM_S5T, 0,
					    immediate, 0, 1)
		# Binary immediate
		immediate = AwlDataType.tryParseImmediate_Bin(rawOps[0])
		if immediate is not None:
			size = 32 if (immediate > 0xFFFF) else 16
			return OpDescriptor(AwlOperator.IMM, size,
					    immediate, 0, 1)
		# Byte array immediate
		immediate, fields = AwlDataType.tryParseImmediate_ByteArray(rawOps)
		if immediate is not None:
			return OpDescriptor(AwlOperator.IMM, size, immediate,
					    0, fields)
		# Hex byte immediate
		immediate = AwlDataType.tryParseImmediate_HexByte(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator.IMM, 8,
					    immediate, 0, 1)
		# Hex word immediate
		immediate = AwlDataType.tryParseImmediate_HexWord(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator.IMM, 16,
					    immediate, 0, 1)
		# Hex dword immediate
		immediate = AwlDataType.tryParseImmediate_HexDWord(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator.IMM, 32,
					    immediate, 0, 1)
		# Long integer immediate
		immediate = AwlDataType.tryParseImmediate_DINT(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator.IMM, 32,
					    immediate, 0, 1)
		# BCD word immediate
		immediate = AwlDataType.tryParseImmediate_BCD_word(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator.IMM, 16,
					    immediate, 0, 1)
		#TODO T#
		#TODO TOD#
		#TODO date D#
		#TODO pointer P#x.y
		raise AwlSimError("Cannot parse operand: " +\
				str(rawOps[0]))

	def translateFrom(self, rawInsn):
		rawOps = rawInsn.getOperators()
		while rawOps:
			opDesc = self.__doTrans(rawInsn, rawOps)

			if opDesc.fieldCount == 2 and\
			   (opDesc.offset == -1 or opDesc.bitOffset == -1):
				self.__translateAddressOperator(opDesc, rawOps[1:])

			if len(rawOps) > opDesc.fieldCount:
				if rawOps[opDesc.fieldCount] != ',':
					raise AwlSimError("Missing comma in operator list")
				opDesc.fieldCount += 1 # Consume comma
				if len(rawOps) <= opDesc.fieldCount:
					raise AwlSimError("Trailing comma")

			operator = AwlOperator(opDesc.operType, opDesc.width,
					       opDesc.offset, opDesc.bitOffset)
			operator.setInsn(self.insn)
			operator.setExtended(rawOps[0].startswith("__"))

			self.insn.ops.append(operator)
			rawOps = rawOps[opDesc.fieldCount : ]

#
# AWL simulator - Operator translator
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

import math

from awlsim.util import *
from awlsim.operators import *
from awlsim.parameters import *
from awlsim.datatypes import *
from awlsim.parser import *
from awlsim.timers import *
from awlsim.cpuspecs import *


class OpDescriptor(object):
	"Instruction operator descriptor"

	def __init__(self, operType, width, offset, fieldCount):
		self.operType = operType
		self.width = width
		self.offset = offset
		self.fieldCount = fieldCount

	def dup(self):
		return OpDescriptor(self.operType, self.width,
				    AwlOffset(self.offset.byteOffset,
				    	      self.offset.bitOffset),
				    self.fieldCount)

class AwlOpTranslator(object):
	"Instruction operator translator"

	__constOperTab_german = {
		"==0"	: OpDescriptor(AwlOperator.MEM_STW_Z, 1,
				       AwlOffset(0, 0), 1),
		"<>0"	: OpDescriptor(AwlOperator.MEM_STW_NZ, 1,
				       AwlOffset(0, 0), 1),
		">0"	: OpDescriptor(AwlOperator.MEM_STW_POS, 1,
				       AwlOffset(0, 0), 1),
		"<0"	: OpDescriptor(AwlOperator.MEM_STW_NEG, 1,
				       AwlOffset(0, 0), 1),
		">=0"	: OpDescriptor(AwlOperator.MEM_STW_POSZ, 1,
				       AwlOffset(0, 0), 1),
		"<=0"	: OpDescriptor(AwlOperator.MEM_STW_NEGZ, 1,
				       AwlOffset(0, 0), 1),
		"OV"	: OpDescriptor(AwlOperator.MEM_STW, 1,
				       AwlOffset(0, 5), 1),
		"OS"	: OpDescriptor(AwlOperator.MEM_STW, 1,
				       AwlOffset(0, 4), 1),
		"UO"	: OpDescriptor(AwlOperator.MEM_STW_UO, 1,
				       AwlOffset(0, 0), 1),
		"BIE"	: OpDescriptor(AwlOperator.MEM_STW, 1,
				       AwlOffset(0, 8), 1),
		"E"	: OpDescriptor(AwlOperator.MEM_E, 1,
				       AwlOffset(-1, -1), 2),
		"EB"	: OpDescriptor(AwlOperator.MEM_E, 8,
				       AwlOffset(-1, 0), 2),
		"EW"	: OpDescriptor(AwlOperator.MEM_E, 16,
				       AwlOffset(-1, 0), 2),
		"ED"	: OpDescriptor(AwlOperator.MEM_E, 32,
				       AwlOffset(-1, 0), 2),
		"A"	: OpDescriptor(AwlOperator.MEM_A, 1,
				       AwlOffset(-1, -1), 2),
		"AB"	: OpDescriptor(AwlOperator.MEM_A, 8,
				       AwlOffset(-1, 0), 2),
		"AW"	: OpDescriptor(AwlOperator.MEM_A, 16,
				       AwlOffset(-1, 0), 2),
		"AD"	: OpDescriptor(AwlOperator.MEM_A, 32,
				       AwlOffset(-1, 0), 2),
		"L"	: OpDescriptor(AwlOperator.MEM_L, 1,
				       AwlOffset(-1, -1), 2),
		"LB"	: OpDescriptor(AwlOperator.MEM_L, 8,
				       AwlOffset(-1, 0), 2),
		"LW"	: OpDescriptor(AwlOperator.MEM_L, 16,
				       AwlOffset(-1, 0), 2),
		"LD"	: OpDescriptor(AwlOperator.MEM_L, 32,
				       AwlOffset(-1, 0), 2),
		"M"	: OpDescriptor(AwlOperator.MEM_M, 1,
				       AwlOffset(-1, -1), 2),
		"MB"	: OpDescriptor(AwlOperator.MEM_M, 8,
				       AwlOffset(-1, 0), 2),
		"MW"	: OpDescriptor(AwlOperator.MEM_M, 16,
				       AwlOffset(-1, 0), 2),
		"MD"	: OpDescriptor(AwlOperator.MEM_M, 32,
				       AwlOffset(-1, 0), 2),
		"T"	: OpDescriptor(AwlOperator.MEM_T, 16,
				       AwlOffset(-1, 0), 2),
		"Z"	: OpDescriptor(AwlOperator.MEM_Z, 16,
				       AwlOffset(-1, 0), 2),
		"FC"	: OpDescriptor(AwlOperator.BLKREF_FC, 16,
				       AwlOffset(-1, 0), 2),
		"SFC"	: OpDescriptor(AwlOperator.BLKREF_SFC, 16,
				       AwlOffset(-1, 0), 2),
		"FB"	: OpDescriptor(AwlOperator.BLKREF_FB, 16,
				       AwlOffset(-1, 0), 2),
		"SFB"	: OpDescriptor(AwlOperator.BLKREF_SFB, 16,
				       AwlOffset(-1, 0), 2),
		"DB"	: OpDescriptor(AwlOperator.BLKREF_DB, 16,
				       AwlOffset(-1, 0), 2),
		"DI"	: OpDescriptor(AwlOperator.BLKREF_DI, 16,
				       AwlOffset(-1, 0), 2),
		"DBX"	: OpDescriptor(AwlOperator.MEM_DB, 1,
				       AwlOffset(-1, -1), 2),
		"DBB"	: OpDescriptor(AwlOperator.MEM_DB, 8,
				       AwlOffset(-1, 0), 2),
		"DBW"	: OpDescriptor(AwlOperator.MEM_DB, 16,
				       AwlOffset(-1, 0), 2),
		"DBD"	: OpDescriptor(AwlOperator.MEM_DB, 32,
				       AwlOffset(-1, 0), 2),
		"DIX"	: OpDescriptor(AwlOperator.MEM_DI, 1,
				       AwlOffset(-1, -1), 2),
		"DIB"	: OpDescriptor(AwlOperator.MEM_DI, 8,
				       AwlOffset(-1, 0), 2),
		"DIW"	: OpDescriptor(AwlOperator.MEM_DI, 16,
				       AwlOffset(-1, 0), 2),
		"DID"	: OpDescriptor(AwlOperator.MEM_DI, 32,
				       AwlOffset(-1, 0), 2),
		"PEB"	: OpDescriptor(AwlOperator.MEM_PE, 8,
				       AwlOffset(-1, 0), 2),
		"PEW"	: OpDescriptor(AwlOperator.MEM_PE, 16,
				       AwlOffset(-1, 0), 2),
		"PED"	: OpDescriptor(AwlOperator.MEM_PE, 32,
				       AwlOffset(-1, 0), 2),
		"PAB"	: OpDescriptor(AwlOperator.MEM_PA, 8,
				       AwlOffset(-1, 0), 2),
		"PAW"	: OpDescriptor(AwlOperator.MEM_PA, 16,
				       AwlOffset(-1, 0), 2),
		"PAD"	: OpDescriptor(AwlOperator.MEM_PA, 32,
				       AwlOffset(-1, 0), 2),
		"STW"	 : OpDescriptor(AwlOperator.MEM_STW, 16,
					AwlOffset(0, 0), 1),
		"__STW"	 : OpDescriptor(AwlOperator.MEM_STW, 1,
					AwlOffset(0, -1), 2),
		"__ACCU" : OpDescriptor(AwlOperator.VIRT_ACCU, 32,
					AwlOffset(-1, 0), 2),
		"__AR"	 : OpDescriptor(AwlOperator.VIRT_AR, 32,
					AwlOffset(-1, 0), 2),
		"__CNST_PI" : OpDescriptor(AwlOperator.IMM_REAL, 32,
					   AwlOffset(pyFloatToDWord(math.pi), 0),
					   1),
		"__CNST_E" : OpDescriptor(AwlOperator.IMM_REAL, 32,
					  AwlOffset(pyFloatToDWord(math.e), 0),
					  1),
		"__CNST_PINF" : OpDescriptor(AwlOperator.IMM_REAL, 32,
					     AwlOffset(posInfDWord, 0), 1),
		"__CNST_NINF" : OpDescriptor(AwlOperator.IMM_REAL, 32,
					     AwlOffset(negInfDWord, 0), 1),
		"__CNST_PNAN" : OpDescriptor(AwlOperator.IMM_REAL, 32,
					     AwlOffset(pNaNDWord, 0), 1),
		"__CNST_NNAN" : OpDescriptor(AwlOperator.IMM_REAL, 32,
					     AwlOffset(nNaNDWord, 0), 1),
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

	def __translateAddressOperator(self, opDesc, rawOps):
		if len(rawOps) < 1:
			raise AwlSimError("Missing address operator")
		if opDesc.width == 1:
			if opDesc.offset.byteOffset == 0 and opDesc.offset.bitOffset == -1:
				try:
					opDesc.offset.bitOffset = int(rawOps[0], 10)
				except ValueError as e:
					if opDesc.operType == AwlOperator.MEM_STW:
						opDesc.offset.bitOffset = S7StatusWord.getBitnrByName(rawOps[0])
					else:
						raise AwlSimError("Invalid bit address")
			else:
				assert(opDesc.offset.byteOffset == -1 and opDesc.offset.bitOffset == -1)
				offset = rawOps[0].split('.')
				if len(offset) != 2:
					raise AwlSimError("Invalid bit address")
				try:
					opDesc.offset.byteOffset = int(offset[0], 10)
					opDesc.offset.bitOffset = int(offset[1], 10)
				except ValueError as e:
					raise AwlSimError("Invalid bit address")
		elif opDesc.width == 8:
			assert(opDesc.offset.byteOffset == -1 and opDesc.offset.bitOffset == 0)
			try:
				opDesc.offset.byteOffset = int(rawOps[0], 10)
			except ValueError as e:
				raise AwlSimError("Invalid byte address")
		elif opDesc.width == 16:
			assert(opDesc.offset.byteOffset == -1 and opDesc.offset.bitOffset == 0)
			try:
				opDesc.offset.byteOffset = int(rawOps[0], 10)
			except ValueError as e:
				raise AwlSimError("Invalid word address")
		elif opDesc.width == 32:
			assert(opDesc.offset.byteOffset == -1 and opDesc.offset.bitOffset == 0)
			try:
				opDesc.offset.byteOffset = int(rawOps[0], 10)
			except ValueError as e:
				raise AwlSimError("Invalid doubleword address")
		else:
			assert(0)

	def __doTrans(self, rawInsn, rawOps):
		if rawInsn and rawInsn.block.hasLabel(rawOps[0]):
			# Label reference
			return OpDescriptor(AwlOperator.LBL_REF, 0,
					    AwlOffset(rawOps[0], 0), 1)
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
		# Local variable
		if rawOps[0].startswith('#'):
			return OpDescriptor(AwlOperator.NAMED_LOCAL, 0,
					    AwlOffset(rawOps[0][1:], 0), 1)
		# Symbolic name
		if rawOps[0].startswith('"') and rawOps[0].endswith('"'):
			pass#TODO
		# Immediate integer
		immediate = AwlDataType.tryParseImmediate_INT(rawOps[0])
		if immediate is not None:
			immediate &= 0xFFFF
			return OpDescriptor(AwlOperator.IMM, 16,
					    AwlOffset(immediate, 0), 1)
		# Immediate float
		immediate = AwlDataType.tryParseImmediate_REAL(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator.IMM_REAL, 32,
					    AwlOffset(immediate, 0), 1)
		# S5Time immediate
		immediate = AwlDataType.tryParseImmediate_S5T(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator.IMM_S5T, 0,
					    AwlOffset(immediate, 0), 1)
		# Time immediate
		immediate = AwlDataType.tryParseImmediate_TIME(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator.IMM_TIME, 0,
					    AwlOffset(immediate, 0), 1)
		# TOD immediate
		immediate = AwlDataType.tryParseImmediate_TOD(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator.IMM_TOD, 0,
					    AwlOffset(immediate, 0), 1)
		# Date immediate
		immediate = AwlDataType.tryParseImmediate_Date(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator.IMM_DATE, 0,
					    AwlOffset(immediate, 0), 1)
		# Pointer immediate
		#TODO
		# Binary immediate
		immediate = AwlDataType.tryParseImmediate_Bin(rawOps[0])
		if immediate is not None:
			size = 32 if (immediate > 0xFFFF) else 16
			return OpDescriptor(AwlOperator.IMM, size,
					    AwlOffset(immediate, 0), 1)
		# Byte array immediate
		immediate, fields = AwlDataType.tryParseImmediate_ByteArray(rawOps)
		if immediate is not None:
			size = 32 if fields == 9 else 16
			return OpDescriptor(AwlOperator.IMM, size,
					    AwlOffset(immediate, 0), fields)
		# Hex byte immediate
		immediate = AwlDataType.tryParseImmediate_HexByte(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator.IMM, 8,
					    AwlOffset(immediate, 0), 1)
		# Hex word immediate
		immediate = AwlDataType.tryParseImmediate_HexWord(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator.IMM, 16,
					    AwlOffset(immediate, 0), 1)
		# Hex dword immediate
		immediate = AwlDataType.tryParseImmediate_HexDWord(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator.IMM, 32,
					    AwlOffset(immediate, 0), 1)
		# Long integer immediate
		immediate = AwlDataType.tryParseImmediate_DINT(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator.IMM, 32,
					    AwlOffset(immediate, 0), 1)
		# BCD word immediate
		immediate = AwlDataType.tryParseImmediate_BCD_word(rawOps[0])
		if immediate is not None:
			return OpDescriptor(AwlOperator.IMM, 16,
					    AwlOffset(immediate, 0), 1)
		raise AwlSimError("Cannot parse operand: " +\
				str(rawOps[0]))

	def __translateOp(self, rawInsn, rawOps):
		opDesc = self.__doTrans(rawInsn, rawOps)

		if opDesc.fieldCount == 2 and\
		   (opDesc.offset.byteOffset == -1 or opDesc.offset.bitOffset == -1):
			self.__translateAddressOperator(opDesc, rawOps[1:])

		operator = AwlOperator(opDesc.operType, opDesc.width,
				       opDesc.offset.byteOffset, opDesc.offset.bitOffset)
		operator.setExtended(rawOps[0].startswith("__"))

		return opDesc, operator

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
			opDesc, rvalueOp = self.__translateOp(None, rvalueTokens)

			# Create assignment
			param = AwlParamAssign(lvalueName, rvalueOp)
			if self.insn:
				self.insn.params.append(param)

			rawOps = rawOps[opDesc.fieldCount + 2 : ]
			if rawOps:
				if rawOps[0] == ',':
					rawOps = rawOps[1:]
				else:
					raise AwlSimError("Missing comma in parameter list")

	def translateFrom(self, rawInsn):
		rawOps = rawInsn.getOperators()
		while rawOps:
			opDesc, operator = self.__translateOp(rawInsn, rawOps)
			operator.setInsn(self.insn)

			if self.insn:
				self.insn.ops.append(operator)

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

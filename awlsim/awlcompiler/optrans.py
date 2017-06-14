#
# AWL simulator - Operator translator
#
# Copyright 2012-2017 Michael Buesch <m@bues.ch>
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

from awlsim.common.sources import AwlSource

import math
import re

#from awlsim.core.statusword cimport * #@cy

from awlsim.common.cpuspecs import * #+cimport
from awlsim.common.cpuconfig import *
from awlsim.common.datatypehelpers import * #+cimport

from awlsim.core.operators import * #+cimport
from awlsim.core.util import *
from awlsim.core.parameters import * #+cimport
from awlsim.core.memory import * #+cimport
from awlsim.core.offset import * #+cimport
from awlsim.core.operatortypes import * #+cimport
from awlsim.core.identifier import *


class OpDescriptor(object):
	"Instruction operator descriptor"

	# operator => AwlOperator or AwlIndirectOp
	# fieldCount => Number of consumed tokens
	def __init__(self, operator, fieldCount, stripLeadingChars=0):
		self.operator = operator
		self.fieldCount = fieldCount
		self.stripLeadingChars = stripLeadingChars

	# Make a deep copy
	def dup(self):
		return OpDescriptor(operator = self.operator.dup(),
				    fieldCount = self.fieldCount,
				    stripLeadingChars = self.stripLeadingChars)

class AwlOpTranslator(object):
	"Instruction operator translator"

	CALC_OFFS	= -1
	NO_OFFS		= -2

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

	def __init__(self, insn=None, mnemonics=None):
		self.insn = insn
		if mnemonics is None and insn is not None:
			mnemonics = insn.getCpu().getConf().getMnemonics()
		assert(mnemonics is not None)
		self.mnemonics = mnemonics

		operPi = make_AwlOperator(AwlOperatorTypes.IMM_REAL, 32, None, None)
		operPi.immediate = pyFloatToDWord(math.pi)
		operE = make_AwlOperator(AwlOperatorTypes.IMM_REAL, 32, None, None)
		operE.immediate = pyFloatToDWord(math.e)
		operPInf = make_AwlOperator(AwlOperatorTypes.IMM_REAL, 32, None, None)
		operPInf.immediate = floatConst.posInfDWord
		operNInf = make_AwlOperator(AwlOperatorTypes.IMM_REAL, 32, None, None)
		operNInf.immediate = floatConst.negInfDWord
		operPNaN = make_AwlOperator(AwlOperatorTypes.IMM_REAL, 32, None, None)
		operPNaN.immediate = floatConst.pNaNDWord
		operNNaN = make_AwlOperator(AwlOperatorTypes.IMM_REAL, 32, None, None)
		operNNaN.immediate = floatConst.nNaNDWord

		# Build the constant operator table for german mnemonics
		self.__constOperTab_german = {
			"B"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.UNSPEC, 8,
					       make_AwlOffset(self.CALC_OFFS, self.CALC_OFFS), None), 2),
			"W"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.UNSPEC, 16,
					       make_AwlOffset(self.CALC_OFFS, self.CALC_OFFS), None), 2),
			"D"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.UNSPEC, 32,
					       make_AwlOffset(self.CALC_OFFS, self.CALC_OFFS), None), 2),
			"==0"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_STW_Z, 1,
					       make_AwlOffset(0, 0), None), 1),
			"<>0"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_STW_NZ, 1,
					       make_AwlOffset(0, 0), None), 1),
			">0"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_STW_POS, 1,
					       make_AwlOffset(0, 0), None), 1),
			"<0"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_STW_NEG, 1,
					       make_AwlOffset(0, 0), None), 1),
			">=0"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_STW_POSZ, 1,
					       make_AwlOffset(0, 0), None), 1),
			"<=0"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_STW_NEGZ, 1,
					       make_AwlOffset(0, 0), None), 1),
			"OV"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_STW, 1,
					       make_AwlOffset(0, 5), None), 1),
			"OS"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_STW, 1,
					       make_AwlOffset(0, 4), None), 1),
			"UO"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_STW_UO, 1,
					       make_AwlOffset(0, 0), None), 1),
			"BIE"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_STW, 1,
					       make_AwlOffset(0, 8), None), 1),
			"E"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_E, 1,
					       make_AwlOffset(self.CALC_OFFS, self.CALC_OFFS), None), 2),
			"EB"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_E, 8,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"EW"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_E, 16,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"ED"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_E, 32,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"A"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_A, 1,
					       make_AwlOffset(self.CALC_OFFS, self.CALC_OFFS), None), 2),
			"AB"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_A, 8,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"AW"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_A, 16,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"AD"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_A, 32,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"L"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_L, 1,
					       make_AwlOffset(self.CALC_OFFS, self.CALC_OFFS), None), 2),
			"LB"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_L, 8,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"LW"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_L, 16,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"LD"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_L, 32,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"M"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_M, 1,
					       make_AwlOffset(self.CALC_OFFS, self.CALC_OFFS), None), 2),
			"MB"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_M, 8,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"MW"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_M, 16,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"MD"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_M, 32,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"T"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_T, 16,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"Z"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_Z, 16,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"FC"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.BLKREF_FC, 16,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"SFC"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.BLKREF_SFC, 16,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"FB"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.BLKREF_FB, 16,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"SFB"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.BLKREF_SFB, 16,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"UDT"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.BLKREF_UDT, 16,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"DB"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.BLKREF_DB, 16,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"DI"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.BLKREF_DI, 16,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"OB"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.BLKREF_OB, 16,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"VAT"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.BLKREF_VAT, 16,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"DBX"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_DB, 1,
					       make_AwlOffset(self.CALC_OFFS, self.CALC_OFFS), None), 2),
			"DBB"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_DB, 8,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"DBW"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_DB, 16,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"DBD"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_DB, 32,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"DIX"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_DI, 1,
					       make_AwlOffset(self.CALC_OFFS, self.CALC_OFFS), None), 2),
			"DIB"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_DI, 8,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"DIW"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_DI, 16,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"DID"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_DI, 32,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"DBLG"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_DBLG, 32,
					       make_AwlOffset(0, 0), None), 1),
			"DBNO"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_DBNO, 32,
					       make_AwlOffset(0, 0), None), 1),
			"DILG"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_DILG, 32,
					       make_AwlOffset(0, 0), None), 1),
			"DINO"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_DINO, 32,
					       make_AwlOffset(0, 0), None), 1),
			"PEB"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_PE, 8,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"PEW"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_PE, 16,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"PED"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_PE, 32,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"PAB"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_PA, 8,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"PAW"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_PA, 16,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"PAD"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_PA, 32,
					       make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"STW"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_STW, 16,
					       make_AwlOffset(0, 0), None), 1),
			"AR2"	: OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_AR2, 32,
					       make_AwlOffset(2, 0), None), 1),
			"__STW"	 : OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_STW, 1,
						make_AwlOffset(0, self.CALC_OFFS), None), 2),
			"__ACCU" : OpDescriptor(make_AwlOperator(AwlOperatorTypes.VIRT_ACCU, 32,
						make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"__AR"	 : OpDescriptor(make_AwlOperator(AwlOperatorTypes.VIRT_AR, 32,
						make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"__DBR"	 : OpDescriptor(make_AwlOperator(AwlOperatorTypes.VIRT_DBR, 16,
						make_AwlOffset(self.CALC_OFFS, 0), None), 2),
			"__CNST_PI"	: OpDescriptor(operPi, 1),
			"__CNST_E"	: OpDescriptor(operE, 1),
			"__CNST_PINF"	: OpDescriptor(operPInf, 1),
			"__CNST_NINF"	: OpDescriptor(operNInf, 1),
			"__CNST_PNAN"	: OpDescriptor(operPNaN, 1),
			"__CNST_NNAN"	: OpDescriptor(operNNaN, 1),
		}

		# Create a constOperTab for english mnemonics
		self.__constOperTab_english = {}
		for name, type in dictItems(self.__constOperTab_german):
			try:
				name = self.__german2english[name]
			except KeyError:
				pass
			self.__constOperTab_english[name] = type

		# Mnemonics identifier to constOperTab lookup.
		self.__mnemonics2constOperTab = {
			S7CPUConfig.MNEMONICS_DE	: self.__constOperTab_german,
			S7CPUConfig.MNEMONICS_EN	: self.__constOperTab_english,
		}

	def __translateIndirectAddressing(self, opDesc, rawOps):
		# rawOps starts _after_ the opening bracket '['
		try:
			if rawOps[0].upper() in ("AR1", "AR2"):
				from awlsim.core.datatypes import AwlDataType

				# Register-indirect access:  "L W [AR1, P#0.0]"
				ar = {
					"AR1"	: AwlIndirectOpConst.AR_1,
					"AR2"	: AwlIndirectOpConst.AR_2,
				}[rawOps[0].upper()]
				if rawOps[1] != ',':
					raise AwlSimError("Missing comma in register-indirect "
						"addressing operator")
				offsetPtr, fields = AwlDataType.tryParseImmediate_Pointer(rawOps[2:])
				if fields != 1:
					raise AwlSimError("Invalid offset pointer in "
						"register indirect addressing operator")
				if offsetPtr.width != 32:
					raise AwlSimError("Only plain pointers allowed as "
						"indirect addressing offset pointer.")
				if offsetPtr.getArea():
					raise AwlSimError("Area internal pointer not "
						"allowed as indirect addressing offset pointer.")
				if rawOps[3] != ']':
					raise AwlSimError("Missing closing brackets in "
						"register indirect addressing operator")
				offsetOp = make_AwlOperator(operType=AwlOperatorTypes.IMM_PTR,
						       width=32,
						       offset=None,
						       insn=opDesc.operator.insn)
				offsetOp.pointer = offsetPtr
				try:
					area = AwlIndirectOpConst.optype2area[opDesc.operator.operType]
				except KeyError:
					raise AwlSimError("Invalid memory area type in "
						"register indirect addressing operator")
				indirectOp = make_AwlIndirectOp(area=area,
								width=opDesc.operator.width,
								addressRegister=ar,
								offsetOper=offsetOp,
								insn=opDesc.operator.insn)
				fieldCount = 4	# ARx + comma + P# + ]
			else:
				# Indirect access:  "L MW [MD 42]"
				# Find the end of the brackets.
				i, lvl = 0, 1
				for i, tok in enumerate(rawOps):
					if tok == ']':
						lvl -= 1
					elif tok == '[':
						lvl += 1
					if lvl == 0:
						end = i
						break
				else:
					raise AwlSimError("Missing closing brackets in "
						"indirect addressing operator")
				# Translate the offset operator
				offsetOpDesc = self.translateOp(None, rawOps[:end])
				if offsetOpDesc.fieldCount != end:
					raise AwlSimError("Invalid indirect addressing "
						"operator format. AR1/AR2 missing?")
				offsetOp = offsetOpDesc.operator
				if offsetOp.operType == AwlOperatorTypes.INDIRECT:
					raise AwlSimError("Only direct operators supported "
						"inside of indirect operator brackets.")
				try:
					area = AwlIndirectOpConst.optype2area[opDesc.operator.operType]
				except KeyError:
					raise AwlSimError("Invalid memory area type in "
						"indirect addressing operator")
				if area == PointerConst.AREA_NONE_S:
					raise AwlSimError("No memory area code specified in "
						"indirect addressing operator")
				if area in (AwlIndirectOpConst.EXT_AREA_T_S,
					    AwlIndirectOpConst.EXT_AREA_Z_S,
					    AwlIndirectOpConst.EXT_AREA_BLKREF_DB_S,
					    AwlIndirectOpConst.EXT_AREA_BLKREF_DI_S,
					    AwlIndirectOpConst.EXT_AREA_BLKREF_FC_S,
					    AwlIndirectOpConst.EXT_AREA_BLKREF_FB_S):
					expectedOffsetOpWidth = 16
				else:
					expectedOffsetOpWidth = 32
				if offsetOp.operType != AwlOperatorTypes.NAMED_LOCAL and\
				   offsetOp.width != expectedOffsetOpWidth:
					#TODO: We should also check for NAMED_LOCAL
					raise AwlSimError("Offset operator in "
						"indirect addressing operator has invalid width. "
						"Got %d bit, but expected %d bit." %\
						(offsetOp.width, expectedOffsetOpWidth))
				indirectOp = make_AwlIndirectOp(area=area,
								width=opDesc.operator.width,
								addressRegister=AwlIndirectOpConst.AR_NONE,
								offsetOper=offsetOp,
								insn=opDesc.operator.insn)
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
		if opDesc.operator.operType == AwlOperatorTypes.UNSPEC:
			raise AwlSimError("No memory area specified in operator")
		# Direct addressing
		if opDesc.operator.width == 1:
			if opDesc.operator.offset.byteOffset == 0 and\
			   opDesc.operator.offset.bitOffset == self.CALC_OFFS:
				try:
					opDesc.operator.offset.bitOffset = int(rawOps[0], 10)
				except ValueError as e:
					if opDesc.operator.operType == AwlOperatorTypes.MEM_STW:
						opDesc.operator.offset.bitOffset =\
							S7StatusWord.getBitnrByName(rawOps[0],
										    self.mnemonics)
					else:
						raise AwlSimError("Invalid bit address")
			else:
				assert(opDesc.operator.offset.byteOffset == self.CALC_OFFS and\
				       opDesc.operator.offset.bitOffset == self.CALC_OFFS)
				offset = rawOps[0].split('.')
				if len(offset) != 2:
					raise AwlSimError("Invalid bit address")
				try:
					opDesc.operator.offset.byteOffset = int(offset[0], 10)
					opDesc.operator.offset.bitOffset = int(offset[1], 10)
				except ValueError as e:
					raise AwlSimError("Invalid bit address")
		elif opDesc.operator.width == 8:
			assert(opDesc.operator.offset.byteOffset == self.CALC_OFFS and\
			       opDesc.operator.offset.bitOffset == 0)
			try:
				opDesc.operator.offset.byteOffset = int(rawOps[0], 10)
			except ValueError as e:
				raise AwlSimError("Invalid byte address")
		elif opDesc.operator.width == 16:
			assert(opDesc.operator.offset.byteOffset == self.CALC_OFFS and\
			       opDesc.operator.offset.bitOffset == 0)
			try:
				opDesc.operator.offset.byteOffset = int(rawOps[0], 10)
			except ValueError as e:
				raise AwlSimError("Invalid word address")
		elif opDesc.operator.width == 32:
			assert(opDesc.operator.offset.byteOffset == self.CALC_OFFS and
			       opDesc.operator.offset.bitOffset == 0)
			try:
				opDesc.operator.offset.byteOffset = int(rawOps[0], 10)
			except ValueError as e:
				raise AwlSimError("Invalid doubleword address")
		else:
			assert(0)
		if opDesc.operator.operType != AwlOperatorTypes.MEM_STW and\
		   opDesc.operator.offset.bitOffset > 7:
			raise AwlSimError("Invalid bit offset %d. "
				"Biggest possible bit offset is 7." %\
				opDesc.operator.offset.bitOffset)

	def __transVarIdents(self, tokens):
		tokens, count = AwlDataIdentChain.expandTokens(tokens)

		# Parse DBx.VARIABLE or "DBname".VARIABLE adressing
		offset = None
		if len(tokens) >= 3 and\
		   tokens[1] == '.':
			if tokens[0].startswith("DB") and\
			   isdecimal(tokens[0][2:]):
				# DBx.VARIABLE
				offset = make_AwlOffset(self.NO_OFFS, self.NO_OFFS)
				offset.dbNumber = int(tokens[0][2:])
			elif tokens[0].startswith('"') and\
			     tokens[0].endswith('"'):
				# "DBname".VARIABLE
				offset = make_AwlOffset(self.NO_OFFS, self.NO_OFFS)
				offset.dbName = tokens[0][1:-1]
			if offset:
				# Parse the variable idents.
				offset.identChain = AwlDataIdentChain.parseTokens(tokens[2:])
		if not offset and\
		   len(tokens) >= 1 and\
		   tokens[0].startswith('#'):
			tokens[0] = tokens[0][1:] # Strip the '#' from the first token
			offset = make_AwlOffset(self.NO_OFFS, self.NO_OFFS)
			offset.identChain = AwlDataIdentChain.parseTokens(tokens)
		if not offset:
			count = 0
		return offset, count

	def __doTrans(self, rawInsn, rawOps):
		assert(len(rawOps) >= 1)
		if rawInsn and rawInsn.block.hasLabel(rawOps[0]):
			# Label reference
			oper = make_AwlOperator(AwlOperatorTypes.LBL_REF, 0, None, None)
			oper.immediateStr = rawOps[0]
			return OpDescriptor(oper, 1)
		token0 = rawOps[0].upper()

		# Constant operator (from table)
		operTable = self.__mnemonics2constOperTab[self.mnemonics]
		if token0 in operTable:
			return operTable[token0].dup()
		# Bitwise indirect addressing
		if token0 == '[':
			# This is special case for the "U [AR1,P#0.0]" bitwise addressing.
			# Create a descriptor for the (yet) unspecified bitwise access.
			opDesc = OpDescriptor(make_AwlOperator(AwlOperatorTypes.UNSPEC, 1,
							  make_AwlOffset(self.CALC_OFFS, self.CALC_OFFS),
							  None), 1)
			# And hand over to indirect address parsing.
			self.__translateIndirectAddressing(opDesc, rawOps[1:])
			assert(opDesc.operator.operType != AwlOperatorTypes.UNSPEC)
			return opDesc
		# Local variable
		if token0.startswith('#'):
			offset, count = self.__transVarIdents(rawOps)
			if not offset:
				raise AwlSimError("Failed to parse variable name: %s" %\
					"".join(rawOps))
			return OpDescriptor(make_AwlOperator(AwlOperatorTypes.NAMED_LOCAL, 0,
							offset, None), count)
		# Pointer to local variable
		if token0.startswith("P##"):
			offset = make_AwlOffset(self.NO_OFFS, self.NO_OFFS)
			# Doesn't support struct or array indexing.
			# Parse it as one identification.
			offset.identChain = AwlDataIdentChain(
				[ AwlDataIdent(rawOps[0][3:]), ]
			)
			return OpDescriptor(make_AwlOperator(AwlOperatorTypes.NAMED_LOCAL_PTR, 0,
							offset, None), 1)
		# Symbolic name
		if token0.startswith('"') and token0.endswith('"'):
			offset = make_AwlOffset(self.NO_OFFS, self.NO_OFFS)
			offset.identChain = AwlDataIdentChain(
				[ AwlDataIdent(rawOps[0][1:-1],
					       doValidateName = False), ]
			)
			return OpDescriptor(make_AwlOperator(AwlOperatorTypes.SYMBOLIC, 0,
							offset, None), 1)

		from awlsim.core.datatypes import AwlDataType

		# Immediate boolean
		immediate = AwlDataType.tryParseImmediate_BOOL(rawOps[0])
		if immediate is not None:
			immediate &= 1
			oper = make_AwlOperator(AwlOperatorTypes.IMM, 1, None, None)
			oper.immediate = immediate
			return OpDescriptor(oper, 1)
		# Immediate integer
		immediate = AwlDataType.tryParseImmediate_INT(rawOps[0])
		if immediate is not None:
			immediate &= 0xFFFF
			oper = make_AwlOperator(AwlOperatorTypes.IMM, 16, None, None)
			oper.immediate = immediate
			return OpDescriptor(oper, 1)
		# Immediate float
		immediate = AwlDataType.tryParseImmediate_REAL(rawOps[0])
		if immediate is not None:
			immediate &= 0xFFFFFFFF
			oper = make_AwlOperator(AwlOperatorTypes.IMM_REAL, 32, None, None)
			oper.immediate = immediate
			return OpDescriptor(oper, 1)
		# S5Time immediate
		immediate = AwlDataType.tryParseImmediate_S5T(rawOps[0])
		if immediate is not None:
			immediate &= 0xFFFF
			oper = make_AwlOperator(AwlOperatorTypes.IMM_S5T, 16, None, None)
			oper.immediate = immediate
			return OpDescriptor(oper, 1)
		# Time immediate
		immediate = AwlDataType.tryParseImmediate_TIME(rawOps[0])
		if immediate is not None:
			immediate &= 0xFFFFFFFF
			oper = make_AwlOperator(AwlOperatorTypes.IMM_TIME, 32, None, None)
			oper.immediate = immediate
			return OpDescriptor(oper, 1)
		# TIME_OF_DAY immediate
		immediate = AwlDataType.tryParseImmediate_TOD(rawOps[0])
		if immediate is not None:
			immediate &= 0xFFFFFFFF
			oper = make_AwlOperator(AwlOperatorTypes.IMM_TOD, 32, None, None)
			oper.immediate = immediate
			return OpDescriptor(oper, 1)
		# DATE immediate
		immediate = AwlDataType.tryParseImmediate_DATE(rawOps[0])
		if immediate is not None:
			immediate &= 0xFFFF
			oper = make_AwlOperator(AwlOperatorTypes.IMM_DATE, 16, None, None)
			oper.immediate = immediate
			return OpDescriptor(oper, 1)
		# DATE_AND_TIME immediate
		immediate = AwlDataType.tryParseImmediate_DT(rawOps)
		if immediate is not None:
			oper = make_AwlOperator(AwlOperatorTypes.IMM_DT,
					   len(immediate) * 8, None, None)
			oper.immediateBytes = immediate
			return OpDescriptor(oper, 5)
		# Pointer immediate
		pointer, fields = AwlDataType.tryParseImmediate_Pointer(rawOps)
		if pointer is not None:
			oper = make_AwlOperator(AwlOperatorTypes.IMM_PTR, pointer.width,
					   None, None)
			oper.pointer = pointer
			return OpDescriptor(oper, fields)
		# Binary immediate
		immediate = AwlDataType.tryParseImmediate_Bin(rawOps[0])
		if immediate is not None:
			immediate &= 0xFFFFFFFF
			size = 32 if (immediate > 0xFFFF) else 16
			oper = make_AwlOperator(AwlOperatorTypes.IMM, size, None, None)
			oper.immediate = immediate
			return OpDescriptor(oper, 1)
		# Byte array immediate
		immediate, fields = AwlDataType.tryParseImmediate_ByteArray(rawOps)
		if immediate is not None:
			size = 32 if fields == 9 else 16
			oper = make_AwlOperator(AwlOperatorTypes.IMM, size, None, None)
			oper.immediate = immediate
			return OpDescriptor(oper, fields)
		# Hex byte immediate
		immediate = AwlDataType.tryParseImmediate_HexByte(rawOps[0])
		if immediate is not None:
			immediate &= 0xFF
			oper = make_AwlOperator(AwlOperatorTypes.IMM, 8, None, None)
			oper.immediate = immediate
			return OpDescriptor(oper, 1)
		# Hex word immediate
		immediate = AwlDataType.tryParseImmediate_HexWord(rawOps[0])
		if immediate is not None:
			immediate &= 0xFFFF
			oper = make_AwlOperator(AwlOperatorTypes.IMM, 16, None, None)
			oper.immediate = immediate
			return OpDescriptor(oper, 1)
		# Hex dword immediate
		immediate = AwlDataType.tryParseImmediate_HexDWord(rawOps[0])
		if immediate is not None:
			immediate &= 0xFFFFFFFF
			oper = make_AwlOperator(AwlOperatorTypes.IMM, 32, None, None)
			oper.immediate = immediate
			return OpDescriptor(oper, 1)
		# Long integer immediate
		immediate = AwlDataType.tryParseImmediate_DINT(rawOps[0])
		if immediate is not None:
			immediate &= 0xFFFFFFFF
			oper = make_AwlOperator(AwlOperatorTypes.IMM, 32, None, None)
			oper.immediate = immediate
			return OpDescriptor(oper, 1)
		# BCD word immediate
		immediate = AwlDataType.tryParseImmediate_BCD_word(rawOps[0])
		if immediate is not None:
			immediate &= 0xFFFF
			oper = make_AwlOperator(AwlOperatorTypes.IMM, 16, None, None)
			oper.immediate = immediate
			return OpDescriptor(oper, 1)
		# String immediate
		immediate = AwlDataType.tryParseImmediate_STRING(rawOps[0])
		if immediate is not None:
			oper = make_AwlOperator(AwlOperatorTypes.IMM_STR,
					   len(immediate) * 8, None, None)
			oper.immediateBytes = immediate
			return OpDescriptor(oper, 1)
		# DBx.DBX/B/W/D addressing
		match = re.match(r'^DB(\d+)\.DB([XBWD])$', rawOps[0])
		if match:
			dbNumber = int(match.group(1))
			width = {
				"X"	: 1,
				"B"	: 8,
				"W"	: 16,
				"D"	: 32,
			}[match.group(2)]
			offset = make_AwlOffset(self.CALC_OFFS, self.CALC_OFFS if (width == 1) else 0)
			offset.dbNumber = dbNumber
			return OpDescriptor(make_AwlOperator(AwlOperatorTypes.MEM_DB, width,
					    offset, None), 2)

		# Try to parse DBx.VARIABLE or "DBname".VARIABLE adressing
		offset, count = self.__transVarIdents(rawOps)
		if offset:
			return OpDescriptor(make_AwlOperator(AwlOperatorTypes.NAMED_DBVAR, 0,
					    offset, None), count)

		# Try convenience operators.
		# A convenience operator is one that lacks otherwise required white space.
		# We thus actively support lazy programmers, yay.
		# For example:
		#	= M0.0
		# (Note the missing white space between M and 0.0)
		for name, opDesc in dictItems(operTable):
			if opDesc.operator.offset is not None and\
			   opDesc.operator.offset.byteOffset >= 0 and\
			   opDesc.operator.offset.bitOffset >= 0:
				# Only for operators with bit/byte addresses.
				continue
			try:
				# Try convenience operator
				if token0.startswith(name) and\
				   token0[len(name)].isdigit():
					opDesc = opDesc.dup()
					opDesc.stripLeadingChars = len(name)
					opDesc.fieldCount -= 1
					return opDesc
			except IndexError:
				pass
		raise AwlSimError("Cannot parse operator: " +\
				str(rawOps[0]))

	def translateOp(self, rawInsn, rawOps):
		"""Translate operator tokens.
		Returns an OpDescriptor().
		"""
		if not rawOps:
			raise AwlSimError("Cannot parse operator: Operator is empty")
		opDesc = self.__doTrans(rawInsn, rawOps)

		if opDesc.operator.offset is not None and\
		   (opDesc.operator.offset.byteOffset == self.CALC_OFFS or\
		    opDesc.operator.offset.bitOffset == self.CALC_OFFS):
			if opDesc.stripLeadingChars:
				strippedRawOps = rawOps[:]
				strippedRawOps[0] = strippedRawOps[0][opDesc.stripLeadingChars : ]
				self.__translateAddressOperator(opDesc, strippedRawOps)
			else:
				self.__translateAddressOperator(opDesc, rawOps[1:])

		assert(opDesc.operator.operType != AwlOperatorTypes.UNSPEC)
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
				self.insn.params = self.insn.params + (param,)

			rawOps = rawOps[opDesc.fieldCount + 2 : ]
			if rawOps:
				if rawOps[0] == ',':
					rawOps = rawOps[1:]
				else:
					raise AwlSimError("Missing comma in parameter list")

	def translateFromRawInsn(self, rawInsn):
		"""Translate operators from rawInsn and add them to self.insn.
		"""
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

	def __tokenizeString(self, string):
		"""Split a string into operator tokens.
		"""
		tokens, s, inSingleQuote, inDoubleQuote = [], [], False, False
		for c in string:
			if inSingleQuote or inDoubleQuote:
				if (inSingleQuote and c == "'") or\
				   (inDoubleQuote and c == '"'):
					inSingleQuote, inDoubleQuote = False, False
					s.append(c)
					tokens.append("".join(s))
					s = []
				else:
					s.append(c)
			else:
				if c in {'"', "'"}:
					inSingleQuote, inDoubleQuote = (c == "'"), (c == '"')
					if s:
						tokens.append("".join(s))
					s = [c]
				elif c.isspace():
					if s:
						tokens.append("".join(s))
						s = []
				else:
					s.append(c)
		if s:
			tokens.append("".join(s))
		return tokens

	def translateFromString(self, string):
		"""Translate an operator string.
		Returns an OpDescriptor().
		"""
		return self.translateOp(rawInsn=None,
					rawOps=self.__tokenizeString(string))

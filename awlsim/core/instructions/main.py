# -*- coding: utf-8 -*-
#
# AWL simulator - instructions
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

from awlsim.common.cpuconfig import *
from awlsim.common.datatypehelpers import * #+cimport
from awlsim.common.exceptions import *

from awlsim.core.instructions.types import * #+cimport
from awlsim.core.instructions.parentinfo import *
from awlsim.core.operatortypes import * #+cimport
from awlsim.core.operators import * #+cimport
from awlsim.core.util import *

from awlsim.awlcompiler.optrans import *


class AwlInsn(object): #+cdef
	"""AWL instruction base class.
	"""

	TYPE_U			= AwlInsnTypes.TYPE_U
	TYPE_UN			= AwlInsnTypes.TYPE_UN
	TYPE_O			= AwlInsnTypes.TYPE_O
	TYPE_ON			= AwlInsnTypes.TYPE_ON
	TYPE_X			= AwlInsnTypes.TYPE_X
	TYPE_XN			= AwlInsnTypes.TYPE_XN
	TYPE_UB			= AwlInsnTypes.TYPE_UB
	TYPE_UNB		= AwlInsnTypes.TYPE_UNB
	TYPE_OB			= AwlInsnTypes.TYPE_OB
	TYPE_ONB		= AwlInsnTypes.TYPE_ONB
	TYPE_XB			= AwlInsnTypes.TYPE_XB
	TYPE_XNB		= AwlInsnTypes.TYPE_XNB
	TYPE_BEND		= AwlInsnTypes.TYPE_BEND
	TYPE_ASSIGN		= AwlInsnTypes.TYPE_ASSIGN
	TYPE_R			= AwlInsnTypes.TYPE_R
	TYPE_S			= AwlInsnTypes.TYPE_S
	TYPE_NOT		= AwlInsnTypes.TYPE_NOT
	TYPE_SET		= AwlInsnTypes.TYPE_SET
	TYPE_CLR		= AwlInsnTypes.TYPE_CLR
	TYPE_SAVE		= AwlInsnTypes.TYPE_SAVE
	TYPE_FN			= AwlInsnTypes.TYPE_FN
	TYPE_FP			= AwlInsnTypes.TYPE_FP
	TYPE_EQ_I		= AwlInsnTypes.TYPE_EQ_I
	TYPE_NE_I		= AwlInsnTypes.TYPE_NE_I
	TYPE_GT_I		= AwlInsnTypes.TYPE_GT_I
	TYPE_LT_I		= AwlInsnTypes.TYPE_LT_I
	TYPE_GE_I		= AwlInsnTypes.TYPE_GE_I
	TYPE_LE_I		= AwlInsnTypes.TYPE_LE_I
	TYPE_EQ_D		= AwlInsnTypes.TYPE_EQ_D
	TYPE_NE_D		= AwlInsnTypes.TYPE_NE_D
	TYPE_GT_D		= AwlInsnTypes.TYPE_GT_D
	TYPE_LT_D		= AwlInsnTypes.TYPE_LT_D
	TYPE_GE_D		= AwlInsnTypes.TYPE_GE_D
	TYPE_LE_D		= AwlInsnTypes.TYPE_LE_D
	TYPE_EQ_R		= AwlInsnTypes.TYPE_EQ_R
	TYPE_NE_R		= AwlInsnTypes.TYPE_NE_R
	TYPE_GT_R		= AwlInsnTypes.TYPE_GT_R
	TYPE_LT_R		= AwlInsnTypes.TYPE_LT_R
	TYPE_GE_R		= AwlInsnTypes.TYPE_GE_R
	TYPE_LE_R		= AwlInsnTypes.TYPE_LE_R
	TYPE_BTI		= AwlInsnTypes.TYPE_BTI
	TYPE_ITB		= AwlInsnTypes.TYPE_ITB
	TYPE_BTD		= AwlInsnTypes.TYPE_BTD
	TYPE_ITD		= AwlInsnTypes.TYPE_ITD
	TYPE_DTB		= AwlInsnTypes.TYPE_DTB
	TYPE_DTR		= AwlInsnTypes.TYPE_DTR
	TYPE_INVI		= AwlInsnTypes.TYPE_INVI
	TYPE_INVD		= AwlInsnTypes.TYPE_INVD
	TYPE_NEGI		= AwlInsnTypes.TYPE_NEGI
	TYPE_NEGD		= AwlInsnTypes.TYPE_NEGD
	TYPE_NEGR		= AwlInsnTypes.TYPE_NEGR
	TYPE_TAW		= AwlInsnTypes.TYPE_TAW
	TYPE_TAD		= AwlInsnTypes.TYPE_TAD
	TYPE_RND		= AwlInsnTypes.TYPE_RND
	TYPE_TRUNC		= AwlInsnTypes.TYPE_TRUNC
	TYPE_RNDP		= AwlInsnTypes.TYPE_RNDP
	TYPE_RNDN		= AwlInsnTypes.TYPE_RNDN
	TYPE_FR			= AwlInsnTypes.TYPE_FR
	TYPE_L			= AwlInsnTypes.TYPE_L
	TYPE_LC			= AwlInsnTypes.TYPE_LC
	TYPE_ZV			= AwlInsnTypes.TYPE_ZV
	TYPE_ZR			= AwlInsnTypes.TYPE_ZR
	TYPE_AUF		= AwlInsnTypes.TYPE_AUF
	TYPE_TDB		= AwlInsnTypes.TYPE_TDB
	TYPE_SPA		= AwlInsnTypes.TYPE_SPA
	TYPE_SPL		= AwlInsnTypes.TYPE_SPL
	TYPE_SPB		= AwlInsnTypes.TYPE_SPB
	TYPE_SPBN		= AwlInsnTypes.TYPE_SPBN
	TYPE_SPBB		= AwlInsnTypes.TYPE_SPBB
	TYPE_SPBNB		= AwlInsnTypes.TYPE_SPBNB
	TYPE_SPBI		= AwlInsnTypes.TYPE_SPBI
	TYPE_SPBIN		= AwlInsnTypes.TYPE_SPBIN
	TYPE_SPO		= AwlInsnTypes.TYPE_SPO
	TYPE_SPS		= AwlInsnTypes.TYPE_SPS
	TYPE_SPZ		= AwlInsnTypes.TYPE_SPZ
	TYPE_SPN		= AwlInsnTypes.TYPE_SPN
	TYPE_SPP		= AwlInsnTypes.TYPE_SPP
	TYPE_SPM		= AwlInsnTypes.TYPE_SPM
	TYPE_SPPZ		= AwlInsnTypes.TYPE_SPPZ
	TYPE_SPMZ		= AwlInsnTypes.TYPE_SPMZ
	TYPE_SPU		= AwlInsnTypes.TYPE_SPU
	TYPE_LOOP		= AwlInsnTypes.TYPE_LOOP
	TYPE_PL_I		= AwlInsnTypes.TYPE_PL_I
	TYPE_MI_I		= AwlInsnTypes.TYPE_MI_I
	TYPE_MU_I		= AwlInsnTypes.TYPE_MU_I
	TYPE_DI_I		= AwlInsnTypes.TYPE_DI_I
	TYPE_PL			= AwlInsnTypes.TYPE_PL
	TYPE_PL_D		= AwlInsnTypes.TYPE_PL_D
	TYPE_MI_D		= AwlInsnTypes.TYPE_MI_D
	TYPE_MU_D		= AwlInsnTypes.TYPE_MU_D
	TYPE_DI_D		= AwlInsnTypes.TYPE_DI_D
	TYPE_MOD		= AwlInsnTypes.TYPE_MOD
	TYPE_PL_R		= AwlInsnTypes.TYPE_PL_R
	TYPE_MI_R		= AwlInsnTypes.TYPE_MI_R
	TYPE_MU_R		= AwlInsnTypes.TYPE_MU_R
	TYPE_DI_R		= AwlInsnTypes.TYPE_DI_R
	TYPE_ABS		= AwlInsnTypes.TYPE_ABS
	TYPE_SQR		= AwlInsnTypes.TYPE_SQR
	TYPE_SQRT		= AwlInsnTypes.TYPE_SQRT
	TYPE_EXP		= AwlInsnTypes.TYPE_EXP
	TYPE_LN			= AwlInsnTypes.TYPE_LN
	TYPE_SIN		= AwlInsnTypes.TYPE_SIN
	TYPE_COS		= AwlInsnTypes.TYPE_COS
	TYPE_TAN		= AwlInsnTypes.TYPE_TAN
	TYPE_ASIN		= AwlInsnTypes.TYPE_ASIN
	TYPE_ACOS		= AwlInsnTypes.TYPE_ACOS
	TYPE_ATAN		= AwlInsnTypes.TYPE_ATAN
	TYPE_LAR1		= AwlInsnTypes.TYPE_LAR1
	TYPE_LAR2		= AwlInsnTypes.TYPE_LAR2
	TYPE_T			= AwlInsnTypes.TYPE_T
	TYPE_TAR		= AwlInsnTypes.TYPE_TAR
	TYPE_TAR1		= AwlInsnTypes.TYPE_TAR1
	TYPE_TAR2		= AwlInsnTypes.TYPE_TAR2
	TYPE_BE			= AwlInsnTypes.TYPE_BE
	TYPE_BEB		= AwlInsnTypes.TYPE_BEB
	TYPE_BEA		= AwlInsnTypes.TYPE_BEA
	TYPE_CALL		= AwlInsnTypes.TYPE_CALL
	TYPE_CC			= AwlInsnTypes.TYPE_CC
	TYPE_UC			= AwlInsnTypes.TYPE_UC
	TYPE_MCRB		= AwlInsnTypes.TYPE_MCRB
	TYPE_BMCR		= AwlInsnTypes.TYPE_BMCR
	TYPE_MCRA		= AwlInsnTypes.TYPE_MCRA
	TYPE_MCRD		= AwlInsnTypes.TYPE_MCRD
	TYPE_SSI		= AwlInsnTypes.TYPE_SSI
	TYPE_SSD		= AwlInsnTypes.TYPE_SSD
	TYPE_SLW		= AwlInsnTypes.TYPE_SLW
	TYPE_SRW		= AwlInsnTypes.TYPE_SRW
	TYPE_SLD		= AwlInsnTypes.TYPE_SLD
	TYPE_SRD		= AwlInsnTypes.TYPE_SRD
	TYPE_RLD		= AwlInsnTypes.TYPE_RLD
	TYPE_RRD		= AwlInsnTypes.TYPE_RRD
	TYPE_RLDA		= AwlInsnTypes.TYPE_RLDA
	TYPE_RRDA		= AwlInsnTypes.TYPE_RRDA
	TYPE_SI			= AwlInsnTypes.TYPE_SI
	TYPE_SV			= AwlInsnTypes.TYPE_SV
	TYPE_SE			= AwlInsnTypes.TYPE_SE
	TYPE_SS			= AwlInsnTypes.TYPE_SS
	TYPE_SA			= AwlInsnTypes.TYPE_SA
	TYPE_UW			= AwlInsnTypes.TYPE_UW
	TYPE_OW			= AwlInsnTypes.TYPE_OW
	TYPE_XOW		= AwlInsnTypes.TYPE_XOW
	TYPE_UD			= AwlInsnTypes.TYPE_UD
	TYPE_OD			= AwlInsnTypes.TYPE_OD
	TYPE_XOD		= AwlInsnTypes.TYPE_XOD
	TYPE_TAK		= AwlInsnTypes.TYPE_TAK
	TYPE_PUSH		= AwlInsnTypes.TYPE_PUSH
	TYPE_POP		= AwlInsnTypes.TYPE_POP
	TYPE_ENT		= AwlInsnTypes.TYPE_ENT
	TYPE_LEAVE		= AwlInsnTypes.TYPE_LEAVE
	TYPE_INC		= AwlInsnTypes.TYPE_INC
	TYPE_DEC		= AwlInsnTypes.TYPE_DEC
	TYPE_INCAR1		= AwlInsnTypes.TYPE_INCAR1
	TYPE_INCAR2		= AwlInsnTypes.TYPE_INCAR2
	TYPE_BLD		= AwlInsnTypes.TYPE_BLD
	TYPE_NOP		= AwlInsnTypes.TYPE_NOP
	TYPE_EXTENDED		= AwlInsnTypes.TYPE_EXTENDED
	TYPE_ASSERT_EQ		= AwlInsnTypes.TYPE_ASSERT_EQ
	TYPE_ASSERT_EQ_R	= AwlInsnTypes.TYPE_ASSERT_EQ_R
	TYPE_ASSERT_NE		= AwlInsnTypes.TYPE_ASSERT_NE
	TYPE_ASSERT_GT		= AwlInsnTypes.TYPE_ASSERT_GT
	TYPE_ASSERT_LT		= AwlInsnTypes.TYPE_ASSERT_LT
	TYPE_ASSERT_GE		= AwlInsnTypes.TYPE_ASSERT_GE
	TYPE_ASSERT_LE		= AwlInsnTypes.TYPE_ASSERT_LE
	TYPE_SLEEP		= AwlInsnTypes.TYPE_SLEEP
	TYPE_STWRST		= AwlInsnTypes.TYPE_STWRST
	TYPE_FEATURE		= AwlInsnTypes.TYPE_FEATURE
	TYPE_GENERIC_CALL	= AwlInsnTypes.TYPE_GENERIC_CALL
	TYPE_INLINE_AWL		= AwlInsnTypes.TYPE_INLINE_AWL

	english2german = AwlInsnTypes.english2german
	german2english = AwlInsnTypes.german2english
	name2type_german = AwlInsnTypes.name2type_german
	type2name_german = AwlInsnTypes.type2name_german
	name2type_english = AwlInsnTypes.name2type_english
	type2name_english = AwlInsnTypes.type2name_english

	__slots__ = (
		"cpu",
		"insnType",
		"ip",
		"ops",
		"opCount",
		"op0",
		"op1",
		"params",
		"labelStr",
		"commentStr",
		"parentInfo",
		"_widths_1",
		"_widths_8_16_32",
		"_widths_16",
		"_widths_32",
		"_widths_scalar",
		"_widths_all",
	)

	def __init__(self, cpu, insnType, rawInsn=None, ops=None):
		"""Initialize base instruction.
		"""
		self.parentInfo = AwlInsnParentInfo()	# Parent information
		self.cpu = cpu				# S7CPU() or None
		self.insnType = insnType		# TYPE_...
		self.parentInfo.rawInsn = rawInsn	# RawAwlInsn() or None
		self.ip = 0				# Instruction pointer (IP)
		self.ops = ops or []			# AwlOperator()s
		self.params = ()			# Parameter assignments (for CALL)
		self.labelStr = None			# Optional label string.
		self.commentStr = ""			# Optional comment string.

		# Local copy of commonly used fetch/store widths.
		self._widths_1		= AwlOperatorWidths.WIDTH_MASK_1
		self._widths_8_16_32	= AwlOperatorWidths.WIDTH_MASK_8_16_32
		self._widths_16		= AwlOperatorWidths.WIDTH_MASK_16
		self._widths_32		= AwlOperatorWidths.WIDTH_MASK_32
		self._widths_scalar	= AwlOperatorWidths.WIDTH_MASK_SCALAR
		self._widths_all	= AwlOperatorWidths.WIDTH_MASK_ALL

		if rawInsn and ops is None:
			opTrans = AwlOpTranslator(self)
			opTrans.translateFromRawInsn(rawInsn)
		self.__setupOpQuickRef()

	def __setupOpQuickRef(self):
		# Add a quick reference to the first and the second operator.
		self.opCount = len(self.ops)
		if self.opCount >= 1:
			self.op0 = self.ops[0]
		if self.opCount >= 2:
			self.op1 = self.ops[1]

	def finalSetup(self):
		"""Run the final setup steps.
		This method has to be called before the
		instruction can be run for the first time.
		"""
		self.__setupOpQuickRef()

	def staticSanityChecks(self):
		"""Run static sanity checks.
		"""
		pass # Default: No sanity checks

	def assertOpCount(self, counts):
		"""Check whether we have the required operator count.
		counts is a list/set/int of possible counts.
		"""
		assert(self.opCount == len(self.ops))
		counts = toList(counts)
		if self.opCount not in counts:
			raise AwlSimError("Invalid number of operators. "
				"Expected %s." % listToHumanStr(counts),
				insn=self)

	def getMnemonics(self):
		"""Return the MNEMONICS_... setting for this instruction.
		Returns None, if the mnemonics setting is unknown.
		"""
		if self.cpu:
			return self.cpu.getMnemonics()
		return None

	def getRawInsn(self):
		return self.parentInfo.rawInsn

	def hasLabel(self):
		"""Returns True, if this insn has a label.
		"""
		if self.labelStr is not None:
			return bool(self.labelStr)
		if self.parentInfo.rawInsn:
			return self.parentInfo.rawInsn.hasLabel()
		return False

	def getLabel(self):
		"""Returns the label string.
		"""
		if self.labelStr is not None:
			return self.labelStr
		if self.parentInfo.rawInsn:
			return self.parentInfo.rawInsn.getLabel()
		return None

	def setLabel(self, labelStr):
		self.labelStr = labelStr or ""

	def getIP(self):
		return self.ip

	def setIP(self, newIp):
		self.ip = newIp

	def getCpu(self):
		return self.cpu

	def getSourceId(self):
		if not self.parentInfo.rawInsn:
			return None
		return self.parentInfo.rawInsn.getSourceId()

	def getLineNr(self):
		if not self.parentInfo.rawInsn:
			return -1
		return self.parentInfo.rawInsn.getLineNr()

	def run(self): #+cdef
		"""Run the instruction.
		The default implementation does nothing.
		"""
		pass

	def _warnDeprecated(self, moreText=""):
		lineNrStr = ""
		lineNr = self.getLineNr()
		if lineNr >= 0:
			lineNrStr = " at line %d" % lineNr
		if moreText:
			moreText = "\n%s" % moreText
		printWarning("Found DEPRECATED instruction%s:\n  %s%s" % (
			     lineNrStr, str(self), moreText))

	def getStr(self, compact=True, withSemicolon=False, withComment=False):
		ret = []
		if self.hasLabel():
			labelStr = self.getLabel() + ":"
			ret.append(labelStr)
			nrPad = 1
			if not compact:
				nrPad = 8 - len(labelStr)
			ret.append(" " * nrPad)
		else:
			if not compact:
				ret.append(" " * 8)
		type2name = AwlInsn.type2name_english
		if self.getMnemonics() == S7CPUConfig.MNEMONICS_DE:
			type2name = AwlInsn.type2name_german
		try:
			name = type2name[self.insnType]
		except KeyError:
			name = "<unknown type %d>" % self.insnType
		ret.append(name)
		if self.ops:
			if compact:
				ret.append(" ")
			else:
				ret.append(" " * (8 - len(name)))
			ret.append(", ".join(str(op) for op in self.ops))
		if self.params:
			ret.append(" ( ")
			ret.append(", ".join(str(param) for param in self.params))
			ret.append(" )")
		if withSemicolon:
			ret.append(";")
		text = "".join(ret)
		if withComment and (self.commentStr or self.parentInfo):
			text += " " * (40 - len(text))
			text += "// "
			if self.commentStr:
				text += self.commentStr
				if self.parentInfo:
					text += "    "
			if self.parentInfo:
				text += str(self.parentInfo)
		return text

	def __repr__(self):
		return self.getStr()

# Sanity check of english2german table
assert(all(germanName in AwlInsn.name2type_german \
	   for englishName, germanName in dictItems(AwlInsn.english2german)))

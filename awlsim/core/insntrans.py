#
# AWL simulator - Instruction translator
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

from awlsim.core.util import *
from awlsim.core.instructions.all_insns import *
from awlsim.core.parser import *
from awlsim.core.cpuspecs import *


class AwlInsnTranslator(object):
	type2class = {
		AwlInsn.TYPE_INVALID	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_U	    	: AwlInsn_U,
		AwlInsn.TYPE_UN	    	: AwlInsn_UN,
		AwlInsn.TYPE_O	    	: AwlInsn_O,
		AwlInsn.TYPE_ON	    	: AwlInsn_ON,
		AwlInsn.TYPE_X	    	: AwlInsn_X,
		AwlInsn.TYPE_XN	    	: AwlInsn_XN,
		AwlInsn.TYPE_UB	    	: AwlInsn_UB,
		AwlInsn.TYPE_UNB    	: AwlInsn_UNB,
		AwlInsn.TYPE_OB	    	: AwlInsn_OB,
		AwlInsn.TYPE_ONB    	: AwlInsn_ONB,
		AwlInsn.TYPE_XB	    	: AwlInsn_XB,
		AwlInsn.TYPE_XNB    	: AwlInsn_XNB,
		AwlInsn.TYPE_BEND   	: AwlInsn_BEND,
		AwlInsn.TYPE_ASSIGN 	: AwlInsn_ASSIGN,
		AwlInsn.TYPE_R	    	: AwlInsn_R,
		AwlInsn.TYPE_S	    	: AwlInsn_S,
		AwlInsn.TYPE_NOT    	: AwlInsn_NOT,
		AwlInsn.TYPE_SET    	: AwlInsn_SET,
		AwlInsn.TYPE_CLR    	: AwlInsn_CLR,
		AwlInsn.TYPE_SAVE   	: AwlInsn_SAVE,
		AwlInsn.TYPE_FN	    	: AwlInsn_FN,
		AwlInsn.TYPE_FP	    	: AwlInsn_FP,
		AwlInsn.TYPE_EQ_I   	: AwlInsn_EQ_I,
		AwlInsn.TYPE_NE_I   	: AwlInsn_NE_I,
		AwlInsn.TYPE_GT_I   	: AwlInsn_GT_I,
		AwlInsn.TYPE_LT_I   	: AwlInsn_LT_I,
		AwlInsn.TYPE_GE_I   	: AwlInsn_GE_I,
		AwlInsn.TYPE_LE_I   	: AwlInsn_LE_I,
		AwlInsn.TYPE_EQ_D   	: AwlInsn_EQ_D,
		AwlInsn.TYPE_NE_D   	: AwlInsn_NE_D,
		AwlInsn.TYPE_GT_D   	: AwlInsn_GT_D,
		AwlInsn.TYPE_LT_D   	: AwlInsn_LT_D,
		AwlInsn.TYPE_GE_D   	: AwlInsn_GE_D,
		AwlInsn.TYPE_LE_D   	: AwlInsn_LE_D,
		AwlInsn.TYPE_EQ_R   	: AwlInsn_EQ_R,
		AwlInsn.TYPE_NE_R   	: AwlInsn_NE_R,
		AwlInsn.TYPE_GT_R   	: AwlInsn_GT_R,
		AwlInsn.TYPE_LT_R   	: AwlInsn_LT_R,
		AwlInsn.TYPE_GE_R   	: AwlInsn_GE_R,
		AwlInsn.TYPE_LE_R   	: AwlInsn_LE_R,
		AwlInsn.TYPE_BTI    	: AwlInsn_BTI,
		AwlInsn.TYPE_ITB    	: AwlInsn_ITB,
		AwlInsn.TYPE_BTD    	: AwlInsn_BTD,
		AwlInsn.TYPE_ITD    	: AwlInsn_ITD,
		AwlInsn.TYPE_DTB    	: AwlInsn_DTB,
		AwlInsn.TYPE_DTR    	: AwlInsn_DTR,
		AwlInsn.TYPE_INVI   	: AwlInsn_INVI,
		AwlInsn.TYPE_INVD   	: AwlInsn_INVD,
		AwlInsn.TYPE_NEGI   	: AwlInsn_NEGI,
		AwlInsn.TYPE_NEGD   	: AwlInsn_NEGD,
		AwlInsn.TYPE_NEGR   	: AwlInsn_NEGR,
		AwlInsn.TYPE_TAW    	: AwlInsn_TAW,
		AwlInsn.TYPE_TAD    	: AwlInsn_TAD,
		AwlInsn.TYPE_RND    	: AwlInsn_RND,
		AwlInsn.TYPE_TRUNC  	: AwlInsn_TRUNC,
		AwlInsn.TYPE_RNDP   	: AwlInsn_RNDP,
		AwlInsn.TYPE_RNDN   	: AwlInsn_RNDN,
		AwlInsn.TYPE_FR	    	: AwlInsn_FR,
		AwlInsn.TYPE_L	    	: AwlInsn_L,
		AwlInsn.TYPE_LC	    	: AwlInsn_LC,
		AwlInsn.TYPE_ZV	    	: AwlInsn_ZV,
		AwlInsn.TYPE_ZR	    	: AwlInsn_ZR,
		AwlInsn.TYPE_AUF    	: AwlInsn_AUF,
		AwlInsn.TYPE_TDB    	: AwlInsn_TDB,
		AwlInsn.TYPE_SPA    	: AwlInsn_SPA,
		AwlInsn.TYPE_SPL    	: AwlInsn_SPL,
		AwlInsn.TYPE_SPB    	: AwlInsn_SPB,
		AwlInsn.TYPE_SPBN   	: AwlInsn_SPBN,
		AwlInsn.TYPE_SPBB   	: AwlInsn_SPBB,
		AwlInsn.TYPE_SPBNB  	: AwlInsn_SPBNB,
		AwlInsn.TYPE_SPBI   	: AwlInsn_SPBI,
		AwlInsn.TYPE_SPBIN  	: AwlInsn_SPBIN,
		AwlInsn.TYPE_SPO    	: AwlInsn_SPO,
		AwlInsn.TYPE_SPS    	: AwlInsn_SPS,
		AwlInsn.TYPE_SPZ    	: AwlInsn_SPZ,
		AwlInsn.TYPE_SPN    	: AwlInsn_SPN,
		AwlInsn.TYPE_SPP    	: AwlInsn_SPP,
		AwlInsn.TYPE_SPM    	: AwlInsn_SPM,
		AwlInsn.TYPE_SPPZ   	: AwlInsn_SPPZ,
		AwlInsn.TYPE_SPMZ   	: AwlInsn_SPMZ,
		AwlInsn.TYPE_SPU    	: AwlInsn_SPU,
		AwlInsn.TYPE_LOOP   	: AwlInsn_LOOP,
		AwlInsn.TYPE_PL_I   	: AwlInsn_PL_I,
		AwlInsn.TYPE_MI_I   	: AwlInsn_MI_I,
		AwlInsn.TYPE_MU_I   	: AwlInsn_MU_I,
		AwlInsn.TYPE_DI_I   	: AwlInsn_DI_I,
		AwlInsn.TYPE_PL	    	: AwlInsn_PL,
		AwlInsn.TYPE_PL_D   	: AwlInsn_PL_D,
		AwlInsn.TYPE_MI_D   	: AwlInsn_MI_D,
		AwlInsn.TYPE_MU_D   	: AwlInsn_MU_D,
		AwlInsn.TYPE_DI_D   	: AwlInsn_DI_D,
		AwlInsn.TYPE_MOD    	: AwlInsn_MOD,
		AwlInsn.TYPE_PL_R   	: AwlInsn_PL_R,
		AwlInsn.TYPE_MI_R   	: AwlInsn_MI_R,
		AwlInsn.TYPE_MU_R   	: AwlInsn_MU_R,
		AwlInsn.TYPE_DI_R   	: AwlInsn_DI_R,
		AwlInsn.TYPE_ABS    	: AwlInsn_ABS,
		AwlInsn.TYPE_SQR    	: AwlInsn_SQR,
		AwlInsn.TYPE_SQRT   	: AwlInsn_SQRT,
		AwlInsn.TYPE_EXP    	: AwlInsn_EXP,
		AwlInsn.TYPE_LN	    	: AwlInsn_LN,
		AwlInsn.TYPE_SIN    	: AwlInsn_SIN,
		AwlInsn.TYPE_COS    	: AwlInsn_COS,
		AwlInsn.TYPE_TAN    	: AwlInsn_TAN,
		AwlInsn.TYPE_ASIN   	: AwlInsn_ASIN,
		AwlInsn.TYPE_ACOS   	: AwlInsn_ACOS,
		AwlInsn.TYPE_ATAN   	: AwlInsn_ATAN,
		AwlInsn.TYPE_LAR1   	: AwlInsn_LAR1,
		AwlInsn.TYPE_LAR2   	: AwlInsn_LAR2,
		AwlInsn.TYPE_T	    	: AwlInsn_T,
		AwlInsn.TYPE_TAR    	: AwlInsn_TAR,
		AwlInsn.TYPE_TAR1   	: AwlInsn_TAR1,
		AwlInsn.TYPE_TAR2   	: AwlInsn_TAR2,
		AwlInsn.TYPE_BE	    	: AwlInsn_BE,
		AwlInsn.TYPE_BEB    	: AwlInsn_BEB,
		AwlInsn.TYPE_BEA    	: AwlInsn_BEA,
		AwlInsn.TYPE_CALL   	: AwlInsn_CALL,
		AwlInsn.TYPE_CC	    	: AwlInsn_CC,
		AwlInsn.TYPE_UC	    	: AwlInsn_UC,
		AwlInsn.TYPE_MCRB   	: AwlInsn_MCRB,
		AwlInsn.TYPE_BMCR   	: AwlInsn_BMCR,
		AwlInsn.TYPE_MCRA   	: AwlInsn_MCRA,
		AwlInsn.TYPE_MCRD   	: AwlInsn_MCRD,
		AwlInsn.TYPE_SSI    	: AwlInsn_SSI,
		AwlInsn.TYPE_SSD    	: AwlInsn_SSD,
		AwlInsn.TYPE_SLW    	: AwlInsn_SLW,
		AwlInsn.TYPE_SRW    	: AwlInsn_SRW,
		AwlInsn.TYPE_SLD    	: AwlInsn_SLD,
		AwlInsn.TYPE_SRD    	: AwlInsn_SRD,
		AwlInsn.TYPE_RLD    	: AwlInsn_RLD,
		AwlInsn.TYPE_RRD    	: AwlInsn_RRD,
		AwlInsn.TYPE_RLDA   	: AwlInsn_RLDA,
		AwlInsn.TYPE_RRDA   	: AwlInsn_RRDA,
		AwlInsn.TYPE_SI	    	: AwlInsn_SI,
		AwlInsn.TYPE_SV	    	: AwlInsn_SV,
		AwlInsn.TYPE_SE	    	: AwlInsn_SE,
		AwlInsn.TYPE_SS	    	: AwlInsn_SS,
		AwlInsn.TYPE_SA	    	: AwlInsn_SA,
		AwlInsn.TYPE_UW	    	: AwlInsn_UW,
		AwlInsn.TYPE_OW	    	: AwlInsn_OW,
		AwlInsn.TYPE_XOW    	: AwlInsn_XOW,
		AwlInsn.TYPE_UD	    	: AwlInsn_UD,
		AwlInsn.TYPE_OD	    	: AwlInsn_OD,
		AwlInsn.TYPE_XOD    	: AwlInsn_XOD,
		AwlInsn.TYPE_TAK    	: AwlInsn_TAK,
		AwlInsn.TYPE_PUSH   	: AwlInsn_PUSH,
		AwlInsn.TYPE_POP    	: AwlInsn_POP,
		AwlInsn.TYPE_ENT    	: AwlInsn_ENT,
		AwlInsn.TYPE_LEAVE  	: AwlInsn_LEAVE,
		AwlInsn.TYPE_INC    	: AwlInsn_INC,
		AwlInsn.TYPE_DEC    	: AwlInsn_DEC,
		AwlInsn.TYPE_INCAR1 	: AwlInsn_INCAR1,
		AwlInsn.TYPE_INCAR2 	: AwlInsn_INCAR2,
		AwlInsn.TYPE_BLD    	: AwlInsn_BLD,
		AwlInsn.TYPE_NOP    	: AwlInsn_NOP,

		AwlInsn.TYPE_ASSERT_EQ		: AwlInsn_ASSERT_EQ,
		AwlInsn.TYPE_ASSERT_EQ_R	: AwlInsn_ASSERT_EQ_R,
		AwlInsn.TYPE_ASSERT_NE		: AwlInsn_ASSERT_NE,
		AwlInsn.TYPE_ASSERT_GT		: AwlInsn_ASSERT_GT,
		AwlInsn.TYPE_ASSERT_LT		: AwlInsn_ASSERT_LT,
		AwlInsn.TYPE_ASSERT_GE		: AwlInsn_ASSERT_GE,
		AwlInsn.TYPE_ASSERT_LE		: AwlInsn_ASSERT_LE,
		AwlInsn.TYPE_SLEEP		: AwlInsn_SLEEP,
		AwlInsn.TYPE_STWRST		: AwlInsn_STWRST,
		AwlInsn.TYPE_FEATURE		: AwlInsn_FEATURE,
	}

	@classmethod
	def name2type(cls, insnName, mnemonics):
		insnName = insnName.upper()
		try:
			if mnemonics == S7CPUSpecs.MNEMONICS_EN:
				insnType = AwlInsn.name2type_english[insnName]
			elif mnemonics == S7CPUSpecs.MNEMONICS_DE:
				insnType = AwlInsn.name2type_german[insnName]
			else:
				assert(0)
		except KeyError:
			return None
		return insnType

	@classmethod
	def fromRawInsn(cls, cpu, rawInsn):
		mnemonics = cpu.getSpecs().getMnemonics()
		try:
			insnType = cls.name2type(rawInsn.getName(), mnemonics)
			if insnType is None:
				raise KeyError
			if insnType >= AwlInsn.TYPE_EXTENDED and\
			   not cpu.extendedInsnsEnabled():
				raise KeyError
			insnClass = cls.type2class[insnType]
		except KeyError:
			raise AwlSimError("Cannot translate instruction: '%s'" %\
				rawInsn.getName())
		insn = insnClass(cpu, rawInsn)
		if not cpu.extendedInsnsEnabled():
			if any(op.isExtended for op in insn.ops):
				raise AwlSimError("Extended operands disabled")
		return insn

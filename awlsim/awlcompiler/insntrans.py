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
from awlsim.common.compat import *

from awlsim.common.cpuspecs import * #+cimport
from awlsim.common.cpuconfig import *

from awlsim.core.util import *
from awlsim.core.instructions.all_insns import * #+cimport
from awlsim.core.instructions.types import * #+cimport

from awlsim.awlcompiler import *


class AwlInsnTranslator(object):
	type2class = {
		AwlInsnTypes.TYPE_U	    	: AwlInsn_U,
		AwlInsnTypes.TYPE_UN	    	: AwlInsn_UN,
		AwlInsnTypes.TYPE_O	    	: AwlInsn_O,
		AwlInsnTypes.TYPE_ON	    	: AwlInsn_ON,
		AwlInsnTypes.TYPE_X	    	: AwlInsn_X,
		AwlInsnTypes.TYPE_XN	    	: AwlInsn_XN,
		AwlInsnTypes.TYPE_UB	    	: AwlInsn_UB,
		AwlInsnTypes.TYPE_UNB    	: AwlInsn_UNB,
		AwlInsnTypes.TYPE_OB	    	: AwlInsn_OB,
		AwlInsnTypes.TYPE_ONB    	: AwlInsn_ONB,
		AwlInsnTypes.TYPE_XB	    	: AwlInsn_XB,
		AwlInsnTypes.TYPE_XNB    	: AwlInsn_XNB,
		AwlInsnTypes.TYPE_BEND   	: AwlInsn_BEND,
		AwlInsnTypes.TYPE_ASSIGN 	: AwlInsn_ASSIGN,
		AwlInsnTypes.TYPE_R	    	: AwlInsn_R,
		AwlInsnTypes.TYPE_S	    	: AwlInsn_S,
		AwlInsnTypes.TYPE_NOT    	: AwlInsn_NOT,
		AwlInsnTypes.TYPE_SET    	: AwlInsn_SET,
		AwlInsnTypes.TYPE_CLR    	: AwlInsn_CLR,
		AwlInsnTypes.TYPE_SAVE   	: AwlInsn_SAVE,
		AwlInsnTypes.TYPE_FN	    	: AwlInsn_FN,
		AwlInsnTypes.TYPE_FP	    	: AwlInsn_FP,
		AwlInsnTypes.TYPE_EQ_I   	: AwlInsn_EQ_I,
		AwlInsnTypes.TYPE_NE_I   	: AwlInsn_NE_I,
		AwlInsnTypes.TYPE_GT_I   	: AwlInsn_GT_I,
		AwlInsnTypes.TYPE_LT_I   	: AwlInsn_LT_I,
		AwlInsnTypes.TYPE_GE_I   	: AwlInsn_GE_I,
		AwlInsnTypes.TYPE_LE_I   	: AwlInsn_LE_I,
		AwlInsnTypes.TYPE_EQ_D   	: AwlInsn_EQ_D,
		AwlInsnTypes.TYPE_NE_D   	: AwlInsn_NE_D,
		AwlInsnTypes.TYPE_GT_D   	: AwlInsn_GT_D,
		AwlInsnTypes.TYPE_LT_D   	: AwlInsn_LT_D,
		AwlInsnTypes.TYPE_GE_D   	: AwlInsn_GE_D,
		AwlInsnTypes.TYPE_LE_D   	: AwlInsn_LE_D,
		AwlInsnTypes.TYPE_EQ_R   	: AwlInsn_EQ_R,
		AwlInsnTypes.TYPE_NE_R   	: AwlInsn_NE_R,
		AwlInsnTypes.TYPE_GT_R   	: AwlInsn_GT_R,
		AwlInsnTypes.TYPE_LT_R   	: AwlInsn_LT_R,
		AwlInsnTypes.TYPE_GE_R   	: AwlInsn_GE_R,
		AwlInsnTypes.TYPE_LE_R   	: AwlInsn_LE_R,
		AwlInsnTypes.TYPE_BTI    	: AwlInsn_BTI,
		AwlInsnTypes.TYPE_ITB    	: AwlInsn_ITB,
		AwlInsnTypes.TYPE_BTD    	: AwlInsn_BTD,
		AwlInsnTypes.TYPE_ITD    	: AwlInsn_ITD,
		AwlInsnTypes.TYPE_DTB    	: AwlInsn_DTB,
		AwlInsnTypes.TYPE_DTR    	: AwlInsn_DTR,
		AwlInsnTypes.TYPE_INVI   	: AwlInsn_INVI,
		AwlInsnTypes.TYPE_INVD   	: AwlInsn_INVD,
		AwlInsnTypes.TYPE_NEGI   	: AwlInsn_NEGI,
		AwlInsnTypes.TYPE_NEGD   	: AwlInsn_NEGD,
		AwlInsnTypes.TYPE_NEGR   	: AwlInsn_NEGR,
		AwlInsnTypes.TYPE_TAW    	: AwlInsn_TAW,
		AwlInsnTypes.TYPE_TAD    	: AwlInsn_TAD,
		AwlInsnTypes.TYPE_RND    	: AwlInsn_RND,
		AwlInsnTypes.TYPE_TRUNC  	: AwlInsn_TRUNC,
		AwlInsnTypes.TYPE_RNDP   	: AwlInsn_RNDP,
		AwlInsnTypes.TYPE_RNDN   	: AwlInsn_RNDN,
		AwlInsnTypes.TYPE_FR	    	: AwlInsn_FR,
		AwlInsnTypes.TYPE_L	    	: AwlInsn_L,
		AwlInsnTypes.TYPE_LC	    	: AwlInsn_LC,
		AwlInsnTypes.TYPE_ZV	    	: AwlInsn_ZV,
		AwlInsnTypes.TYPE_ZR	    	: AwlInsn_ZR,
		AwlInsnTypes.TYPE_AUF    	: AwlInsn_AUF,
		AwlInsnTypes.TYPE_TDB    	: AwlInsn_TDB,
		AwlInsnTypes.TYPE_SPA    	: AwlInsn_SPA,
		AwlInsnTypes.TYPE_SPL    	: AwlInsn_SPL,
		AwlInsnTypes.TYPE_SPB    	: AwlInsn_SPB,
		AwlInsnTypes.TYPE_SPBN   	: AwlInsn_SPBN,
		AwlInsnTypes.TYPE_SPBB   	: AwlInsn_SPBB,
		AwlInsnTypes.TYPE_SPBNB  	: AwlInsn_SPBNB,
		AwlInsnTypes.TYPE_SPBI   	: AwlInsn_SPBI,
		AwlInsnTypes.TYPE_SPBIN  	: AwlInsn_SPBIN,
		AwlInsnTypes.TYPE_SPO    	: AwlInsn_SPO,
		AwlInsnTypes.TYPE_SPS    	: AwlInsn_SPS,
		AwlInsnTypes.TYPE_SPZ    	: AwlInsn_SPZ,
		AwlInsnTypes.TYPE_SPN    	: AwlInsn_SPN,
		AwlInsnTypes.TYPE_SPP    	: AwlInsn_SPP,
		AwlInsnTypes.TYPE_SPM    	: AwlInsn_SPM,
		AwlInsnTypes.TYPE_SPPZ   	: AwlInsn_SPPZ,
		AwlInsnTypes.TYPE_SPMZ   	: AwlInsn_SPMZ,
		AwlInsnTypes.TYPE_SPU    	: AwlInsn_SPU,
		AwlInsnTypes.TYPE_LOOP   	: AwlInsn_LOOP,
		AwlInsnTypes.TYPE_PL_I   	: AwlInsn_PL_I,
		AwlInsnTypes.TYPE_MI_I   	: AwlInsn_MI_I,
		AwlInsnTypes.TYPE_MU_I   	: AwlInsn_MU_I,
		AwlInsnTypes.TYPE_DI_I   	: AwlInsn_DI_I,
		AwlInsnTypes.TYPE_PL	    	: AwlInsn_PL,
		AwlInsnTypes.TYPE_PL_D   	: AwlInsn_PL_D,
		AwlInsnTypes.TYPE_MI_D   	: AwlInsn_MI_D,
		AwlInsnTypes.TYPE_MU_D   	: AwlInsn_MU_D,
		AwlInsnTypes.TYPE_DI_D   	: AwlInsn_DI_D,
		AwlInsnTypes.TYPE_MOD    	: AwlInsn_MOD,
		AwlInsnTypes.TYPE_PL_R   	: AwlInsn_PL_R,
		AwlInsnTypes.TYPE_MI_R   	: AwlInsn_MI_R,
		AwlInsnTypes.TYPE_MU_R   	: AwlInsn_MU_R,
		AwlInsnTypes.TYPE_DI_R   	: AwlInsn_DI_R,
		AwlInsnTypes.TYPE_ABS    	: AwlInsn_ABS,
		AwlInsnTypes.TYPE_SQR    	: AwlInsn_SQR,
		AwlInsnTypes.TYPE_SQRT   	: AwlInsn_SQRT,
		AwlInsnTypes.TYPE_EXP    	: AwlInsn_EXP,
		AwlInsnTypes.TYPE_LN	    	: AwlInsn_LN,
		AwlInsnTypes.TYPE_SIN    	: AwlInsn_SIN,
		AwlInsnTypes.TYPE_COS    	: AwlInsn_COS,
		AwlInsnTypes.TYPE_TAN    	: AwlInsn_TAN,
		AwlInsnTypes.TYPE_ASIN   	: AwlInsn_ASIN,
		AwlInsnTypes.TYPE_ACOS   	: AwlInsn_ACOS,
		AwlInsnTypes.TYPE_ATAN   	: AwlInsn_ATAN,
		AwlInsnTypes.TYPE_LAR1   	: AwlInsn_LAR1,
		AwlInsnTypes.TYPE_LAR2   	: AwlInsn_LAR2,
		AwlInsnTypes.TYPE_T	    	: AwlInsn_T,
		AwlInsnTypes.TYPE_TAR    	: AwlInsn_TAR,
		AwlInsnTypes.TYPE_TAR1   	: AwlInsn_TAR1,
		AwlInsnTypes.TYPE_TAR2   	: AwlInsn_TAR2,
		AwlInsnTypes.TYPE_BE	    	: AwlInsn_BE,
		AwlInsnTypes.TYPE_BEB    	: AwlInsn_BEB,
		AwlInsnTypes.TYPE_BEA    	: AwlInsn_BEA,
		AwlInsnTypes.TYPE_CALL   	: AwlInsn_CALL,
		AwlInsnTypes.TYPE_CC	    	: AwlInsn_CC,
		AwlInsnTypes.TYPE_UC	    	: AwlInsn_UC,
		AwlInsnTypes.TYPE_MCRB   	: AwlInsn_MCRB,
		AwlInsnTypes.TYPE_BMCR   	: AwlInsn_BMCR,
		AwlInsnTypes.TYPE_MCRA   	: AwlInsn_MCRA,
		AwlInsnTypes.TYPE_MCRD   	: AwlInsn_MCRD,
		AwlInsnTypes.TYPE_SSI    	: AwlInsn_SSI,
		AwlInsnTypes.TYPE_SSD    	: AwlInsn_SSD,
		AwlInsnTypes.TYPE_SLW    	: AwlInsn_SLW,
		AwlInsnTypes.TYPE_SRW    	: AwlInsn_SRW,
		AwlInsnTypes.TYPE_SLD    	: AwlInsn_SLD,
		AwlInsnTypes.TYPE_SRD    	: AwlInsn_SRD,
		AwlInsnTypes.TYPE_RLD    	: AwlInsn_RLD,
		AwlInsnTypes.TYPE_RRD    	: AwlInsn_RRD,
		AwlInsnTypes.TYPE_RLDA   	: AwlInsn_RLDA,
		AwlInsnTypes.TYPE_RRDA   	: AwlInsn_RRDA,
		AwlInsnTypes.TYPE_SI	    	: AwlInsn_SI,
		AwlInsnTypes.TYPE_SV	    	: AwlInsn_SV,
		AwlInsnTypes.TYPE_SE	    	: AwlInsn_SE,
		AwlInsnTypes.TYPE_SS	    	: AwlInsn_SS,
		AwlInsnTypes.TYPE_SA	    	: AwlInsn_SA,
		AwlInsnTypes.TYPE_UW	    	: AwlInsn_UW,
		AwlInsnTypes.TYPE_OW	    	: AwlInsn_OW,
		AwlInsnTypes.TYPE_XOW    	: AwlInsn_XOW,
		AwlInsnTypes.TYPE_UD	    	: AwlInsn_UD,
		AwlInsnTypes.TYPE_OD	    	: AwlInsn_OD,
		AwlInsnTypes.TYPE_XOD    	: AwlInsn_XOD,
		AwlInsnTypes.TYPE_TAK    	: AwlInsn_TAK,
		AwlInsnTypes.TYPE_PUSH   	: AwlInsn_PUSH,
		AwlInsnTypes.TYPE_POP    	: AwlInsn_POP,
		AwlInsnTypes.TYPE_ENT    	: AwlInsn_ENT,
		AwlInsnTypes.TYPE_LEAVE  	: AwlInsn_LEAVE,
		AwlInsnTypes.TYPE_INC    	: AwlInsn_INC,
		AwlInsnTypes.TYPE_DEC    	: AwlInsn_DEC,
		AwlInsnTypes.TYPE_INCAR1 	: AwlInsn_INCAR1,
		AwlInsnTypes.TYPE_INCAR2 	: AwlInsn_INCAR2,
		AwlInsnTypes.TYPE_BLD    	: AwlInsn_BLD,
		AwlInsnTypes.TYPE_NOP    	: AwlInsn_NOP,

		AwlInsnTypes.TYPE_ASSERT_EQ	: AwlInsn_ASSERT_EQ,
		AwlInsnTypes.TYPE_ASSERT_EQ_R	: AwlInsn_ASSERT_EQ_R,
		AwlInsnTypes.TYPE_ASSERT_NE	: AwlInsn_ASSERT_NE,
		AwlInsnTypes.TYPE_ASSERT_GT	: AwlInsn_ASSERT_GT,
		AwlInsnTypes.TYPE_ASSERT_LT	: AwlInsn_ASSERT_LT,
		AwlInsnTypes.TYPE_ASSERT_GE	: AwlInsn_ASSERT_GE,
		AwlInsnTypes.TYPE_ASSERT_LE	: AwlInsn_ASSERT_LE,
		AwlInsnTypes.TYPE_SLEEP		: AwlInsn_SLEEP,
		AwlInsnTypes.TYPE_STWRST	: AwlInsn_STWRST,
		AwlInsnTypes.TYPE_FEATURE	: AwlInsn_FEATURE,
	}

	mnemonics2nameTypeTable = {
		S7CPUConfig.MNEMONICS_EN	: AwlInsnTypes.name2type_english,
		S7CPUConfig.MNEMONICS_DE	: AwlInsnTypes.name2type_german,
	}

	@classmethod
	def name2type(cls, insnName, mnemonics):
		name2typeTable = cls.mnemonics2nameTypeTable[mnemonics]
		try:
			return name2typeTable[insnName.upper()]
		except KeyError:
			return None

	@classmethod
	def fromRawInsn(cls, cpu, rawInsn):
		mnemonics = cpu.getConf().getMnemonics()
		try:
			insnType = cls.name2type(rawInsn.getName(), mnemonics)
			if insnType is None or\
			   (insnType >= AwlInsnTypes.TYPE_EXTENDED and\
			    not cpu.extendedInsnsEnabled()):
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

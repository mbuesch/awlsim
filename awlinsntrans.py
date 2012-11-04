#
# AWL simulator - Instruction translator
# Copyright 2012 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from util import *
from awlinstructions import *
from awlparser import *


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
		AwlInsn.TYPE_EQ_R   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_NE_R   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_GT_R   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_LT_R   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_GE_R   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_LE_R   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_BTI    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_ITB    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_BTD    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_ITD    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_DTB    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_DTR    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_INVI   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_INVD   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_NEGI   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_NEGD   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_NEGR   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_TAW    	: AwlInsn_TAW,
		AwlInsn.TYPE_TAD    	: AwlInsn_TAD,
		AwlInsn.TYPE_RND    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_TRUNC  	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_RNDP   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_RNDN   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_FR	    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_L	    	: AwlInsn_L,
		AwlInsn.TYPE_LC	    	: AwlInsn_LC,
		AwlInsn.TYPE_ZV	    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_ZR	    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_AUF    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_TDB    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_SPA    	: AwlInsn_SPA,
		AwlInsn.TYPE_SPL    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_SPB    	: AwlInsn_SPB,
		AwlInsn.TYPE_SPBN   	: AwlInsn_SPBN,
		AwlInsn.TYPE_SPBB   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_SPBNB  	: AwlInsn_SPBNB,
		AwlInsn.TYPE_SPBI   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_SPBIN  	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_SPO    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_SPS    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_SPZ    	: AwlInsn_SPZ,
		AwlInsn.TYPE_SPN    	: AwlInsn_SPN,
		AwlInsn.TYPE_SPP    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_SPM    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_SPPZ   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_SPMZ   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_SPU    	: AwlInsn_NotImplemented,
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
		AwlInsn.TYPE_PL_R   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_MI_R   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_MU_R   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_DI_R   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_ABS    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_SQR    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_SQRT   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_EXP    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_LN	    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_SIN    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_COS    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_TAN    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_ASIN   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_ACOS   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_ATAN   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_LAR1   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_LAR2   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_T	    	: AwlInsn_T,
		AwlInsn.TYPE_TAR    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_TAR1   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_TAR2   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_BE	    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_BEB    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_BEA    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_CALL   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_CC	    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_UC	    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_MCRB   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_BMCR   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_MCRA   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_MCRD   	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_SSI    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_SSD    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_SLW    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_SRW    	: AwlInsn_NotImplemented,
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
		AwlInsn.TYPE_UW	    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_OW	    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_XOW    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_UD	    	: AwlInsn_UD,
		AwlInsn.TYPE_OD	    	: AwlInsn_OD,
		AwlInsn.TYPE_XOD    	: AwlInsn_XOD,
		AwlInsn.TYPE_TAK    	: AwlInsn_TAK,
		AwlInsn.TYPE_PUSH   	: AwlInsn_PUSH,
		AwlInsn.TYPE_POP    	: AwlInsn_POP,
		AwlInsn.TYPE_ENT    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_LEAVE  	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_INC    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_DEC    	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_INCAR1 	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_INCAR2 	: AwlInsn_NotImplemented,
		AwlInsn.TYPE_BLD    	: AwlInsn_BLD,
		AwlInsn.TYPE_NOP    	: AwlInsn_NOP,

		AwlInsn.TYPE_ASSERT_EQ	: AwlInsn_ASSERT_EQ,
		AwlInsn.TYPE_ASSERT_NE	: AwlInsn_ASSERT_NE,
		AwlInsn.TYPE_ASSERT_GT	: AwlInsn_ASSERT_GT,
		AwlInsn.TYPE_ASSERT_LT	: AwlInsn_ASSERT_LT,
		AwlInsn.TYPE_ASSERT_GE	: AwlInsn_ASSERT_GE,
		AwlInsn.TYPE_ASSERT_LE	: AwlInsn_ASSERT_LE,
		AwlInsn.TYPE_SLEEP	: AwlInsn_SLEEP,
	}

	@classmethod
	def fromRawInsn(cls, rawInsn):
		try:
			insnType = AwlInsn.name2type[rawInsn.getName().upper()]
			insnClass = cls.type2class[insnType]
		except KeyError as e:
			raise AwlSimError("Cannot translate instruction: '%s'" %\
				rawInsn.getName())
		return insnClass(rawInsn)

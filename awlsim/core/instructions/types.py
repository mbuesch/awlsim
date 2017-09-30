# -*- coding: utf-8 -*-
#
# AWL simulator - Instruction types
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

from awlsim.common.enumeration import *
from awlsim.common.util import *


__all__ = [
	"AwlInsnTypes",
]


class __AwlInsnTypesClass(object): #+cdef
	def __init__(self):
		EnumGen.start
		self.TYPE_U		= EnumGen.item	# U
		self.TYPE_UN		= EnumGen.item	# UN
		self.TYPE_O		= EnumGen.item	# O
		self.TYPE_ON		= EnumGen.item	# ON
		self.TYPE_X		= EnumGen.item	# X
		self.TYPE_XN		= EnumGen.item	# XN
		self.TYPE_UB		= EnumGen.item	# U(
		self.TYPE_UNB		= EnumGen.item	# UN(
		self.TYPE_OB		= EnumGen.item	# O(
		self.TYPE_ONB		= EnumGen.item	# ON(
		self.TYPE_XB		= EnumGen.item	# X(
		self.TYPE_XNB		= EnumGen.item	# XN(
		self.TYPE_BEND		= EnumGen.item	# )
		self.TYPE_ASSIGN	= EnumGen.item	# =
		self.TYPE_R		= EnumGen.item	# R
		self.TYPE_S		= EnumGen.item	# S
		self.TYPE_NOT		= EnumGen.item	# NOT
		self.TYPE_SET		= EnumGen.item	# SET
		self.TYPE_CLR		= EnumGen.item	# CLR
		self.TYPE_SAVE		= EnumGen.item	# SAVE
		self.TYPE_FN		= EnumGen.item	# FN
		self.TYPE_FP		= EnumGen.item	# FP
		self.TYPE_EQ_I		= EnumGen.item	# ==I
		self.TYPE_NE_I		= EnumGen.item	# <>I
		self.TYPE_GT_I		= EnumGen.item	# >I
		self.TYPE_LT_I		= EnumGen.item	# <I
		self.TYPE_GE_I		= EnumGen.item	# >=I
		self.TYPE_LE_I		= EnumGen.item	# <=I
		self.TYPE_EQ_D		= EnumGen.item	# ==D
		self.TYPE_NE_D		= EnumGen.item	# <>D
		self.TYPE_GT_D		= EnumGen.item	# >D
		self.TYPE_LT_D		= EnumGen.item	# <D
		self.TYPE_GE_D		= EnumGen.item	# >=D
		self.TYPE_LE_D		= EnumGen.item	# <=D
		self.TYPE_EQ_R		= EnumGen.item	# ==R
		self.TYPE_NE_R		= EnumGen.item	# <>R
		self.TYPE_GT_R		= EnumGen.item	# >R
		self.TYPE_LT_R		= EnumGen.item	# <R
		self.TYPE_GE_R		= EnumGen.item	# >=R
		self.TYPE_LE_R		= EnumGen.item	# <=R
		self.TYPE_BTI		= EnumGen.item	# BTI
		self.TYPE_ITB		= EnumGen.item	# ITB
		self.TYPE_BTD		= EnumGen.item	# BTD
		self.TYPE_ITD		= EnumGen.item	# ITD
		self.TYPE_DTB		= EnumGen.item	# DTB
		self.TYPE_DTR		= EnumGen.item	# DTR
		self.TYPE_INVI		= EnumGen.item	# INVI
		self.TYPE_INVD		= EnumGen.item	# INVD
		self.TYPE_NEGI		= EnumGen.item	# NEGI
		self.TYPE_NEGD		= EnumGen.item	# NEGD
		self.TYPE_NEGR		= EnumGen.item	# NEGR
		self.TYPE_TAW		= EnumGen.item	# TAW
		self.TYPE_TAD		= EnumGen.item	# TAD
		self.TYPE_RND		= EnumGen.item	# RND
		self.TYPE_TRUNC		= EnumGen.item	# TRUNC
		self.TYPE_RNDP		= EnumGen.item	# RND+
		self.TYPE_RNDN		= EnumGen.item	# RND-
		self.TYPE_FR		= EnumGen.item	# FR
		self.TYPE_L		= EnumGen.item	# L
		self.TYPE_LC		= EnumGen.item	# LC
		self.TYPE_ZV		= EnumGen.item	# ZV
		self.TYPE_ZR		= EnumGen.item	# ZR
		self.TYPE_AUF		= EnumGen.item	# AUF
		self.TYPE_TDB		= EnumGen.item	# TDB
		self.TYPE_SPA		= EnumGen.item	# SPA
		self.TYPE_SPL		= EnumGen.item	# SPL
		self.TYPE_SPB		= EnumGen.item	# SPB
		self.TYPE_SPBN		= EnumGen.item	# SPBN
		self.TYPE_SPBB		= EnumGen.item	# SPBB
		self.TYPE_SPBNB		= EnumGen.item	# SPBNB
		self.TYPE_SPBI		= EnumGen.item	# SPBI
		self.TYPE_SPBIN		= EnumGen.item	# SPBIN
		self.TYPE_SPO		= EnumGen.item	# SPO
		self.TYPE_SPS		= EnumGen.item	# SPS
		self.TYPE_SPZ		= EnumGen.item	# SPZ
		self.TYPE_SPN		= EnumGen.item	# SPN
		self.TYPE_SPP		= EnumGen.item	# SPP
		self.TYPE_SPM		= EnumGen.item	# SPM
		self.TYPE_SPPZ		= EnumGen.item	# SPPZ
		self.TYPE_SPMZ		= EnumGen.item	# SPMZ
		self.TYPE_SPU		= EnumGen.item	# SPU
		self.TYPE_LOOP		= EnumGen.item	# LOOP
		self.TYPE_PL_I		= EnumGen.item	# +I
		self.TYPE_MI_I		= EnumGen.item	# -I
		self.TYPE_MU_I		= EnumGen.item	# *I
		self.TYPE_DI_I		= EnumGen.item	# /I
		self.TYPE_PL		= EnumGen.item	# +
		self.TYPE_PL_D		= EnumGen.item	# +D
		self.TYPE_MI_D		= EnumGen.item	# -D
		self.TYPE_MU_D		= EnumGen.item	# *D
		self.TYPE_DI_D		= EnumGen.item	# /D
		self.TYPE_MOD		= EnumGen.item	# MOD
		self.TYPE_PL_R		= EnumGen.item	# +R
		self.TYPE_MI_R		= EnumGen.item	# -R
		self.TYPE_MU_R		= EnumGen.item	# *R
		self.TYPE_DI_R		= EnumGen.item	# /R
		self.TYPE_ABS		= EnumGen.item	# ABS
		self.TYPE_SQR		= EnumGen.item	# SQR
		self.TYPE_SQRT		= EnumGen.item	# SQRT
		self.TYPE_EXP		= EnumGen.item	# EXP
		self.TYPE_LN		= EnumGen.item	# LN
		self.TYPE_SIN		= EnumGen.item	# SIN
		self.TYPE_COS		= EnumGen.item	# COS
		self.TYPE_TAN		= EnumGen.item	# TAN
		self.TYPE_ASIN		= EnumGen.item	# ASIN
		self.TYPE_ACOS		= EnumGen.item	# ACOS
		self.TYPE_ATAN		= EnumGen.item	# ATAN
		self.TYPE_LAR1		= EnumGen.item	# LAR1
		self.TYPE_LAR2		= EnumGen.item	# LAR2
		self.TYPE_T		= EnumGen.item	# T
		self.TYPE_TAR		= EnumGen.item	# TAR
		self.TYPE_TAR1		= EnumGen.item	# TAR1
		self.TYPE_TAR2		= EnumGen.item	# TAR2
		self.TYPE_BE		= EnumGen.item	# BE
		self.TYPE_BEB		= EnumGen.item	# BEB
		self.TYPE_BEA		= EnumGen.item	# BEA
		self.TYPE_CALL		= EnumGen.item	# CALL
		self.TYPE_CC		= EnumGen.item	# CC
		self.TYPE_UC		= EnumGen.item	# UC
		self.TYPE_MCRB		= EnumGen.item	# MCR(
		self.TYPE_BMCR		= EnumGen.item	# )MCR
		self.TYPE_MCRA		= EnumGen.item	# MCRA
		self.TYPE_MCRD		= EnumGen.item	# MCRD
		self.TYPE_SSI		= EnumGen.item	# SSI
		self.TYPE_SSD		= EnumGen.item	# SSD
		self.TYPE_SLW		= EnumGen.item	# SLW
		self.TYPE_SRW		= EnumGen.item	# SRW
		self.TYPE_SLD		= EnumGen.item	# SLD
		self.TYPE_SRD		= EnumGen.item	# SRD
		self.TYPE_RLD		= EnumGen.item	# RLD
		self.TYPE_RRD		= EnumGen.item	# RRD
		self.TYPE_RLDA		= EnumGen.item	# RLDA
		self.TYPE_RRDA		= EnumGen.item	# RRDA
		self.TYPE_SI		= EnumGen.item	# SI
		self.TYPE_SV		= EnumGen.item	# SV
		self.TYPE_SE		= EnumGen.item	# SE
		self.TYPE_SS		= EnumGen.item	# SS
		self.TYPE_SA		= EnumGen.item	# SA
		self.TYPE_UW		= EnumGen.item	# UW
		self.TYPE_OW		= EnumGen.item	# OW
		self.TYPE_XOW		= EnumGen.item	# XOW
		self.TYPE_UD		= EnumGen.item	# UD
		self.TYPE_OD		= EnumGen.item	# OD
		self.TYPE_XOD		= EnumGen.item	# XOD
		self.TYPE_TAK		= EnumGen.item	# TAK
		self.TYPE_PUSH		= EnumGen.item	# PUSH
		self.TYPE_POP		= EnumGen.item	# POP
		self.TYPE_ENT		= EnumGen.item	# ENT
		self.TYPE_LEAVE		= EnumGen.item	# LEAVE
		self.TYPE_INC		= EnumGen.item	# INC
		self.TYPE_DEC		= EnumGen.item	# DEC
		self.TYPE_INCAR1	= EnumGen.item	# +AR1
		self.TYPE_INCAR2	= EnumGen.item	# +AR2
		self.TYPE_BLD		= EnumGen.item	# BLD
		self.TYPE_NOP		= EnumGen.item	# NOP
		# Special instructions for debugging of the simulator
		self.TYPE_EXTENDED	= EnumGen.itemNoInc
		self.TYPE_ASSERT_EQ	= EnumGen.item	# __ASSERT==
		self.TYPE_ASSERT_EQ_R	= EnumGen.item 	# __ASSERT==R
		self.TYPE_ASSERT_NE	= EnumGen.item 	# __ASSERT<>
		self.TYPE_ASSERT_GT	= EnumGen.item 	# __ASSERT>
		self.TYPE_ASSERT_LT	= EnumGen.item 	# __ASSERT<
		self.TYPE_ASSERT_GE	= EnumGen.item 	# __ASSERT>=
		self.TYPE_ASSERT_LE	= EnumGen.item 	# __ASSERT<=
		self.TYPE_SLEEP		= EnumGen.item 	# __SLEEP
		self.TYPE_STWRST	= EnumGen.item 	# __STWRST
		self.TYPE_FEATURE	= EnumGen.item 	# __FEATURE
		# Special instructions for internal usage
		self.TYPE_GENERIC_CALL	= EnumGen.item	# No mnemonic
		self.TYPE_INLINE_AWL	= EnumGen.item	# No mnemonic
		EnumGen.end

		self.name2type_german = {
			"U"	: self.TYPE_U,
			"UN"	: self.TYPE_UN,
			"O"	: self.TYPE_O,
			"ON"	: self.TYPE_ON,
			"X"	: self.TYPE_X,
			"XN"	: self.TYPE_XN,
			"U("	: self.TYPE_UB,
			"UN("	: self.TYPE_UNB,
			"O("	: self.TYPE_OB,
			"ON("	: self.TYPE_ONB,
			"X("	: self.TYPE_XB,
			"XN("	: self.TYPE_XNB,
			")"	: self.TYPE_BEND,
			"="	: self.TYPE_ASSIGN,
			"R"	: self.TYPE_R,
			"S"	: self.TYPE_S,
			"NOT"	: self.TYPE_NOT,
			"SET"	: self.TYPE_SET,
			"CLR"	: self.TYPE_CLR,
			"SAVE"	: self.TYPE_SAVE,
			"FN"	: self.TYPE_FN,
			"FP"	: self.TYPE_FP,
			"==I"	: self.TYPE_EQ_I,
			"<>I"	: self.TYPE_NE_I,
			">I"	: self.TYPE_GT_I,
			"<I"	: self.TYPE_LT_I,
			">=I"	: self.TYPE_GE_I,
			"<=I"	: self.TYPE_LE_I,
			"==D"	: self.TYPE_EQ_D,
			"<>D"	: self.TYPE_NE_D,
			">D"	: self.TYPE_GT_D,
			"<D"	: self.TYPE_LT_D,
			">=D"	: self.TYPE_GE_D,
			"<=D"	: self.TYPE_LE_D,
			"==R"	: self.TYPE_EQ_R,
			"<>R"	: self.TYPE_NE_R,
			">R"	: self.TYPE_GT_R,
			"<R"	: self.TYPE_LT_R,
			">=R"	: self.TYPE_GE_R,
			"<=R"	: self.TYPE_LE_R,
			"BTI"	: self.TYPE_BTI,
			"ITB"	: self.TYPE_ITB,
			"BTD"	: self.TYPE_BTD,
			"ITD"	: self.TYPE_ITD,
			"DTB"	: self.TYPE_DTB,
			"DTR"	: self.TYPE_DTR,
			"INVI"	: self.TYPE_INVI,
			"INVD"	: self.TYPE_INVD,
			"NEGI"	: self.TYPE_NEGI,
			"NEGD"	: self.TYPE_NEGD,
			"NEGR"	: self.TYPE_NEGR,
			"TAW"	: self.TYPE_TAW,
			"TAD"	: self.TYPE_TAD,
			"RND"	: self.TYPE_RND,
			"TRUNC"	: self.TYPE_TRUNC,
			"RND+"	: self.TYPE_RNDP,
			"RND-"	: self.TYPE_RNDN,
			"FR"	: self.TYPE_FR,
			"L"	: self.TYPE_L,
			"LC"	: self.TYPE_LC,
			"ZV"	: self.TYPE_ZV,
			"ZR"	: self.TYPE_ZR,
			"AUF"	: self.TYPE_AUF,
			"TDB"	: self.TYPE_TDB,
			"SPA"	: self.TYPE_SPA,
			"SPL"	: self.TYPE_SPL,
			"SPB"	: self.TYPE_SPB,
			"SPBN"	: self.TYPE_SPBN,
			"SPBB"	: self.TYPE_SPBB,
			"SPBNB"	: self.TYPE_SPBNB,
			"SPBI"	: self.TYPE_SPBI,
			"SPBIN"	: self.TYPE_SPBIN,
			"SPO"	: self.TYPE_SPO,
			"SPS"	: self.TYPE_SPS,
			"SPZ"	: self.TYPE_SPZ,
			"SPN"	: self.TYPE_SPN,
			"SPP"	: self.TYPE_SPP,
			"SPM"	: self.TYPE_SPM,
			"SPPZ"	: self.TYPE_SPPZ,
			"SPMZ"	: self.TYPE_SPMZ,
			"SPU"	: self.TYPE_SPU,
			"LOOP"	: self.TYPE_LOOP,
			"+I"	: self.TYPE_PL_I,
			"-I"	: self.TYPE_MI_I,
			"*I"	: self.TYPE_MU_I,
			"/I"	: self.TYPE_DI_I,
			"+"	: self.TYPE_PL,
			"+D"	: self.TYPE_PL_D,
			"-D"	: self.TYPE_MI_D,
			"*D"	: self.TYPE_MU_D,
			"/D"	: self.TYPE_DI_D,
			"MOD"	: self.TYPE_MOD,
			"+R"	: self.TYPE_PL_R,
			"-R"	: self.TYPE_MI_R,
			"*R"	: self.TYPE_MU_R,
			"/R"	: self.TYPE_DI_R,
			"ABS"	: self.TYPE_ABS,
			"SQR"	: self.TYPE_SQR,
			"SQRT"	: self.TYPE_SQRT,
			"EXP"	: self.TYPE_EXP,
			"LN"	: self.TYPE_LN,
			"SIN"	: self.TYPE_SIN,
			"COS"	: self.TYPE_COS,
			"TAN"	: self.TYPE_TAN,
			"ASIN"	: self.TYPE_ASIN,
			"ACOS"	: self.TYPE_ACOS,
			"ATAN"	: self.TYPE_ATAN,
			"LAR1"	: self.TYPE_LAR1,
			"LAR2"	: self.TYPE_LAR2,
			"T"	: self.TYPE_T,
			"TAR"	: self.TYPE_TAR,
			"TAR1"	: self.TYPE_TAR1,
			"TAR2"	: self.TYPE_TAR2,
			"BE"	: self.TYPE_BE,
			"BEB"	: self.TYPE_BEB,
			"BEA"	: self.TYPE_BEA,
			"CALL"	: self.TYPE_CALL,
			"CC"	: self.TYPE_CC,
			"UC"	: self.TYPE_UC,
			"MCR("	: self.TYPE_MCRB,
			")MCR"	: self.TYPE_BMCR,
			"MCRA"	: self.TYPE_MCRA,
			"MCRD"	: self.TYPE_MCRD,
			"SSI"	: self.TYPE_SSI,
			"SSD"	: self.TYPE_SSD,
			"SLW"	: self.TYPE_SLW,
			"SRW"	: self.TYPE_SRW,
			"SLD"	: self.TYPE_SLD,
			"SRD"	: self.TYPE_SRD,
			"RLD"	: self.TYPE_RLD,
			"RRD"	: self.TYPE_RRD,
			"RLDA"	: self.TYPE_RLDA,
			"RRDA"	: self.TYPE_RRDA,
			"SI"	: self.TYPE_SI,
			"SV"	: self.TYPE_SV,
			"SE"	: self.TYPE_SE,
			"SS"	: self.TYPE_SS,
			"SA"	: self.TYPE_SA,
			"UW"	: self.TYPE_UW,
			"OW"	: self.TYPE_OW,
			"XOW"	: self.TYPE_XOW,
			"UD"	: self.TYPE_UD,
			"OD"	: self.TYPE_OD,
			"XOD"	: self.TYPE_XOD,
			"TAK"	: self.TYPE_TAK,
			"PUSH"	: self.TYPE_PUSH,
			"POP"	: self.TYPE_POP,
			"ENT"	: self.TYPE_ENT,
			"LEAVE"	: self.TYPE_LEAVE,
			"INC"	: self.TYPE_INC,
			"DEC"	: self.TYPE_DEC,
			"+AR1"	: self.TYPE_INCAR1,
			"+AR2"	: self.TYPE_INCAR2,
			"BLD"	: self.TYPE_BLD,
			"NOP"	: self.TYPE_NOP,

			"__ASSERT=="		: self.TYPE_ASSERT_EQ,
			"__ASSERT==R"		: self.TYPE_ASSERT_EQ_R,
			"__ASSERT<>"		: self.TYPE_ASSERT_NE,
			"__ASSERT>"		: self.TYPE_ASSERT_GT,
			"__ASSERT<"		: self.TYPE_ASSERT_LT,
			"__ASSERT>="		: self.TYPE_ASSERT_GE,
			"__ASSERT<="		: self.TYPE_ASSERT_LE,
			"__SLEEP"		: self.TYPE_SLEEP,
			"__STWRST"		: self.TYPE_STWRST,
			"__FEATURE"		: self.TYPE_FEATURE,

			"__GENERIC_CALL__"	: self.TYPE_GENERIC_CALL,
			"__INLINE_AWL__"	: self.TYPE_INLINE_AWL,
		}
		self.type2name_german = pivotDict(self.name2type_german)

		self.english2german = {
			"OPN"	: "AUF",
			"BEU"	: "BEA",
			"BEC"	: "BEB",
			"SF"	: "SA",
			"SD"	: "SE",
			"SP"	: "SI",
			"JU"	: "SPA",
			"JC"	: "SPB",
			"JCB"	: "SPBB",
			"JBI"	: "SPBI",
			"JNBI"	: "SPBIN",
			"JCN"	: "SPBN",
			"JNB"	: "SPBNB",
			"JL"	: "SPL",
			"JM"	: "SPM",
			"JMZ"	: "SPMZ",
			"JN"	: "SPN",
			"JO"	: "SPO",
			"JP"	: "SPP",
			"JPZ"	: "SPPZ",
			"JOS"	: "SPS",
			"JUO"	: "SPU",
			"JZ"	: "SPZ",
			"SE"	: "SV",
			"CAD"	: "TAD",
			"CAR"	: "TAR",
			"CAW"	: "TAW",
			"CDB"	: "TDB",
			"A"	: "U",
			"A("	: "U(",
			"AD"	: "UD",
			"AN"	: "UN",
			"AN("	: "UN(",
			"AW"	: "UW",
			"CD"	: "ZR",
			"CU"	: "ZV",
		}
		self.german2english = pivotDict(self.english2german)

		# Create a name2type dict for english mnemonics using the translation dict.
		self.name2type_english = {}
		for _name, _insnType in dictItems(self.name2type_german):
			with contextlib.suppress(KeyError):
				_name = self.german2english[_name]
			self.name2type_english[_name] = _insnType
		self.type2name_english = pivotDict(self.name2type_english)

AwlInsnTypes = __AwlInsnTypesClass() #+cdef-public-__AwlInsnTypesClass

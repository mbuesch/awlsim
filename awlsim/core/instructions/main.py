# -*- coding: utf-8 -*-
#
# AWL simulator - instructions
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

from awlsim.core.util import *
from awlsim.core.operators import *
from awlsim.core.optrans import *
from awlsim.core.parser import *
from awlsim.core.datatypehelpers import *


class AwlInsn(object):
	EnumGen.start
	TYPE_INVALID		= EnumGen.item
	TYPE_U			= EnumGen.item	# U
	TYPE_UN			= EnumGen.item	# UN
	TYPE_O			= EnumGen.item	# O
	TYPE_ON			= EnumGen.item	# ON
	TYPE_X			= EnumGen.item	# X
	TYPE_XN			= EnumGen.item	# XN
	TYPE_UB			= EnumGen.item	# U(
	TYPE_UNB		= EnumGen.item	# UN(
	TYPE_OB			= EnumGen.item	# O(
	TYPE_ONB		= EnumGen.item	# ON(
	TYPE_XB			= EnumGen.item	# X(
	TYPE_XNB		= EnumGen.item	# XN(
	TYPE_BEND		= EnumGen.item	# )
	TYPE_ASSIGN		= EnumGen.item	# =
	TYPE_R			= EnumGen.item	# R
	TYPE_S			= EnumGen.item	# S
	TYPE_NOT		= EnumGen.item	# NOT
	TYPE_SET		= EnumGen.item	# SET
	TYPE_CLR		= EnumGen.item	# CLR
	TYPE_SAVE		= EnumGen.item	# SAVE
	TYPE_FN			= EnumGen.item	# FN
	TYPE_FP			= EnumGen.item	# FP
	TYPE_EQ_I		= EnumGen.item	# ==I
	TYPE_NE_I		= EnumGen.item	# <>I
	TYPE_GT_I		= EnumGen.item	# >I
	TYPE_LT_I		= EnumGen.item	# <I
	TYPE_GE_I		= EnumGen.item	# >=I
	TYPE_LE_I		= EnumGen.item	# <=I
	TYPE_EQ_D		= EnumGen.item	# ==D
	TYPE_NE_D		= EnumGen.item	# <>D
	TYPE_GT_D		= EnumGen.item	# >D
	TYPE_LT_D		= EnumGen.item	# <D
	TYPE_GE_D		= EnumGen.item	# >=D
	TYPE_LE_D		= EnumGen.item	# <=D
	TYPE_EQ_R		= EnumGen.item	# ==R
	TYPE_NE_R		= EnumGen.item	# <>R
	TYPE_GT_R		= EnumGen.item	# >R
	TYPE_LT_R		= EnumGen.item	# <R
	TYPE_GE_R		= EnumGen.item	# >=R
	TYPE_LE_R		= EnumGen.item	# <=R
	TYPE_BTI		= EnumGen.item	# BTI
	TYPE_ITB		= EnumGen.item	# ITB
	TYPE_BTD		= EnumGen.item	# BTD
	TYPE_ITD		= EnumGen.item	# ITD
	TYPE_DTB		= EnumGen.item	# DTB
	TYPE_DTR		= EnumGen.item	# DTR
	TYPE_INVI		= EnumGen.item	# INVI
	TYPE_INVD		= EnumGen.item	# INVD
	TYPE_NEGI		= EnumGen.item	# NEGI
	TYPE_NEGD		= EnumGen.item	# NEGD
	TYPE_NEGR		= EnumGen.item	# NEGR
	TYPE_TAW		= EnumGen.item	# TAW
	TYPE_TAD		= EnumGen.item	# TAD
	TYPE_RND		= EnumGen.item	# RND
	TYPE_TRUNC		= EnumGen.item	# TRUNC
	TYPE_RNDP		= EnumGen.item	# RND+
	TYPE_RNDN		= EnumGen.item	# RND-
	TYPE_FR			= EnumGen.item	# FR
	TYPE_L			= EnumGen.item	# L
	TYPE_LC			= EnumGen.item	# LC
	TYPE_ZV			= EnumGen.item	# ZV
	TYPE_ZR			= EnumGen.item	# ZR
	TYPE_AUF		= EnumGen.item	# AUF
	TYPE_TDB		= EnumGen.item	# TDB
	TYPE_SPA		= EnumGen.item	# SPA
	TYPE_SPL		= EnumGen.item	# SPL
	TYPE_SPB		= EnumGen.item	# SPB
	TYPE_SPBN		= EnumGen.item	# SPBN
	TYPE_SPBB		= EnumGen.item	# SPBB
	TYPE_SPBNB		= EnumGen.item	# SPBNB
	TYPE_SPBI		= EnumGen.item	# SPBI
	TYPE_SPBIN		= EnumGen.item	# SPBIN
	TYPE_SPO		= EnumGen.item	# SPO
	TYPE_SPS		= EnumGen.item	# SPS
	TYPE_SPZ		= EnumGen.item	# SPZ
	TYPE_SPN		= EnumGen.item	# SPN
	TYPE_SPP		= EnumGen.item	# SPP
	TYPE_SPM		= EnumGen.item	# SPM
	TYPE_SPPZ		= EnumGen.item	# SPPZ
	TYPE_SPMZ		= EnumGen.item	# SPMZ
	TYPE_SPU		= EnumGen.item	# SPU
	TYPE_LOOP		= EnumGen.item	# LOOP
	TYPE_PL_I		= EnumGen.item	# +I
	TYPE_MI_I		= EnumGen.item	# -I
	TYPE_MU_I		= EnumGen.item	# *I
	TYPE_DI_I		= EnumGen.item	# /I
	TYPE_PL			= EnumGen.item	# +
	TYPE_PL_D		= EnumGen.item	# +D
	TYPE_MI_D		= EnumGen.item	# -D
	TYPE_MU_D		= EnumGen.item	# *D
	TYPE_DI_D		= EnumGen.item	# /D
	TYPE_MOD		= EnumGen.item	# MOD
	TYPE_PL_R		= EnumGen.item	# +R
	TYPE_MI_R		= EnumGen.item	# -R
	TYPE_MU_R		= EnumGen.item	# *R
	TYPE_DI_R		= EnumGen.item	# /R
	TYPE_ABS		= EnumGen.item	# ABS
	TYPE_SQR		= EnumGen.item	# SQR
	TYPE_SQRT		= EnumGen.item	# SQRT
	TYPE_EXP		= EnumGen.item	# EXP
	TYPE_LN			= EnumGen.item	# LN
	TYPE_SIN		= EnumGen.item	# SIN
	TYPE_COS		= EnumGen.item	# COS
	TYPE_TAN		= EnumGen.item	# TAN
	TYPE_ASIN		= EnumGen.item	# ASIN
	TYPE_ACOS		= EnumGen.item	# ACOS
	TYPE_ATAN		= EnumGen.item	# ATAN
	TYPE_LAR1		= EnumGen.item	# LAR1
	TYPE_LAR2		= EnumGen.item	# LAR2
	TYPE_T			= EnumGen.item	# T
	TYPE_TAR		= EnumGen.item	# TAR
	TYPE_TAR1		= EnumGen.item	# TAR1
	TYPE_TAR2		= EnumGen.item	# TAR2
	TYPE_BE			= EnumGen.item	# BE
	TYPE_BEB		= EnumGen.item	# BEB
	TYPE_BEA		= EnumGen.item	# BEA
	TYPE_CALL		= EnumGen.item	# CALL
	TYPE_CC			= EnumGen.item	# CC
	TYPE_UC			= EnumGen.item	# UC
	TYPE_MCRB		= EnumGen.item	# MCR(
	TYPE_BMCR		= EnumGen.item	# )MCR
	TYPE_MCRA		= EnumGen.item	# MCRA
	TYPE_MCRD		= EnumGen.item	# MCRD
	TYPE_SSI		= EnumGen.item	# SSI
	TYPE_SSD		= EnumGen.item	# SSD
	TYPE_SLW		= EnumGen.item	# SLW
	TYPE_SRW		= EnumGen.item	# SRW
	TYPE_SLD		= EnumGen.item	# SLD
	TYPE_SRD		= EnumGen.item	# SRD
	TYPE_RLD		= EnumGen.item	# RLD
	TYPE_RRD		= EnumGen.item	# RRD
	TYPE_RLDA		= EnumGen.item	# RLDA
	TYPE_RRDA		= EnumGen.item	# RRDA
	TYPE_SI			= EnumGen.item	# SI
	TYPE_SV			= EnumGen.item	# SV
	TYPE_SE			= EnumGen.item	# SE
	TYPE_SS			= EnumGen.item	# SS
	TYPE_SA			= EnumGen.item	# SA
	TYPE_UW			= EnumGen.item	# UW
	TYPE_OW			= EnumGen.item	# OW
	TYPE_XOW		= EnumGen.item	# XOW
	TYPE_UD			= EnumGen.item	# UD
	TYPE_OD			= EnumGen.item	# OD
	TYPE_XOD		= EnumGen.item	# XOD
	TYPE_TAK		= EnumGen.item	# TAK
	TYPE_PUSH		= EnumGen.item	# PUSH
	TYPE_POP		= EnumGen.item	# POP
	TYPE_ENT		= EnumGen.item	# ENT
	TYPE_LEAVE		= EnumGen.item	# LEAVE
	TYPE_INC		= EnumGen.item	# INC
	TYPE_DEC		= EnumGen.item	# DEC
	TYPE_INCAR1		= EnumGen.item	# +AR1
	TYPE_INCAR2		= EnumGen.item	# +AR2
	TYPE_BLD		= EnumGen.item	# BLD
	TYPE_NOP		= EnumGen.item	# NOP
	# Special instructions for debugging of the simulator
	TYPE_EXTENDED		= EnumGen.itemNoInc
	TYPE_ASSERT_EQ		= EnumGen.item	# __ASSERT==
	TYPE_ASSERT_EQ_R	= EnumGen.item 	# __ASSERT==R
	TYPE_ASSERT_NE		= EnumGen.item 	# __ASSERT<>
	TYPE_ASSERT_GT		= EnumGen.item 	# __ASSERT>
	TYPE_ASSERT_LT		= EnumGen.item 	# __ASSERT<
	TYPE_ASSERT_GE		= EnumGen.item 	# __ASSERT>=
	TYPE_ASSERT_LE		= EnumGen.item 	# __ASSERT<=
	TYPE_SLEEP		= EnumGen.item 	# __SLEEP
	TYPE_STWRST		= EnumGen.item 	# __STWRST
	TYPE_FEATURE		= EnumGen.item 	# __FEATURE
	# Special instructions for internal usage
	TYPE_GENERIC_CALL	= EnumGen.item	# No mnemonic
	EnumGen.end

	name2type_german = {
		"U"	: TYPE_U,
		"UN"	: TYPE_UN,
		"O"	: TYPE_O,
		"ON"	: TYPE_ON,
		"X"	: TYPE_X,
		"XN"	: TYPE_XN,
		"U("	: TYPE_UB,
		"UN("	: TYPE_UNB,
		"O("	: TYPE_OB,
		"ON("	: TYPE_ONB,
		"X("	: TYPE_XB,
		"XN("	: TYPE_XNB,
		")"	: TYPE_BEND,
		"="	: TYPE_ASSIGN,
		"R"	: TYPE_R,
		"S"	: TYPE_S,
		"NOT"	: TYPE_NOT,
		"SET"	: TYPE_SET,
		"CLR"	: TYPE_CLR,
		"SAVE"	: TYPE_SAVE,
		"FN"	: TYPE_FN,
		"FP"	: TYPE_FP,
		"==I"	: TYPE_EQ_I,
		"<>I"	: TYPE_NE_I,
		">I"	: TYPE_GT_I,
		"<I"	: TYPE_LT_I,
		">=I"	: TYPE_GE_I,
		"<=I"	: TYPE_LE_I,
		"==D"	: TYPE_EQ_D,
		"<>D"	: TYPE_NE_D,
		">D"	: TYPE_GT_D,
		"<D"	: TYPE_LT_D,
		">=D"	: TYPE_GE_D,
		"<=D"	: TYPE_LE_D,
		"==R"	: TYPE_EQ_R,
		"<>R"	: TYPE_NE_R,
		">R"	: TYPE_GT_R,
		"<R"	: TYPE_LT_R,
		">=R"	: TYPE_GE_R,
		"<=R"	: TYPE_LE_R,
		"BTI"	: TYPE_BTI,
		"ITB"	: TYPE_ITB,
		"BTD"	: TYPE_BTD,
		"ITD"	: TYPE_ITD,
		"DTB"	: TYPE_DTB,
		"DTR"	: TYPE_DTR,
		"INVI"	: TYPE_INVI,
		"INVD"	: TYPE_INVD,
		"NEGI"	: TYPE_NEGI,
		"NEGD"	: TYPE_NEGD,
		"NEGR"	: TYPE_NEGR,
		"TAW"	: TYPE_TAW,
		"TAD"	: TYPE_TAD,
		"RND"	: TYPE_RND,
		"TRUNC"	: TYPE_TRUNC,
		"RND+"	: TYPE_RNDP,
		"RND-"	: TYPE_RNDN,
		"FR"	: TYPE_FR,
		"L"	: TYPE_L,
		"LC"	: TYPE_LC,
		"ZV"	: TYPE_ZV,
		"ZR"	: TYPE_ZR,
		"AUF"	: TYPE_AUF,
		"TDB"	: TYPE_TDB,
		"SPA"	: TYPE_SPA,
		"SPL"	: TYPE_SPL,
		"SPB"	: TYPE_SPB,
		"SPBN"	: TYPE_SPBN,
		"SPBB"	: TYPE_SPBB,
		"SPBNB"	: TYPE_SPBNB,
		"SPBI"	: TYPE_SPBI,
		"SPBIN"	: TYPE_SPBIN,
		"SPO"	: TYPE_SPO,
		"SPS"	: TYPE_SPS,
		"SPZ"	: TYPE_SPZ,
		"SPN"	: TYPE_SPN,
		"SPP"	: TYPE_SPP,
		"SPM"	: TYPE_SPM,
		"SPPZ"	: TYPE_SPPZ,
		"SPMZ"	: TYPE_SPMZ,
		"SPU"	: TYPE_SPU,
		"LOOP"	: TYPE_LOOP,
		"+I"	: TYPE_PL_I,
		"-I"	: TYPE_MI_I,
		"*I"	: TYPE_MU_I,
		"/I"	: TYPE_DI_I,
		"+"	: TYPE_PL,
		"+D"	: TYPE_PL_D,
		"-D"	: TYPE_MI_D,
		"*D"	: TYPE_MU_D,
		"/D"	: TYPE_DI_D,
		"MOD"	: TYPE_MOD,
		"+R"	: TYPE_PL_R,
		"-R"	: TYPE_MI_R,
		"*R"	: TYPE_MU_R,
		"/R"	: TYPE_DI_R,
		"ABS"	: TYPE_ABS,
		"SQR"	: TYPE_SQR,
		"SQRT"	: TYPE_SQRT,
		"EXP"	: TYPE_EXP,
		"LN"	: TYPE_LN,
		"SIN"	: TYPE_SIN,
		"COS"	: TYPE_COS,
		"TAN"	: TYPE_TAN,
		"ASIN"	: TYPE_ASIN,
		"ACOS"	: TYPE_ACOS,
		"ATAN"	: TYPE_ATAN,
		"LAR1"	: TYPE_LAR1,
		"LAR2"	: TYPE_LAR2,
		"T"	: TYPE_T,
		"TAR"	: TYPE_TAR,
		"TAR1"	: TYPE_TAR1,
		"TAR2"	: TYPE_TAR2,
		"BE"	: TYPE_BE,
		"BEB"	: TYPE_BEB,
		"BEA"	: TYPE_BEA,
		"CALL"	: TYPE_CALL,
		"CC"	: TYPE_CC,
		"UC"	: TYPE_UC,
		"MCR("	: TYPE_MCRB,
		")MCR"	: TYPE_BMCR,
		"MCRA"	: TYPE_MCRA,
		"MCRD"	: TYPE_MCRD,
		"SSI"	: TYPE_SSI,
		"SSD"	: TYPE_SSD,
		"SLW"	: TYPE_SLW,
		"SRW"	: TYPE_SRW,
		"SLD"	: TYPE_SLD,
		"SRD"	: TYPE_SRD,
		"RLD"	: TYPE_RLD,
		"RRD"	: TYPE_RRD,
		"RLDA"	: TYPE_RLDA,
		"RRDA"	: TYPE_RRDA,
		"SI"	: TYPE_SI,
		"SV"	: TYPE_SV,
		"SE"	: TYPE_SE,
		"SS"	: TYPE_SS,
		"SA"	: TYPE_SA,
		"UW"	: TYPE_UW,
		"OW"	: TYPE_OW,
		"XOW"	: TYPE_XOW,
		"UD"	: TYPE_UD,
		"OD"	: TYPE_OD,
		"XOD"	: TYPE_XOD,
		"TAK"	: TYPE_TAK,
		"PUSH"	: TYPE_PUSH,
		"POP"	: TYPE_POP,
		"ENT"	: TYPE_ENT,
		"LEAVE"	: TYPE_LEAVE,
		"INC"	: TYPE_INC,
		"DEC"	: TYPE_DEC,
		"+AR1"	: TYPE_INCAR1,
		"+AR2"	: TYPE_INCAR2,
		"BLD"	: TYPE_BLD,
		"NOP"	: TYPE_NOP,

		"__ASSERT=="		: TYPE_ASSERT_EQ,
		"__ASSERT==R"		: TYPE_ASSERT_EQ_R,
		"__ASSERT<>"		: TYPE_ASSERT_NE,
		"__ASSERT>"		: TYPE_ASSERT_GT,
		"__ASSERT<"		: TYPE_ASSERT_LT,
		"__ASSERT>="		: TYPE_ASSERT_GE,
		"__ASSERT<="		: TYPE_ASSERT_LE,
		"__SLEEP"		: TYPE_SLEEP,
		"__STWRST"		: TYPE_STWRST,
		"__FEATURE"		: TYPE_FEATURE,
		"__GENERIC_CALL__"	: TYPE_GENERIC_CALL,
	}
	type2name_german = pivotDict(name2type_german)

	english2german = {
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
	german2english = pivotDict(english2german)
	# Sanity check of english2german table
	for __englishName, __germanName in english2german.items():
		assert(__germanName in name2type_german)

	# Create a name2type dict for english mnemonics using the translation dict.
	name2type_english = {}
	for name, type in name2type_german.items():
		try:
			name = german2english[name]
		except KeyError:
			pass
		name2type_english[name] = type
	type2name_english = pivotDict(name2type_english)

	def __init__(self, cpu, type, rawInsn):
		self.type = type
		self.rawInsn = rawInsn
		self.cpu = cpu
		self.ip = None
		self.ops = []		# Operators
		self.params = []	# Parameter assignments (for CALL)

		if rawInsn:
			opTrans = AwlOpTranslator(self)
			opTrans.translateFromRawInsn(rawInsn)

	def staticSanityChecks(self):
		"Run static sanity checks"
		pass # Default none

	def assertOpCount(self, counts):
		counts = toList(counts)
		if len(self.ops) not in counts:
			raise AwlSimError("Invalid number of operators. "
				"Expected %s." % listToHumanStr(counts),
				insn=self)

	def getRawInsn(self):
		return self.rawInsn

	def getIP(self):
		return self.ip

	def setIP(self, newIp):
		self.ip = newIp

	def getCpu(self):
		return self.cpu

	def getLineNr(self):
		if not self.rawInsn:
			return -1
		return self.rawInsn.getLineNr()

	def run(self):
		"Simulate the instruction. Override this method."
		pass

	def __repr__(self):
		ret = []
		type2name = AwlInsn.type2name_english
		if self.cpu and\
		   self.cpu.getSpecs().getMnemonics() == S7CPUSpecs.MNEMONICS_DE:
			type2name = AwlInsn.type2name_german
		try:
			name = type2name[self.type]
		except KeyError:
			name = "<unknown type %d>" % self.type
		ret.append(name)
		if self.ops:
			ret.append(" ")
			ret.append(", ".join(str(op) for op in self.ops))
		if self.params:
			ret.append(" ( ")
			ret.append(", ".join(str(param) for param in self.params))
			ret.append(" )")
		return "".join(ret)

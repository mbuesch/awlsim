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

import math

from awlsim.util import *
from awlsim.operators import *
from awlsim.optrans import *
from awlsim.parser import *
from awlsim.datatypehelpers import *


class AwlInsn(object):
	enum.start
	TYPE_INVALID		= enum.item
	TYPE_U			= enum.item	# U
	TYPE_UN			= enum.item	# UN
	TYPE_O			= enum.item	# O
	TYPE_ON			= enum.item	# ON
	TYPE_X			= enum.item	# X
	TYPE_XN			= enum.item	# XN
	TYPE_UB			= enum.item	# U(
	TYPE_UNB		= enum.item	# UN(
	TYPE_OB			= enum.item	# O(
	TYPE_ONB		= enum.item	# ON(
	TYPE_XB			= enum.item	# X(
	TYPE_XNB		= enum.item	# XN(
	TYPE_BEND		= enum.item	# )
	TYPE_ASSIGN		= enum.item	# =
	TYPE_R			= enum.item	# R
	TYPE_S			= enum.item	# S
	TYPE_NOT		= enum.item	# NOT
	TYPE_SET		= enum.item	# SET
	TYPE_CLR		= enum.item	# CLR
	TYPE_SAVE		= enum.item	# SAVE
	TYPE_FN			= enum.item	# FN
	TYPE_FP			= enum.item	# FP
	TYPE_EQ_I		= enum.item	# ==I
	TYPE_NE_I		= enum.item	# <>I
	TYPE_GT_I		= enum.item	# >I
	TYPE_LT_I		= enum.item	# <I
	TYPE_GE_I		= enum.item	# >=I
	TYPE_LE_I		= enum.item	# <=I
	TYPE_EQ_D		= enum.item	# ==D
	TYPE_NE_D		= enum.item	# <>D
	TYPE_GT_D		= enum.item	# >D
	TYPE_LT_D		= enum.item	# <D
	TYPE_GE_D		= enum.item	# >=D
	TYPE_LE_D		= enum.item	# <=D
	TYPE_EQ_R		= enum.item	# ==R
	TYPE_NE_R		= enum.item	# <>R
	TYPE_GT_R		= enum.item	# >R
	TYPE_LT_R		= enum.item	# <R
	TYPE_GE_R		= enum.item	# >=R
	TYPE_LE_R		= enum.item	# <=R
	TYPE_BTI		= enum.item	# BTI
	TYPE_ITB		= enum.item	# ITB
	TYPE_BTD		= enum.item	# BTD
	TYPE_ITD		= enum.item	# ITD
	TYPE_DTB		= enum.item	# DTB
	TYPE_DTR		= enum.item	# DTR
	TYPE_INVI		= enum.item	# INVI
	TYPE_INVD		= enum.item	# INVD
	TYPE_NEGI		= enum.item	# NEGI
	TYPE_NEGD		= enum.item	# NEGD
	TYPE_NEGR		= enum.item	# NEGR
	TYPE_TAW		= enum.item	# TAW
	TYPE_TAD		= enum.item	# TAD
	TYPE_RND		= enum.item	# RND
	TYPE_TRUNC		= enum.item	# TRUNC
	TYPE_RNDP		= enum.item	# RND+
	TYPE_RNDN		= enum.item	# RND-
	TYPE_FR			= enum.item	# FR
	TYPE_L			= enum.item	# L
	TYPE_LC			= enum.item	# LC
	TYPE_ZV			= enum.item	# ZV
	TYPE_ZR			= enum.item	# ZR
	TYPE_AUF		= enum.item	# AUF
	TYPE_TDB		= enum.item	# TDB
	TYPE_SPA		= enum.item	# SPA
	TYPE_SPL		= enum.item	# SPL
	TYPE_SPB		= enum.item	# SPB
	TYPE_SPBN		= enum.item	# SPBN
	TYPE_SPBB		= enum.item	# SPBB
	TYPE_SPBNB		= enum.item	# SPBNB
	TYPE_SPBI		= enum.item	# SPBI
	TYPE_SPBIN		= enum.item	# SPBIN
	TYPE_SPO		= enum.item	# SPO
	TYPE_SPS		= enum.item	# SPS
	TYPE_SPZ		= enum.item	# SPZ
	TYPE_SPN		= enum.item	# SPN
	TYPE_SPP		= enum.item	# SPP
	TYPE_SPM		= enum.item	# SPM
	TYPE_SPPZ		= enum.item	# SPPZ
	TYPE_SPMZ		= enum.item	# SPMZ
	TYPE_SPU		= enum.item	# SPU
	TYPE_LOOP		= enum.item	# LOOP
	TYPE_PL_I		= enum.item	# +I
	TYPE_MI_I		= enum.item	# -I
	TYPE_MU_I		= enum.item	# *I
	TYPE_DI_I		= enum.item	# /I
	TYPE_PL			= enum.item	# +
	TYPE_PL_D		= enum.item	# +D
	TYPE_MI_D		= enum.item	# -D
	TYPE_MU_D		= enum.item	# *D
	TYPE_DI_D		= enum.item	# /D
	TYPE_MOD		= enum.item	# MOD
	TYPE_PL_R		= enum.item	# +R
	TYPE_MI_R		= enum.item	# -R
	TYPE_MU_R		= enum.item	# *R
	TYPE_DI_R		= enum.item	# /R
	TYPE_ABS		= enum.item	# ABS
	TYPE_SQR		= enum.item	# SQR
	TYPE_SQRT		= enum.item	# SQRT
	TYPE_EXP		= enum.item	# EXP
	TYPE_LN			= enum.item	# LN
	TYPE_SIN		= enum.item	# SIN
	TYPE_COS		= enum.item	# COS
	TYPE_TAN		= enum.item	# TAN
	TYPE_ASIN		= enum.item	# ASIN
	TYPE_ACOS		= enum.item	# ACOS
	TYPE_ATAN		= enum.item	# ATAN
	TYPE_LAR1		= enum.item	# LAR1
	TYPE_LAR2		= enum.item	# LAR2
	TYPE_T			= enum.item	# T
	TYPE_TAR		= enum.item	# TAR
	TYPE_TAR1		= enum.item	# TAR1
	TYPE_TAR2		= enum.item	# TAR2
	TYPE_BE			= enum.item	# BE
	TYPE_BEB		= enum.item	# BEB
	TYPE_BEA		= enum.item	# BEA
	TYPE_CALL		= enum.item	# CALL
	TYPE_CC			= enum.item	# CC
	TYPE_UC			= enum.item	# UC
	TYPE_MCRB		= enum.item	# MCR(
	TYPE_BMCR		= enum.item	# )MCR
	TYPE_MCRA		= enum.item	# MCRA
	TYPE_MCRD		= enum.item	# MCRD
	TYPE_SSI		= enum.item	# SSI
	TYPE_SSD		= enum.item	# SSD
	TYPE_SLW		= enum.item	# SLW
	TYPE_SRW		= enum.item	# SRW
	TYPE_SLD		= enum.item	# SLD
	TYPE_SRD		= enum.item	# SRD
	TYPE_RLD		= enum.item	# RLD
	TYPE_RRD		= enum.item	# RRD
	TYPE_RLDA		= enum.item	# RLDA
	TYPE_RRDA		= enum.item	# RRDA
	TYPE_SI			= enum.item	# SI
	TYPE_SV			= enum.item	# SV
	TYPE_SE			= enum.item	# SE
	TYPE_SS			= enum.item	# SS
	TYPE_SA			= enum.item	# SA
	TYPE_UW			= enum.item	# UW
	TYPE_OW			= enum.item	# OW
	TYPE_XOW		= enum.item	# XOW
	TYPE_UD			= enum.item	# UD
	TYPE_OD			= enum.item	# OD
	TYPE_XOD		= enum.item	# XOD
	TYPE_TAK		= enum.item	# TAK
	TYPE_PUSH		= enum.item	# PUSH
	TYPE_POP		= enum.item	# POP
	TYPE_ENT		= enum.item	# ENT
	TYPE_LEAVE		= enum.item	# LEAVE
	TYPE_INC		= enum.item	# INC
	TYPE_DEC		= enum.item	# DEC
	TYPE_INCAR1		= enum.item	# +AR1
	TYPE_INCAR2		= enum.item	# +AR2
	TYPE_BLD		= enum.item	# BLD
	TYPE_NOP		= enum.item	# NOP
	# Special instructions for debugging of the simulator
	TYPE_EXTENDED		= enum.itemNoInc
	TYPE_ASSERT_EQ		= enum.item	# __ASSERT==
	TYPE_ASSERT_EQ_R	= enum.item 	# __ASSERT==R
	TYPE_ASSERT_NE		= enum.item 	# __ASSERT<>
	TYPE_ASSERT_GT		= enum.item 	# __ASSERT>
	TYPE_ASSERT_LT		= enum.item 	# __ASSERT<
	TYPE_ASSERT_GE		= enum.item 	# __ASSERT>=
	TYPE_ASSERT_LE		= enum.item 	# __ASSERT<=
	TYPE_SLEEP		= enum.item 	# __SLEEP
	TYPE_STWRST		= enum.item 	# __STWRST
	TYPE_FEATURE		= enum.item 	# __FEATURE
	# Special instructions for internal usage
	TYPE_GENERIC_CALL	= enum.item	# No mnemonic
	enum.end

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

		"__ASSERT=="	: TYPE_ASSERT_EQ,
		"__ASSERT==R"	: TYPE_ASSERT_EQ_R,
		"__ASSERT<>"	: TYPE_ASSERT_NE,
		"__ASSERT>"	: TYPE_ASSERT_GT,
		"__ASSERT<"	: TYPE_ASSERT_LT,
		"__ASSERT>="	: TYPE_ASSERT_GE,
		"__ASSERT<="	: TYPE_ASSERT_LE,
		"__SLEEP"	: TYPE_SLEEP,
		"__STWRST"	: TYPE_STWRST,
		"__FEATURE"	: TYPE_FEATURE,
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
			name = "<unknown>"
		ret.append(name)
		if self.ops:
			ret.append(" ")
			ret.append(", ".join(str(op) for op in self.ops))
		if self.params:
			ret.append(" ( ")
			ret.append(", ".join(str(param) for param in self.params))
			ret.append(" )")
		return "".join(ret)

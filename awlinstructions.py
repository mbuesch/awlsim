# -*- coding: utf-8 -*-
#
# AWL simulator - instructions
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

import time
import math

from util import *
from awloperators import *
from awloptrans import *
from awlparser import *


class AwlInsn(object):
	TYPE_INVALID	= 0
	TYPE_U		= 1	# U
	TYPE_UN		= 2	# UN
	TYPE_O		= 3	# O
	TYPE_ON		= 4	# ON
	TYPE_X		= 5	# X
	TYPE_XN		= 6	# XN
	TYPE_UB		= 7	# U(
	TYPE_UNB	= 8	# UN(
	TYPE_OB		= 9	# O(
	TYPE_ONB	= 10	# ON(
	TYPE_XB		= 11	# X(
	TYPE_XNB	= 12	# XN(
	TYPE_BEND	= 13	# )
	TYPE_ASSIGN	= 14	# =
	TYPE_R		= 15	# R
	TYPE_S		= 16	# S
	TYPE_NOT	= 17	# NOT
	TYPE_SET	= 18	# SET
	TYPE_CLR	= 19	# CLR
	TYPE_SAVE	= 20	# SAVE
	TYPE_FN		= 21	# FN
	TYPE_FP		= 22	# FP
	TYPE_EQ_I	= 23	# ==I
	TYPE_NE_I	= 24	# <>I
	TYPE_GT_I	= 25	# >I
	TYPE_LT_I	= 26	# <I
	TYPE_GE_I	= 27	# >=I
	TYPE_LE_I	= 28	# <=I
	TYPE_EQ_D	= 29	# ==D
	TYPE_NE_D	= 30	# <>D
	TYPE_GT_D	= 31	# >D
	TYPE_LT_D	= 32	# <D
	TYPE_GE_D	= 33	# >=D
	TYPE_LE_D	= 34	# <=D
	TYPE_EQ_R	= 35	# ==R
	TYPE_NE_R	= 36	# <>R
	TYPE_GT_R	= 37	# >R
	TYPE_LT_R	= 38	# <R
	TYPE_GE_R	= 39	# >=R
	TYPE_LE_R	= 40	# <=R
	TYPE_BTI	= 41	# BTI
	TYPE_ITB	= 42	# ITB
	TYPE_BTD	= 43	# BTD
	TYPE_ITD	= 44	# ITD
	TYPE_DTB	= 45	# DTB
	TYPE_DTR	= 46	# DTR
	TYPE_INVI	= 47	# INVI
	TYPE_INVD	= 48	# INVD
	TYPE_NEGI	= 49	# NEGI
	TYPE_NEGD	= 50	# NEGD
	TYPE_NEGR	= 51	# NEGR
	TYPE_TAW	= 52	# TAW
	TYPE_TAD	= 53	# TAD
	TYPE_RND	= 54	# RND
	TYPE_TRUNC	= 55	# TRUNC
	TYPE_RNDP	= 56	# RND+
	TYPE_RNDN	= 57	# RND-
	TYPE_FR		= 58	# FR
	TYPE_L		= 59	# L
	TYPE_LC		= 60	# LC
	TYPE_ZV		= 61	# ZV
	TYPE_ZR		= 62	# ZR
	TYPE_AUF	= 63	# AUF
	TYPE_TDB	= 64	# TDB
	TYPE_SPA	= 65	# SPA
	TYPE_SPL	= 66	# SPL
	TYPE_SPB	= 67	# SPB
	TYPE_SPBN	= 68	# SPBN
	TYPE_SPBB	= 69	# SPBB
	TYPE_SPBNB	= 70	# SPBNB
	TYPE_SPBI	= 71	# SPBI
	TYPE_SPBIN	= 72	# SPBIN
	TYPE_SPO	= 73	# SPO
	TYPE_SPS	= 74	# SPS
	TYPE_SPZ	= 75	# SPZ
	TYPE_SPN	= 76	# SPN
	TYPE_SPP	= 77	# SPP
	TYPE_SPM	= 78	# SPM
	TYPE_SPPZ	= 79	# SPPZ
	TYPE_SPMZ	= 80	# SPMZ
	TYPE_SPU	= 81	# SPU
	TYPE_LOOP	= 82	# LOOP
	TYPE_PL_I	= 83	# +I
	TYPE_MI_I	= 84	# -I
	TYPE_MU_I	= 85	# *I
	TYPE_DI_I	= 86	# /I
	TYPE_PL		= 87	# +
	TYPE_PL_D	= 88	# +D
	TYPE_MI_D	= 89	# -D
	TYPE_MU_D	= 90	# *D
	TYPE_DI_D	= 91	# /D
	TYPE_MOD	= 92	# MOD
	TYPE_PL_R	= 93	# +R
	TYPE_MI_R	= 94	# -R
	TYPE_MU_R	= 95	# *R
	TYPE_DI_R	= 96	# /R
	TYPE_ABS	= 97	# ABS
	TYPE_SQR	= 98	# SQR
	TYPE_SQRT	= 99	# SQRT
	TYPE_EXP	= 100	# EXP
	TYPE_LN		= 101	# LN
	TYPE_SIN	= 102	# SIN
	TYPE_COS	= 103	# COS
	TYPE_TAN	= 104	# TAN
	TYPE_ASIN	= 105	# ASIN
	TYPE_ACOS	= 106	# ACOS
	TYPE_ATAN	= 107	# ATAN
	TYPE_LAR1	= 108	# LAR1
	TYPE_LAR2	= 109	# LAR2
	TYPE_T		= 110	# T
	TYPE_TAR	= 111	# TAR
	TYPE_TAR1	= 112	# TAR1
	TYPE_TAR2	= 113	# TAR2
	TYPE_BE		= 114	# BE
	TYPE_BEB	= 115	# BEB
	TYPE_BEA	= 116	# BEA
	TYPE_CALL	= 117	# CALL
	TYPE_CC		= 118	# CC
	TYPE_UC		= 119	# UC
	TYPE_MCRB	= 120	# MCR(
	TYPE_BMCR	= 121	# )MCR
	TYPE_MCRA	= 122	# MCRA
	TYPE_MCRD	= 123	# MCRD
	TYPE_SSI	= 124	# SSI
	TYPE_SSD	= 125	# SSD
	TYPE_SLW	= 126	# SLW
	TYPE_SRW	= 127	# SRW
	TYPE_SLD	= 128	# SLD
	TYPE_SRD	= 129	# SRD
	TYPE_RLD	= 130	# RLD
	TYPE_RRD	= 131	# RRD
	TYPE_RLDA	= 132	# RLDA
	TYPE_RRDA	= 133	# RRDA
	TYPE_SI		= 134	# SI
	TYPE_SV		= 135	# SV
	TYPE_SE		= 136	# SE
	TYPE_SS		= 137	# SS
	TYPE_SA		= 138	# SA
	TYPE_UW		= 139	# UW
	TYPE_OW		= 140	# OW
	TYPE_XOW	= 141	# XOW
	TYPE_UD		= 142	# UD
	TYPE_OD		= 143	# OD
	TYPE_XOD	= 144	# XOD
	TYPE_TAK	= 145	# TAK
	TYPE_PUSH	= 146	# PUSH
	TYPE_POP	= 147	# POP
	TYPE_ENT	= 148	# ENT
	TYPE_LEAVE	= 149	# LEAVE
	TYPE_INC	= 150	# INC
	TYPE_DEC	= 151	# DEC
	TYPE_INCAR1	= 152	# +AR1
	TYPE_INCAR2	= 153	# +AR2
	TYPE_BLD	= 154	# BLD
	TYPE_NOP	= 155	# NOP

	# Special instructions for debugging of the simulator
	TYPE_EXTENDED		= 500
	TYPE_ASSERT_EQ		= TYPE_EXTENDED + 0	# __ASSERT==
	TYPE_ASSERT_EQ_R	= TYPE_EXTENDED + 1	# __ASSERT==R
	TYPE_ASSERT_NE		= TYPE_EXTENDED + 2	# __ASSERT<>
	TYPE_ASSERT_GT		= TYPE_EXTENDED + 3	# __ASSERT>
	TYPE_ASSERT_LT		= TYPE_EXTENDED + 4	# __ASSERT<
	TYPE_ASSERT_GE		= TYPE_EXTENDED + 5	# __ASSERT>=
	TYPE_ASSERT_LE		= TYPE_EXTENDED + 6	# __ASSERT<=
	TYPE_SLEEP		= TYPE_EXTENDED + 7	# __SLEEP
	TYPE_STWRST		= TYPE_EXTENDED + 8	# __STWRST
	TYPE_SSPEC		= TYPE_EXTENDED + 9	# __SSPEC

	name2type = {
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
		"__SSPEC"	: TYPE_SSPEC,
	}

	type2name = { }
	for name, type in name2type.items():
		type2name[type] = name

	def __init__(self, type, rawInsn):
		self.type = type
		self.rawInsn = rawInsn
		self.cpu = None
		self.ip = None
		self.ops = []
		opTrans = AwlOpTranslator(self)
		opTrans.translateFrom(rawInsn)

	def _assertOps(self, count):
		if isinstance(count, int):
			count = [count]
		if len(self.ops) not in count:
			raise AwlSimError("Invalid Operator")

	def getRawInsn(self):
		return self.rawInsn

	def getIP(self):
		return self.ip

	def setIP(self, newIp):
		self.ip = newIp

	def setCpu(self, cpu):
		self.cpu = cpu

	def getCpu(self):
		return self.cpu

	def getLineNr(self):
		return self.rawInsn.getLineNr()

	def run(self):
		"Simulate the instruction. Override this method."
		pass

	def __repr__(self):
		return AwlInsn.type2name[self.type] +\
			(' ' if self.ops else '') +\
			', '.join(str(op) for op in self.ops)

class AwlInsn_NotImplemented(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_INVALID, rawInsn)
		raise AwlSimError("AWL instruction '%s' not "
			"implemented, yet" %\
			rawInsn.getName())

class AwlInsn_U(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_U, rawInsn)
		self._assertOps(1)

	def run(self):
		s = self.cpu.status
		s.STA = self.cpu.fetch(self.ops[0])
		if s.NER:
			s.VKE &= s.STA
			s.VKE |= s.OR
		else:
			s.VKE, s.NER = s.STA, 1

class AwlInsn_UN(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_UN, rawInsn)
		self._assertOps(1)

	def run(self):
		s = self.cpu.status
		s.STA = self.cpu.fetch(self.ops[0])
		if s.NER:
			s.VKE &= ~s.STA & 1
			s.VKE |= s.OR
		else:
			s.VKE, s.NER = (~s.STA & 1), 1

class AwlInsn_O(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_O, rawInsn)
		self._assertOps((0, 1))

	def run(self):
		s = self.cpu.status
		if self.ops:
			s.STA = self.cpu.fetch(self.ops[0])
			if s.NER:
				s.VKE |= s.STA
			else:
				s.VKE = s.STA
			s.OR, s.NER = 0, 1
		else:
			# UND vor ODER
			s.OR, s.STA, s.NER = s.VKE, 1, 0

class AwlInsn_ON(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_ON, rawInsn)
		self._assertOps(1)

	def run(self):
		s = self.cpu.status
		s.STA = self.cpu.fetch(self.ops[0])
		if s.NER:
			s.VKE |= ~s.STA & 1
		else:
			s.VKE = ~s.STA & 1
		s.OR, s.NER = 0, 1

class AwlInsn_X(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_X, rawInsn)
		self._assertOps(1)

	def run(self):
		s = self.cpu.status
		s.STA = self.cpu.fetch(self.ops[0])
		if s.NER:
			s.VKE ^= s.STA
		else:
			s.VKE = s.STA
		s.OR, s.NER = 0, 1

class AwlInsn_XN(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_XN, rawInsn)
		self._assertOps(1)

	def run(self):
		s = self.cpu.status
		s.STA = self.cpu.fetch(self.ops[0])
		if s.NER:
			s.VKE ^= ~s.STA & 1
		else:
			s.VKE = ~s.STA & 1
		s.OR, s.NER = 0, 1

class AwlInsn_UB(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_UB, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		self.cpu.parenStackAppend(AwlInsn.TYPE_UB, s)
		s.OR, s.STA, s.NER = 0, 1, 0

class AwlInsn_UNB(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_UNB, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		self.cpu.parenStackAppend(AwlInsn.TYPE_UNB, s)
		s.OR, s.STA, s.NER = 0, 1, 0

class AwlInsn_OB(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_OB, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		self.cpu.parenStackAppend(AwlInsn.TYPE_OB, s)
		s.OR, s.STA, s.NER = 0, 1, 0

class AwlInsn_ONB(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_ONB, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		self.cpu.parenStackAppend(AwlInsn.TYPE_ONB, s)
		s.OR, s.STA, s.NER = 0, 1, 0

class AwlInsn_XB(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_XB, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		self.cpu.parenStackAppend(AwlInsn.TYPE_XB, s)
		s.OR, s.STA, s.NER = 0, 1, 0

class AwlInsn_XNB(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_XNB, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		self.cpu.parenStackAppend(AwlInsn.TYPE_XNB, s)
		s.OR, s.STA, s.NER = 0, 1, 0

class AwlInsn_BEND(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_BEND, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		try:
			pse = self.cpu.parenStack.pop()
		except IndexError as e:
			raise AwlSimError("Parenthesis stack underflow")
		if pse.insnType == AwlInsn.TYPE_UB:
			if pse.NER:
				s.VKE &= pse.VKE
				s.VKE |= pse.OR
		elif pse.insnType == AwlInsn.TYPE_UNB:
			s.VKE = (~s.VKE) & 1
			if pse.NER:
				s.VKE &= pse.VKE
				s.VKE |= pse.OR
		elif pse.insnType == AwlInsn.TYPE_OB:
			if pse.NER:
				s.VKE |= pse.VKE
		elif pse.insnType == AwlInsn.TYPE_ONB:
			s.VKE = (~s.VKE) & 1
			if pse.NER:
				s.VKE |= pse.VKE
		elif pse.insnType == AwlInsn.TYPE_XB:
			if pse.NER:
				s.VKE ^= pse.VKE
		elif pse.insnType == AwlInsn.TYPE_XNB:
			s.VKE = (~s.VKE) & 1
			if pse.NER:
				s.VKE ^= pse.VKE & 1
		else:
			assert(0)
		s.OR, s.STA, s.NER = pse.OR, 1, 1

class AwlInsn_ASSIGN(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_ASSIGN, rawInsn)
		self._assertOps(1)

	def run(self):
		s = self.cpu.status
		s.STA = s.VKE
		if not self.cpu.mcrIsOn():
			s.STA = 0
		self.cpu.store(self.ops[0], s.STA)
		s.OR, s.NER = 0, 0

class AwlInsn_R(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_R, rawInsn)
		self._assertOps(1)

	def run(self):
		s = self.cpu.status
		oper = self.ops[0]
		if oper.type == AwlOperator.MEM_Z:
			if s.VKE:
				self.cpu.getCounter(oper.offset).reset()
			s.OR, s.NER = 0, 0
		elif oper.type == AwlOperator.MEM_T:
			if s.VKE:
				self.cpu.getTimer(oper.offset).reset()
			s.OR, s.NER = 0, 0
		else:
			if s.VKE and self.cpu.mcrIsOn():
				self.cpu.store(oper, 0)
			s.OR, s.STA, s.NER = 0, s.VKE, 0

class AwlInsn_S(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_S, rawInsn)
		self._assertOps(1)

	def run(self):
		s = self.cpu.status
		oper = self.ops[0]
		if oper.type == AwlOperator.MEM_Z:
			self.cpu.getCounter(oper.offset).set(s.VKE)
			s.OR, s.NER = 0, 0
		else:
			if s.VKE and self.cpu.mcrIsOn():
				self.cpu.store(oper, 1)
			s.OR, s.STA, s.NER = 0, s.VKE, 0

class AwlInsn_NOT(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_NOT, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		s.STA, s.VKE = 1, (~s.VKE & 1)

class AwlInsn_SET(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_CLR, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		s.OR, s.STA, s.VKE, s.NER = 0, 1, 1, 0

class AwlInsn_CLR(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_CLR, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		s.OR, s.STA, s.VKE, s.NER = 0, 0, 0, 0

class AwlInsn_SAVE(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SAVE, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		s.BIE = s.VKE

class AwlInsn_FN(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_FN, rawInsn)
		self._assertOps(1)

	def run(self):
		s = self.cpu.status
		fm = self.cpu.fetch(self.ops[0])
		self.cpu.store(self.ops[0], s.VKE)
		s.OR, s.STA, s.NER = 0, s.VKE, 1
		s.VKE = (~s.VKE & fm) & 1

class AwlInsn_FP(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_FP, rawInsn)
		self._assertOps(1)

	def run(self):
		s = self.cpu.status
		fm = self.cpu.fetch(self.ops[0])
		self.cpu.store(self.ops[0], s.VKE)
		s.OR, s.STA, s.NER = 0, s.VKE, 1
		s.VKE = (s.VKE & ~fm) & 1

class AwlInsn_EQ_I(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_EQ_I, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		accu1, accu2 = self.cpu.accu1.getSignedWord(),\
			       self.cpu.accu2.getSignedWord()
		if accu1 == accu2:
			s.A1, s.A0, s.VKE = 0, 0, 1
		elif accu1 > accu2:
			s.A1, s.A0, s.VKE = 0, 1, 0
		else:
			s.A1, s.A0, s.VKE = 1, 0, 0
		s.OV, s.OR, s.STA, s.NER = 0, 0, s.VKE, 1

class AwlInsn_NE_I(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_NE_I, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		accu1, accu2 = self.cpu.accu1.getSignedWord(),\
			       self.cpu.accu2.getSignedWord()
		if accu1 == accu2:
			s.A1, s.A0, s.VKE = 0, 0, 0
		elif accu1 > accu2:
			s.A1, s.A0, s.VKE = 0, 1, 1
		else:
			s.A1, s.A0, s.VKE = 1, 0, 1
		s.OV, s.OR, s.STA, s.NER = 0, 0, s.VKE, 1

class AwlInsn_GT_I(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_GT_I, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		accu1, accu2 = self.cpu.accu1.getSignedWord(),\
			       self.cpu.accu2.getSignedWord()
		if accu1 == accu2:
			s.A1, s.A0, s.VKE = 0, 0, 0
		elif accu1 > accu2:
			s.A1, s.A0, s.VKE = 0, 1, 0
		else:
			s.A1, s.A0, s.VKE = 1, 0, 1
		s.OV, s.OR, s.STA, s.NER = 0, 0, s.VKE, 1

class AwlInsn_LT_I(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_LT_I, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		accu1, accu2 = self.cpu.accu1.getSignedWord(),\
			       self.cpu.accu2.getSignedWord()
		if accu1 == accu2:
			s.A1, s.A0, s.VKE = 0, 0, 0
		elif accu1 > accu2:
			s.A1, s.A0, s.VKE = 0, 1, 1
		else:
			s.A1, s.A0, s.VKE = 1, 0, 0
		s.OV, s.OR, s.STA, s.NER = 0, 0, s.VKE, 1

class AwlInsn_GE_I(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_GE_I, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		accu1, accu2 = self.cpu.accu1.getSignedWord(),\
			       self.cpu.accu2.getSignedWord()
		if accu1 == accu2:
			s.A1, s.A0, s.VKE = 0, 0, 1
		elif accu1 > accu2:
			s.A1, s.A0, s.VKE = 0, 1, 0
		else:
			s.A1, s.A0, s.VKE = 1, 0, 1
		s.OV, s.OR, s.STA, s.NER = 0, 0, s.VKE, 1

class AwlInsn_LE_I(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_LE_I, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		accu1, accu2 = self.cpu.accu1.getSignedWord(),\
			       self.cpu.accu2.getSignedWord()
		if accu1 == accu2:
			s.A1, s.A0, s.VKE = 0, 0, 1
		elif accu1 > accu2:
			s.A1, s.A0, s.VKE = 0, 1, 1
		else:
			s.A1, s.A0, s.VKE = 1, 0, 0
		s.OV, s.OR, s.STA, s.NER = 0, 0, s.VKE, 1

class AwlInsn_EQ_D(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_EQ_D, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		accu1, accu2 = self.cpu.accu1.getSignedDWord(),\
			       self.cpu.accu2.getSignedDWord()
		if accu1 == accu2:
			s.A1, s.A0, s.VKE = 0, 0, 1
		elif accu1 > accu2:
			s.A1, s.A0, s.VKE = 0, 1, 0
		else:
			s.A1, s.A0, s.VKE = 1, 0, 0
		s.OV, s.OR, s.STA, s.NER = 0, 0, s.VKE, 1

class AwlInsn_NE_D(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_NE_D, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		accu1, accu2 = self.cpu.accu1.getSignedDWord(),\
			       self.cpu.accu2.getSignedDWord()
		if accu1 == accu2:
			s.A1, s.A0, s.VKE = 0, 0, 0
		elif accu1 > accu2:
			s.A1, s.A0, s.VKE = 0, 1, 1
		else:
			s.A1, s.A0, s.VKE = 1, 0, 1
		s.OV, s.OR, s.STA, s.NER = 0, 0, s.VKE, 1

class AwlInsn_GT_D(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_GT_D, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		accu1, accu2 = self.cpu.accu1.getSignedDWord(),\
			       self.cpu.accu2.getSignedDWord()
		if accu1 == accu2:
			s.A1, s.A0, s.VKE = 0, 0, 0
		elif accu1 > accu2:
			s.A1, s.A0, s.VKE = 0, 1, 0
		else:
			s.A1, s.A0, s.VKE = 1, 0, 1
		s.OV, s.OR, s.STA, s.NER = 0, 0, s.VKE, 1

class AwlInsn_LT_D(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_LT_D, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		accu1, accu2 = self.cpu.accu1.getSignedDWord(),\
			       self.cpu.accu2.getSignedDWord()
		if accu1 == accu2:
			s.A1, s.A0, s.VKE = 0, 0, 0
		elif accu1 > accu2:
			s.A1, s.A0, s.VKE = 0, 1, 1
		else:
			s.A1, s.A0, s.VKE = 1, 0, 0
		s.OV, s.OR, s.STA, s.NER = 0, 0, s.VKE, 1

class AwlInsn_GE_D(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_GE_D, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		accu1, accu2 = self.cpu.accu1.getSignedDWord(),\
			       self.cpu.accu2.getSignedDWord()
		if accu1 == accu2:
			s.A1, s.A0, s.VKE = 0, 0, 1
		elif accu1 > accu2:
			s.A1, s.A0, s.VKE = 0, 1, 0
		else:
			s.A1, s.A0, s.VKE = 1, 0, 1
		s.OV, s.OR, s.STA, s.NER = 0, 0, s.VKE, 1

class AwlInsn_LE_D(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_LE_D, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		accu1, accu2 = self.cpu.accu1.getSignedDWord(),\
			       self.cpu.accu2.getSignedDWord()
		if accu1 == accu2:
			s.A1, s.A0, s.VKE = 0, 0, 1
		elif accu1 > accu2:
			s.A1, s.A0, s.VKE = 0, 1, 1
		else:
			s.A1, s.A0, s.VKE = 1, 0, 0
		s.OV, s.OR, s.STA, s.NER = 0, 0, s.VKE, 1

class AwlInsn_EQ_R(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_EQ_R, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		if isNaN(self.cpu.accu1.getDWord()) or\
		   isNaN(self.cpu.accu2.getDWord()):
			s.A0, s.A1, s.OV, s.OS, s.STA = 1, 1, 1, 1, 0
		else:
			diff = self.cpu.accu2.getPyFloat() -\
			       self.cpu.accu1.getPyFloat()
			s.setForFloatingPoint(diff)
			s.STA = (~s.A0 & ~s.A1) & 1
		s.OR, s.VKE, s.NER = 0, s.STA, 1

class AwlInsn_NE_R(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_NE_R, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		if isNaN(self.cpu.accu1.getDWord()) or\
		   isNaN(self.cpu.accu2.getDWord()):
			s.A0, s.A1, s.OV, s.OS, s.STA = 1, 1, 1, 1, 0
		else:
			diff = self.cpu.accu2.getPyFloat() -\
			       self.cpu.accu1.getPyFloat()
			s.setForFloatingPoint(diff)
			s.STA = s.A0 | s.A1
		s.OR, s.VKE, s.NER = 0, s.STA, 1

class AwlInsn_GT_R(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_GT_R, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		if isNaN(self.cpu.accu1.getDWord()) or\
		   isNaN(self.cpu.accu2.getDWord()):
			s.A0, s.A1, s.OV, s.OS, s.STA = 1, 1, 1, 1, 0
		else:
			diff = self.cpu.accu2.getPyFloat() -\
			       self.cpu.accu1.getPyFloat()
			s.setForFloatingPoint(diff)
			s.STA = (~s.A0 & s.A1) & 1
		s.OR, s.VKE, s.NER = 0, s.STA, 1

class AwlInsn_LT_R(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_LT_R, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		if isNaN(self.cpu.accu1.getDWord()) or\
		   isNaN(self.cpu.accu2.getDWord()):
			s.A0, s.A1, s.OV, s.OS, s.STA = 1, 1, 1, 1, 0
		else:
			diff = self.cpu.accu2.getPyFloat() -\
			       self.cpu.accu1.getPyFloat()
			s.setForFloatingPoint(diff)
			s.STA = (s.A0 & ~s.A1) & 1
		s.OR, s.VKE, s.NER = 0, s.STA, 1

class AwlInsn_GE_R(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_GE_R, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		if isNaN(self.cpu.accu1.getDWord()) or\
		   isNaN(self.cpu.accu2.getDWord()):
			s.A0, s.A1, s.OV, s.OS, s.STA = 1, 1, 1, 1, 0
		else:
			diff = self.cpu.accu2.getPyFloat() -\
			       self.cpu.accu1.getPyFloat()
			s.setForFloatingPoint(diff)
			s.STA = ~s.A0 & 1
		s.OR, s.VKE, s.NER = 0, s.STA, 1

class AwlInsn_LE_R(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_LE_R, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		if isNaN(self.cpu.accu1.getDWord()) or\
		   isNaN(self.cpu.accu2.getDWord()):
			s.A0, s.A1, s.OV, s.OS, s.STA = 1, 1, 1, 1, 0
		else:
			diff = self.cpu.accu2.getPyFloat() -\
			       self.cpu.accu1.getPyFloat()
			s.setForFloatingPoint(diff)
			s.STA = ~s.A1 & 1
		s.OR, s.VKE, s.NER = 0, s.STA, 1

class AwlInsn_BTI(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_BTI, rawInsn)
		self._assertOps(0)

	def run(self):
		accu1 = self.cpu.accu1.get()
		bcd = accu1 & 0xFFF
		a, b, c = (bcd & 0xF), ((bcd >> 4) & 0xF), ((bcd >> 8) & 0xF)
		if bcd > 0x999 or a > 9 or b > 9 or c > 9:
			raise AwlSimError("Invalid BCD value")
		binval = (a + (b * 10) + (c * 100)) & 0xFFFF
		if accu1 & 0x8000:
			binval = (-binval) & 0xFFFF
		self.cpu.accu1.setWord(binval)

class AwlInsn_ITB(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_ITB, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		accu1 = self.cpu.accu1.get()
		binval, bcd = wordToSignedPyInt(accu1), 0
		if binval < 0:
			bcd |= 0xF000
		binval = abs(binval)
		if binval > 999:
			s.OV, s.OS = 1, 1
			return
		bcd |= binval % 10
		bcd |= ((binval // 10) % 10) << 4
		bcd |= ((binval // 100) % 10) << 8
		self.cpu.accu1.setWord(bcd)
		s.OV, s.OS = 0, 0

class AwlInsn_BTD(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_BTD, rawInsn)
		self._assertOps(0)

	def run(self):
		accu1 = self.cpu.accu1.get()
		bcd = accu1 & 0x0FFFFFFF
		a, b, c, d, e, f, g = (bcd & 0xF), ((bcd >> 4) & 0xF),\
				((bcd >> 8) & 0xF), ((bcd >> 12) & 0xF),\
				((bcd >> 16) & 0xF), ((bcd >> 20) & 0xF),\
				((bcd >> 24) & 0xF)
		if bcd > 0x9999999 or a > 9 or b > 9 or c > 9 or\
		   d > 9 or e > 9 or f > 9 or g > 9:
			raise AwlSimError("Invalid BCD value")
		binval = (a + (b * 10) + (c * 100) + (d * 1000) +\
			  (e * 10000) + (f * 100000) +\
			  (g * 1000000)) & 0xFFFFFFFF
		if accu1 & 0x80000000:
			binval = (-binval) & 0xFFFFFFFF
		self.cpu.accu1.set(binval)

class AwlInsn_ITD(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_ITD, rawInsn)
		self._assertOps(0)

	def run(self):
		self.cpu.accu1.setDWord(self.cpu.accu1.getSignedWord())

class AwlInsn_DTB(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_DTB, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		binval, bcd = dwordToSignedPyInt(self.cpu.accu1.get()), 0
		if binval < 0:
			bcd |= 0xF0000000
		binval = abs(binval)
		if binval > 9999999:
			s.OV, s.OS = 1, 1
			return
		bcd |= binval % 10
		bcd |= ((binval // 10) % 10) << 4
		bcd |= ((binval // 100) % 10) << 8
		bcd |= ((binval // 1000) % 10) << 12
		bcd |= ((binval // 10000) % 10) << 16
		bcd |= ((binval // 100000) % 10) << 20
		bcd |= ((binval // 1000000) % 10) << 24
		self.cpu.accu1.set(bcd)
		s.OV, s.OS = 0, 0

class AwlInsn_DTR(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_DTR, rawInsn)
		self._assertOps(0)

	def run(self):
		accu1 = self.cpu.accu1.getSignedDWord()
		self.cpu.accu1.setPyFloat(float(accu1))

class AwlInsn_INVI(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_INVI, rawInsn)
		self._assertOps(0)

	def run(self):
		self.cpu.accu1.setWord(~self.cpu.accu1.getWord())

class AwlInsn_INVD(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_INVD, rawInsn)
		self._assertOps(0)

	def run(self):
		self.cpu.accu1.setDWord(~self.cpu.accu1.getDWord())

class AwlInsn_NEGI(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_NEGI, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		value = -(self.cpu.accu1.getSignedWord())
		self.cpu.accu1.setWord(value)
		accu1 = self.cpu.accu1.getSignedWord()
		if accu1 == 0:
			s.A1, s.A0, s.OV = 0, 0, 0
		elif accu1 < 0:
			s.A1, s.A0, s.OV = 0, 1, 0
		else:
			s.A1, s.A0, s.OV = 1, 0, 0
		if value > 0x7FFF or value < -32768:
			s.OV, s.OS = 1, 1

class AwlInsn_NEGD(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_NEGD, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		value = -(self.cpu.accu1.getSignedDWord())
		self.cpu.accu1.setDWord(value)
		accu1 = self.cpu.accu1.getSignedDWord()
		if accu1 == 0:
			s.A1, s.A0, s.OV = 0, 0, 0
		elif accu1 < 0:
			s.A1, s.A0, s.OV = 0, 1, 0
		else:
			s.A1, s.A0, s.OV = 1, 0, 0
		if value > 0x7FFFFFFF or value < -2147483648:
			s.OV, s.OS = 1, 1

class AwlInsn_NEGR(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_NEGR, rawInsn)
		self._assertOps(0)

	def run(self):
		accu1 = -(self.cpu.accu1.getPyFloat())
		self.cpu.accu1.setPyFloat(accu1)
		self.cpu.status.setForFloatingPoint(accu1)

class AwlInsn_TAW(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_TAW, rawInsn)
		self._assertOps(0)

	def run(self):
		accu1 = self.cpu.accu1.get()
		accu1 = (accu1 & 0xFFFF0000) |\
			((accu1 & 0xFF) << 8) |\
			((accu1 & 0xFF00) >> 8)
		self.cpu.accu1.set(accu1)

class AwlInsn_TAD(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_TAD, rawInsn)
		self._assertOps(0)

	def run(self):
		accu1 = self.cpu.accu1.get()
		accu1 = ((accu1 & 0xFF000000) >> 24) |\
			((accu1 & 0x00FF0000) >> 8) |\
			((accu1 & 0x0000FF00) << 8) |\
			((accu1 & 0x000000FF) << 24)
		self.cpu.accu1.set(accu1)

class AwlInsn_RND(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_RND, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		accu1 = self.cpu.accu1.getPyFloat()
		try:
			accu1 = int(round(accu1))
			if accu1 > 2147483647 or accu1 < -2147483648:
				raise ValueError
		except ValueError:
			s.OV, s.OS = 1, 1
			return
		self.cpu.accu1.setDWord(accu1)

class AwlInsn_TRUNC(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_TRUNC, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		accu1 = self.cpu.accu1.getPyFloat()
		try:
			accu1 = int(accu1)
			if accu1 > 2147483647 or accu1 < -2147483648:
				raise ValueError
		except ValueError:
			s.OV, s.OS = 1, 1
			return
		self.cpu.accu1.setDWord(accu1)

class AwlInsn_RNDP(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_RNDP, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		accu1 = self.cpu.accu1.getPyFloat()
		try:
			rounded = int(accu1)
			if rounded >= 0 and\
			   not pyFloatEqual(float(rounded), accu1):
				rounded += 1
			if accu1 > 2147483647 or accu1 < -2147483648:
				raise ValueError
		except ValueError:
			s.OV, s.OS = 1, 1
			return
		self.cpu.accu1.setDWord(rounded)

class AwlInsn_RNDN(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_RNDN, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		accu1 = self.cpu.accu1.getPyFloat()
		try:
			rounded = int(accu1)
			if rounded < 0 and\
			   not pyFloatEqual(float(rounded), accu1):
				rounded -= 1
			if accu1 > 2147483647 or accu1 < -2147483648:
				raise ValueError
		except ValueError:
			s.OV, s.OS = 1, 1
			return
		self.cpu.accu1.setDWord(rounded)

class AwlInsn_FR(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_FR, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.MEM_Z:
			raise AwlSimError("Invalid operator")

	def run(self):
		counter = self.cpu.getCounter(self.ops[0].offset)
		counter.run_FR(self.cpu.status.VKE)

class AwlInsn_L(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_L, rawInsn)
		self._assertOps(1)

	def run(self):
		self.cpu.accu2.set(self.cpu.accu1.get())
		self.cpu.accu1.set(self.cpu.fetch(self.ops[0]))

class AwlInsn_LC(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_LC, rawInsn)
		self._assertOps(1)

	def run(self):
		self.cpu.accu2.set(self.cpu.accu1.get())
		# fetch() does the BCD conversion for us
		self.cpu.accu1.set(self.cpu.fetch(self.ops[0]))

class AwlInsn_ZV(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_ZV, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.MEM_Z:
			raise AwlSimError("Invalid operator")

	def run(self):
		s = self.cpu.status
		counter = self.cpu.getCounter(self.ops[0].offset)
		counter.run_ZV(self.cpu.status.VKE)
		s.OR, s.NER = 0, 0

class AwlInsn_ZR(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_ZR, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.MEM_Z:
			raise AwlSimError("Invalid operator")

	def run(self):
		s = self.cpu.status
		counter = self.cpu.getCounter(self.ops[0].offset)
		counter.run_ZR(self.cpu.status.VKE)
		s.OR, s.NER = 0, 0

class AwlInsn_AUF(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_AUF, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.BLKREF_DB and\
		   self.ops[0].type != AwlOperator.BLKREF_DI:
			raise AwlSimError("Invalid operator")

	def run(self):
		self.cpu.run_AUF(self.ops[0])

class AwlInsn_TDB(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_TDB, rawInsn)
		self._assertOps(0)

	def run(self):
		self.cpu.run_TDB()

class AwlInsn_SPA(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SPA, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.LBL_REF:
			raise AwlSimError("Jump instruction expects label operand")

	def run(self):
		self.cpu.jumpToLabel(self.ops[0].labelIndex)

class AwlInsn_SPL(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SPL, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.LBL_REF:
			raise AwlSimError("Jump instruction expects label operand")

	def run(self):
		defaultJmp = self.cpu.labelIdxToRelJump(self.ops[0].labelIndex)
		lookup = self.cpu.accu1.getByte() + 1
		if lookup >= defaultJmp:
			self.cpu.jumpRelative(defaultJmp)
		else:
			self.cpu.jumpRelative(lookup)

class AwlInsn_SPB(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SPB, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.LBL_REF:
			raise AwlSimError("Jump instruction expects label operand")

	def run(self):
		s = self.cpu.status
		if s.VKE:
			self.cpu.jumpToLabel(self.ops[0].labelIndex)
		s.OR, s.STA, s.VKE, s.NER = 0, 1, 1, 0

class AwlInsn_SPBN(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SPBN, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.LBL_REF:
			raise AwlSimError("Jump instruction expects label operand")

	def run(self):
		s = self.cpu.status
		if not s.VKE:
			self.cpu.jumpToLabel(self.ops[0].labelIndex)
		s.OR, s.STA, s.VKE, s.NER = 0, 1, 1, 0

class AwlInsn_SPBB(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SPBB, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.LBL_REF:
			raise AwlSimError("Jump instruction expects label operand")

	def run(self):
		s = self.cpu.status
		if s.VKE:
			self.cpu.jumpToLabel(self.ops[0].labelIndex)
		s.BIE, s.OR, s.STA, s.VKE, s.NER = s.VKE, 0, 1, 1, 0

class AwlInsn_SPBNB(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SPBNB, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.LBL_REF:
			raise AwlSimError("Jump instruction expects label operand")

	def run(self):
		s = self.cpu.status
		if not s.VKE:
			self.cpu.jumpToLabel(self.ops[0].labelIndex)
		s.BIE, s.OR, s.STA, s.VKE, s.NER = s.VKE, 0, 1, 1, 0

class AwlInsn_SPBI(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SPBI, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.LBL_REF:
			raise AwlSimError("Jump instruction expects label operand")

	def run(self):
		s = self.cpu.status
		if s.BIE:
			self.cpu.jumpToLabel(self.ops[0].labelIndex)
		s.OR, s.STA, s.NER = 0, 1, 0

class AwlInsn_SPBIN(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SPBIN, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.LBL_REF:
			raise AwlSimError("Jump instruction expects label operand")

	def run(self):
		s = self.cpu.status
		if not s.BIE:
			self.cpu.jumpToLabel(self.ops[0].labelIndex)
		s.OR, s.STA, s.NER = 0, 1, 0

class AwlInsn_SPO(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SPO, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.LBL_REF:
			raise AwlSimError("Jump instruction expects label operand")

	def run(self):
		s = self.cpu.status
		if s.OV:
			self.cpu.jumpToLabel(self.ops[0].labelIndex)

class AwlInsn_SPS(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SPS, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.LBL_REF:
			raise AwlSimError("Jump instruction expects label operand")

	def run(self):
		s = self.cpu.status
		if s.OS:
			self.cpu.jumpToLabel(self.ops[0].labelIndex)
			s.OS = 0

class AwlInsn_SPZ(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SPZ, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.LBL_REF:
			raise AwlSimError("Jump instruction expects label operand")

	def run(self):
		s = self.cpu.status
		if (s.A0 | s.A1) == 0:
			self.cpu.jumpToLabel(self.ops[0].labelIndex)

class AwlInsn_SPN(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SPN, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.LBL_REF:
			raise AwlSimError("Jump instruction expects label operand")

	def run(self):
		s = self.cpu.status
		if s.A1 ^ s.A0:
			self.cpu.jumpToLabel(self.ops[0].labelIndex)

class AwlInsn_SPP(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SPP, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.LBL_REF:
			raise AwlSimError("Jump instruction expects label operand")

	def run(self):
		s = self.cpu.status
		if ~s.A0 & s.A1 & 1:
			self.cpu.jumpToLabel(self.ops[0].labelIndex)

class AwlInsn_SPM(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SPM, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.LBL_REF:
			raise AwlSimError("Jump instruction expects label operand")

	def run(self):
		s = self.cpu.status
		if s.A0 & ~s.A1 & 1:
			self.cpu.jumpToLabel(self.ops[0].labelIndex)

class AwlInsn_SPPZ(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SPPZ, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.LBL_REF:
			raise AwlSimError("Jump instruction expects label operand")

	def run(self):
		s = self.cpu.status
		if s.A0 == 0:
			self.cpu.jumpToLabel(self.ops[0].labelIndex)

class AwlInsn_SPMZ(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SPMZ, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.LBL_REF:
			raise AwlSimError("Jump instruction expects label operand")

	def run(self):
		s = self.cpu.status
		if s.A1 == 0:
			self.cpu.jumpToLabel(self.ops[0].labelIndex)

class AwlInsn_SPU(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SPU, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.LBL_REF:
			raise AwlSimError("Jump instruction expects label operand")

	def run(self):
		s = self.cpu.status
		if s.A0 & s.A1:
			self.cpu.jumpToLabel(self.ops[0].labelIndex)

class AwlInsn_LOOP(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_LOOP, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.LBL_REF:
			raise AwlSimError("Jump instruction expects label operand")

	def run(self):
		s = self.cpu.status
		accu1l = (self.cpu.accu1.getWord() - 1) & 0xFFFF
		self.cpu.accu1.setWord(accu1l)
		if accu1l != 0:
			self.cpu.jumpToLabel(self.ops[0].labelIndex)

class AwlInsn_PL_I(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_PL_I, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		_sum = self.cpu.accu1.getSignedWord() +\
		       self.cpu.accu2.getSignedWord()
		self.cpu.accu1.setWord(_sum)
		if self.cpu.is4accu:
			self.cpu.accu2.setDWord(self.cpu.accu3.getDWord())
			self.cpu.accu3.setDWord(self.cpu.accu4.getDWord())
		accu1 = self.cpu.accu1.getSignedWord()
		if accu1 == 0:
			s.A1, s.A0, s.OV = 0, 0, 0
		elif accu1 < 0:
			s.A1, s.A0, s.OV = 0, 1, 0
		else:
			s.A1, s.A0, s.OV = 1, 0, 0
		if _sum > 0x7FFF or _sum < -32768:
			s.OV, s.OS = 1, 1

class AwlInsn_MI_I(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_MI_I, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		diff = self.cpu.accu2.getSignedWord() -\
		       self.cpu.accu1.getSignedWord()
		self.cpu.accu1.setWord(diff)
		if self.cpu.is4accu:
			self.cpu.accu2.setDWord(self.cpu.accu3.getDWord())
			self.cpu.accu3.setDWord(self.cpu.accu4.getDWord())
		accu1 = self.cpu.accu1.getSignedWord()
		if accu1 == 0:
			s.A1, s.A0, s.OV = 0, 0, 0
		elif accu1 < 0:
			s.A1, s.A0, s.OV = 0, 1, 0
		else:
			s.A1, s.A0, s.OV = 1, 0, 0
		if diff > 0x7FFF or diff < -32768:
			s.OV, s.OS = 1, 1

class AwlInsn_MU_I(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_MU_I, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		prod = self.cpu.accu2.getSignedWord() *\
		       self.cpu.accu1.getSignedWord()
		self.cpu.accu1.setDWord(prod)
		if self.cpu.is4accu:
			self.cpu.accu2.setDWord(self.cpu.accu3.getDWord())
			self.cpu.accu3.setDWord(self.cpu.accu4.getDWord())
		if prod == 0:
			s.A1, s.A0, s.OV = 0, 0, 0
		elif prod < 0:
			s.A1, s.A0, s.OV = 0, 1, 0
		else:
			s.A1, s.A0, s.OV = 1, 0, 0
		if prod > 0x7FFF or prod < -32768:
			s.OV, s.OS = 1, 1

class AwlInsn_DI_I(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_DI_I, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		accu2, accu1 = self.cpu.accu2.getSignedWord(),\
			       self.cpu.accu1.getSignedWord()
		if self.cpu.is4accu:
			self.cpu.accu2.setDWord(self.cpu.accu3.getDWord())
			self.cpu.accu3.setDWord(self.cpu.accu4.getDWord())
		try:
			quo = abs(accu2) // abs(accu1)
			if int(accu1 < 0) ^ int(accu2 < 0):
				quo = -quo
			mod = abs(accu2) % abs(accu1)
			if accu2 < 0:
				mod = -mod
		except ZeroDivisionError:
			s.A1, s.A0, s.OV, s.OS = 1, 1, 1, 1
			return
		self.cpu.accu1.setDWord(((mod & 0xFFFF) << 16) |\
					(quo & 0xFFFF))
		if quo == 0:
			s.A1, s.A0, s.OV = 0, 0, 0
		elif quo < 0:
			s.A1, s.A0, s.OV = 0, 1, 0
		else:
			s.A1, s.A0, s.OV = 1, 0, 0
		if quo > 0x7FFF:
			s.OV, s.OS = 1, 1

class AwlInsn_PL(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_PL, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.IMM:
			raise AwlSimError("Immediate expected")

	def run(self):
		oper = self.ops[0]
		if oper.width == 16:
			self.cpu.accu1.setWord(self.cpu.accu1.getSignedWord() +\
					       self.cpu.fetch(oper))
		elif oper.width == 32:
			self.cpu.accu1.setDWord(self.cpu.accu1.getSignedDWord() +\
						self.cpu.fetch(oper))
		else:
			raise AwlSimError("Unexpected operator width")

class AwlInsn_PL_D(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_PL_D, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		_sum = self.cpu.accu2.getSignedDWord() +\
		       self.cpu.accu1.getSignedDWord()
		self.cpu.accu1.setDWord(_sum)
		if self.cpu.is4accu:
			self.cpu.accu2.setDWord(self.cpu.accu3.getDWord())
			self.cpu.accu3.setDWord(self.cpu.accu4.getDWord())
		accu1 = self.cpu.accu1.getSignedDWord()
		if accu1 == 0:
			s.A1, s.A0, s.OV = 0, 0, 0
		elif accu1 < 0:
			s.A1, s.A0, s.OV = 0, 1, 0
		else:
			s.A1, s.A0, s.OV = 1, 0, 0
		if _sum > 0x7FFFFFFF or _sum < -2147483648:
			s.OV, s.OS = 1, 1

class AwlInsn_MI_D(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_MI_D, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		diff = self.cpu.accu2.getSignedDWord() -\
		       self.cpu.accu1.getSignedDWord()
		self.cpu.accu1.setDWord(diff)
		if self.cpu.is4accu:
			self.cpu.accu2.setDWord(self.cpu.accu3.getDWord())
			self.cpu.accu3.setDWord(self.cpu.accu4.getDWord())
		accu1 = self.cpu.accu1.getSignedDWord()
		if accu1 == 0:
			s.A1, s.A0, s.OV = 0, 0, 0
		elif accu1 < 0:
			s.A1, s.A0, s.OV = 0, 1, 0
		else:
			s.A1, s.A0, s.OV = 1, 0, 0
		if diff > 0x7FFFFFFF or diff < -2147483648:
			s.OV, s.OS = 1, 1

class AwlInsn_MU_D(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_MU_D, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		prod = self.cpu.accu2.getSignedDWord() *\
		       self.cpu.accu1.getSignedDWord()
		self.cpu.accu1.setDWord(prod)
		if self.cpu.is4accu:
			self.cpu.accu2.setDWord(self.cpu.accu3.getDWord())
			self.cpu.accu3.setDWord(self.cpu.accu4.getDWord())
		if prod == 0:
			s.A1, s.A0, s.OV = 0, 0, 0
		elif prod < 0:
			s.A1, s.A0, s.OV = 0, 1, 0
		else:
			s.A1, s.A0, s.OV = 1, 0, 0
		if prod > 0x7FFFFFFF or prod < -2147483648:
			s.OV, s.OS = 1, 1

class AwlInsn_DI_D(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_DI_D, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		accu2, accu1 = self.cpu.accu2.getSignedDWord(),\
			       self.cpu.accu1.getSignedDWord()
		if self.cpu.is4accu:
			self.cpu.accu2.setDWord(self.cpu.accu3.getDWord())
			self.cpu.accu3.setDWord(self.cpu.accu4.getDWord())
		try:
			quo = abs(accu2) // abs(accu1)
			if int(accu1 < 0) ^ int(accu2 < 0):
				quo = -quo
		except ZeroDivisionError:
			s.A1, s.A0, s.OV, s.OS = 1, 1, 1, 1
			return
		self.cpu.accu1.setDWord(quo)
		if quo == 0:
			s.A1, s.A0, s.OV = 0, 0, 0
		elif quo < 0:
			s.A1, s.A0, s.OV = 0, 1, 0
		else:
			s.A1, s.A0, s.OV = 1, 0, 0
		if quo > 0x7FFFFFFF:
			s.OV, s.OS = 1, 1

class AwlInsn_MOD(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_MOD, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		accu2, accu1 = self.cpu.accu2.getSignedDWord(),\
			       self.cpu.accu1.getSignedDWord()
		if self.cpu.is4accu:
			self.cpu.accu2.setDWord(self.cpu.accu3.getDWord())
			self.cpu.accu3.setDWord(self.cpu.accu4.getDWord())
		try:
			rem = abs(accu2) % abs(accu1)
			if accu2 < 0:
				rem = -rem
		except ZeroDivisionError:
			s.A1, s.A0, s.OV, s.OS = 1, 1, 1, 1
			return
		self.cpu.accu1.setDWord(rem)
		if rem == 0:
			s.A1, s.A0, s.OV = 0, 0, 0
		elif rem < 0:
			s.A1, s.A0, s.OV = 0, 1, 0
		else:
			s.A1, s.A0, s.OV = 1, 0, 0

class AwlInsn_PL_R(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_PL_R, rawInsn)
		self._assertOps(0)

	def run(self):
		accu2, accu1 = self.cpu.accu2.getPyFloat(),\
			       self.cpu.accu1.getPyFloat()
		_sum = accu2 + accu1
		self.cpu.accu1.setPyFloat(_sum)
		self.cpu.status.setForFloatingPoint(_sum)

class AwlInsn_MI_R(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_MI_R, rawInsn)
		self._assertOps(0)

	def run(self):
		accu2, accu1 = self.cpu.accu2.getPyFloat(),\
			       self.cpu.accu1.getPyFloat()
		diff = accu2 - accu1
		self.cpu.accu1.setPyFloat(diff)
		self.cpu.status.setForFloatingPoint(diff)

class AwlInsn_MU_R(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_MU_R, rawInsn)
		self._assertOps(0)

	def run(self):
		accu2, accu1 = self.cpu.accu2.getPyFloat(),\
			       self.cpu.accu1.getPyFloat()
		prod = accu2 * accu1
		self.cpu.accu1.setPyFloat(prod)
		self.cpu.status.setForFloatingPoint(prod)

class AwlInsn_DI_R(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_DI_R, rawInsn)
		self._assertOps(0)

	def run(self):
		accu2, accu1 = self.cpu.accu2.getPyFloat(),\
			       self.cpu.accu1.getPyFloat()
		try:
			quo = accu2 / accu1
		except ZeroDivisionError:
			if accu2 >= 0.0:
				quo = posInfFloat
			else:
				quo = negInfFloat
		self.cpu.accu1.setPyFloat(quo)
		self.cpu.status.setForFloatingPoint(quo)

class AwlInsn_ABS(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_ABS, rawInsn)
		self._assertOps(0)

	def run(self):
		self.cpu.accu1.setPyFloat(abs(self.cpu.accu1.getPyFloat()))

class AwlInsn_SQR(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SQR, rawInsn)
		self._assertOps(0)

	def run(self):
		accu1 = self.cpu.accu1.getPyFloat()
		accu1 **= 2
		self.cpu.accu1.setPyFloat(accu1)
		self.cpu.status.setForFloatingPoint(accu1)

class AwlInsn_SQRT(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SQRT, rawInsn)
		self._assertOps(0)

	def run(self):
		accu1 = self.cpu.accu1.getPyFloat()
		try:
			accu1 = math.sqrt(accu1)
		except ValueError:
			accu1 = nanFloat
		self.cpu.accu1.setPyFloat(accu1)
		self.cpu.status.setForFloatingPoint(accu1)

class AwlInsn_EXP(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_EXP, rawInsn)
		self._assertOps(0)

	def run(self):
		accu1 = self.cpu.accu1.getPyFloat()
		accu1 = math.exp(accu1)
		self.cpu.accu1.setPyFloat(accu1)
		self.cpu.status.setForFloatingPoint(accu1)

class AwlInsn_LN(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_LN, rawInsn)
		self._assertOps(0)

	def run(self):
		accu1 = self.cpu.accu1.getPyFloat()
		try:
			if accu1 == 0.0:
				accu1 = negInfFloat
			else:
				accu1 = math.log(accu1)
		except ValueError:
			accu1 = nanFloat
		self.cpu.accu1.setPyFloat(accu1)
		self.cpu.status.setForFloatingPoint(accu1)

class AwlInsn_SIN(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SIN, rawInsn)
		self._assertOps(0)

	def run(self):
		accu1 = math.sin(self.cpu.accu1.getPyFloat())
		for extremum in (-1.0, 0.0, 1.0):
			if pyFloatEqual(accu1, extremum):
				accu1 = extremum
		self.cpu.accu1.setPyFloat(accu1)
		self.cpu.status.setForFloatingPoint(accu1)

class AwlInsn_COS(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_COS, rawInsn)
		self._assertOps(0)

	def run(self):
		accu1 = math.cos(self.cpu.accu1.getPyFloat())
		for extremum in (-1.0, 0.0, 1.0):
			if pyFloatEqual(accu1, extremum):
				accu1 = extremum
		self.cpu.accu1.setPyFloat(accu1)
		self.cpu.status.setForFloatingPoint(accu1)

class AwlInsn_TAN(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_TAN, rawInsn)
		self._assertOps(0)

	def run(self):
		accu1 = self.cpu.accu1.getPyFloat()
		if pyFloatEqual(accu1, math.pi / 2):
			accu1 = posInfFloat
		elif pyFloatEqual(accu1, -math.pi / 2):
			accu1 = negInfFloat
		else:
			accu1 = math.tan(accu1)
			for extremum in (-1.0, 0.0, 1.0):
				if pyFloatEqual(accu1, extremum):
					accu1 = extremum
		self.cpu.accu1.setPyFloat(accu1)
		self.cpu.status.setForFloatingPoint(accu1)

class AwlInsn_ASIN(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_ASIN, rawInsn)
		self._assertOps(0)

	def run(self):
		accu1 = math.asin(self.cpu.accu1.getPyFloat())
		self.cpu.accu1.setPyFloat(accu1)
		self.cpu.status.setForFloatingPoint(accu1)

class AwlInsn_ACOS(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_ACOS, rawInsn)
		self._assertOps(0)

	def run(self):
		accu1 = math.acos(self.cpu.accu1.getPyFloat())
		self.cpu.accu1.setPyFloat(accu1)
		self.cpu.status.setForFloatingPoint(accu1)

class AwlInsn_ATAN(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_ATAN, rawInsn)
		self._assertOps(0)

	def run(self):
		accu1 = math.atan(self.cpu.accu1.getPyFloat())
		self.cpu.accu1.setPyFloat(accu1)
		self.cpu.status.setForFloatingPoint(accu1)

class AwlInsn_T(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_T, rawInsn)
		self._assertOps(1)

	def run(self):
		if self.cpu.mcrIsOn():
			self.cpu.store(self.ops[0], self.cpu.accu1.get())
		else:
			self.cpu.store(self.ops[0], 0)

class AwlInsn_TAR(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_TAR, rawInsn)
		self._assertOps(0)

	def run(self):
		oldAr1 = self.cpu.ar1.get()
		self.cpu.ar1.set(self.cpu.ar2.get())
		self.cpu.ar2.set(oldAr1)

class AwlInsn_BE(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_BE, rawInsn)
		self._assertOps(0)

	def run(self):
		self.cpu.run_BE()

class AwlInsn_BEB(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_BEB, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		if s.VKE:
			self.cpu.run_BE()
		else:
			s.OS, s.OR, s.STA, s.VKE, s.NER = 0, 0, 1, 1, 0

class AwlInsn_BEA(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_BEA, rawInsn)
		self._assertOps(0)

	def run(self):
		self.cpu.run_BE()

class AwlInsn_CALL(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_CALL, rawInsn)
		self._assertOps((1,2))

	def run(self):
		s = self.cpu.status
		if len(self.ops) == 1:
			self.cpu.run_CALL(self.ops[0])
		elif len(self.ops) == 2:
			self.cpu.run_CALL(self.ops[0], self.ops[1])
		else:
			assert(0)
		s.OS, s.OR, s.STA, s.NER = 0, 0, 1, 0

class AwlInsn_CC(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_CC, rawInsn)
		self._assertOps(1)

	def run(self):
		s = self.cpu.status
		if s.VKE:
			self.cpu.run_CALL(self.ops[0])
		s.OS, s.OR, s.STA, s.VKE, s.NER = 0, 0, 1, 1, 0

class AwlInsn_UC(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_UC, rawInsn)
		self._assertOps(1)

	def run(self):
		s = self.cpu.status
		self.cpu.run_CALL(self.ops[0])
		s.OS, s.OR, s.STA, s.NER = 0, 0, 1, 0

class AwlInsn_MCRB(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_MCRB, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		self.cpu.mcrStackAppend(s)
		s.OR, s.STA, s.NER = 0, 1, 0

class AwlInsn_BMCR(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_BMCR, rawInsn)
		self._assertOps(0)

	def run(self):
		s = self.cpu.status
		self.cpu.mcrStackPop()
		s.OR, s.STA, s.NER = 0, 1, 0

class AwlInsn_MCRA(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_MCRA, rawInsn)
		self._assertOps(0)

	def run(self):
		self.cpu.setMcrActive(True)

class AwlInsn_MCRD(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_MCRD, rawInsn)
		self._assertOps(0)

	def run(self):
		self.cpu.setMcrActive(False)

class AwlInsn_SSI(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SSI, rawInsn)
		self._assertOps((0, 1))
		if self.ops:
			self.ops[0].assertType(AwlOperator.IMM, 0, 255)

	def run(self):
		s = self.cpu.status
		accu1 = self.cpu.accu1.getSignedWord()
		if self.ops:
			count = self.ops[0].immediate
		else:
			count = self.cpu.accu2.getByte()
		if count <= 0:
			return
		count = min(count, 16)
		s.A1, s.A0, s.OV = (accu1 >> (count - 1)) & 1, 0, 0
		accu1 >>= count
		self.cpu.accu1.setWord(accu1)

class AwlInsn_SSD(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SSD, rawInsn)
		self._assertOps((0, 1))
		if self.ops:
			self.ops[0].assertType(AwlOperator.IMM, 0, 255)

	def run(self):
		s = self.cpu.status
		accu1 = self.cpu.accu1.getSignedDWord()
		if self.ops:
			count = self.ops[0].immediate
		else:
			count = self.cpu.accu2.getByte()
		if count <= 0:
			return
		count = min(count, 32)
		s.A1, s.A0, s.OV = (accu1 >> (count - 1)) & 1, 0, 0
		accu1 >>= count
		self.cpu.accu1.setDWord(accu1)

class AwlInsn_SLW(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SLW, rawInsn)
		self._assertOps((0, 1))
		if self.ops:
			self.ops[0].assertType(AwlOperator.IMM, 0, 255)

	def run(self):
		s = self.cpu.status
		accu1 = self.cpu.accu1.getWord()
		if self.ops:
			count = self.ops[0].immediate
		else:
			count = self.cpu.accu2.getByte()
		if count <= 0:
			return
		count = min(count, 16)
		s.A1, s.A0, s.OV = (accu1 >> (16 - count)) & 1, 0, 0
		accu1 <<= count
		self.cpu.accu1.setWord(accu1)

class AwlInsn_SRW(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SRW, rawInsn)
		self._assertOps((0, 1))
		if self.ops:
			self.ops[0].assertType(AwlOperator.IMM, 0, 255)

	def run(self):
		s = self.cpu.status
		accu1 = self.cpu.accu1.getWord()
		if self.ops:
			count = self.ops[0].immediate
		else:
			count = self.cpu.accu2.getByte()
		if count <= 0:
			return
		count = min(count, 16)
		s.A1, s.A0, s.OV = (accu1 >> (count - 1)) & 1, 0, 0
		accu1 >>= count
		self.cpu.accu1.setWord(accu1)

class AwlInsn_SLD(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SLD, rawInsn)
		self._assertOps((0, 1))
		if self.ops:
			self.ops[0].assertType(AwlOperator.IMM, 0, 255)

	def run(self):
		s = self.cpu.status
		accu1 = self.cpu.accu1.getDWord()
		if self.ops:
			count = self.ops[0].immediate
		else:
			count = self.cpu.accu2.getByte()
		if count <= 0:
			return
		count = min(count, 32)
		s.A1, s.A0, s.OV = (accu1 >> (32 - count)) & 1, 0, 0
		accu1 <<= count
		self.cpu.accu1.setDWord(accu1)

class AwlInsn_SRD(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SRD, rawInsn)
		self._assertOps((0, 1))
		if self.ops:
			self.ops[0].assertType(AwlOperator.IMM, 0, 255)

	def run(self):
		s = self.cpu.status
		accu1 = self.cpu.accu1.getDWord()
		if self.ops:
			count = self.ops[0].immediate
		else:
			count = self.cpu.accu2.getByte()
		if count <= 0:
			return
		count = min(count, 32)
		s.A1, s.A0, s.OV = (accu1 >> (count - 1)) & 1, 0, 0
		accu1 >>= count
		self.cpu.accu1.setDWord(accu1)

class AwlInsn_RLD(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_RLD, rawInsn)
		self._assertOps((0, 1))
		if self.ops:
			self.ops[0].assertType(AwlOperator.IMM, 0, 255)

	def run(self):
		s = self.cpu.status
		count, accu = 1, self.cpu.accu1.get()
		if self.ops:
			count = self.cpu.fetch(self.ops[0])
		if count <= 0:
			return
		count = max(0, count % 32)
		accu &= 0xFFFFFFFF
		accu = ((accu << count) | (accu >> (32 - count))) & 0xFFFFFFFF
		self.cpu.accu1.set(accu)
		#TODO A1
		s.A0, s.OV = 0, 0

class AwlInsn_RRD(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_RRD, rawInsn)
		self._assertOps((0, 1))
		if self.ops:
			self.ops[0].assertType(AwlOperator.IMM, 0, 255)

	def run(self):
		s = self.cpu.status
		count, accu = 1, self.cpu.accu1.get()
		if self.ops:
			count = self.cpu.fetch(self.ops[0])
		if count <= 0:
			return
		count = max(0, count % 32)
		accu &= 0xFFFFFFFF
		accu = ((accu >> count) | (accu << (32 - count))) & 0xFFFFFFFF
		self.cpu.accu1.set(accu)
		#TODO A1
		s.A0, s.OV = 0, 0

class AwlInsn_RLDA(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_RLDA, rawInsn)
		self._assertOps((0, 1))
		if self.ops:
			self.ops[0].assertType(AwlOperator.IMM, 0, 255)

	def run(self):
		s = self.cpu.status
		count, accu = 1, self.cpu.accu1.get()
		if self.ops:
			count = self.cpu.fetch(self.ops[0])
		if count > 0:
			s.A0, s.OV = 0, 0
		count = max(0, count % 32)
		accu &= 0xFFFFFFFF
		accu |= (s.A1 & 1) << 32
		accu = ((accu << count) | (accu >> (33 - count))) & 0x1FFFFFFFF
		s.A1 = (accu >> 32) & 1
		accu &= 0xFFFFFFFF
		self.cpu.accu1.set(accu)

class AwlInsn_RRDA(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_RRDA, rawInsn)
		self._assertOps((0, 1))
		if self.ops:
			self.ops[0].assertType(AwlOperator.IMM, 0, 255)

	def run(self):
		s = self.cpu.status
		count, accu = 1, self.cpu.accu1.get()
		if self.ops:
			count = self.cpu.fetch(self.ops[0])
		if count > 0:
			s.A0, s.OV = 0, 0
		count = max(0, count % 32)
		accu &= 0xFFFFFFFF
		accu |= (s.A1 & 1) << 32
		accu = ((accu >> count) | (accu << (33 - count))) & 0x1FFFFFFFF
		s.A1 = (accu >> 32) & 1
		accu &= 0xFFFFFFFF
		self.cpu.accu1.set(accu)

class AwlInsn_SI(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SI, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.MEM_T:
			raise AwlSimError("Timer expected")

	def run(self):
		timerNumber = self.ops[0].offset
		timer = self.cpu.getTimer(timerNumber)
		timer.run_SI(self.cpu.accu1.get())

class AwlInsn_SV(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SV, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.MEM_T:
			raise AwlSimError("Timer expected")

	def run(self):
		timerNumber = self.ops[0].offset
		timer = self.cpu.getTimer(timerNumber)
		timer.run_SV(self.cpu.accu1.get())

class AwlInsn_SE(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SE, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.MEM_T:
			raise AwlSimError("Timer expected")

	def run(self):
		timerNumber = self.ops[0].offset
		timer = self.cpu.getTimer(timerNumber)
		timer.run_SE(self.cpu.accu1.get())

class AwlInsn_SS(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SS, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.MEM_T:
			raise AwlSimError("Timer expected")

	def run(self):
		timerNumber = self.ops[0].offset
		timer = self.cpu.getTimer(timerNumber)
		timer.run_SS(self.cpu.accu1.get())

class AwlInsn_SA(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SA, rawInsn)
		self._assertOps(1)
		if self.ops[0].type != AwlOperator.MEM_T:
			raise AwlSimError("Timer expected")

	def run(self):
		timerNumber = self.ops[0].offset
		timer = self.cpu.getTimer(timerNumber)
		timer.run_SA(self.cpu.accu1.get())

class AwlInsn_UW(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_UW, rawInsn)
		self._assertOps((0, 1))
		if self.ops:
			self.ops[0].assertType(AwlOperator.IMM, 0, 0xFFFF)

	def run(self):
		s = self.cpu.status
		accu1 = self.cpu.accu1.getWord()
		if self.ops:
			accu2 = self.ops[0].immediate
		else:
			accu2 = self.cpu.accu2.getWord()
		accu1 &= accu2
		self.cpu.accu1.setWord(accu1)
		s.A1 = 1 if accu1 else 0
		s.A0, s.OV = 0, 0

class AwlInsn_OW(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_OW, rawInsn)
		self._assertOps((0, 1))
		if self.ops:
			self.ops[0].assertType(AwlOperator.IMM, 0, 0xFFFF)

	def run(self):
		s = self.cpu.status
		accu1 = self.cpu.accu1.getWord()
		if self.ops:
			accu2 = self.ops[0].immediate
		else:
			accu2 = self.cpu.accu2.getWord()
		accu1 |= accu2
		self.cpu.accu1.setWord(accu1)
		s.A1 = 1 if accu1 else 0
		s.A0, s.OV = 0, 0

class AwlInsn_XOW(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_XOW, rawInsn)
		self._assertOps((0, 1))
		if self.ops:
			self.ops[0].assertType(AwlOperator.IMM, 0, 0xFFFF)

	def run(self):
		s = self.cpu.status
		accu1 = self.cpu.accu1.getWord()
		if self.ops:
			accu2 = self.ops[0].immediate
		else:
			accu2 = self.cpu.accu2.getWord()
		accu1 ^= accu2
		self.cpu.accu1.setWord(accu1)
		s.A1 = 1 if accu1 else 0
		s.A0, s.OV = 0, 0

class AwlInsn_UD(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_UD, rawInsn)
		self._assertOps((0, 1))
		if self.ops:
			self.ops[0].assertType(AwlOperator.IMM)

	def run(self):
		s = self.cpu.status
		accu1 = self.cpu.accu1.getDWord()
		if self.ops:
			accu2 = self.ops[0].immediate
		else:
			accu2 = self.cpu.accu2.getDWord()
		accu1 &= accu2
		self.cpu.accu1.setDWord(accu1)
		s.A1 = 1 if accu1 else 0
		s.A0, s.OV = 0, 0

class AwlInsn_OD(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_OD, rawInsn)
		self._assertOps((0, 1))
		if self.ops:
			self.ops[0].assertType(AwlOperator.IMM)

	def run(self):
		s = self.cpu.status
		accu1 = self.cpu.accu1.getDWord()
		if self.ops:
			accu2 = self.ops[0].immediate
		else:
			accu2 = self.cpu.accu2.getDWord()
		accu1 |= accu2
		self.cpu.accu1.setDWord(accu1)
		s.A1 = 1 if accu1 else 0
		s.A0, s.OV = 0, 0

class AwlInsn_XOD(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_XOD, rawInsn)
		self._assertOps((0, 1))
		if self.ops:
			self.ops[0].assertType(AwlOperator.IMM)

	def run(self):
		s = self.cpu.status
		accu1 = self.cpu.accu1.getDWord()
		if self.ops:
			accu2 = self.ops[0].immediate
		else:
			accu2 = self.cpu.accu2.getDWord()
		accu1 ^= accu2
		self.cpu.accu1.setDWord(accu1)
		s.A1 = 1 if accu1 else 0
		s.A0, s.OV = 0, 0

class AwlInsn_TAK(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_TAK, rawInsn)
		self._assertOps(0)

	def run(self):
		oldAccu1 = self.cpu.accu1.get()
		self.cpu.accu1.set(self.cpu.accu2.get())
		self.cpu.accu2.set(oldAccu1)

class AwlInsn_PUSH(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_PUSH, rawInsn)
		self._assertOps(0)

	def run(self):
		self.cpu.accu2.set(self.cpu.accu1.get())

class AwlInsn_POP(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_POP, rawInsn)
		self._assertOps(0)

	def run(self):
		self.cpu.accu1.set(self.cpu.accu2.get())

class AwlInsn_ENT(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_ENT, rawInsn)
		self._assertOps(0)

	def run(self):
		if not self.cpu.is4accu:
			raise AwlSimError("ENT not supported on 2-accu CPU")
		self.cpu.accu4.setDWord(self.cpu.accu3.getDWord())
		self.cpu.accu3.setDWord(self.cpu.accu2.getDWord())

class AwlInsn_LEAVE(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_LEAVE, rawInsn)
		self._assertOps(0)

	def run(self):
		if not self.cpu.is4accu:
			raise AwlSimError("LEAVE not supported on 2-accu CPU")
		self.cpu.accu2.setDWord(self.cpu.accu3.getDWord())
		self.cpu.accu3.setDWord(self.cpu.accu4.getDWord())

class AwlInsn_INC(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_INC, rawInsn)
		self._assertOps(1)
		self.ops[0].assertType(AwlOperator.IMM, 0, 255)

	def run(self):
		self.cpu.accu1.setByte(self.cpu.accu1.getByte() +\
				       self.ops[0].immediate)

class AwlInsn_DEC(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_DEC, rawInsn)
		self._assertOps(1)
		self.ops[0].assertType(AwlOperator.IMM, 0, 255)

	def run(self):
		self.cpu.accu1.setByte(self.cpu.accu1.getByte() -\
				       self.ops[0].immediate)

class AwlInsn_INCAR1(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_INCAR1, rawInsn)
		self._assertOps((0, 1))

	def run(self):
		if self.ops:
			pass#TODO
		else:
			pass#TODO

class AwlInsn_INCAR2(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_INCAR2, rawInsn)
		self._assertOps((0, 1))

	def run(self):
		if self.ops:
			pass#TODO
		else:
			pass#TODO

class AwlInsn_BLD(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_BLD, rawInsn)
		self._assertOps(1)

	def run(self):
		pass # NOP

class AwlInsn_NOP(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_NOP, rawInsn)
		self._assertOps(1)
		self.ops[0].assertType(AwlOperator.IMM, 0, 1)

	def run(self):
		pass # NOP

class AwlInsn_ASSERT_EQ(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_ASSERT_EQ, rawInsn)
		self._assertOps(2)

	def run(self):
		s = self.cpu.status
		val0 = self.cpu.fetch(self.ops[0])
		val1 = self.cpu.fetch(self.ops[1])
		if not (val0 == val1):
			raise AwlSimError("Assertion failed")
		s.NER = 0

class AwlInsn_ASSERT_EQ_R(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_ASSERT_EQ_R, rawInsn)
		self._assertOps(2)

	def run(self):
		s = self.cpu.status
		val0 = self.cpu.fetch(self.ops[0])
		val1 = self.cpu.fetch(self.ops[1])
		if not floatEqual(val0, val1):
			raise AwlSimError("Assertion failed")
		s.NER = 0

class AwlInsn_ASSERT_NE(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_ASSERT_NE, rawInsn)
		self._assertOps(2)

	def run(self):
		s = self.cpu.status
		val0 = self.cpu.fetch(self.ops[0])
		val1 = self.cpu.fetch(self.ops[1])
		if not (val0 != val1):
			raise AwlSimError("Assertion failed")
		s.NER = 0

class AwlInsn_ASSERT_GT(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_ASSERT_GT, rawInsn)
		self._assertOps(2)

	def run(self):
		s = self.cpu.status
		val0 = self.cpu.fetch(self.ops[0])
		val1 = self.cpu.fetch(self.ops[1])
		if not (val0 > val1):
			raise AwlSimError("Assertion failed")
		s.NER = 0

class AwlInsn_ASSERT_LT(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_ASSERT_LT, rawInsn)
		self._assertOps(2)

	def run(self):
		s = self.cpu.status
		val0 = self.cpu.fetch(self.ops[0])
		val1 = self.cpu.fetch(self.ops[1])
		if not (val0 < val1):
			raise AwlSimError("Assertion failed")
		s.NER = 0

class AwlInsn_ASSERT_GE(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_ASSERT_GE, rawInsn)
		self._assertOps(2)

	def run(self):
		s = self.cpu.status
		val0 = self.cpu.fetch(self.ops[0])
		val1 = self.cpu.fetch(self.ops[1])
		if not (val0 >= val1):
			raise AwlSimError("Assertion failed")
		s.NER = 0

class AwlInsn_ASSERT_LE(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_ASSERT_LE, rawInsn)
		self._assertOps(2)

	def run(self):
		s = self.cpu.status
		val0 = self.cpu.fetch(self.ops[0])
		val1 = self.cpu.fetch(self.ops[1])
		if not (val0 <= val1):
			raise AwlSimError("Assertion failed")
		s.NER = 0

class AwlInsn_SLEEP(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SLEEP, rawInsn)
		self._assertOps(1)

	def run(self):
		msecs = self.cpu.fetch(self.ops[0])

		if float(msecs) / 1000 >= self.cpu.cycleTimeLimit:
			raise AwlSimError("__SLEEP time exceed cycle time limit")

		while msecs > 0:
			m = min(50, msecs)
			time.sleep(float(m) / 1000)
			self.cpu.updateTimestamp()
			self.cpu.requestScreenUpdate()
			msecs -= m

class AwlInsn_STWRST(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_STWRST, rawInsn)
		self._assertOps(0)

	def run(self):
		self.cpu.status.reset()

class AwlInsn_SSPEC(AwlInsn):
	def __init__(self, rawInsn):
		AwlInsn.__init__(self, AwlInsn.TYPE_SSPEC, rawInsn)
		self._assertOps(2)

	def run(self):
		target = self.cpu.fetch(self.ops[0])
		value = self.cpu.fetch(self.ops[1])
		if target == 0:
			self.cpu.specs.setNrAccus(value)
		else:
			raise AwlSimError("Unsupported SSPEC target")

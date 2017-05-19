# -*- coding: utf-8 -*-
#
# AWL simulator - Operator types
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


class AwlOperatorTypes(object):
	EnumGen.start	# Operator types

	_IMM_START	= EnumGen.item
	IMM		= EnumGen.item	# Immediate value (constant)
	IMM_REAL	= EnumGen.item	# Real
	IMM_S5T		= EnumGen.item	# S5T immediate
	IMM_TIME	= EnumGen.item	# T# immediate
	IMM_DATE	= EnumGen.item	# D# immediate
	IMM_TOD		= EnumGen.item	# TOD# immediate
	IMM_DT		= EnumGen.item	# DT# immediate
	IMM_PTR		= EnumGen.item	# Pointer immediate (P#x.y, P#area x.y, P#DBn.DBX x.y)
	IMM_STR		= EnumGen.item	# STRING immediate ('abc')
	_IMM_END	= EnumGen.item

	MEM_E		= EnumGen.item	# Input
	MEM_A		= EnumGen.item	# Output
	MEM_M		= EnumGen.item	# Flags
	MEM_L		= EnumGen.item	# Localstack
	MEM_VL		= EnumGen.item	# Parent localstack (indirect access)
	MEM_DB		= EnumGen.item	# Global datablock
	MEM_DI		= EnumGen.item	# Instance datablock
	MEM_T		= EnumGen.item	# Timer
	MEM_Z		= EnumGen.item	# Counter
	MEM_PA		= EnumGen.item	# Peripheral output
	MEM_PE		= EnumGen.item	# Peripheral input

	MEM_STW		= EnumGen.item	# Status word bit read
	MEM_STW_Z	= EnumGen.item	# Status word "==0" read
	MEM_STW_NZ	= EnumGen.item	# Status word "<>0" read
	MEM_STW_POS	= EnumGen.item	# Status word ">0" read
	MEM_STW_NEG	= EnumGen.item	# Status word "<0" read
	MEM_STW_POSZ	= EnumGen.item	# Status word ">=0" read
	MEM_STW_NEGZ	= EnumGen.item	# Status word "<=0" read
	MEM_STW_UO	= EnumGen.item	# Status word "UO" read

	MEM_DBLG	= EnumGen.item	# DB-register: DB length
	MEM_DBNO	= EnumGen.item	# DB-register: DB number
	MEM_DILG	= EnumGen.item	# DI-register: DB length
	MEM_DINO	= EnumGen.item	# DI-register: DB number

	MEM_AR2		= EnumGen.item	# AR2 register

	BLKREF_FC	= EnumGen.item	# FC reference
	BLKREF_SFC	= EnumGen.item	# SFC reference
	BLKREF_FB	= EnumGen.item	# FB reference
	BLKREF_SFB	= EnumGen.item	# SFB reference
	BLKREF_UDT	= EnumGen.item	# UDT reference
	BLKREF_DB	= EnumGen.item	# DB reference
	BLKREF_DI	= EnumGen.item	# DI reference
	BLKREF_OB	= EnumGen.item	# OB reference (only symbol table)
	BLKREF_VAT	= EnumGen.item	# VAT reference (only symbol table)
	MULTI_FB	= EnumGen.item	# FB multiinstance reference
	MULTI_SFB	= EnumGen.item	# SFB multiinstance reference

	LBL_REF		= EnumGen.item	# Label reference
	SYMBOLIC	= EnumGen.item	# Classic symbolic reference ("xyz")
	NAMED_LOCAL	= EnumGen.item	# Named local reference (#abc)
	NAMED_LOCAL_PTR	= EnumGen.item	# Pointer to named local (P##abc)
	NAMED_DBVAR	= EnumGen.item	# Named DB variable reference (DBx.VAR)

	INDIRECT	= EnumGen.item	# Indirect access
	UNSPEC		= EnumGen.item	# Not (yet) specified memory region

	# Virtual operators used internally in awlsim, only.
	# These operators do not have standard AWL mnemonics.
	VIRT_ACCU	= EnumGen.item	# Accu
	VIRT_AR		= EnumGen.item	# AR
	VIRT_DBR	= EnumGen.item	# DB and DI registers

	EnumGen.end	# Operator types

	# Type to string map
	type2str = {
		IMM		: "IMMEDIATE",
		IMM_REAL	: "REAL",
		IMM_S5T		: "S5T",
		IMM_TIME	: "TIME",
		IMM_DATE	: "DATE",
		IMM_TOD		: "TOD",
		IMM_DT		: "DT",
		IMM_PTR		: "P#",

		MEM_E		: "E",
		MEM_A		: "A",
		MEM_M		: "M",
		MEM_L		: "L",
		MEM_VL		: "VL",
		MEM_DB		: "DB",
		MEM_DI		: "DI",
		MEM_T		: "T",
		MEM_Z		: "Z",
		MEM_PA		: "PA",
		MEM_PE		: "PE",

		MEM_DBLG	: "DBLG",
		MEM_DBNO	: "DBNO",
		MEM_DILG	: "DILG",
		MEM_DINO	: "DINO",
		MEM_AR2		: "AR2",

		MEM_STW		: "STW",
		MEM_STW_Z	: "==0",
		MEM_STW_NZ	: "<>0",
		MEM_STW_POS	: ">0",
		MEM_STW_NEG	: "<0",
		MEM_STW_POSZ	: ">=0",
		MEM_STW_NEGZ	: "<=0",
		MEM_STW_UO	: "UO",

		LBL_REF		: "LABEL",

		BLKREF_FC	: "BLOCK_FC",
		BLKREF_SFC	: "BLOCK_SFC",
		BLKREF_FB	: "BLOCK_FB",
		BLKREF_SFB	: "BLOCK_SFB",
		BLKREF_UDT	: "BLOCK_UDT",
		BLKREF_DB	: "BLOCK_DB",
		BLKREF_DI	: "BLOCK_DI",
		BLKREF_OB	: "BLOCK_OB",
		BLKREF_VAT	: "BLOCK_VAT",

		INDIRECT	: "__INDIRECT",

		VIRT_ACCU	: "__ACCU",
		VIRT_AR		: "__AR",
		VIRT_DBR	: "__DBR",
	}

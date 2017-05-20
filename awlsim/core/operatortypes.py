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


__all__ = [
	"AwlOperatorTypes",
]


class __AwlOperatorTypesClass(object): #+cdef
	def __init__(self):
		EnumGen.start	# Operator types

		self._IMM_START		= EnumGen.item
		self.IMM		= EnumGen.item	# Immediate value (constant)
		self.IMM_REAL		= EnumGen.item	# Real
		self.IMM_S5T		= EnumGen.item	# S5T immediate
		self.IMM_TIME		= EnumGen.item	# T# immediate
		self.IMM_DATE		= EnumGen.item	# D# immediate
		self.IMM_TOD		= EnumGen.item	# TOD# immediate
		self.IMM_DT		= EnumGen.item	# DT# immediate
		self.IMM_PTR		= EnumGen.item	# Pointer immediate (P#x.y, P#area x.y, P#DBn.DBX x.y)
		self.IMM_STR		= EnumGen.item	# STRING immediate ('abc')
		self._IMM_END		= EnumGen.item

		self.MEM_E		= EnumGen.item	# Input
		self.MEM_A		= EnumGen.item	# Output
		self.MEM_M		= EnumGen.item	# Flags
		self.MEM_L		= EnumGen.item	# Localstack
		self.MEM_VL		= EnumGen.item	# Parent localstack (indirect access)
		self.MEM_DB		= EnumGen.item	# Global datablock
		self.MEM_DI		= EnumGen.item	# Instance datablock
		self.MEM_T		= EnumGen.item	# Timer
		self.MEM_Z		= EnumGen.item	# Counter
		self.MEM_PA		= EnumGen.item	# Peripheral output
		self.MEM_PE		= EnumGen.item	# Peripheral input

		self.MEM_STW		= EnumGen.item	# Status word bit read
		self.MEM_STW_Z		= EnumGen.item	# Status word "==0" read
		self.MEM_STW_NZ		= EnumGen.item	# Status word "<>0" read
		self.MEM_STW_POS	= EnumGen.item	# Status word ">0" read
		self.MEM_STW_NEG	= EnumGen.item	# Status word "<0" read
		self.MEM_STW_POSZ	= EnumGen.item	# Status word ">=0" read
		self.MEM_STW_NEGZ	= EnumGen.item	# Status word "<=0" read
		self.MEM_STW_UO		= EnumGen.item	# Status word "UO" read

		self.MEM_DBLG		= EnumGen.item	# DB-register: DB length
		self.MEM_DBNO		= EnumGen.item	# DB-register: DB number
		self.MEM_DILG		= EnumGen.item	# DI-register: DB length
		self.MEM_DINO		= EnumGen.item	# DI-register: DB number

		self.MEM_AR2		= EnumGen.item	# AR2 register

		self.BLKREF_FC		= EnumGen.item	# FC reference
		self.BLKREF_SFC		= EnumGen.item	# SFC reference
		self.BLKREF_FB		= EnumGen.item	# FB reference
		self.BLKREF_SFB		= EnumGen.item	# SFB reference
		self.BLKREF_UDT		= EnumGen.item	# UDT reference
		self.BLKREF_DB		= EnumGen.item	# DB reference
		self.BLKREF_DI		= EnumGen.item	# DI reference
		self.BLKREF_OB		= EnumGen.item	# OB reference (only symbol table)
		self.BLKREF_VAT		= EnumGen.item	# VAT reference (only symbol table)
		self.MULTI_FB		= EnumGen.item	# FB multiinstance reference
		self.MULTI_SFB		= EnumGen.item	# SFB multiinstance reference

		self.LBL_REF		= EnumGen.item	# Label reference
		self.SYMBOLIC		= EnumGen.item	# Classic symbolic reference ("xyz")
		self.NAMED_LOCAL	= EnumGen.item	# Named local reference (#abc)
		self.NAMED_LOCAL_PTR	= EnumGen.item	# Pointer to named local (P##abc)
		self.NAMED_DBVAR	= EnumGen.item	# Named DB variable reference (DBx.VAR)

		self.INDIRECT		= EnumGen.item	# Indirect access
		self.UNSPEC		= EnumGen.item	# Not (yet) specified memory region

		# Virtual operators used internally in awlsim, only.
		# These operators do not have standard AWL mnemonics.
		self.VIRT_ACCU		= EnumGen.item	# Accu
		self.VIRT_AR		= EnumGen.item	# AR
		self.VIRT_DBR		= EnumGen.item	# DB and DI registers

		EnumGen.end	# Operator types

		# Type to string map
		self.type2str = {
			self.IMM		: "IMMEDIATE",
			self.IMM_REAL		: "REAL",
			self.IMM_S5T		: "S5T",
			self.IMM_TIME		: "TIME",
			self.IMM_DATE		: "DATE",
			self.IMM_TOD		: "TOD",
			self.IMM_DT		: "DT",
			self.IMM_PTR		: "P#",

			self.MEM_E		: "E",
			self.MEM_A		: "A",
			self.MEM_M		: "M",
			self.MEM_L		: "L",
			self.MEM_VL		: "VL",
			self.MEM_DB		: "DB",
			self.MEM_DI		: "DI",
			self.MEM_T		: "T",
			self.MEM_Z		: "Z",
			self.MEM_PA		: "PA",
			self.MEM_PE		: "PE",

			self.MEM_DBLG		: "DBLG",
			self.MEM_DBNO		: "DBNO",
			self.MEM_DILG		: "DILG",
			self.MEM_DINO		: "DINO",
			self.MEM_AR2		: "AR2",

			self.MEM_STW		: "STW",
			self.MEM_STW_Z		: "==0",
			self.MEM_STW_NZ		: "<>0",
			self.MEM_STW_POS	: ">0",
			self.MEM_STW_NEG	: "<0",
			self.MEM_STW_POSZ	: ">=0",
			self.MEM_STW_NEGZ	: "<=0",
			self.MEM_STW_UO		: "UO",

			self.LBL_REF		: "LABEL",

			self.BLKREF_FC		: "BLOCK_FC",
			self.BLKREF_SFC		: "BLOCK_SFC",
			self.BLKREF_FB		: "BLOCK_FB",
			self.BLKREF_SFB		: "BLOCK_SFB",
			self.BLKREF_UDT		: "BLOCK_UDT",
			self.BLKREF_DB		: "BLOCK_DB",
			self.BLKREF_DI		: "BLOCK_DI",
			self.BLKREF_OB		: "BLOCK_OB",
			self.BLKREF_VAT		: "BLOCK_VAT",

			self.INDIRECT		: "__INDIRECT",

			self.VIRT_ACCU		: "__ACCU",
			self.VIRT_AR		: "__AR",
			self.VIRT_DBR		: "__DBR",
		}

AwlOperatorTypes = __AwlOperatorTypesClass() #+cdef-public-__AwlOperatorTypesClass

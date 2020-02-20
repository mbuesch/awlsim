# -*- coding: utf-8 -*-
#
# AWL simulator - Operator types
#
# Copyright 2012-2020 Michael Buesch <m@bues.ch>
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
#from awlsim.common.cython_support cimport * #@cy
from awlsim.common.compat import *

from awlsim.common.enumeration import *
from awlsim.common.util import *
from awlsim.common.exceptions import *

from awlsim.core.memory import * #+cimport


__all__ = [
	"AwlOperatorTypes",
	"AwlOperatorWidths",
	"makeAwlOperatorWidthMask",
	"AwlIndirectOpConst",
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
			self._IMM_START		: "_IMM_START",
			self.IMM		: "IMMEDIATE",
			self.IMM_REAL		: "REAL",
			self.IMM_S5T		: "S5T",
			self.IMM_TIME		: "TIME",
			self.IMM_DATE		: "DATE",
			self.IMM_TOD		: "TOD",
			self.IMM_DT		: "DT",
			self.IMM_PTR		: "P#",
			self.IMM_STR		: "STRING",
			self._IMM_END		: "_IMM_END",

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

			self.MEM_STW		: "STW",
			self.MEM_STW_Z		: "==0",
			self.MEM_STW_NZ		: "<>0",
			self.MEM_STW_POS	: ">0",
			self.MEM_STW_NEG	: "<0",
			self.MEM_STW_POSZ	: ">=0",
			self.MEM_STW_NEGZ	: "<=0",
			self.MEM_STW_UO		: "UO",

			self.MEM_DBLG		: "DBLG",
			self.MEM_DBNO		: "DBNO",
			self.MEM_DILG		: "DILG",
			self.MEM_DINO		: "DINO",

			self.MEM_AR2		: "AR2",

			self.BLKREF_FC		: "BLOCK_FC",
			self.BLKREF_SFC		: "BLOCK_SFC",
			self.BLKREF_FB		: "BLOCK_FB",
			self.BLKREF_SFB		: "BLOCK_SFB",
			self.BLKREF_UDT		: "BLOCK_UDT",
			self.BLKREF_DB		: "BLOCK_DB",
			self.BLKREF_DI		: "BLOCK_DI",
			self.BLKREF_OB		: "BLOCK_OB",
			self.BLKREF_VAT		: "BLOCK_VAT",
			self.MULTI_FB		: "MULTI_FB",
			self.MULTI_SFB		: "MULTI_SFB",

			self.LBL_REF		: "LABEL",
			self.SYMBOLIC		: "SYMBOLIC",
			self.NAMED_LOCAL	: "NAMED_LOCAL",
			self.NAMED_LOCAL_PTR	: "NAMED_LOCAL_PTR",
			self.NAMED_DBVAR	: "NAMED_DBVAR",

			self.INDIRECT		: "INDIRECT",
			self.UNSPEC		: "UNSPEC",

			self.VIRT_ACCU		: "__ACCU",
			self.VIRT_AR		: "__AR",
			self.VIRT_DBR		: "__DBR",
		}

AwlOperatorTypes = __AwlOperatorTypesClass() #+cdef-public-__AwlOperatorTypesClass


# Make a "width mask".
# That is a bit mask representing a width.
# Different width masks can be ORed together.
# It must be assured that width is either 1, bigger than 32 or a multiple of 8.
# The Cython variant of this function is defined in .pxd.in
def makeAwlOperatorWidthMask(width):					#@nocy
	return (1 << (width // 8)) if (width <= 32) else 0x10000	#@nocy

class __AwlOperatorWidthsClass(object): #+cdef
	def __init__(self):
		self.WIDTH_MASK_1	= makeAwlOperatorWidthMask(1)
		self.WIDTH_MASK_8	= makeAwlOperatorWidthMask(8)
		self.WIDTH_MASK_16	= makeAwlOperatorWidthMask(16)
		self.WIDTH_MASK_24	= makeAwlOperatorWidthMask(24)
		self.WIDTH_MASK_32	= makeAwlOperatorWidthMask(32)
		self.WIDTH_MASK_COMP	= makeAwlOperatorWidthMask(0xFFFF) # Compound type

		self.WIDTH_MASK_8_16_32	= self.WIDTH_MASK_8 |\
					  self.WIDTH_MASK_16 |\
					  self.WIDTH_MASK_32

		self.WIDTH_MASK_SCALAR	= self.WIDTH_MASK_1 |\
					  self.WIDTH_MASK_8_16_32

		self.WIDTH_MASK_ALL	= self.WIDTH_MASK_SCALAR |\
					  self.WIDTH_MASK_24 |\
					  self.WIDTH_MASK_COMP

	def maskToList(self, widthMask):
		ret = []
		if widthMask & self.WIDTH_MASK_1:
			ret.append(1)
		if widthMask & self.WIDTH_MASK_8:
			ret.append(8)
		if widthMask & self.WIDTH_MASK_16:
			ret.append(16)
		if widthMask & self.WIDTH_MASK_24:
			ret.append(24)
		if widthMask & self.WIDTH_MASK_32:
			ret.append(32)
		return ret

AwlOperatorWidths = __AwlOperatorWidthsClass() #+cdef-public-__AwlOperatorWidthsClass

assert(AwlOperatorWidths.WIDTH_MASK_1 == (1 << 0))
assert(AwlOperatorWidths.WIDTH_MASK_8 == (1 << 1))
assert(AwlOperatorWidths.WIDTH_MASK_16 == (1 << 2))
assert(AwlOperatorWidths.WIDTH_MASK_24 == (1 << 3))
assert(AwlOperatorWidths.WIDTH_MASK_32 == (1 << 4))
assert(AwlOperatorWidths.WIDTH_MASK_COMP == (1 << 16))


class __AwlIndirectOpConstClass(object): #+cdef
	def __init__(self):
		# Address register
		self.AR_NONE		= 0	# No address register
		self.AR_1		= 1	# Use AR1
		self.AR_2		= 2	# Use AR2

		# Area code position
		self.AREA_SHIFT		= 24
		self.AREA_MASK		= 0xFF
		self.AREA_MASK_S	= self.AREA_MASK << self.AREA_SHIFT

		# Area codes
		self.AREA_NONE		= 0x00
		self.AREA_P		= 0x80	# Peripheral area
		self.AREA_E		= 0x81	# Input
		self.AREA_A		= 0x82	# Output
		self.AREA_M		= 0x83	# Flags
		self.AREA_DB		= 0x84	# Global datablock
		self.AREA_DI		= 0x85	# Instance datablock
		self.AREA_L		= 0x86	# Localstack
		self.AREA_VL		= 0x87	# Parent localstack

		# Area codes (shifted to the pointer location)
		self.AREA_NONE_S	= self.AREA_NONE << self.AREA_SHIFT
		self.AREA_P_S		= self.AREA_P << self.AREA_SHIFT
		self.AREA_E_S		= self.AREA_E << self.AREA_SHIFT
		self.AREA_A_S		= self.AREA_A << self.AREA_SHIFT
		self.AREA_M_S		= self.AREA_M << self.AREA_SHIFT
		self.AREA_DB_S		= self.AREA_DB << self.AREA_SHIFT
		self.AREA_DI_S		= self.AREA_DI << self.AREA_SHIFT
		self.AREA_L_S		= self.AREA_L << self.AREA_SHIFT
		self.AREA_VL_S		= self.AREA_VL << self.AREA_SHIFT

		# Pointer area constants
		self.EXT_AREA_MASK	= 0xFFFF
		self.EXT_AREA_MASK_S	= self.EXT_AREA_MASK << self.AREA_SHIFT

		# Extended area encodings. Only used for internal purposes.
		# These are not used in the interpreted AWL code.
		self.EXT_AREA_T			= 0x01FF	# Timer
		self.EXT_AREA_Z			= 0x02FF	# Counter
		self.EXT_AREA_BLKREF_DB		= 0x03FF	# DB block reference
		self.EXT_AREA_BLKREF_DI		= 0x04FF	# DI block reference
		self.EXT_AREA_BLKREF_FB		= 0x05FF	# FB block reference
		self.EXT_AREA_BLKREF_FC		= 0x06FF	# FC block reference

		# Extended area encodings (shifted).
		self.EXT_AREA_T_S		= self.EXT_AREA_T << self.AREA_SHIFT
		self.EXT_AREA_Z_S		= self.EXT_AREA_Z << self.AREA_SHIFT
		self.EXT_AREA_BLKREF_DB_S	= self.EXT_AREA_BLKREF_DB << self.AREA_SHIFT
		self.EXT_AREA_BLKREF_DI_S	= self.EXT_AREA_BLKREF_DI << self.AREA_SHIFT
		self.EXT_AREA_BLKREF_FB_S	= self.EXT_AREA_BLKREF_FB << self.AREA_SHIFT
		self.EXT_AREA_BLKREF_FC_S	= self.EXT_AREA_BLKREF_FC << self.AREA_SHIFT

	# Method for converting area code to operator type for store and fetch operations.
	def area2optype(self, area, store): #@nocy
#@cy	cdef int32_t area2optype(self, uint64_t area, _Bool store):
		if area == self.AREA_M_S:
			return AwlOperatorTypes.MEM_M
		elif area == self.AREA_E_S:
			return AwlOperatorTypes.MEM_E
		elif area == self.AREA_A_S:
			return AwlOperatorTypes.MEM_A
		elif area == self.AREA_L_S:
			return AwlOperatorTypes.MEM_L
		elif area == self.AREA_VL_S:
			return AwlOperatorTypes.MEM_VL
		elif area == self.AREA_DB_S:
			return AwlOperatorTypes.MEM_DB
		elif area == self.AREA_DI_S:
			return AwlOperatorTypes.MEM_DI
		elif area == self.EXT_AREA_T_S:
			return AwlOperatorTypes.MEM_T
		elif area == self.EXT_AREA_Z_S:
			return AwlOperatorTypes.MEM_Z
		elif area == self.AREA_P_S:
			if store:
				return AwlOperatorTypes.MEM_PA
			return AwlOperatorTypes.MEM_PE
		elif area == self.EXT_AREA_BLKREF_DB_S:
			return AwlOperatorTypes.BLKREF_DB
		elif area == self.EXT_AREA_BLKREF_DI_S:
			return AwlOperatorTypes.BLKREF_DI
		elif area == self.EXT_AREA_BLKREF_FB_S:
			return AwlOperatorTypes.BLKREF_FB
		elif area == self.EXT_AREA_BLKREF_FC_S:
			return AwlOperatorTypes.BLKREF_FC
		return -1

	# Method for converting operator type to area code
	def optype2area(self, operType): #@nocy
#@cy	cdef int64_t optype2area(self, uint32_t operType):
		if operType == AwlOperatorTypes.MEM_M:
			return self.AREA_M_S
		elif operType == AwlOperatorTypes.MEM_E:
			return self.AREA_E_S
		elif operType == AwlOperatorTypes.MEM_A:
			return self.AREA_A_S
		elif operType == AwlOperatorTypes.MEM_L:
			return self.AREA_L_S
		elif operType == AwlOperatorTypes.MEM_VL:
			return self.AREA_VL_S
		elif operType == AwlOperatorTypes.MEM_DB or\
		     operType == AwlOperatorTypes.NAMED_DBVAR:
			return self.AREA_DB_S
		elif operType == AwlOperatorTypes.MEM_DI or\
		     operType == AwlOperatorTypes.MULTI_FB or\
		     operType == AwlOperatorTypes.MULTI_SFB:
			return self.AREA_DI_S
		elif operType == AwlOperatorTypes.MEM_T:
			return self.EXT_AREA_T_S
		elif operType == AwlOperatorTypes.MEM_Z:
			return self.EXT_AREA_Z_S
		elif operType == AwlOperatorTypes.MEM_PE or\
		     operType == AwlOperatorTypes.MEM_PA:
			return self.AREA_P_S
		elif operType == AwlOperatorTypes.BLKREF_DB:
			return self.EXT_AREA_BLKREF_DB_S
		elif operType == AwlOperatorTypes.BLKREF_DI:
			return self.EXT_AREA_BLKREF_DI_S
		elif operType == AwlOperatorTypes.BLKREF_FB:
			return self.EXT_AREA_BLKREF_FB_S
		elif operType == AwlOperatorTypes.BLKREF_FC:
			return self.EXT_AREA_BLKREF_FC_S
		elif operType == AwlOperatorTypes.UNSPEC:
			return self.AREA_NONE_S
		return -1

AwlIndirectOpConst = __AwlIndirectOpConstClass() #+cdef-public-__AwlIndirectOpConstClass

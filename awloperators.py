# -*- coding: utf-8 -*-
#
# AWL simulator - operators
# Copyright 2012 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from awlstatusword import *
from util import *


class AwlOperator(object):
	# Operator types
	IMM		= 0	# Immediate value (constant)
	IMM_S5T		= 1	# S5T immediate

	MEM_E		= 100	# Input
	MEM_A		= 101	# Output
	MEM_M		= 102	# Flags
	MEM_L		= 103	# Localstack
	MEM_D		= 104	# Datamodule
	MEM_T		= 105	# Timer
	MEM_Z		= 106	# Counter

	MEM_STW		= 200	# Status word bit read
	MEM_STW_Z	= 201	# Status word "==0" read
	MEM_STW_NZ	= 202	# Status word "<>0" read
	MEM_STW_POS	= 203	# Status word ">0" read
	MEM_STW_NEG	= 204	# Status word "<0" read
	MEM_STW_POSZ	= 205	# Status word ">=0" read
	MEM_STW_NEGZ	= 206	# Status word "<=0" read
	MEM_STW_UO	= 207	# Status word "UO" read

	LBL_REF		= 300	# Label reference

	BLKREF_FC	= 400	# FC reference
	BLKREF_SFC	= 401	# SFC reference
	BLKREF_FB	= 402	# FB reference
	BLKREF_SFB	= 403	# SFB reference
	BLKREF_DB	= 404	# DB reference

	# Virtual operators used for debugging of the simulator
	VIRT_ACCU	= 1000	# Accu
	VIRT_AR		= 1001	# AR

	def __init__(self, type, width, offset, bitOffset=0):
		self.type = type
		self.width = width
		self.offset = offset
		self.bitOffset = bitOffset
		self.labelIndex = None
		self.insn = None

	def setInsn(self, newInsn):
		self.insn = newInsn

	@property
	def immediate(self):
		return self.offset

	@property
	def label(self):
		return self.offset

	def setLabelIndex(self, newLabelIndex):
		self.labelIndex = newLabelIndex

	type2str = {
		MEM_STW_Z	: "==0",
                MEM_STW_NZ	: "<>0",
                MEM_STW_POS	: ">0",
                MEM_STW_NEG	: "<0",
                MEM_STW_POSZ	: ">=0",
                MEM_STW_NEGZ	: "<=0",
                MEM_STW_UO	: "UO",
	}

	type2prefix = {
		MEM_E		: "E",
		MEM_A		: "A",
		MEM_M		: "M",
		MEM_L		: "L",
		MEM_D		: "D",
		MEM_T		: "T",
		MEM_Z		: "Z",
	}

	def __repr__(self):
		try:
			return self.type2str[self.type]
		except KeyError as e:
			pass
		if self.type == self.IMM:
			return str(self.immediate)
		elif self.type == self.IMM_S5T:
			return "S5T#" #TODO
		elif self.type in (self.MEM_A, self.MEM_E,
				   self.MEM_M, self.MEM_L):
			pfx = self.type2prefix[self.type]
			if self.width == 1:
				return "%s %d.%d" %\
					(pfx, self.offset, self.bitOffset)
			elif self.width == 8:
				return "%sB %d" % (pfx, self.offset)
			elif self.width == 16:
				return "%sW %d" % (pfx, self.offset)
			elif self.width == 32:
				return "%sD %d" % (pfx, self.offset)
		elif self.type == self.MEM_D:
			if self.width == 1:
				return "DBX %d.%d" % (self.offset, self.bitOffset)
			elif self.width == 8:
				return "DBB %d" % self.offset
			elif self.width == 16:
				return "DBW %d" % self.offset
			elif self.width == 32:
				return "DBD %d" % self.offset
		elif self.type == self.MEM_T:
			return "T %d" % self.offset
		elif self.type == self.MEM_Z:
			return "Z %d" % self.offset
		elif self.type == self.MEM_STW:
			return "__STW " + S7StatusWord.nr2name[self.bitOffset]
		elif self.type == self.LBL_REF:
			return self.label
		elif self.type == self.VIRT_ACCU:
			return "__ACCU %d" % self.offset
		elif self.type == self.VIRT_AR:
			return "__AR %d" % self.offset
		#TODO
		assert(0)

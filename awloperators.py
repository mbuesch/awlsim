# -*- coding: utf-8 -*-
#
# AWL simulator - operators
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from awlstatusword import *
from util import *


class AwlOperator(object):
	enum.start	# Operator types

	IMM		= enum.item	# Immediate value (constant)
	IMM_REAL	= enum.item	# Real
	IMM_S5T		= enum.item	# S5T immediate
	IMM_TIME	= enum.item	# T# immediate
	IMM_DATE	= enum.item	# D# immediate
	IMM_TOD		= enum.item	# TOD# immediate

	MEM_E		= enum.item	# Input
	MEM_A		= enum.item	# Output
	MEM_M		= enum.item	# Flags
	MEM_L		= enum.item	# Localstack
	MEM_DB		= enum.item	# Global datablock
	MEM_DI		= enum.item	# Instance datablock
	MEM_T		= enum.item	# Timer
	MEM_Z		= enum.item	# Counter
	MEM_PA		= enum.item	# Peripheral output
	MEM_PE		= enum.item	# Peripheral input

	MEM_STW		= enum.item	# Status word bit read
	MEM_STW_Z	= enum.item	# Status word "==0" read
	MEM_STW_NZ	= enum.item	# Status word "<>0" read
	MEM_STW_POS	= enum.item	# Status word ">0" read
	MEM_STW_NEG	= enum.item	# Status word "<0" read
	MEM_STW_POSZ	= enum.item	# Status word ">=0" read
	MEM_STW_NEGZ	= enum.item	# Status word "<=0" read
	MEM_STW_UO	= enum.item	# Status word "UO" read

	LBL_REF		= enum.item	# Label reference

	BLKREF_FC	= enum.item	# FC reference
	BLKREF_SFC	= enum.item	# SFC reference
	BLKREF_FB	= enum.item	# FB reference
	BLKREF_SFB	= enum.item	# SFB reference
	BLKREF_DB	= enum.item	# DB reference
	BLKREF_DI	= enum.item	# DI reference

	NAMED_LOCAL	= enum.item	# Named local reference (#abc)
	INTERF_DB	= enum.item	# Interface-DB access (translated NAMED_LOCAL)

	# Virtual operators used for debugging of the simulator
	VIRT_ACCU	= enum.item	# Accu
	VIRT_AR		= enum.item	# AR

	enum.end	# Operator types

	# TODO: Use AwlOffset
	def __init__(self, type, width, offset, bitOffset=0):
		self.type = type
		self.width = width
		self.offset = offset
		self.bitOffset = bitOffset
		self.labelIndex = None
		self.insn = None
		self.setExtended(False)

	def setInsn(self, newInsn):
		self.insn = newInsn

	def setExtended(self, isExtended):
		self.isExtended = isExtended

	def setType(self, newType):
		self.type = newType

	def setOffset(self, newByteOffset, newBitOffset):
		self.offset = newByteOffset
		self.bitOffset = newBitOffset

	def setWidth(self, newWidth):
		self.width = newWidth

	@property
	def immediate(self):
		return self.offset

	@property
	def label(self):
		return self.offset

	def setLabelIndex(self, newLabelIndex):
		self.labelIndex = newLabelIndex

	def assertType(self, types, lowerLimit=None, upperLimit=None):
		if not isinstance(types, list) and\
		   not isinstance(types, tuple):
			types = [ types, ]
		if not self.type in types:
			raise AwlSimError("Operator is type is invalid")
		if lowerLimit is not None:
			if self.offset < lowerLimit:
				raise AwlSimError("Operator value too small")
		if upperLimit is not None:
			if self.offset > upperLimit:
				raise AwlSimError("Operator value too big")

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
		MEM_T		: "T",
		MEM_Z		: "Z",
	}

	def __repr__(self):
		try:
			return self.type2str[self.type]
		except KeyError as e:
			pass
		if self.type == self.IMM:
			if self.width == 16:
				return str(self.immediate)
			elif self.width == 32:
				return "L#" + str(self.immediate)
		if self.type == self.IMM_REAL:
			return str(dwordToPyFloat(self.immediate))
		elif self.type == self.IMM_S5T:
			return "S5T#" #TODO
		elif self.type == self.IMM_TIME:
			return "T#" #TODO
		elif self.type == self.IMM_DATE:
			return "D#" #TODO
		elif self.type == self.IMM_TOD:
			return "TOD#" #TODO
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
		elif self.type == self.MEM_DB:
			if self.width == 1:
				return "DBX %d.%d" % (self.offset, self.bitOffset)
			elif self.width == 8:
				return "DBB %d" % self.offset
			elif self.width == 16:
				return "DBW %d" % self.offset
			elif self.width == 32:
				return "DBD %d" % self.offset
		elif self.type == self.MEM_DI:
			if self.width == 1:
				return "DIX %d.%d" % (self.offset, self.bitOffset)
			elif self.width == 8:
				return "DIB %d" % self.offset
			elif self.width == 16:
				return "DIW %d" % self.offset
			elif self.width == 32:
				return "DID %d" % self.offset
		elif self.type == self.MEM_T:
			return "T %d" % self.offset
		elif self.type == self.MEM_Z:
			return "Z %d" % self.offset
		elif self.type == self.MEM_PA:
			if self.width == 8:
				return "PAB %d" % self.offset
			elif self.width == 16:
				return "PAW %d" % self.offset
			elif self.width == 32:
				return "PAD %d" % self.offset
		elif self.type == self.MEM_PE:
			if self.width == 8:
				return "PEB %d" % self.offset
			elif self.width == 16:
				return "PEW %d" % self.offset
			elif self.width == 32:
				return "PED %d" % self.offset
		elif self.type == self.MEM_STW:
			return "__STW " + S7StatusWord.nr2name[self.bitOffset]
		elif self.type == self.LBL_REF:
			return self.label
		elif self.type == self.BLKREF_FC:
			return "FC %d" % self.offset
		elif self.type == self.BLKREF_SFC:
			return "SFC %d" % self.offset
		elif self.type == self.BLKREF_FB:
			return "FB %d" % self.offset
		elif self.type == self.BLKREF_SFB:
			return "SFB %d" % self.offset
		elif self.type == self.BLKREF_DB:
			return "DB %d" % self.offset
		elif self.type == self.BLKREF_DI:
			return "DI %d" % self.offset
		elif self.type == self.NAMED_LOCAL:
			return "#%s" % self.offset
		elif self.type == self.INTERF_DB:
			return "__INTERFACE_DB" #FIXME
		elif self.type == self.VIRT_ACCU:
			return "__ACCU %d" % self.offset
		elif self.type == self.VIRT_AR:
			return "__AR %d" % self.offset
		assert(0)

	@classmethod
	def fetchFromByteArray(cls, array, operator):
		width, byteOff, bitOff =\
			operator.width, operator.offset, operator.bitOffset
		try:
			if width == 1:
				return array[byteOff].getBit(bitOff)
			elif width == 8:
				assert(bitOff == 0)
				return array[byteOff].get()
			elif width == 16:
				assert(bitOff == 0)
				return (array[byteOff].get() << 8) |\
				       array[byteOff + 1].get()
			elif width == 32:
				assert(bitOff == 0)
				return (array[byteOff].get() << 24) |\
				       (array[byteOff + 1].get() << 16) |\
				       (array[byteOff + 2].get() << 8) |\
				       array[byteOff + 3].get()
		except IndexError as e:
			raise AwlSimError("fetch: Operator offset out of range")
		assert(0)

	@classmethod
	def storeToByteArray(cls, array, operator, value):
		width, byteOff, bitOff =\
			operator.width, operator.offset, operator.bitOffset
		try:
			if width == 1:
				array[byteOff].setBitValue(bitOff, value)
			elif width == 8:
				assert(bitOff == 0)
				array[byteOff].set(value)
			elif width == 16:
				assert(bitOff == 0)
				array[byteOff].set(value >> 8)
				array[byteOff + 1].set(value)
			elif width == 32:
				assert(bitOff == 0)
				array[byteOff].set(value >> 24)
				array[byteOff + 1].set(value >> 16)
				array[byteOff + 2].set(value >> 8)
				array[byteOff + 3].set(value)
			else:
				assert(0)
		except IndexError as e:
			raise AwlSimError("store: Operator offset out of range")

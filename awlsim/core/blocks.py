# -*- coding: utf-8 -*-
#
# AWL simulator - blocks
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

from awlsim.common.refmanager import *
from awlsim.common.blockinfo import *
from awlsim.common.wordpacker import *
from awlsim.common.exceptions import *

from awlsim.core.blockinterface import *
from awlsim.core.labels import *
from awlsim.core.datatypes import *
from awlsim.core.memory import * #+cimport
from awlsim.core.operatortypes import * #+cimport
from awlsim.core.operators import * #+cimport
from awlsim.core.util import *
from awlsim.core.offset import * #+cimport
from awlsim.core.lstack import * #+cimport

import hashlib


__all__ = [
	"Block",
	"CodeBlock",
	"StaticCodeBlock",
	"OB",
	"FB",
	"FC",
]


class Block(object): #+cdef
	"""Base class for blocks (OBs, FCs, FBs, DBs, etc...)"""

	BLOCKTYPESTR	= "Block"
	IDENT_HASH	= hashlib.sha256

	def __init__(self, index):
		self.index = index
		self.sourceRef = None
		self.__identHash = None

	def setSourceRef(self, sourceManagerOrRef, inheritRef = False):
		self.sourceRef = ObjRef.make(
			name = lambda ref: str(ref.obj),
			managerOrRef = sourceManagerOrRef,
			obj = self,
			inheritRef = inheritRef)
		self.__identHash = None

	def destroySourceRef(self):
		if self.sourceRef:
			self.sourceRef.destroy()
			self.sourceRef = None
		self.__identHash = None

	def getSource(self):
		"""Get this block's source (AwlSource() object), if any.
		"""
		sourceRef = self.sourceRef
		if sourceRef:
			manager = sourceRef.manager
			if manager:
				return manager.source
		return None

	@property
	def identHash(self):
		if not self.__identHash:
			# Calculate the ident hash
			h = self.IDENT_HASH(self.BLOCKTYPESTR.encode(
					"utf-8", "strict"))
			h.update(WordPacker.toBytes(bytearray(2), 16, 0, self.index))
			source = self.getSource()
			if source:
				h.update(source.identHash)
			self.__identHash = h.digest()
		return self.__identHash

	def getBlockInfo(self):
		"""Get a BlockInfo instance for this block.
		"""
		# By default there is no BlockInfo. Override this method.
		return None

	def __repr__(self):
		return "%s %d" % (self.BLOCKTYPESTR, self.index)

class CodeBlock(Block): #+cdef
	"""Base class for code blocks (OBs, (S)FCs, (S)FBs)"""

	BLOCKTYPESTR	= "CodeBlock"

	# Simple and fast tests for checking block identity.
	# These are partially overridden in the subclasses.
	_isOB		= False
	_isFC		= False
	_isFB		= False
	_isSystemBlock	= False
	_isLibraryBlock	= False

	def __init__(self, insns, index, interface):
		self.isOB = self._isOB
		self.isFC = self._isFC
		self.isFB = self._isFB
		self.isSystemBlock = self._isSystemBlock
		self.isLibraryBlock = self._isLibraryBlock
		Block.__init__(self, index)

		self.insns = insns
		self.nrInsns = len(insns)
		self.labels = None
		self.interface = interface
		self.tempAllocation = 0		# The number of allocated TEMP bytes
		self.resolveLabels()

	def resolveLabels(self):
		if self.insns:
			self.labels = AwlLabel.resolveLabels(self.insns)
		else:
			self.labels = None

	def resolveSymbols(self):
		pass

	# Account for interface TEMP allocations and
	# direct TEMP (L, LB, LW, LD) accesses.
	def accountTempAllocations(self):
		directAlloc = 0

		def accountDirect(currentAlloc, oper):
			if oper.operType != AwlOperatorTypes.MEM_L:
				return currentAlloc
			offset = oper.offset + make_AwlOffset(0, oper.width)
			return max(offset.roundUp(2).byteOffset,
				   currentAlloc)

		for insn in self.insns:
			for oper in insn.ops:
				directAlloc = accountDirect(directAlloc,
							    oper)
			for param in insn.params:
				directAlloc = accountDirect(directAlloc,
							    param.rvalueOp)

		self.tempAllocation = max(self.interface.tempAllocation,
					  directAlloc)

class StaticCodeBlock(CodeBlock): #+cdef
	"""Base class for static code blocks. (system and library blocks)."""

	BLOCKTYPESTR	= "StaticCodeBlock"

	# Static interface definition.
	# To be overridden by the subclass.
	interfaceFields = {
		BlockInterfaceField.FTYPE_IN	: (),
		BlockInterfaceField.FTYPE_OUT	: (),
		BlockInterfaceField.FTYPE_INOUT	: (),
		BlockInterfaceField.FTYPE_STAT	: (),
		BlockInterfaceField.FTYPE_TEMP	: (),
	}

	# Set to True by the subclass, if the implementation is incomplete.
	broken = False

	def __init__(self, insns, index, interface):
		CodeBlock.__init__(self, insns, index, interface)

		# Register the interface.
		for ftype in (BlockInterfaceField.FTYPE_IN,
			      BlockInterfaceField.FTYPE_OUT,
			      BlockInterfaceField.FTYPE_INOUT,
			      BlockInterfaceField.FTYPE_STAT,
			      BlockInterfaceField.FTYPE_TEMP):
			try:
				fields = self.interfaceFields[ftype]
			except KeyError:
				continue
			for field in fields:
				if ftype == BlockInterfaceField.FTYPE_IN:
					self.interface.addField_IN(field)
				elif ftype == BlockInterfaceField.FTYPE_OUT:
					self.interface.addField_OUT(field)
				elif ftype == BlockInterfaceField.FTYPE_INOUT:
					self.interface.addField_INOUT(field)
				elif ftype == BlockInterfaceField.FTYPE_STAT:
					self.interface.addField_STAT(field)
				elif ftype == BlockInterfaceField.FTYPE_TEMP:
					self.interface.addField_TEMP(field)
				else:
					assert(0)

class OB(CodeBlock): #+cdef

	BLOCKTYPESTR	= "OB"
	_isOB = True

	def __init__(self, insns, index):
		CodeBlock.__init__(self, insns, index, OBInterface())

		self.lstack = LStackAllocator(0)

	def getBlockInfo(self):
		"""Get a BlockInfo instance for this block.
		"""
		return BlockInfo(blockType = BlockInfo.TYPE_OB,
				 blockIndex = self.index,
				 identHash = self.identHash)

class FB(CodeBlock): #+cdef

	BLOCKTYPESTR	= "FB"
	_isFB = True

	def __init__(self, insns, index):
		CodeBlock.__init__(self, insns, index, FBInterface())

	def getBlockInfo(self):
		"""Get a BlockInfo instance for this block.
		"""
		return BlockInfo(blockType = BlockInfo.TYPE_FB,
				 blockIndex = self.index,
				 identHash = self.identHash)

class FC(CodeBlock): #+cdef

	BLOCKTYPESTR	= "FC"
	_isFC = True

	def __init__(self, insns, index):
		CodeBlock.__init__(self, insns, index, FCInterface())

	def getBlockInfo(self):
		"""Get a BlockInfo instance for this block.
		"""
		return BlockInfo(blockType = BlockInfo.TYPE_FC,
				 blockIndex = self.index,
				 identHash = self.identHash)

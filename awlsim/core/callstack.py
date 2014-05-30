# -*- coding: utf-8 -*-
#
# AWL simulator - CPU call stack
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

from awlsim.core.datatypes import *
from awlsim.core.blocks import *
from awlsim.core.parameters import *
from awlsim.core.objectcache import *
from awlsim.core.lstack import *
from awlsim.core.util import *


class CallStackElem(object):
	"Call stack element"

	lallocCache = ObjectCache(
		lambda cpu: LStackAllocator(cpu.specs.nrLocalbytes)
	)

	@classmethod
	def resetCache(cls):
		cls.lallocCache.reset()

	def __init__(self, cpu, block, instanceDB=None, parameters=(),
		     isRawCall=False):
		# Init the call stack element.
		# cpu -> The CPU this runs on.
		# block -> The code block that is being called.
		# instanceDB -> The instance-DB, if FB-call. Otherwise None.
		# parameters -> An iterable of AwlParamAssign instances
		#               representing the parameter assignments in CALL insn.
		# isRawCall -> True, if the calling instruction was UC or CC.
		(self.cpu,
		 self.parenStack,
		 self.ip,
		 self.lalloc,
		 self.block,
		 self.insns,
		 self.labels,
		 self.isRawCall,
		 self.instanceDB,
		 self.prevDbRegister,
		 self.prevDiRegister) = (
			cpu,
			[],
			0,
			self.lallocCache.get(cpu),
			block,
			block.insns,
			block.labels,
			isRawCall,
			instanceDB,
			cpu.dbRegister,
			cpu.diRegister,
		)
		self.localdata = self.lalloc.localdata
		self.lalloc.allocation = block.interface.tempAllocation

		# Handle parameters
		self.__outboundParams = []
		if parameters and not isRawCall:
			blockInterface = block.interface
			if blockInterface.hasInstanceDB:
				structInstance, callByRef_Types =\
					instanceDB.structInstance, \
					BlockInterface.callByRef_Types
				# This is a call to an FB.
				# Copy the inbound data into the instance DB
				# and add the outbound parameters to the list.
				for param in parameters:
					if param.isOutbound(blockInterface):
						# This is an outbound parameter.
						self.__outboundParams.append(param)
					if param.isInbound(blockInterface):
						# This is an inbound parameter.
						# Transfer data into DBI
						structField = param.getLvalueStructField(instanceDB)
						if structField.dataType.type in callByRef_Types:
							data = param.rvalueOp.resolve().value.byteOffset
						else:
							data = cpu.fetch(param.rvalueOp)
						structInstance.setFieldData(structField, data)
			else:
				# This is a call to an FC.
				# Prepare the interface (IN/OUT/INOUT) references.
				# self.interfRefs is a dict of AwlIndirectOps for the FC interface.
				#                 The key of self.interfRefs is the interface field index.
				#                 This dict is used by the CPU for lookup and resolve of
				#                 the FC interface r-value.
				self.interfRefs = {}
				for param in parameters:
					try:
						translator = self.__paramTrans[param.rvalueOp.type]
					except KeyError as e:
						raise AwlSimError("Do not know how to translate "
							"FC parameter '%s' for call. The specified "
							"actual-parameter is not allowed in this call." %\
							str(param))
					self.interfRefs[param.getInterfaceFieldIndex(blockInterface)] =\
						translator(self, param.rvalueOp)

	def __trans_IMM(self, oper):
		# 'oper' is an immediate.
		# Allocate space in the caller-L-stack.
		lalloc = self.cpu.callStackTop.lalloc
		loff = lalloc.alloc((oper.width // 8) if (oper.width > 8) else 1)
		# Write the immediate to the allocated space.
		WordPacker.toBytes(lalloc.localdata, oper.width, loff, oper.value)
		# Make an operator for the allocated space.
		return AwlOperator(AwlOperator.MEM_VL,
				   oper.width,
				   AwlOffset(loff, 0),
				   oper.insn)

	def __trans_MEM(self, oper):
		# 'oper' is a memory access.
		return oper

	def __trans_MEM_L(self, oper):
		# 'oper' is an L-stack memory access.
		return AwlOperator(oper.MEM_VL,
				   oper.width,
				   oper.value,
				   oper.insn)

	def __trans_MEM_VL(self, oper):
		# 'oper' is a VL-stack reference (i.e. the L-stack of the caller's caller).
		# Allocate space in the caller-L-stack and copy the data.
		lalloc = self.cpu.callStackTop.lalloc
		loff = lalloc.alloc((oper.width // 8) if (oper.width > 8) else 1)
		# Write the value to the allocated space.
		WordPacker.toBytes(lalloc.localdata, oper.width, loff,
				   self.cpu.fetch(oper))
		# Make an operator for the allocated space.
		return AwlOperator(AwlOperator.MEM_VL,
				   oper.width,
				   AwlOffset(loff, 0),
				   oper.insn)

	def __trans_MEM_DB(self, oper):
		# A parameter is forwarded from an FB to an FC.
		if oper.value.dbNumber is not None:
			# This is a fully qualified DB access.
			# Just forward it.
			return oper
		#FIXME the data should be copied
		offset = oper.value.dup()
		offset.dbNumber = self.cpu.dbRegister.index
		return AwlOperator(oper.MEM_DB,
				   oper.width,
				   offset,
				   oper.insn)

	def __trans_MEM_DI(self, oper):
		# A parameter is forwarded from an FB to an FC.
		#FIXME the data should be copied
		offset = oper.value.dup()
		offset.dbNumber = self.cpu.diRegister.index
		return AwlOperator(oper.MEM_DB,
				   oper.width,
				   offset,
				   oper.insn)

	def __trans_BLKREF(self, oper):
		# 'oper' is a block reference (e.g. 'FC 1', 'DB 10', ...)
		return oper

	def __trans_NAMED_LOCAL(self, oper):
		# 'oper' is a named-local (#abc)
		oper = self.cpu.callStackTop.interfRefs[oper.interfaceIndex]
		if oper.type == oper.MEM_VL:
			return self.__trans_MEM_VL(oper)
		if oper.type == oper.MEM_DB:
			return self.__trans_MEM_DB(oper)
		assert(0)

	# FC call parameter translators
	__paramTrans = {
		AwlOperator.IMM			: __trans_IMM,
		AwlOperator.IMM_REAL		: __trans_IMM,
		AwlOperator.IMM_S5T		: __trans_IMM,
		AwlOperator.IMM_TIME		: __trans_IMM,
		AwlOperator.IMM_DATE		: __trans_IMM,
		AwlOperator.IMM_TOD		: __trans_IMM,
		AwlOperator.IMM_DT		: __trans_IMM,
		AwlOperator.IMM_PTR		: __trans_IMM,

		AwlOperator.MEM_E		: __trans_MEM,
		AwlOperator.MEM_A		: __trans_MEM,
		AwlOperator.MEM_M		: __trans_MEM,
		AwlOperator.MEM_L		: __trans_MEM_L,
		AwlOperator.MEM_VL		: __trans_MEM_VL,
		AwlOperator.MEM_DB		: __trans_MEM_DB,
		AwlOperator.MEM_DI		: __trans_MEM_DI,
		AwlOperator.MEM_T		: __trans_MEM,
		AwlOperator.MEM_Z		: __trans_MEM,
		AwlOperator.MEM_PA		: __trans_MEM,
		AwlOperator.MEM_PE		: __trans_MEM,

		AwlOperator.BLKREF_FC		: __trans_BLKREF,
		AwlOperator.BLKREF_FB		: __trans_BLKREF,
		AwlOperator.BLKREF_DB		: __trans_BLKREF,

		AwlOperator.NAMED_LOCAL		: __trans_NAMED_LOCAL,
	}

	# Handle the exit from this code block.
	def handleBlockExit(self):
		if self.isRawCall:
			return
		if self.block.interface.hasInstanceDB:
			# We are returning from an FB.
			# Transfer data out of DBI.
			if self.__outboundParams:
				cpu = self.cpu
				instanceDB = cpu.diRegister
				structInstance = instanceDB.structInstance
				for param in self.__outboundParams:
					cpu.store(
						param.rvalueOp,
						structInstance.getFieldData(param.getLvalueStructField(instanceDB))
					)
			# Assign the DB/DI registers.
			self.cpu.dbRegister, self.cpu.diRegister = self.instanceDB, self.prevDiRegister
		else:
			# We are returning from an FC.
			# Assign the DB/DI registers.
			self.cpu.dbRegister, self.cpu.diRegister = self.prevDbRegister, self.prevDiRegister

	def destroy(self):
		# Only put it back into the cache, if the size didn't change.
		if len(self.localdata) == self.cpu.specs.nrLocalbytes:
			self.lallocCache.put(self.lalloc)

	def __repr__(self):
		return str(self.block)

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
		self.cpu = cpu
		self.parenStack = []
		self.ip = 0
		self.block = block
		self.insns = block.insns
		self.isRawCall = isRawCall
		self.instanceDB = instanceDB
		self.prevDbRegister = cpu.dbRegister
		self.prevDiRegister = cpu.diRegister
		self.lalloc = self.lallocCache.get(cpu)
		self.lalloc.allocation = block.interface.tempAllocation
		self.localdata = self.lalloc.localdata

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
					#TODO param interface and instanceDB assignments should
					#     be done at translation time.
					param.interface, param.instanceDB =\
						blockInterface, instanceDB
					if param.isOutbound:
						# This is an outbound parameter.
						self.__outboundParams.append(param)
					if param.isInbound:
						# This is an inbound parameter.
						# Transfer data into DBI
						structField = param.lValueStructField
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
					#TODO param interface assignment should
					#     be done at translation time.
					param.interface = blockInterface
					try:
						trans = self.__paramTrans[param.rvalueOp.type]
					except KeyError as e:
						raise AwlSimError("Do not know how to translate "
							"FC parameter '%s' for call. The specified "
							"actual-parameter is not allowed in this call." %\
							str(param))
					self.interfRefs[param.interfaceFieldIndex] = trans(self, param, param.rvalueOp)

	# Don't perform translation.
	# For various MEM and BLKREF accesses.
	def __trans_direct(self, param, rvalueOp):
		return rvalueOp

	# Copy parameter r-value to the caller-L-stack, if inbound
	# and register a copy-back request, if outbound.
	def __trans_copyToVL(self, param, rvalueOp):
		# Allocate space in the caller-L-stack.
		lalloc = self.cpu.callStackTop.lalloc
		loffset = lalloc.alloc(rvalueOp.width)
		if param.isInbound:
			# Write the value to the allocated space.
			WordPacker.toBytes(lalloc.localdata, rvalueOp.width,
					   loffset.byteOffset,
					   self.cpu.fetch(rvalueOp))
		# Make an operator for the allocated space.
		oper = AwlOperator(AwlOperator.MEM_VL,
				   rvalueOp.width,
				   loffset,
				   rvalueOp.insn)
		# If outbound, save param and operator for return from CALL.
		if param.isOutbound:
			param.scratchSpaceOp = oper
			self.__outboundParams.append(param)
		return oper

	# Translate L-stack access r-value.
	def __trans_MEM_L(self, param, rvalueOp):
		# r-value is an L-stack memory access.
		# Translate it to a VL-stack memory access.
		return AwlOperator(rvalueOp.MEM_VL,
				   rvalueOp.width,
				   rvalueOp.value,
				   rvalueOp.insn)

	# Translate DB access r-value.
	def __trans_MEM_DB(self, param, rvalueOp, copyToVL=False):
		# A parameter is forwarded from an FB to an FC.
		if rvalueOp.value.dbNumber is not None:
			# This is a fully qualified DB access.
			self.cpu.run_AUF(AwlOperator(AwlOperator.BLKREF_DB, 16,
						     AwlOffset(rvalueOp.value.dbNumber),
						     rvalueOp.insn))
			copyToVL = True
		if copyToVL:
			# Copy to caller-L-stack.
			return self.__trans_copyToVL(param, rvalueOp)
		# Do not copy to caller-L-stack. Just make a DB-reference.
		offset = rvalueOp.value.dup()
		return AwlOperator(rvalueOp.MEM_DB,
				   rvalueOp.width,
				   offset,
				   rvalueOp.insn)

	# Translate named local variable r-value.
	def __trans_NAMED_LOCAL(self, param, rvalueOp):
		# r-value is a named-local (#abc)
		oper = self.cpu.callStackTop.interfRefs[rvalueOp.interfaceIndex]
		if oper.type == oper.MEM_DB:
			return self.__trans_MEM_DB(param, oper, True)
		try:
			return self.__paramTrans[oper.type](self, param, oper)
		except KeyError as e:
			raise AwlSimBug("Unhandled call translation of "
				"named local parameter assignment:\n"
				"'%s' => r-value operator '%s'" %\
				(str(param), str(oper)))

	# FC call parameter translators
	__paramTrans = {
		AwlOperator.IMM			: __trans_copyToVL,
		AwlOperator.IMM_REAL		: __trans_copyToVL,
		AwlOperator.IMM_S5T		: __trans_copyToVL,
		AwlOperator.IMM_TIME		: __trans_copyToVL,
		AwlOperator.IMM_DATE		: __trans_copyToVL,
		AwlOperator.IMM_TOD		: __trans_copyToVL,
		AwlOperator.IMM_DT		: __trans_copyToVL,
		AwlOperator.IMM_PTR		: __trans_copyToVL,

		AwlOperator.MEM_E		: __trans_direct,
		AwlOperator.MEM_A		: __trans_direct,
		AwlOperator.MEM_M		: __trans_direct,
		AwlOperator.MEM_L		: __trans_MEM_L,
		AwlOperator.MEM_VL		: __trans_copyToVL,
		AwlOperator.MEM_DB		: __trans_MEM_DB,
		AwlOperator.MEM_DI		: __trans_copyToVL,
		AwlOperator.MEM_T		: __trans_direct,
		AwlOperator.MEM_Z		: __trans_direct,
		AwlOperator.MEM_PA		: __trans_direct,
		AwlOperator.MEM_PE		: __trans_direct,

		AwlOperator.BLKREF_FC		: __trans_direct,
		AwlOperator.BLKREF_FB		: __trans_direct,
		AwlOperator.BLKREF_DB		: __trans_direct,

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
						structInstance.getFieldData(param.lValueStructField)
					)
			# Assign the DB/DI registers.
			self.cpu.dbRegister, self.cpu.diRegister = self.instanceDB, self.prevDiRegister
		else:
			# We are returning from an FC.
			# Transfer data out of temporary sections.
			if self.__outboundParams:
				cpu = self.cpu
				for param in self.__outboundParams:
					cpu.store(
						param.rvalueOp,
						cpu.fetch(AwlOperator(AwlOperator.MEM_L,
								      param.scratchSpaceOp.width,
								      param.scratchSpaceOp.value))
					)
			# Assign the DB/DI registers.
			self.cpu.dbRegister, self.cpu.diRegister = self.prevDbRegister, self.prevDiRegister

	def destroy(self):
		# Only put it back into the cache, if the size didn't change.
		if len(self.localdata) == self.cpu.specs.nrLocalbytes:
			self.lallocCache.put(self.lalloc)

	def __repr__(self):
		return str(self.block)

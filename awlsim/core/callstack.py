# -*- coding: utf-8 -*-
#
# AWL simulator - CPU call stack
#
# Copyright 2012-2015 Michael Buesch <m@bues.ch>
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

	def __init__(self, cpu, block,
		     instanceDB=None, instanceBaseOffset=None,
		     parameters=(),
		     isRawCall=False):
		# Init the call stack element.
		# cpu -> The CPU this runs on.
		# block -> The code block that is being called.
		# instanceDB -> The instance-DB, if FB-call. Otherwise None.
		# instanceBaseOffset -> AwlOffset for use as AR2 instance base (multi-instance).
		#                       If None, AR2 is not modified.
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

		# Prepare the localdata stack.
		# (This also clears all previous allocations on the cached
		# region, if any.)
		self.lalloc = self.lallocCache.get(cpu)
		self.lalloc.reset(cpu.specs.nrLocalbytes, #FIXME we should not allow full nrLocalbytes range here.
				  block.tempAllocation)
		self.localdata = self.lalloc.localdata

		# Handle parameters
		self.__outboundParams = []
		if parameters and not isRawCall:
			if block.isFB:
				structInstance, callByRef_Types =\
					instanceDB.structInstance, \
					BlockInterface.callByRef_Types
				# This is a call to an FB.
				# Copy the inbound data into the instance DB
				# and add the outbound parameters to the list.
				for param in parameters:
					structField = param.lValueStructField
					if param.isOutbound:
						# This is an outbound parameter.
						# If it is not IN_OUT compound data type,
						# add it to the outbound parameter list
						# for use at BE time.
						if not param.isInbound or\
						   not structField.compound:
							self.__outboundParams.append(param)
					if param.isInbound:
						# This is an inbound parameter.
						# Check if this is an IN_OUT compound data
						# type variable. These are passed via DB-ptr.
						if param.isOutbound and\
						   structField.compound:
							# Compound data type with IN_OUT decl.
							# Make a DB-ptr to the actual data.
							data = self.__FB_trans_dbpointer(
									param, param.rvalueOp)
							# Get the DB-ptr struct field.
							structField = structField.finalOverride
						else:
							# Non-compound (basic) data type or
							# not IN_OUT declaration.
							# Get the actual data.
							if structField.dataType.type in callByRef_Types:
								# Do not fetch. Type is passed 'by reference'.
								# This is for TIMER, COUNTER, etc...
								data = param.rvalueOp.resolve().value.byteOffset
							else:
								data = cpu.fetch(param.rvalueOp)
						# Transfer data into DBI.
						structInstance.setFieldData(structField,
									    data,
									    instanceBaseOffset)
			else:
				# This is a call to an FC.
				# Prepare the interface (IN/OUT/INOUT) references.
				# self.interfRefs is a dict of AwlOperators for the FC interface.
				#                 The key of self.interfRefs is the interface field index.
				#                 This dict is used by the CPU for lookup and resolve of
				#                 the FC interface r-value.
				self.interfRefs = {}
				for param in parameters:
					try:
						trans = self.__FC_paramTrans[param.rvalueOp.type]
					except KeyError as e:
						raise AwlSimError("Do not know how to translate "
							"FC parameter '%s' for call. The specified "
							"actual-parameter is not allowed in this call." %\
							str(param))
					self.interfRefs[param.interfaceFieldIndex] = trans(self, param, param.rvalueOp)

		# Set AR2 to the specified multi-instance base
		# and save the old AR2 value.
		self.prevAR2value = cpu.ar2.get()
		if instanceBaseOffset is not None:
			cpu.ar2.set(AwlIndirectOp.AREA_DB |\
				    instanceBaseOffset.toPointerValue())

	# FB parameter translation:
	# Translate FB DB-pointer variable.
	# This is used for FB IN_OUT compound data type parameters.
	# Returns the actual DB-pointer data. (Not an operator!)
	def __FB_trans_dbpointer(self, param, rvalueOp):
		dbPtrData = ByteArray(6)
		dbNumber = rvalueOp.value.dbNumber
		if dbNumber is not None:
			dbPtrData[0] = (dbNumber >> 8) & 0xFF
			dbPtrData[1] = dbNumber & 0xFF
		ptr = rvalueOp.makePointerValue()
		dbPtrData[2] = (ptr >> 24) & 0xFF
		dbPtrData[3] = (ptr >> 16) & 0xFF
		dbPtrData[4] = (ptr >> 8) & 0xFF
		dbPtrData[5] = ptr & 0xFF
		return dbPtrData

	# FC parameter translation:
	# Don't perform translation.
	# For various MEM and BLKREF accesses.
	# Returns the translated rvalueOp.
	def __FC_trans_direct(self, param, rvalueOp):
		return rvalueOp

	# FC parameter translation:
	# Copy parameter r-value to the caller-L-stack, if inbound
	# and register a copy-back request, if outbound.
	# Returns the translated rvalueOp.
	def __FC_trans_copyToVL(self, param, rvalueOp):
		# Allocate space in the caller-L-stack.
		loffset = self.cpu.callStackTop.lalloc.alloc(rvalueOp.width)
		# Make an operator for the allocated space.
		oper = AwlOperator(AwlOperator.MEM_L,
				   rvalueOp.width,
				   loffset,
				   rvalueOp.insn)
		# Write the value to the allocated space.
		# This would only be necessary for inbound parameters,
		# but S7 supports read access to certain outbound
		# FC parameters as well. So copy the value unconditionally.
		self.cpu.store(oper, self.cpu.fetch(rvalueOp))
		# Change the operator to VL
		oper.type = oper.MEM_VL
		# If outbound, save param and operator for return from CALL.
		# Do not do this for immediates (which would be pointer
		# immediates, for example), because there is nothing to copy
		# back in that case.
		if param.isOutbound and not rvalueOp.isImmediate():
			param.scratchSpaceOp = oper
			self.__outboundParams.append(param)
		return oper

	# FC parameter translation:
	# Create a DB-pointer to the r-value in the caller's L-stack (VL).
	# Returns the translated rvalueOp.
	def __FC_trans_dbpointerInVL(self, param, rvalueOp):
		# Allocate space for the DB-ptr in the caller-L-stack
		loffset = self.cpu.callStackTop.lalloc.alloc(48) # 48 bits
		# Create and store the the DB-ptr to the allocated space.
		storeOper = AwlOperator(AwlOperator.MEM_L,
					16,
					loffset)
		if rvalueOp.type == AwlOperator.MEM_DI:
			dbNumber = self.cpu.diRegister.index
		else:
			dbNumber = rvalueOp.value.dbNumber
		self.cpu.store(storeOper, 0 if dbNumber is None else dbNumber)
		storeOper.value = loffset + AwlOffset(2)
		storeOper.width = 32
		area = AwlIndirectOp.optype2area[rvalueOp.type]
		if area == AwlIndirectOp.AREA_L:
			area = AwlIndirectOp.AREA_VL
		elif area == AwlIndirectOp.AREA_VL:
			raise AwlSimError("Cannot forward VL-parameter "
					  "to called FC")
		elif area == AwlIndirectOp.AREA_DI:
			area = AwlIndirectOp.AREA_DB
		self.cpu.store(storeOper,
			       area | rvalueOp.value.toPointerValue())
		# Return the operator for the DB pointer.
		return AwlOperator(AwlOperator.MEM_VL,
				   48,
				   loffset,
				   rvalueOp.insn)

	# FC parameter translation:
	# Copy the r-value to the caller's L-stack (VL) and also create
	# a DB-pointer to the copied value in VL.
	# Returns the translated rvalueOp.
	def __FC_trans_copyToVLWithDBPtr(self, param, rvalueOp):
		oper = self.__FC_trans_copyToVL(param, rvalueOp)
		oper.type = oper.MEM_L
		return self.__FC_trans_dbpointerInVL(param, oper)

	# FC parameter translation:
	# Translate L-stack access r-value.
	# Returns the translated rvalueOp.
	def __FC_trans_MEM_L(self, param, rvalueOp):
		# r-value is an L-stack memory access.
		if rvalueOp.compound:
			# rvalue is a compound data type.
			# Create a DB-pointer to it in VL.
			return self.__FC_trans_dbpointerInVL(param, rvalueOp)
		# Translate it to a VL-stack memory access.
		return AwlOperator(rvalueOp.MEM_VL,
				   rvalueOp.width,
				   rvalueOp.value,
				   rvalueOp.insn)

	# FC parameter translation:
	# Translate DB access r-value.
	# Returns the translated rvalueOp.
	def __FC_trans_MEM_DB(self, param, rvalueOp, copyToVL=False):
		# A (fully qualified) DB variable is passed to an FC.
		if rvalueOp.value.dbNumber is not None:
			# This is a fully qualified DB access.
			if rvalueOp.compound:
				# rvalue is a compound data type.
				# Create a DB-pointer to it in VL.
				return self.__FC_trans_dbpointerInVL(param, rvalueOp)
			# Basic data type.
			self.cpu.run_AUF(AwlOperator(AwlOperator.BLKREF_DB, 16,
						     AwlOffset(rvalueOp.value.dbNumber),
						     rvalueOp.insn))
			copyToVL = True
		if copyToVL:
			# Copy to caller-L-stack.
			return self.__FC_trans_copyToVL(param, rvalueOp)
		# Do not copy to caller-L-stack. Just make a DB-reference.
		offset = rvalueOp.value.dup()
		return AwlOperator(rvalueOp.MEM_DB,
				   rvalueOp.width,
				   offset,
				   rvalueOp.insn)

	# FC parameter translation:
	# Translate DI access r-value.
	# Returns the translated rvalueOp.
	def __FC_trans_MEM_DI(self, param, rvalueOp):
		# A parameter is forwarded from an FB to an FC
		if rvalueOp.compound:
			# rvalue is a compound data type.
			# Create a DB-pointer to it in VL.
			return self.__FC_trans_dbpointerInVL(param, rvalueOp)
		# Basic data type.
		# Copy the value to VL.
		return self.__FC_trans_copyToVL(param, rvalueOp)

	# FC parameter translation:
	# Translate named local variable r-value.
	# Returns the translated rvalueOp.
	def __FC_trans_NAMED_LOCAL(self, param, rvalueOp):
		# r-value is a named-local (#abc)
		oper = self.cpu.callStackTop.interfRefs[rvalueOp.interfaceIndex]
		if oper.type == oper.MEM_DB:
			return self.__FC_trans_MEM_DB(param, oper, True)
		try:
			return self.__FC_paramTrans[oper.type](self, param, oper)
		except KeyError as e:
			raise AwlSimBug("Unhandled call translation of "
				"named local parameter assignment:\n"
				"'%s' => r-value operator '%s'" %\
				(str(param), str(oper)))

	# FC call parameter translators
	__FC_paramTrans = {
		AwlOperator.IMM			: __FC_trans_copyToVL,
		AwlOperator.IMM_REAL		: __FC_trans_copyToVL,
		AwlOperator.IMM_S5T		: __FC_trans_copyToVL,
		AwlOperator.IMM_TIME		: __FC_trans_copyToVL,
		AwlOperator.IMM_DATE		: __FC_trans_copyToVL,
		AwlOperator.IMM_TOD		: __FC_trans_copyToVL,
		AwlOperator.IMM_DT		: __FC_trans_copyToVLWithDBPtr,
		AwlOperator.IMM_PTR		: __FC_trans_copyToVL,
		AwlOperator.IMM_STR		: __FC_trans_copyToVLWithDBPtr,

		AwlOperator.MEM_E		: __FC_trans_direct,
		AwlOperator.MEM_A		: __FC_trans_direct,
		AwlOperator.MEM_M		: __FC_trans_direct,
		AwlOperator.MEM_L		: __FC_trans_MEM_L,
		AwlOperator.MEM_VL		: __FC_trans_copyToVL,
		AwlOperator.MEM_DB		: __FC_trans_MEM_DB,
		AwlOperator.MEM_DI		: __FC_trans_MEM_DI,
		AwlOperator.MEM_T		: __FC_trans_direct,
		AwlOperator.MEM_Z		: __FC_trans_direct,
		AwlOperator.MEM_PA		: __FC_trans_direct,
		AwlOperator.MEM_PE		: __FC_trans_direct,

		AwlOperator.BLKREF_FC		: __FC_trans_direct,
		AwlOperator.BLKREF_FB		: __FC_trans_direct,
		AwlOperator.BLKREF_DB		: __FC_trans_direct,

		AwlOperator.NAMED_LOCAL		: __FC_trans_NAMED_LOCAL,
	}

	# Handle the exit from this code block.
	# This stack element (self) will already have been
	# removed from the CPU's call stack.
	def handleBlockExit(self):
		cpu = self.cpu
		if not self.isRawCall:
			# Handle outbound parameters.
			if self.block.isFB:
				# We are returning from an FB.

				# Get the multi-instance base offset.
				instanceBaseOffset = AwlOffset.fromPointerValue(cpu.ar2.get())
				# Restore the AR2 register.
				cpu.ar2.set(self.prevAR2value)

				# Transfer data out of DBI.
				structInstance = cpu.diRegister.structInstance
				for param in self.__outboundParams:
					cpu.store(
						param.rvalueOp,
						structInstance.getFieldData(param.lValueStructField,
									    instanceBaseOffset)
					)
				# Assign the DB/DI registers.
				cpu.dbRegister, cpu.diRegister = self.instanceDB, self.prevDiRegister
			else:
				# We are returning from an FC.

				# Restore the AR2 register.
				cpu.ar2.set(self.prevAR2value)

				# Transfer data out of temporary sections.
				for param in self.__outboundParams:
					cpu.store(
						param.rvalueOp,
						cpu.fetch(AwlOperator(AwlOperator.MEM_L,
								      param.scratchSpaceOp.width,
								      param.scratchSpaceOp.value))
					)
				# Assign the DB/DI registers.
				cpu.dbRegister, cpu.diRegister = self.prevDbRegister, self.prevDiRegister

		# Destroy this call stack element (self).
		# Put the L-stack back into the cache, if the size did not change.
		if len(self.localdata) == cpu.specs.nrLocalbytes:
			self.lallocCache.put(self.lalloc)

	def __repr__(self):
		return str(self.block)

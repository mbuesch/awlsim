# -*- coding: utf-8 -*-
#
# AWL simulator - CPU call stack
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

from awlsim.common.exceptions import *

from awlsim.core.datatypes import *
from awlsim.core.memory import * #+cimport
from awlsim.core.offset import * #+cimport
from awlsim.core.operatortypes import * #+cimport
from awlsim.core.operators import * #+cimport
from awlsim.core.blocks import * #+cimport
from awlsim.core.blockinterface import *
from awlsim.core.datablocks import * #+cimport
from awlsim.core.parameters import * #+cimport
from awlsim.core.util import *


__all__ = [
	"CallStackElem",
	"make_CallStackElem",
]


class CallStackElem(object): #+cdef
	"""Call stack element.
	"""

	__slots__ = (
		"prevCse",		# Previous call stack element (None if at OB level)
		"cpu",			# S7CPU that belongs to this CSE
		"parenStack",		# Active parenthesis stack
		"insns",		# Instruction list that is being executed
		"nrInsns",		# Length of the instruction list
		"ip",			# Current instruction pointer
		"block",		# CodeBlock that is being executed
		"isRawCall",		# True, if this call is raw (UC, CC)
		"instanceDB",		# Instance data block, if any
		"prevDbRegister",	# DB register from before this call
		"prevDiRegister",	# DI register from before this call
		"prevAR2value",		# AR2 register from before this call
		"_outboundParams",	# List of outbound AwlParamAssign. (Internal)
		"_interfRefs",		# List of translated interface references (Internal; FC only)
	)

	# Get an FC interface operand by interface field index.
	def getInterfIdxOper(self, interfaceFieldIndex): #@nocy
#@cy	cpdef AwlOperator getInterfIdxOper(self, uint32_t interfaceFieldIndex):
		try:
#@cy			if self._interfRefs is None:
#@cy				raise KeyError
			return self._interfRefs[interfaceFieldIndex]
		except (AttributeError, KeyError) as e:
			# Huh, no interface ref? We might have been called via raw call.
			raise AwlSimError("The block interface field could not "
				"be found. This probably means that this function block "
				"has been called with a raw call instruction like UC or CC, "
				"but the function block has an interface. This is not "
				"allowed in Awlsim.")

	# FB parameter translation:
	# Translate FB DB-pointer variable.
	# This is used for FB IN_OUT compound data type parameters.
	# Returns the actual DB-pointer data. (Not an operator!)
	def _FB_trans_dbpointer(self, param, rvalueOp): #@nocy
#@cy	cdef bytearray _FB_trans_dbpointer(self, AwlParamAssign param, AwlOperator rvalueOp):
#@cy		cdef uint32_t ptr
#@cy		cdef int32_t dbNumber
#@cy		cdef bytearray dbPtrData

		dbPtrData = bytearray(6)
		dbNumber = rvalueOp.offset.dbNumber
		if dbNumber >= 0:
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
	def _FC_trans_direct(self, param, rvalueOp): #@nocy
#@cy	cdef AwlOperator _FC_trans_direct(self, AwlParamAssign param, AwlOperator rvalueOp):
		return rvalueOp

	# FC parameter translation:
	# Copy parameter r-value to the caller-L-stack, if inbound
	# and register a copy-back request, if outbound.
	# Returns the translated rvalueOp.
	def _FC_trans_copyToVL(self, param, rvalueOp): #@nocy
#@cy	cdef AwlOperator _FC_trans_copyToVL(self, AwlParamAssign param, AwlOperator rvalueOp):
#@cy		cdef S7CPU cpu
#@cy		cdef AwlOffset loffset
#@cy		cdef AwlOperator oper
#@cy		cdef uint32_t widthMaskAll

		widthMaskAll = AwlOperatorWidths.WIDTH_MASK_ALL
		cpu = self.cpu

		# Allocate space in the caller-L-stack.
		loffset = cpu.activeLStack.alloc(rvalueOp.width)
		# Make an operator for the allocated space.
		oper = make_AwlOperator(AwlOperatorTypes.MEM_L,
				   rvalueOp.width,
				   loffset,
				   rvalueOp.insn)
		# Write the value to the allocated space.
		# This would only be necessary for inbound parameters,
		# but S7 supports read access to certain outbound
		# FC parameters as well. So copy the value unconditionally.
		cpu.store(oper,
			  cpu.fetch(rvalueOp, widthMaskAll),
			  widthMaskAll)
		# Change the operator to VL
		oper.operType = AwlOperatorTypes.MEM_VL
		# If outbound, save param and operator for return from CALL.
		# Do not do this for immediates (which would be pointer
		# immediates, for example), because there is nothing to copy
		# back in that case.
		if param.isOutbound and not rvalueOp.isImmediate():
			param.scratchSpaceOp = oper
			self._outboundParams.append(param)
		return oper

	# FC parameter translation:
	# Create a DB-pointer to the r-value in the caller's L-stack (VL).
	# Returns the translated rvalueOp.
	def _FC_trans_dbpointerInVL(self, param, rvalueOp): #@nocy
#@cy	cdef AwlOperator _FC_trans_dbpointerInVL(self, AwlParamAssign param, AwlOperator rvalueOp):
#@cy		cdef S7CPU cpu
#@cy		cdef AwlOffset loffset
#@cy		cdef int32_t dbNumber
#@cy		cdef uint64_t area
#@cy		cdef AwlOperator storeOper
#@cy		cdef uint32_t widthMaskAll

		widthMaskAll = AwlOperatorWidths.WIDTH_MASK_ALL
		cpu = self.cpu

		# Allocate space for the DB-ptr in the caller-L-stack
		loffset = cpu.activeLStack.alloc(48) # 48 bits
		# Create and store the the DB-ptr to the allocated space.
		storeOper = make_AwlOperator(AwlOperatorTypes.MEM_L,
					16,
					loffset,
					rvalueOp.insn)
		if rvalueOp.operType == AwlOperatorTypes.MEM_DI:
			dbNumber = cpu.diRegister.index
		else:
			dbNumber = rvalueOp.offset.dbNumber
		cpu.store(storeOper,
			  max(0, dbNumber),
			  widthMaskAll)
		storeOper.offset = loffset + make_AwlOffset(2, 0)
		storeOper.width = 32
		area = AwlIndirectOpConst.optype2area[rvalueOp.operType]
		if area == PointerConst.AREA_L_S:
			area = PointerConst.AREA_VL_S
		elif area == PointerConst.AREA_VL_S:
			raise AwlSimError("Cannot forward VL-parameter "
					  "to called FC")
		elif area == PointerConst.AREA_DI_S:
			area = PointerConst.AREA_DB_S
		cpu.store(storeOper,
			  area | rvalueOp.offset.toPointerValue(),
			  widthMaskAll)
		# Return the operator for the DB pointer.
		return make_AwlOperator(AwlOperatorTypes.MEM_VL,
				   48,
				   loffset,
				   rvalueOp.insn)

	# FC parameter translation:
	# Copy the r-value to the caller's L-stack (VL) and also create
	# a DB-pointer to the copied value in VL.
	# Returns the translated rvalueOp.
	def _FC_trans_copyToVLWithDBPtr(self, param, rvalueOp): #@nocy
#@cy	cdef AwlOperator _FC_trans_copyToVLWithDBPtr(self, AwlParamAssign param, AwlOperator rvalueOp):
#@cy		cdef AwlOperator oper

		oper = self._FC_trans_copyToVL(param, rvalueOp)
		oper.operType = AwlOperatorTypes.MEM_L
		return self._FC_trans_dbpointerInVL(param, oper)

	# FC parameter translation:
	# Translate L-stack access r-value.
	# Returns the translated rvalueOp.
	def _FC_trans_MEM_L(self, param, rvalueOp): #@nocy
#@cy	cdef AwlOperator _FC_trans_MEM_L(self, AwlParamAssign param, AwlOperator rvalueOp):
		# r-value is an L-stack memory access.
		if rvalueOp.compound:
			# rvalue is a compound data type.
			# Create a DB-pointer to it in VL.
			return self._FC_trans_dbpointerInVL(param, rvalueOp)
		# Translate it to a VL-stack memory access.
		return make_AwlOperator(AwlOperatorTypes.MEM_VL,
				   rvalueOp.width,
				   rvalueOp.offset,
				   rvalueOp.insn)

	# FC parameter translation:
	# Translate DB access r-value.
	# Returns the translated rvalueOp.
	def _FC_trans_MEM_DB(self, param, rvalueOp, copyToVL=False): #@nocy
#@cy	cdef AwlOperator _FC_trans_MEM_DB(self, AwlParamAssign param, AwlOperator rvalueOp, _Bool copyToVL=False):
#@cy		cdef AwlOffset offset
#@cy		cdef int32_t dbNumber

		# A (fully qualified) DB variable is passed to an FC.
		dbNumber = rvalueOp.offset.dbNumber
		if dbNumber >= 0:
			# This is a fully qualified DB access.
			if rvalueOp.compound:
				# rvalue is a compound data type.
				# Create a DB-pointer to it in VL.
				return self._FC_trans_dbpointerInVL(param, rvalueOp)
			# Basic data type.
			self.cpu.openDB(dbNumber, False)
			copyToVL = True
		if copyToVL:
			# Copy to caller-L-stack.
			return self._FC_trans_copyToVL(param, rvalueOp)
		# Do not copy to caller-L-stack. Just make a DB-reference.
		offset = rvalueOp.offset.dup()
		return make_AwlOperator(AwlOperatorTypes.MEM_DB,
				   rvalueOp.width,
				   offset,
				   rvalueOp.insn)

	# FC parameter translation:
	# Translate DI access r-value.
	# Returns the translated rvalueOp.
	def _FC_trans_MEM_DI(self, param, rvalueOp): #@nocy
#@cy	cdef AwlOperator _FC_trans_MEM_DI(self, AwlParamAssign param, AwlOperator rvalueOp):
		# A parameter is forwarded from an FB to an FC
		if rvalueOp.compound:
			# rvalue is a compound data type.
			# Create a DB-pointer to it in VL.
			return self._FC_trans_dbpointerInVL(param, rvalueOp)
		# Basic data type.
		# Copy the value to VL.
		return self._FC_trans_copyToVL(param, rvalueOp)

	# FC parameter translation:
	# Translate named local variable r-value.
	# Returns the translated rvalueOp.
	def _FC_trans_NAMED_LOCAL(self, param, rvalueOp): #@nocy
#@cy	cdef AwlOperator _FC_trans_NAMED_LOCAL(self, AwlParamAssign param, AwlOperator rvalueOp):
#@cy		cdef AwlOperator oper

		# r-value is a named-local (#abc)
		oper = self.cpu.callStackTop.getInterfIdxOper(rvalueOp.interfaceIndex)
		if oper.operType == AwlOperatorTypes.MEM_DB:
			return self._FC_trans_MEM_DB(param, oper, True)

		# Call the operator translation handler (Python)
		try:							#@nocy
			trans = self._FC_paramTrans[oper.operType]	#@nocy
		except KeyError as e:					#@nocy
			self._FCTransBug(param, oper)			#@nocy
		return trans(self, param, oper)				#@nocy

		# Call the operator translation handler (Cython)
#@cy		oper = self._translateFCParam(param, oper)
#@cy		if oper is None:
#@cy			self._FCTransBug(param, oper)
#@cy		return oper

	# FC call parameter translators
	_FC_paramTrans = {							#@nocy
		AwlOperatorTypes.IMM		: _FC_trans_copyToVL,		#@nocy
		AwlOperatorTypes.IMM_REAL	: _FC_trans_copyToVL,		#@nocy
		AwlOperatorTypes.IMM_S5T	: _FC_trans_copyToVL,		#@nocy
		AwlOperatorTypes.IMM_TIME	: _FC_trans_copyToVL,		#@nocy
		AwlOperatorTypes.IMM_DATE	: _FC_trans_copyToVL,		#@nocy
		AwlOperatorTypes.IMM_TOD	: _FC_trans_copyToVL,		#@nocy
		AwlOperatorTypes.IMM_DT		: _FC_trans_copyToVLWithDBPtr,	#@nocy
		AwlOperatorTypes.IMM_PTR	: _FC_trans_copyToVL,		#@nocy
		AwlOperatorTypes.IMM_STR	: _FC_trans_copyToVLWithDBPtr,	#@nocy
		AwlOperatorTypes.MEM_E		: _FC_trans_direct,		#@nocy
		AwlOperatorTypes.MEM_A		: _FC_trans_direct,		#@nocy
		AwlOperatorTypes.MEM_M		: _FC_trans_direct,		#@nocy
		AwlOperatorTypes.MEM_L		: _FC_trans_MEM_L,		#@nocy
		AwlOperatorTypes.MEM_VL		: _FC_trans_copyToVL,		#@nocy
		AwlOperatorTypes.MEM_DB		: _FC_trans_MEM_DB,		#@nocy
		AwlOperatorTypes.MEM_DI		: _FC_trans_MEM_DI,		#@nocy
		AwlOperatorTypes.MEM_T		: _FC_trans_direct,		#@nocy
		AwlOperatorTypes.MEM_Z		: _FC_trans_direct,		#@nocy
		AwlOperatorTypes.MEM_PA		: _FC_trans_direct,		#@nocy
		AwlOperatorTypes.MEM_PE		: _FC_trans_direct,		#@nocy
		AwlOperatorTypes.BLKREF_FC	: _FC_trans_direct,		#@nocy
		AwlOperatorTypes.BLKREF_FB	: _FC_trans_direct,		#@nocy
		AwlOperatorTypes.BLKREF_DB	: _FC_trans_direct,		#@nocy
		AwlOperatorTypes.NAMED_LOCAL	: _FC_trans_NAMED_LOCAL,	#@nocy
	}									#@nocy

#@cy	cdef AwlOperator _translateFCParam(self, AwlParamAssign param, AwlOperator rvalueOp):
#@cy		cdef uint32_t operType
#@cy		cdef AwlOperator oper
#@cy
#@cy		operType = rvalueOp.operType
#@cy		if operType == AwlOperatorTypes.IMM:
#@cy			oper = self._FC_trans_copyToVL(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.IMM_REAL:
#@cy			oper = self._FC_trans_copyToVL(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.IMM_S5T:
#@cy			oper = self._FC_trans_copyToVL(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.IMM_TIME:
#@cy			oper = self._FC_trans_copyToVL(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.IMM_DATE:
#@cy			oper = self._FC_trans_copyToVL(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.IMM_TOD:
#@cy			oper = self._FC_trans_copyToVL(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.IMM_DT:
#@cy			oper = self._FC_trans_copyToVLWithDBPtr(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.IMM_PTR:
#@cy			oper = self._FC_trans_copyToVL(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.IMM_STR:
#@cy			oper = self._FC_trans_copyToVLWithDBPtr(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.MEM_E:
#@cy			oper = self._FC_trans_direct(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.MEM_A:
#@cy			oper = self._FC_trans_direct(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.MEM_M:
#@cy			oper = self._FC_trans_direct(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.MEM_L:
#@cy			oper = self._FC_trans_MEM_L(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.MEM_VL:
#@cy			oper = self._FC_trans_copyToVL(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.MEM_DB:
#@cy			oper = self._FC_trans_MEM_DB(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.MEM_DI:
#@cy			oper = self._FC_trans_MEM_DI(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.MEM_T:
#@cy			oper = self._FC_trans_direct(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.MEM_Z:
#@cy			oper = self._FC_trans_direct(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.MEM_PA:
#@cy			oper = self._FC_trans_direct(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.MEM_PE:
#@cy			oper = self._FC_trans_direct(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.BLKREF_FC:
#@cy			oper = self._FC_trans_direct(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.BLKREF_FB:
#@cy			oper = self._FC_trans_direct(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.BLKREF_DB:
#@cy			oper = self._FC_trans_direct(param, rvalueOp)
#@cy		elif operType == AwlOperatorTypes.NAMED_LOCAL:
#@cy			oper = self._FC_trans_NAMED_LOCAL(param, rvalueOp)
#@cy		else:
#@cy			oper = None
#@cy		return oper

	def _FCTransError(self, param, oper):
		raise AwlSimError("Do not know how to translate "
			"FC parameter '%s' for call. The specified "
			"actual-parameter is not allowed in this call." % (
			str(param)))

	def _FCTransBug(self, param, oper):
		raise AwlSimBug("Unhandled call translation of "
			"named local parameter assignment:\n"
			"'%s' => r-value operator '%s'" % (
			(str(param), str(oper))))

	# Handle the exit from this code block.
	# This stack element (self) will already have been
	# removed from the CPU's call stack.
	def handleBlockExit(self): #+cdef
#@cy		cdef S7CPU cpu
#@cy		cdef AwlOffset instanceBaseOffset
#@cy		cdef AwlParamAssign param
#@cy		cdef uint32_t widthMaskAll

		cpu = self.cpu

		# Destroy this call stack element.
		cpu.activeLStack.exitStackFrame()

		if not self.isRawCall:
			widthMaskAll = AwlOperatorWidths.WIDTH_MASK_ALL

			# Handle outbound parameters.
			if self.block.isFB:
				# We are returning from an FB.

				# Get the multi-instance base offset.
				instanceBaseOffset = make_AwlOffset_fromPointerValue(cpu.ar2.get())
				# Restore the AR2 register.
				cpu.ar2.set(self.prevAR2value)

				# Transfer data out of DBI.
				structInstance = cpu.diRegister.structInstance
				for param in self._outboundParams:
					cpu.store(
						param.rvalueOp,
						structInstance.getFieldData(param.lValueStructField,
									    instanceBaseOffset),
						widthMaskAll
					)
				# Assign the DB/DI registers.
				cpu.dbRegister, cpu.diRegister = self.instanceDB, self.prevDiRegister
			else:
				# We are returning from an FC.

				# Restore the AR2 register.
				cpu.ar2.set(self.prevAR2value)

				# Transfer data out of temporary sections.
				for param in self._outboundParams:
					cpu.store(
						param.rvalueOp,
						cpu.fetch(make_AwlOperator(AwlOperatorTypes.MEM_L,
									   param.scratchSpaceOp.width,
									   param.scratchSpaceOp.offset,
									   None),
							  widthMaskAll),
						widthMaskAll
					)
				# Assign the DB/DI registers.
				cpu.dbRegister, cpu.diRegister = self.prevDbRegister, self.prevDiRegister

		# Unlink this call stack element from the previous one.
		self.prevCse = None

	def __repr__(self):
		return "CallStackElem of %s" % str(self.block)

#
# make_CallStackElem() - Create a CallStackElem instance.
#
# Init the call stack element.
# cpu -> The CPU this runs on.
# block -> The code block that is being called.
# instanceDB -> The instance-DB, if FB-call. Otherwise None.
# instanceBaseOffset -> AwlOffset for use as AR2 instance base (multi-instance).
#                       If None, AR2 is not modified.
# parameters -> A tuple of AwlParamAssign instances
#               representing the parameter assignments in CALL insn.
# isRawCall -> True, if the calling instruction was UC or CC.
#
def make_CallStackElem(cpu,						#@nocy
		       block,						#@nocy
		       instanceDB,					#@nocy
		       instanceBaseOffset,				#@nocy
		       parameters,					#@nocy
		       isRawCall,					#@nocy
		       CallStackElem=CallStackElem):			#@nocy
#cdef CallStackElem make_CallStackElem(S7CPU cpu,			#@cy
#				       CodeBlock block,			#@cy
#				       DB instanceDB,			#@cy
#				       AwlOffset instanceBaseOffset,	#@cy
#				       tuple parameters,		#@cy
#				       _Bool isRawCall):		#@cy
#@cy	cdef CallStackElem cse
#@cy	cdef AwlOperator oper
#@cy	cdef AwlParamAssign param
#@cy	cdef AwlStructField structField
#@cy	cdef AwlStructInstance structInstance
#@cy	cdef uint32_t widthMaskAll

	cse = CallStackElem()

	cse.cpu = cpu
	cse.parenStack = []
	cse.ip = 0
	cse.block = block
	cse.insns = block.insns
	cse.nrInsns = block.nrInsns
	cse.isRawCall = isRawCall
	cse.instanceDB = instanceDB
	cse.prevDbRegister = cpu.dbRegister
	cse.prevDiRegister = cpu.diRegister
	cse.prevCse = cpu.callStackTop

	# Handle parameters
	cse._outboundParams = []
	if parameters and not isRawCall: #@nocy
#@cy	if not isRawCall:
		if block.isFB:
			structInstance = instanceDB.structInstance
			widthMaskAll = AwlOperatorWidths.WIDTH_MASK_ALL
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
						cse._outboundParams.append(param)
				if param.isInbound:
					# This is an inbound parameter.
					# Check if this is an IN_OUT compound data
					# type variable. These are passed via DB-ptr.
					if param.isOutbound and\
					   structField.compound:
						# Compound data type with IN_OUT decl.
						# Make a DB-ptr to the actual data.
						data = cse._FB_trans_dbpointer(
								param, param.rvalueOp)
						# Get the DB-ptr struct field.
						structField = structField.finalOverride
					else:
						# Non-compound (basic) data type or
						# not IN_OUT declaration.
						# Get the actual data.
						if structField.callByRef:
							# Do not fetch. Type is passed 'by reference'.
							# This is for TIMER, COUNTER, etc...
							data = param.rvalueOp.resolve().offset.byteOffset
						else:
							data = cpu.fetch(param.rvalueOp, widthMaskAll)
					# Transfer data into DBI.
					structInstance.setFieldData(structField,
								    data,
								    instanceBaseOffset)
		else:
			# This is a call to an FC.
			# Prepare the interface (IN/OUT/INOUT) references.
			# cse._interfRefs is a dict of AwlOperators for the FC interface.
			#                   The key of cse._interfRefs is the interface field index.
			#                   This dict is used by the CPU for lookup and resolve of
			#                   the FC interface r-value.
			cse._interfRefs = {}
			for param in parameters:
				oper = param.rvalueOp

				# Call the operator translation handler (Python)
				try:							#@nocy
					trans = cse._FC_paramTrans[oper.operType]	#@nocy
				except KeyError as e:					#@nocy
					cse._FCTransError(param, oper)			#@nocy
				cse._interfRefs[param.interfaceFieldIndex] = trans(	#@nocy
						cse, param, oper)			#@nocy

				# Call the operator translation handler (Cython)
#@cy				oper = cse._translateFCParam(param, oper)
#@cy				if oper is None:
#@cy					cse._FCTransError(param, oper)
#@cy				cse._interfRefs[param.interfaceFieldIndex] = oper

	# Prepare the localdata stack.
	cpu.activeLStack.enterStackFrame()
	if block.tempAllocation:
		cpu.activeLStack.alloc(block.tempAllocation * 8)

	# Set AR2 to the specified multi-instance base
	# and save the old AR2 value.
	cse.prevAR2value = cpu.ar2.get()
	if instanceBaseOffset is not None:
		cpu.ar2.set(PointerConst.AREA_DB_S |\
			    instanceBaseOffset.toPointerValue())

	return cse

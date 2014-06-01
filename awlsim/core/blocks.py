# -*- coding: utf-8 -*-
#
# AWL simulator - blocks
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

from awlsim.core.labels import *
from awlsim.core.datastructure import *
from awlsim.core.datatypes import *
from awlsim.core.operators import *
from awlsim.core.util import *


class BlockInterfaceField(object):
	EnumGen.start = -1
	FTYPE_UNKNOWN	= EnumGen.item
	FTYPE_IN	= EnumGen.item
	FTYPE_OUT	= EnumGen.item
	FTYPE_INOUT	= EnumGen.item
	FTYPE_STAT	= EnumGen.item
	FTYPE_TEMP	= EnumGen.item
	EnumGen.end

	def __init__(self, name, dataType, initialValue=None):
		# name -> The name string of the field, as defined
		#         in the block interface definition.
		# dataType -> One of AwlDataType instance.
		# initialValue -> Initial value for this field, as defined in
		#                 the block interface definition.
		self.name = name
		self.dataType = dataType
		self.fieldType = self.FTYPE_UNKNOWN
		self.initialValue = initialValue

class BlockInterface(object):
	# Data-types that must be passed "by-reference" to FCs/FBs.
	callByRef_Types = (
		AwlDataType.TYPE_TIMER,
		AwlDataType.TYPE_COUNTER,
		AwlDataType.TYPE_BLOCK_DB,
		AwlDataType.TYPE_BLOCK_FB,
		AwlDataType.TYPE_BLOCK_FC,
	)

	# Specifies whether this interface has a DI assigned.
	# Set to true for FBs and SFBs
	hasInstanceDB = False

	# The number of allocated bytes on startup.
	# This is only non-zero for OBs
	startupTempAllocation = 0

	def __init__(self):
		self.struct = None # Instance-DB structure (IN, OUT, INOUT, STAT)
		self.tempStruct = None # Local-stack structure (TEMP)

		self.fieldNameMap = {}
		self.fields_IN = []
		self.fields_OUT = []
		self.fields_INOUT = []
		self.fields_STAT = []
		self.fields_TEMP = []

		self.interfaceFieldCount = 0	# The number of interface fields
		self.staticFieldCount = 0	# The number of static fields
		self.tempFieldCount = 0		# The number of temp fields
		self.tempAllocation = 0		# The number of allocated TEMP bytes

	@property
	def fields_IN_OUT_INOUT(self):
		ret = self.fields_IN[:]
		ret.extend(self.fields_OUT)
		ret.extend(self.fields_INOUT)
		return ret

	@property
	def fields_IN_OUT_INOUT_STAT(self):
		ret = self.fields_IN_OUT_INOUT # don't copy
		ret.extend(self.fields_STAT)
		return ret

	def __addField(self, field):
		if field.name in self.fieldNameMap:
			raise AwlSimError("Data structure field name '%s' is ambiguous." %\
				field.name)
		if field.fieldType == BlockInterfaceField.FTYPE_TEMP:
			self.tempFieldCount += 1
		elif field.fieldType == BlockInterfaceField.FTYPE_STAT:
			self.staticFieldCount += 1
		else:
			self.interfaceFieldCount += 1
		self.fieldNameMap[field.name] = field

	def addField_IN(self, field):
		field.fieldType = field.FTYPE_IN
		self.__addField(field)
		self.fields_IN.append(field)

	def addField_OUT(self, field):
		field.fieldType = field.FTYPE_OUT
		self.__addField(field)
		self.fields_OUT.append(field)

	def addField_INOUT(self, field):
		field.fieldType = field.FTYPE_INOUT
		self.__addField(field)
		self.fields_INOUT.append(field)

	def addField_STAT(self, field):
		field.fieldType = field.FTYPE_STAT
		self.__addField(field)
		self.fields_STAT.append(field)

	def addField_TEMP(self, field):
		field.fieldType = field.FTYPE_TEMP
		self.__addField(field)
		self.fields_TEMP.append(field)

	def __buildField(self, struct, field, isFirst):
		if isFirst:
			struct.addFieldAligned(field.name,
					       field.dataType, 2)
		else:
			struct.addFieldNaturallyAligned(field.name,
							field.dataType)

	def buildDataStructure(self):
		if self.hasInstanceDB:
			# Build instance-DB structure for the FB
			self.struct = AwlStruct()
			for i, field in enumerate(self.fields_IN):
				self.__buildField(self.struct, field, i==0)
			for i, field in enumerate(self.fields_OUT):
				self.__buildField(self.struct, field, i==0)
			for i, field in enumerate(self.fields_INOUT):
				self.__buildField(self.struct, field, i==0)
			for i, field in enumerate(self.fields_STAT):
				self.__buildField(self.struct, field, i==0)
		else:
			# An FC does not have an instance-DB
			assert(not self.fields_STAT) # No static data.

		# Build local-stack structure
		self.tempStruct = AwlStruct()
		for i, field in enumerate(self.fields_TEMP):
			self.__buildField(self.tempStruct, field, i==0)
		self.tempAllocation = self.tempStruct.getSize()
		# If the OB-interface did not specify all automatic TEMP-fields,
		# just force allocate them, so the lstack-allocator will not be confused.
		if self.tempAllocation < self.startupTempAllocation:
			self.tempAllocation = self.startupTempAllocation

	def getFieldByName(self, name):
		try:
			return self.fieldNameMap[name]
		except KeyError:
			raise AwlSimError("Data structure field '%s' does not exist." %\
				name)

	def getOperatorForFieldName(self, name, wantPointer):
		return self.getOperatorForField(self.getFieldByName(name),
						wantPointer)

	# Get an AwlOperator for TEMP access.
	def __getOperatorForField_TEMP(self, interfaceField, wantPointer):
		structField = self.tempStruct.getField(interfaceField.name)
		if wantPointer:
			ptrValue = structField.offset.toPointerValue()
			return AwlOperator(type = AwlOperator.IMM_PTR,
					   width = 32,
					   value = (AwlIndirectOp.AREA_L |\
						    ptrValue))
		return AwlOperator(type=AwlOperator.MEM_L,
				   width=structField.bitSize,
				   value=structField.offset.dup())

	# Get an AwlOperator that addresses the specified interfaceField.
	# If wantPointer is true, an IMM_PTR AwlOperator to the interfaceField
	# is returned.
	def getOperatorForField(self, interfaceField, wantPointer):
		if interfaceField.fieldType == interfaceField.FTYPE_TEMP:
			# get TEMP interface field operator
			return self.__getOperatorForField_TEMP(interfaceField, wantPointer)
		# otherwise get IN/OUT/INOUT/STAT interface field operator

		structField = self.struct.getField(interfaceField.name)

		# FC-parameters cannot be resolved statically.
		assert(self.hasInstanceDB)

		if wantPointer:
			ptrValue = structField.offset.toPointerValue()
			return AwlOperator(type = AwlOperator.IMM_PTR,
					   width = 32,
					   value = (AwlIndirectOp.AREA_DI |\
						    ptrValue))

		# Translate to instance-DB access
		if structField.dataType.type in BlockInterface.callByRef_Types:
			# "call by reference"
			offsetOper = AwlOperator(type=AwlOperator.MEM_DI,
						 width=structField.dataType.width,
						 value=structField.offset.dup())
			if structField.dataType.type == AwlDataType.TYPE_TIMER:
				area = AwlIndirectOp.EXT_AREA_T
				width = 16
			elif structField.dataType.type == AwlDataType.TYPE_COUNTER:
				area = AwlIndirectOp.EXT_AREA_Z
				width = 16
			elif structField.dataType.type == AwlDataType.TYPE_BLOCK_DB:
				area = AwlIndirectOp.EXT_AREA_BLKREF_DB
				width = 16
			elif structField.dataType.type == AwlDataType.TYPE_BLOCK_FB:
				area = AwlIndirectOp.EXT_AREA_BLKREF_FB
				width = 16
			elif structField.dataType.type == AwlDataType.TYPE_BLOCK_FC:
				area = AwlIndirectOp.EXT_AREA_BLKREF_FC
				width = 16
			else:
				assert(0)
			return AwlIndirectOp(
				area=area,
				width=width,
				addressRegister=AwlIndirectOp.AR_NONE,
				offsetOper=offsetOper)
		# "call by value"
		return AwlOperator(type=AwlOperator.MEM_DI,
				   width=structField.bitSize,
				   value=structField.offset.dup())

	# Get a stable index number for an IN, OUT or INOUT field.
	# (This method is slow)
	def getFieldIndex(self, name):
		for i, field in enumerate(self.fields_IN_OUT_INOUT):
			if field.name == name:
				return i
		raise AwlSimError("Interface field '%s' is not part of IN, OUT "
			"or IN_OUT declaration." % name)

	def __repr__(self):
		ret = []
		for flist, fname in ((self.fields_IN, "VAR_IN"),
				     (self.fields_OUT, "VAR_OUT"),
				     (self.fields_INOUT, "VAR_IN_OUT")):
			if not flist:
				continue
			ret.append(fname)
			for field in flist:
				ret.append("  %s : %s;" %\
					   (field.name, str(field.dataType)))
			ret.append("END_VAR")
		if not ret:
			ret = [ "<None>" ]
		return '\n'.join(ret)

class Block(object):
	def __init__(self, insns, index, interface):
		self.insns = insns
		self.labels = None
		self.index = index
		if insns:
			self.labels = AwlLabel.resolveLabels(insns)
		self.interface = interface

	def __repr__(self):
		return "Block %d" % self.index

class OBInterface(BlockInterface):
	startupTempAllocation = 20

	def addField_IN(self, field):
		raise AwlSimError("VAR_INPUT not possible in an OB")

	def addField_OUT(self, field):
		raise AwlSimError("VAR_OUTPUT not possible in an OB")

	def addField_INOUT(self, field):
		raise AwlSimError("VAR_IN_OUT not possible in an OB")

	def addField_STAT(self, field):
		raise AwlSimError("Static VAR not possible in an OB")

class OB(Block):
	def __init__(self, insns, index):
		Block.__init__(self, insns, index, OBInterface())

	def __repr__(self):
		return "OB %d" % self.index

class FBInterface(BlockInterface):
	hasInstanceDB = True

class FB(Block):
	def __init__(self, insns, index):
		Block.__init__(self, insns, index, FBInterface())

	def __repr__(self):
		return "FB %d" % self.index

class FCInterface(BlockInterface):
	def addField_STAT(self, field):
		raise AwlSimError("Static VAR not possible in an FC")

class FC(Block):
	def __init__(self, insns, index):
		Block.__init__(self, insns, index, FCInterface())

	def __repr__(self):
		return "FC %d" % self.index

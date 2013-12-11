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

from awlsim.labels import *
from awlsim.datastructure import *
from awlsim.datatypes import *
from awlsim.operators import *
from awlsim.util import *


class BlockInterface(object):
	class Field(object):
		enum.start = -1
		FTYPE_UNKNOWN	= enum.item
		FTYPE_IN	= enum.item
		FTYPE_OUT	= enum.item
		FTYPE_INOUT	= enum.item
		FTYPE_STAT	= enum.item
		FTYPE_TEMP	= enum.item
		enum.end

		def __init__(self, name, dataType, initialValue=None):
			self.name = name
			self.dataType = dataType
			self.fieldType = self.FTYPE_UNKNOWN
			self.initialValue = initialValue

	# Data-types that must be passed "by-reference" to FCs/FBs.
	callByRef_Types = (
		AwlDataType.TYPE_TIMER,
		AwlDataType.TYPE_COUNTER,
		AwlDataType.TYPE_BLOCK_DB,
		AwlDataType.TYPE_BLOCK_FB,
		AwlDataType.TYPE_BLOCK_FC,
	)

	# Set to true for FBs and SFBs
	requiresInstanceDB = False

	def __init__(self):
		self.struct = None # Instance-DB structure (IN, OUT, INOUT, STAT)
		self.tempStruct = None # Local-stack structure (TEMP)

		self.fieldNameMap = {}
		self.fields_IN = []
		self.fields_OUT = []
		self.fields_INOUT = []
		self.fields_STAT = []
		self.fields_TEMP = []

		self.interfaceFieldCount = 0
		self.staticFieldCount = 0
		self.tempFieldCount = 0

	def __addField(self, field):
		if field.name in self.fieldNameMap:
			raise AwlSimError("Data structure field name '%s' is ambiguous." %\
				field.name)
		if field.fieldType == BlockInterface.Field.FTYPE_TEMP:
			self.tempFieldCount += 1
		elif field.fieldType == BlockInterface.Field.FTYPE_STAT:
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
		# Build interface-DB structure
		self.struct = AwlStruct()
		for i, field in enumerate(self.fields_IN):
			self.__buildField(self.struct, field, i==0)
		for i, field in enumerate(self.fields_OUT):
			self.__buildField(self.struct, field, i==0)
		for i, field in enumerate(self.fields_INOUT):
			self.__buildField(self.struct, field, i==0)
		for i, field in enumerate(self.fields_STAT):
			self.__buildField(self.struct, field, i==0)

		# Build local-stack structure
		self.tempStruct = AwlStruct()
		for i, field in enumerate(self.fields_TEMP):
			self.__buildField(self.tempStruct, field, i==0)

	def getFieldByName(self, name):
		try:
			return self.fieldNameMap[name]
		except KeyError:
			raise AwlSimError("Data structure field '%s' does not exist." %\
				name)

	def getOperatorForFieldName(self, name, wantPointer):
		return self.getOperatorForField(self.getFieldByName(name),
						wantPointer)

	# Get an AwlOperator that addresses the specified interfaceField.
	# If wantPointer is true, an IMM_PTR AwlOperator to the interfaceField
	# is returned.
	def getOperatorForField(self, interfaceField, wantPointer):
		if interfaceField.fieldType == interfaceField.FTYPE_TEMP:
			structField = self.tempStruct.getField(interfaceField.name)

			if wantPointer:
				ptrValue = structField.offset.toPointerValue()
				return AwlOperator(type = AwlOperator.IMM_PTR,
						   width = 32,
						   value = (AwlIndirectOp.AREA_L |\
							    ptrValue))

			# Translate to local-stack access
			operType = AwlOperator.MEM_L
		else: # IN/OUT/INOUT/STAT
			structField = self.struct.getField(interfaceField.name)

			if wantPointer:
				ptrValue = structField.offset.toPointerValue()
				return AwlOperator(type = AwlOperator.IMM_PTR,
						   width = 32,
						   value = (AwlIndirectOp.AREA_DI |\
							    ptrValue))

			# Translate to interface-DB access
			if structField.dataType.type in BlockInterface.callByRef_Types:
				# "call by reference"
				offsetOper = AwlOperator(type=AwlOperator.INTERF_DB,
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
			else:
				# "call by value"
				operType = AwlOperator.INTERF_DB
		return AwlOperator(type=operType,
				   width=structField.bitSize,
				   value=structField.offset.dup())

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
	requiresInstanceDB = True

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

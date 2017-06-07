# -*- coding: utf-8 -*-
#
# AWL simulator - block interface
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

from awlsim.common.util import *
from awlsim.common.enumeration import *
from awlsim.common.exceptions import *

from awlsim.core.memory import * #+cimport
from awlsim.core.identifier import *
from awlsim.core.datastructure import * #+cimport
from awlsim.core.operatortypes import * #+cimport
from awlsim.core.operators import * #+cimport


__all__ = [
	"BlockInterfaceField",
	"VerboseBlockIntfField",
	"BlockInterface",
	"OBInterface",
	"FBInterface",
	"FCInterface",
]


class BlockInterfaceField(object):
	"""Block interface field descriptor."""

	EnumGen.start = -1
	FTYPE_UNKNOWN	= EnumGen.item
	FTYPE_IN	= EnumGen.item
	FTYPE_OUT	= EnumGen.item
	FTYPE_INOUT	= EnumGen.item
	FTYPE_STAT	= EnumGen.item
	FTYPE_TEMP	= EnumGen.item
	EnumGen.end

	__slots__ = (
		"name",
		"__dataType",
		"fieldType",
		"fieldIndex",
	)

	def __init__(self, name, dataType):
		# name -> The name string of the field, as defined
		#         in the block interface definition.
		# dataType -> AwlDataType instance or a type name string.
		self.name = name
		self.__dataType = dataType
		self.fieldType = self.FTYPE_UNKNOWN	# set later
		self.fieldIndex = None			# set later

	@property
	def dataType(self):
		from awlsim.core.datatypes import AwlDataType

		dataType = self.__dataType
		if not isinstance(dataType, AwlDataType):
			dataType = AwlDataType.makeByName(dataType)
			self.__dataType = dataType
		return dataType

	def varDeclString(self):
		return "%s : %s;" %\
			(self.name, str(self.dataType))

	def __repr__(self):
		ftype = {
			self.FTYPE_UNKNOWN	: "UNKNOWN",
			self.FTYPE_IN		: "IN",
			self.FTYPE_OUT		: "OUT",
			self.FTYPE_INOUT	: "IN_OUT",
			self.FTYPE_STAT		: "STAT",
			self.FTYPE_TEMP		: "TEMP",
		}[self.fieldType]
		return "(%s)  %s" %\
			(ftype, BlockInterfaceField.varDeclString(self))

class VerboseBlockIntfField(BlockInterfaceField):
	"""Block interface field descriptor,
	with verbose description string."""

	__slots__ = (
		"desc",
	)

	def __init__(self, name, dataType, desc=""):
		BlockInterfaceField.__init__(self, name, dataType)
		self.desc = desc

	def varDeclString(self):
		ret = [ BlockInterfaceField.varDeclString(self), ]
		if self.desc:
			ret.append(" // ")
			ret.append(self.desc)
		return "".join(ret)

class BlockInterface(object):
	"""Code block interface (IN/OUT/IN_OUT/STAT/TEMP parameters) base class."""

	# Structs (self._struct and self.tempStruct) build status.
	EnumGen.start
	STRUCT_NOT_BUILT	= EnumGen.item # Structs not built, yet.
	STRUCT_BUILDING		= EnumGen.item # Currently building structs.
	STRUCT_BUILT		= EnumGen.item # Structs are completely built.
	EnumGen.end

	# Specifies whether this interface has a DI assigned.
	# Set to true for FBs and SFBs
	hasInstanceDB = False

	# The number of allocated bytes on startup.
	# This is only non-zero for OBs
	startupTempAllocation = 0

	class StructRecursion(Exception): pass

	def __init__(self):
		self._struct = None # Instance-DB structure (IN, OUT, INOUT, STAT)
		self.tempStruct = None # Local-stack structure (TEMP)
		self.__structState = self.STRUCT_NOT_BUILT

		self.fieldNameMap = {}
		self.fields_IN = []
		self.fields_OUT = []
		self.fields_INOUT = []
		self.fields_STAT = []
		self.fields_TEMP = []

		self.interfaceFieldCount = 0	# The number of interface fields
		self.staticFieldCount = 0	# The number of static fields
		self.tempFieldCount = 0		# The number of temp fields
		self.tempAllocation = 0		# The number of allocated TEMP bytes (interface only!)

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

	# Set fieldIndex of each field.
	def __enumerateFields(self):
		for i, field in enumerate(self.fields_IN_OUT_INOUT):
			field.fieldIndex = i

	def __buildField(self, cpu, struct, field, isFirst):
		if isFirst:
			# Align to word boundary.
			structField = struct.addFieldAligned(cpu,
							field.name,
							field.dataType, 2)
		else:
			# Align naturally.
			structField = struct.addFieldNaturallyAligned(cpu,
							field.name,
							field.dataType)
		if self.hasInstanceDB and\
		   field.fieldType == field.FTYPE_INOUT and\
		   field.dataType.compound:
			# This is an FB IN_OUT compound data type parameter.
			# These are special. They are passed via DB-pointer.
			# The DB-pointer is stored in the instance DB.
			# Set the struct field override for this struct field
			# to DB-pointer type.
			structField.override = AwlStructField(
					structField.name, structField.offset,
					"POINTER")

	def __resolveMultiInstanceField(self, cpu, field):
		from awlsim.core.datatypes import AwlDataType

		if field.dataType.type != AwlDataType.TYPE_FB_X and\
		   field.dataType.type != AwlDataType.TYPE_SFB_X:
			# Not a multi-instance field.
			return
		if field.dataType.width >= 0:
			# Already resolved.
			return

		# This is a multi-instance element.
		# Get the FB that is embedded as multi-instance.
		try:
			if field.dataType.type == AwlDataType.TYPE_SFB_X:
				multiFB = cpu.sfbs[field.dataType.index]
			else:
				multiFB = cpu.fbs[field.dataType.index]
		except KeyError:
			raise AwlSimError("The function block '%s' of the "
				"embedded multi-instance '%s' "
				"does not exist." %\
				(str(field.dataType), str(field.name)))

		# This embedded (S)FB might contain multi-instances, too.
		# Resolve them first. Do this by building its data structure.
		# Catch recursions.
		try:
			multiFB.interface.buildDataStructure(cpu)
		except self.StructRecursion:
			raise AwlSimError("Recursion detected while trying to "
				"resolve the multiinstance variables in %s." %\
				(str(multiFB)))

		# Assign the type width, in bits.
		field.dataType.width = multiFB.interface._struct.getSize() * 8
		if field.dataType.width == 0:
			# This is not supported by S7.
			# Awlsim _could_ support it, though.
			raise AwlSimError("Multiinstances with zero size "
				"are not supported. Please declare at least "
				"one static, input, output or in_out variable "
				"in %s" % str(multiFB))

	def buildDataStructure(self, cpu):
		if self.__structState == self.STRUCT_BUILT:
			# We already built this block's interface structure.
			return
		if self.__structState == self.STRUCT_BUILDING:
			# Whoops, we recursed! This is bad.
			raise self.StructRecursion()
		self.__structState = self.STRUCT_BUILDING

		self.__enumerateFields()

		# Build instance-DB structure, if any.
		if self.hasInstanceDB:
			# Resolve the sizes of all multi-instance
			# fields in our STAT area.
			for field in self.fields_STAT:
				self.__resolveMultiInstanceField(cpu, field)

			# Build instance-DB structure for the FB
			self._struct = AwlStruct()
			for i, field in enumerate(self.fields_IN):
				self.__buildField(cpu, self._struct, field, i==0)
			for i, field in enumerate(self.fields_OUT):
				self.__buildField(cpu, self._struct, field, i==0)
			for i, field in enumerate(self.fields_INOUT):
				self.__buildField(cpu, self._struct, field, i==0)
			for i, field in enumerate(self.fields_STAT):
				self.__buildField(cpu, self._struct, field, i==0)
		else:
			# An FC does not have an instance-DB
			assert(not self.fields_STAT) # No static data.

		# Build local-stack structure
		self.tempStruct = AwlStruct()
		for i, field in enumerate(self.fields_TEMP):
			self.__buildField(cpu, self.tempStruct, field, i==0)
		self.tempAllocation = self.tempStruct.getSize()
		# If the OB-interface did not specify all automatic TEMP-fields,
		# just force allocate them, so the lstack-allocator will not be confused.
		if self.tempAllocation < self.startupTempAllocation:
			self.tempAllocation = self.startupTempAllocation

		self.__structState = self.STRUCT_BUILT

	# Get an interface field by name string.
	def getFieldByName(self, name):
		try:
			return self.fieldNameMap[name]
		except KeyError:
			raise AwlSimError("Interface field '%s' does not exist." %\
				name)

	# Get the interface field (BlockInterfaceField) by AwlDataIdentChain.
	# Only the first element of the chain is honored.
	# (Other elements belong to sub-STRUCTs.)
	def getFieldByIdentChain(self, identChain):
		fieldName = identChain[0].name
		field = self.getFieldByName(fieldName)
		return field

	# Get the interface field type (FTYPE_xxx) for a
	# given identifier chain (AwlDataIdentChain).
	def getFieldType(self, identChain):
		return self.getFieldByIdentChain(identChain).fieldType

	# Get the data type (AwlDataType) of an interface field
	# identified by a given ident chain (AwlDataIdentChain).
	# If 'deep' is True, get the data type of the last element
	# in the chain. If 'deep' is False, get the type of the first
	# element (the interface element) only.
	def getFieldDataType(self, identChain, deep=True):
		# The interface field is determined by the first ident
		# chain element.
		fieldName = identChain[0].name
		field = self.getFieldByName(fieldName)
		if len(identChain) == 1 or not deep:
			return field.dataType
		identChain = AwlDataIdentChain(identChain[1:])
		# Walk the rest of the identifier chain to get to
		# the data type of the final element.
		structFieldName = identChain.dup(withIndices=False).getString()
		if field.dataType.itemStruct is None:
			raise AwlSimError("Data type '%s' does not have sub fields. "
				"Resolve of sub field '%s' failed." %\
				(str(field.dataType), structFieldName))
		structField = field.dataType.itemStruct.getField(structFieldName)
		return structField.dataType

	# Get an AwlOperator for TEMP access.
	def __getOperatorForField_TEMP(self, identChain, wantPointer):
		structField = self.tempStruct.getField(
			identChain.dup(withIndices=False).getString())
		if wantPointer:
			ptrValue = structField.offset.toPointerValue()
			ptrValue |= PointerConst.AREA_L_S
			oper = make_AwlOperator(operType=AwlOperatorTypes.IMM_PTR,
					   width=32,
					   offset=None,
					   insn=None)
			oper.pointer = Pointer(ptrValue)
			return oper
		oper = make_AwlOperator(operType=AwlOperatorTypes.MEM_L,
				   width=structField.bitSize,
				   offset=structField.offset.dup(),
				   insn=None)
		# If this is a compound data type access, mark
		# the operand as such.
		oper.compound = structField.dataType.compound
		return oper

	# Get an AwlOperator that addresses the specified interface field identified
	# by "identChain", which is an AwlDataIdentChain instance.
	# If wantPointer is true, an IMM_PTR AwlOperator to the interfaceField
	# is returned.
	def getOperatorForField(self, identChain, wantPointer):
		from awlsim.core.datatypes import AwlDataType

		interfaceFieldType = self.getFieldType(identChain)

		if interfaceFieldType == BlockInterfaceField.FTYPE_TEMP:
			# get TEMP interface field operator
			return self.__getOperatorForField_TEMP(identChain,
							       wantPointer)
		# otherwise get IN/OUT/INOUT/STAT interface field operator

		structField = self._struct.getField(identChain.getString())

		# FC-parameters cannot be resolved statically.
		assert(self.hasInstanceDB)

		if wantPointer:
			ptrValue = structField.offset.toPointerValue()
			ptrValue |= PointerConst.AREA_DI_S
			oper = make_AwlOperator(operType=AwlOperatorTypes.IMM_PTR,
					   width=32,
					   offset=None,
					   insn=None)
			oper.pointer = Pointer(ptrValue)
			return oper

		# Translate to instance-DB access

		if structField.dataType.type in AwlDataType.callByRefTypes:
			# "call by reference"
			offsetOper = make_AwlOperator(operType=AwlOperatorTypes.MEM_DI,
						 width=structField.dataType.width,
						 offset=structField.offset.dup(),
						 insn=None)
			if structField.dataType.type == AwlDataType.TYPE_TIMER:
				area = AwlIndirectOpConst.EXT_AREA_T_S
				width = 16
			elif structField.dataType.type == AwlDataType.TYPE_COUNTER:
				area = AwlIndirectOpConst.EXT_AREA_Z_S
				width = 16
			elif structField.dataType.type == AwlDataType.TYPE_BLOCK_DB:
				area = AwlIndirectOpConst.EXT_AREA_BLKREF_DB_S
				width = 16
			elif structField.dataType.type == AwlDataType.TYPE_BLOCK_FB:
				area = AwlIndirectOpConst.EXT_AREA_BLKREF_FB_S
				width = 16
			elif structField.dataType.type == AwlDataType.TYPE_BLOCK_FC:
				area = AwlIndirectOpConst.EXT_AREA_BLKREF_FC_S
				width = 16
			else:
				assert(0)
				return
			return make_AwlIndirectOp(
				area=area,
				width=width,
				addressRegister=AwlIndirectOpConst.AR_NONE,
				offsetOper=offsetOper,
				insn=None)

		if structField.dataType.type in (AwlDataType.TYPE_FB_X,
						 AwlDataType.TYPE_SFB_X):
			# Multi-instance operator (CALL)
			if structField.dataType.type == AwlDataType.TYPE_FB_X:
				operType = AwlOperatorTypes.MULTI_FB
			else:
				operType = AwlOperatorTypes.MULTI_SFB
			offset = structField.offset.dup()
			offset.fbNumber = structField.dataType.index
			return make_AwlOperator(operType=operType,
					   width=structField.bitSize,
					   offset=offset,
					   insn=None)

		# "call by value"
		oper = make_AwlOperator(operType=AwlOperatorTypes.MEM_DI,
				   width=structField.bitSize,
				   offset=structField.offset.dup(),
				   insn=None)
		# If this is a compound data type access, mark
		# the operand as such.
		oper.compound = structField.dataType.compound
		return oper

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

class FBInterface(BlockInterface):
	hasInstanceDB = True

class FCInterface(BlockInterface):
	def addField_STAT(self, field):
		raise AwlSimError("Static VAR not possible in an FC")

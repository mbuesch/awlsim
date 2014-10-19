# -*- coding: utf-8 -*-
#
# AWL simulator - AWL translator and symbol resolver
#
# Copyright 2012-2014 Michael Buesch <m@bues.ch>
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

#from awlsim.core.instructions.all_insns cimport * #@cy

from awlsim.core.instructions.all_insns import * #@nocy
from awlsim.core.optrans import *
from awlsim.core.insntrans import *
from awlsim.core.util import *


class AwlTranslator(object):
	"AWL instruction and operator translator."

	def __init__(self, cpu):
		self.cpu = cpu

	def __translateInsn(self, rawInsn, ip):
		ex = None
		try:
			insn = AwlInsnTranslator.fromRawInsn(self.cpu, rawInsn)
			insn.setIP(ip)
		except AwlSimError as e:
			if e.getRawInsn() is None:
				e.setRawInsn(rawInsn)
			raise e
		return insn

	def __translateInsns(self, rawInsns):
		insns = []
		# Translate raw instructions to simulator instructions
		for ip, rawInsn in enumerate(rawInsns):
			insns.append(self.__translateInsn(rawInsn, ip))
		# If the last instruction is not BE or BEA, add an implicit BE
		if not insns or insns[-1].insnType not in (AwlInsn.TYPE_BE,
							   AwlInsn.TYPE_BEA):
			insns.append(AwlInsn_BE(cpu = self.cpu, rawInsn = None))
		return insns

	def __translateInterfaceField(self, rawVar):
		dtype = AwlDataType.makeByName(rawVar.typeTokens, rawVar.dimensions)
		assert(len(rawVar.idents) == 1) #TODO no structs, yet
		field = BlockInterfaceField(name = rawVar.idents[0].name,
					    dataType = dtype)
		return field

	def translateCodeBlock(self, rawBlock, blockClass):
		insns = self.__translateInsns(rawBlock.insns)
		block = blockClass(insns, rawBlock.index)

		# Construct the block interface
		for rawVar in rawBlock.vars_in:
			block.interface.addField_IN(self.__translateInterfaceField(rawVar))
		for rawVar in rawBlock.vars_out:
			block.interface.addField_OUT(self.__translateInterfaceField(rawVar))
		if rawBlock.retTypeTokens:
			# ARRAY is not supported for RET_VAL. So make non-array dtype.
			dtype = AwlDataType.makeByName(rawBlock.retTypeTokens)
			if dtype.type != AwlDataType.TYPE_VOID:
				# Ok, we have a RET_VAL.
				field = BlockInterfaceField(name = "RET_VAL",
							    dataType = dtype)
				block.interface.addField_OUT(field)
		for rawVar in rawBlock.vars_inout:
			block.interface.addField_INOUT(self.__translateInterfaceField(rawVar))
		for rawVar in rawBlock.vars_static:
			block.interface.addField_STAT(self.__translateInterfaceField(rawVar))
		for rawVar in rawBlock.vars_temp:
			block.interface.addField_TEMP(self.__translateInterfaceField(rawVar))
		return block

	# Initialize a DB (global or instance) data field from a raw data-init.
	def __initDBField(self, db, dataType, rawDataInit):
		if dataType.type == AwlDataType.TYPE_ARRAY:
			index = dataType.arrayIndicesCollapse(rawDataInit.idents[-1].indices)
		else:
			index = None
		value = dataType.parseMatchingImmediate(rawDataInit.valueTokens)
		db.structInstance.setFieldDataByName(rawDataInit.idents[-1].name,
						     index, value)

	def __translateGlobalDB(self, rawDB):
		db = DB(rawDB.index, None)
		# Create the data structure fields
		for field in rawDB.fields:
			assert(len(field.idents) == 1) #TODO no structs, yet
			if not rawDB.getFieldInit(field):
				raise AwlSimError(
					"DB %d declares field '%s', "
					"but does not initialize." %\
					(rawDB.index, field.idents[0].name))
			dtype = AwlDataType.makeByName(field.typeTokens,
						       field.dimensions)
			db.struct.addFieldNaturallyAligned(field.idents[0].name,
							   dtype)
		# Allocate the data structure fields
		db.allocate()
		# Initialize the data structure fields
		for field, init in rawDB.allFieldInits():
			if not field:
				raise AwlSimError(
					"DB %d assigns field '%s', "
					"but does not declare it." %\
					(rawDB.index, init.getIdentString()))
			assert(len(field.idents) == 1 and len(init.idents) == 1) #TODO no structs, yet
			dtype = AwlDataType.makeByName(field.typeTokens,
						       field.dimensions)
			self.__initDBField(db, dtype, init)
		return db

	def __translateInstanceDB(self, rawDB):
		if rawDB.fields:
			raise AwlSimError("DB %d is an "
				"instance DB, but it also "
				"declares a data structure." %\
				rawDB.index)

		if rawDB.fb.fbSymbol is None:
			# The FB name is absolute.
			fbStr = "SFB" if rawDB.fb.isSFB else "FB"
			fbNumber = rawDB.fb.fbNumber
			isSFB = rawDB.fb.isSFB
		else:
			# The FB name is symbolic. Resolve it.
			resolver = AwlSymResolver(self.cpu)
			fbStr = '"%s"' % rawDB.fb.fbSymbol
			fbNumber, sym = resolver.resolveBlockName((AwlDataType.TYPE_FB_X,
								   AwlDataType.TYPE_SFB_X),
								  rawDB.fb.fbSymbol)
			isSFB = sym.type.type == AwlDataType.TYPE_SFB_X

		# Get the FB/SFB code block
		try:
			if isSFB:
				fb = self.cpu.sfbs[fbNumber]
			else:
				fb = self.cpu.fbs[fbNumber]
		except KeyError:
			raise AwlSimError("Instance DB %d references %s %d, "
				"but %s %d does not exist." %\
				(rawDB.index,
				 fbStr, fbNumber,
				 fbStr, fbNumber))

		# Create an instance data block
		db = DB(rawDB.index, fb)
		interface = fb.interface
		# Allocate the data structure fields
		db.allocate()
		# Initialize the data structure fields
		for init in rawDB.fieldInits:
			assert(len(init.idents) == 1) #TODO no structs, yet
			dtype = interface.getFieldByName(init.idents[-1].name).dataType
			self.__initDBField(db, dtype, init)
		return db

	def translateDB(self, rawDB):
		if rawDB.index < 0 or rawDB.index > 0xFFFF:
			raise AwlSimError("DB number %d is invalid" % rawDB.index)
		if rawDB.isInstanceDB():
			return self.__translateInstanceDB(rawDB)
		return self.__translateGlobalDB(rawDB)

class AwlSymResolver(object):
	"Global and local symbol resolver."

	def __init__(self, cpu):
		self.cpu = cpu

	# Resolve classic symbols ("abc")
	def __resolveClassicSym(self, block, insn, oper):
		if oper.type == AwlOperator.SYMBOLIC:
			symbol = self.cpu.symbolTable.findOneByName(oper.value.varName)
			if not symbol:
				raise AwlSimError("Symbol \"%s\" not found in "
					"symbol table." % oper.value.varName,
					insn = insn)
			newOper = symbol.operator.dup()
			newOper.setInsn(oper.insn)
			return newOper
		return oper

	# Resolve symbolic OB/FB/FC/DB block name
	def resolveBlockName(self, blockTypeIds, blockName):
		if isString(blockName):
			symbol = self.cpu.symbolTable.findOneByName(blockName)
			if not symbol:
				raise AwlSimError("Symbolic block name \"%s\" "
					"not found in symbol table." % blockName)
			if symbol.type.type not in blockTypeIds:
				raise AwlSimError("Symbolic block name \"%s\" "
					"has an invalid type." % blockName)
			return symbol.operator.value.byteOffset, symbol
		return blockName, None

	# Resolve local symbols (#abc or P##abc)
	# If pointer is false, try to resolve #abc.
	# If pointer is true, try to resolve P##abc.
	# If allowWholeArrayAccess is true, unsubscripted accesses
	# to array variables are supported.
	def resolveNamedLocal(self, block, insn, oper,
			      pointer=False, allowWholeArrayAccess=False):
		if pointer:
			if oper.type != AwlOperator.NAMED_LOCAL_PTR:
				return oper
		else:
			if oper.type != AwlOperator.NAMED_LOCAL:
				return oper

		# Get the interface field for this variable
		field = block.interface.getFieldByName(oper.value.varName)

		# Sanity checks
		if field.dataType.type == AwlDataType.TYPE_ARRAY:
			if not oper.value.indices and\
			   oper.type != AwlOperator.NAMED_LOCAL_PTR and\
			   not allowWholeArrayAccess:
				raise AwlSimError("Cannot address array #%s "
					"without subscript list." %\
					oper.value.varName)
		else:
			if oper.value.indices:
				raise AwlSimError("Trying to subscript array, "
					"but #%s is not an array." %\
					oper.value.varName)

		if oper.value.indices:
			assert(field.dataType.type == AwlDataType.TYPE_ARRAY)
			# This is an array access.
			# Resolve the array index to a byte/bit-offset.
			arrayIndex = field.dataType.arrayIndicesCollapse(oper.value.indices)
			elemWidth = field.dataType.children[0].width
			bitOffset = arrayIndex * elemWidth
			byteOffset = bitOffset // 8
			bitOffset %= 8
			oper.value.subOffset = AwlOffset(byteOffset, bitOffset)
			# Store the element-access-width in the operator.
			oper.width = elemWidth
		else:
			# Non-array accesses don't have a sub-offset.
			oper.value.subOffset = AwlOffset()
			# Store the access-width in the operator.
			oper.width = field.dataType.width

		if block.interface.hasInstanceDB or\
		   field.fieldType == BlockInterfaceField.FTYPE_TEMP:
			# This is an FB or a TEMP access. Translate the operator
			# to a DI/TEMP access.
			newOper = block.interface.getOperatorForField(oper.value.varName,
								      oper.value.indices,
								      pointer)
			newOper.setInsn(oper.insn)
			return newOper
		else:
			# This is an FC. Accesses to local symbols
			# are resolved at runtime.
			# Just set interface index in the operator.
			index = block.interface.getFieldIndex(oper.value.varName)
			oper.interfaceIndex = index
		return oper

	# Resolve named fully qualified accesses (DBx.VARx)
	# If allowWholeArrayAccess is true, unsubscripted accesses
	# to array variables are supported.
	def __resolveNamedFullyQualified(self, block, insn, oper,
					 allowWholeArrayAccess=False):
		if oper.type != AwlOperator.NAMED_DBVAR:
			return oper

		# Resolve the symbolic DB name, if needed
		assert(oper.value.dbNumber is not None or\
		       oper.value.dbName is not None)
		if oper.value.dbNumber is None:
			symbol = self.cpu.symbolTable.findOneByName(oper.value.dbName)
			if not symbol:
				raise AwlSimError("Symbol \"%s\" specified as DB in "
					"fully qualified operator not found." %\
					oper.value.dbName)
			if symbol.type.type != AwlDataType.TYPE_DB_X:
				raise AwlSimError("Symbol \"%s\" specified as DB in "
					"fully qualified operator is not a DB-symbol." %\
					oper.value.dbName)
			oper.value.dbNumber = symbol.operator.value.byteOffset

		# Get the DB
		try:
			db = self.cpu.dbs[oper.value.dbNumber]
		except KeyError as e:
			raise AwlSimError("DB %d specified in fully qualified "
				"operator does not exist." % oper.value.dbNumber)

		# Get the data structure field descriptor
		# and construct the AwlOffset.
		field = db.struct.getField(oper.value.varName)
		if oper.value.indices is None:
			# Access without array indices.
			if field.dataType.type == AwlDataType.TYPE_ARRAY:
				# This is a whole-array access.
				#  e.g.  DB1.ARRAYVAR
				if not allowWholeArrayAccess:
					raise AwlSimError("Variable '%s' in fully qualified "
						"DB access is an ARRAY." %\
						oper.value.varName)
		else:
			# This is an array field access.
			if field.dataType.type != AwlDataType.TYPE_ARRAY:
				raise AwlSimError("Indexed variable '%s' in fully qualified "
					"DB access is not an ARRAY." %\
					oper.value.varName)
			index = field.dataType.arrayIndicesCollapse(oper.value.indices)
			# Get the actual data field
			field = db.struct.getField(oper.value.varName, index)
		# Extract the offset data
		offset = field.offset.dup()
		width = field.bitSize
		offset.dbNumber = oper.value.dbNumber

		# Construct an absolute operator
		return AwlOperator(type = AwlOperator.MEM_DB,
				   width = width,
				   value = offset,
				   insn = oper.insn)

	# Resolve all symbols in the given code block
	def resolveSymbols_block(self, block):
		block.resolveSymbols()
		for insn in block.insns:
			try:
				for i, oper in enumerate(insn.ops):
					oper = self.__resolveClassicSym(block, insn, oper)
					oper = self.resolveNamedLocal(block, insn, oper, False)
					oper = self.__resolveNamedFullyQualified(block,
										 insn, oper, False)
					if oper.type == AwlOperator.INDIRECT:
						oper.offsetOper = self.__resolveClassicSym(block,
									insn, oper.offsetOper)
						oper.offsetOper = self.resolveNamedLocal(block,
									insn, oper.offsetOper, False)
					oper = self.resolveNamedLocal(block, insn, oper, True)
					insn.ops[i] = oper
				for param in insn.params:
					oper = param.rvalueOp
					oper = self.__resolveClassicSym(block, insn, oper)
					oper = self.resolveNamedLocal(block, insn, oper, False, True)
					oper = self.__resolveNamedFullyQualified(block,
										 insn, oper, True)
					if oper.type == AwlOperator.INDIRECT:
						oper.offsetOper = self.__resolveClassicSym(block,
									insn, oper.offsetOper)
						oper.offsetOper = self.resolveNamedLocal(block,
									insn, oper.offsetOper, False)
					oper = self.resolveNamedLocal(block, insn, oper, False, True)
					param.rvalueOp = oper
			except AwlSimError as e:
				if not e.getInsn():
					e.setInsn(insn)
				raise e

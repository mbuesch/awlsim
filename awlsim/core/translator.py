# -*- coding: utf-8 -*-
#
# AWL simulator - AWL translator and symbol resolver
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

#from awlsim.core.instructions.all_insns cimport * #@cy

from awlsim.core.instructions.all_insns import * #@nocy
from awlsim.core.optrans import *
from awlsim.core.insntrans import *
from awlsim.core.parser import *
from awlsim.core.util import *
from awlsim.core.datastructure import *


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

	def __translateInterfaceField(self, rawField):
		name, dataType, initBytes = self.rawFieldTranslate(rawField)
		if not dataType.allowedInInterface:
			raise AwlSimError("Data type '%s' not allowed in block interface" %\
				str(dataType))
		field = BlockInterfaceField(name = name,
					    dataType = dataType)
		return field

	def translateLibraryCodeBlock(self, block):
		# Switch mnemonics to DE for translation of library code.
		oldMnemonics = self.cpu.getSpecs().getConfiguredMnemonics()
		self.cpu.getSpecs().setConfiguredMnemonics(S7CPUSpecs.MNEMONICS_DE)

		# Enable extended instructions for library code.
		oldExtEn = self.cpu.extendedInsnsEnabled()
		self.cpu.enableExtendedInsns(True)

		# Parse the library code
		p = AwlParser()
		p.parseText(block.getCode())
		tree = p.getParseTree()
		if block.isFC:
			assert(len(tree.fcs) == 1)
			rawBlock = getfirst(dictValues(tree.fcs))
		elif block.isFB:
			assert(len(tree.fbs) == 1)
			rawBlock = getfirst(dictValues(tree.fbs))
		else:
			assert(0)
		# Translate the library block instructions.
		block.insns = self.__translateInsns(rawBlock.insns)
		block.resolveLabels()

		# Switch back to old extended-instructions state.
		self.cpu.enableExtendedInsns(oldExtEn)

		# Switch back to old mnemonics.
		self.cpu.getSpecs().setConfiguredMnemonics(oldMnemonics)

		return block

	def translateCodeBlock(self, rawBlock, blockClass):
		insns = self.__translateInsns(rawBlock.insns)
		block = blockClass(insns, rawBlock.index)
		block.setSourceRef(rawBlock.sourceRef, inheritRef = True)

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

	# Create an AwlStruct from a list of RawAwlDataFields.
	def __createStructFromRawFields(self, rawFields):
		struct = AwlStruct()
		for rawField in rawFields:
			name, dataType, initBytes = self.rawFieldTranslate(rawField)
			if not dataType.allowedInStruct:
				raise AwlSimError("Data type '%s' not allowed in STRUCT" %\
					str(dataType))
			name = rawField.getIdentString(fullChain = False)
			struct.addFieldNaturallyAligned(self.cpu, name,
							dataType, initBytes)
		return struct

	# Translate a RawAwlDataField to an AwlDataType.
	def __rawFieldToDataType(self, rawField):
		dtype = AwlDataType.makeByName(nameTokens = rawField.typeTokens,
					       arrayDimensions = rawField.dimensions)
		if dtype.type == AwlDataType.TYPE_STRUCT:
			# Make the AwlStruct that represents the STRUCT contents.
			if not rawField.children:
				raise AwlSimError("Data structure does not have "
					"any containing variables. (STRUCT is empty)")
			struct = self.__createStructFromRawFields(rawField.children)
			dtype.setStruct(struct)
		elif dtype.type == AwlDataType.TYPE_ARRAY and\
		     dtype.arrayElementType.type == AwlDataType.TYPE_STRUCT:
			# Make the AwlStruct that represents the
			# ARRAY-element (of type STRUCT) contents.
			if not rawField.children:
				raise AwlSimError("Data structure does not have "
					"any containing variables. (STRUCT is empty)")
			struct = self.__createStructFromRawFields(rawField.children)
			dtype.arrayElementType.setStruct(struct)
		else:
			if rawField.children:
				raise AwlSimError("Data type '%s' has children '%s', "
					"but is not a STRUCT." %\
					(str(dtype), str(rawField.children)))
		return dtype

	# Translate a RawAwlDataField to a (name, dataType, initBytes) tuple where:
	# name: The data field name string.
	# dataType: The AwlDataType for this field.
	# initBytes: The initialization bytes for this field, or None.
	def rawFieldTranslate(self, rawField):
		# Get the field name
		name = rawField.getIdentString()
		# Get the field data type
		if len(rawField.typeTokens) == 1 and\
		   rawField.typeTokens[0].startswith('"') and\
		   rawField.typeTokens[0].endswith('"') and\
		   self.cpu:
			# The data type is symbolic.
			# (symbolic multi instance field)
			# Resolve it.
			assert(not rawField.dimensions)
			symStr = rawField.typeTokens[0][1:-1] # Strip quotes
			resolver = AwlSymResolver(self.cpu)
			fbNumber, sym = resolver.resolveBlockName((AwlDataType.TYPE_FB_X,
								   AwlDataType.TYPE_SFB_X),
								  symStr)
			# Get the data type from the symbol.
			dataType = sym.type
		else:
			# Parse the data type.
			dataType = self.__rawFieldToDataType(rawField)
		# Get the field inits
		if rawField.defaultInits:
			# Translate the initialization values and
			# put them into a ByteArray.
			initBytes = ByteArray(intDivRoundUp(dataType.width, 8))
			if dataType.type == AwlDataType.TYPE_ARRAY:
				for rawDataInit in rawField.defaultInits:
					value = dataType.parseMatchingImmediate(rawDataInit.valueTokens)
					linArrayIndex = dataType.arrayIndicesCollapse(
						rawDataInit.identChain[-1].indices)
					offset = AwlOffset.fromBitOffset(linArrayIndex *
									 dataType.arrayElementType.width)
					try:
						initBytes.store(offset, dataType.arrayElementType.width,
								value)
					except AwlSimError as e:
						raise AwlSimError("Data field '%s' initialization "
							"is out of range." % str(rawField))
			else:
				assert(len(rawField.defaultInits) == 1)
				value = dataType.parseMatchingImmediate(rawField.defaultInits[0].valueTokens)
				try:
					initBytes.store(AwlOffset(), dataType.width, value)
				except AwlSimError as e:
					raise AwlSimError("Data field '%s' initialization "
						"is out of range." % str(rawField))
		else:
			initBytes = None
		return name, dataType, initBytes

	# Initialize a DB (global or instance) data field from a raw data-init.
	def __initDBField(self, db, dataType, rawDataInit):
		fieldName = rawDataInit.getIdentString()
		value = dataType.parseMatchingImmediate(rawDataInit.valueTokens)
		db.structInstance.setFieldDataByName(fieldName, value)

	# Create a DB data field.
	def __createDBField(self, db, rawDataField):
		name, dataType, initBytes = self.rawFieldTranslate(rawDataField)
		if not dataType.allowedInStruct:
			raise AwlSimError("Data type '%s' not allowed in DB" %\
				str(dataType))
		db.struct.addFieldNaturallyAligned(self.cpu, name,
						   dataType, initBytes)

	def __translateGlobalDB(self, rawDB):
		db = DB(rawDB.index, None)
		db.setSourceRef(rawDB.sourceRef, inheritRef = True)
		# Create the data structure fields
		for rawField in rawDB.fields:
			self.__createDBField(db, rawField)
		# Allocate the data structure fields
		db.allocate()
		# Assign data structure initializations.
		for field, init in rawDB.allFieldInits():
			if not field:
				raise AwlSimError(
					"DB %d assigns field '%s', "
					"but does not declare it." %\
					(rawDB.index, init.getIdentString()))
			assert(field.getIdentChain() == init.identChain)
			dtype = self.__rawFieldToDataType(field)
			if dtype == AwlDataType.TYPE_STRUCT:
				raise AwlSimError(
					"Invalid assignment to STRUCT.")
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
			fbNumber = rawDB.fb.fbNumber
			fbStr = "SFB" if rawDB.fb.isSFB else "FB"
			fbStr += " %d" % fbNumber
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
			raise AwlSimError("Instance DB %d references %s, "
				"but %s does not exist." %\
				(rawDB.index, fbStr, fbStr))

		# Create an instance data block
		db = DB(rawDB.index, fb)
		db.setSourceRef(rawDB.sourceRef, inheritRef = True)
		interface = fb.interface
		# Allocate the data structure fields
		db.allocate()
		# Initialize the data structure fields
		for init in rawDB.fieldInits:
			structField = db.struct.getField(init.getIdentString())
			self.__initDBField(db, structField.dataType, init)
		return db

	def translateDB(self, rawDB):
		if rawDB.index < 1 or rawDB.index > 0xFFFF:
			raise AwlSimError("DB number %d is invalid" % rawDB.index)
		if rawDB.isInstanceDB():
			return self.__translateInstanceDB(rawDB)
		return self.__translateGlobalDB(rawDB)

	# Translate implicit pointer immediates.
	# Implicit pointer immediates are assignments of non-pointer
	# operands to POINTER or ANY l-values.
	def __translateParamPointer(self, param):
		if param.lValueDataType.type == AwlDataType.TYPE_POINTER:
			# POINTER parameter.
			if param.rvalueOp.type == AwlOperator.IMM_PTR:
				# Make sure this is a DB-pointer immediate (48 bit).
				if param.rvalueOp.width not in {32, 48}:
					raise AwlSimError("Invalid pointer immediate "
						"assignment to POINTER parameter.")
				param.rvalueOp.value = param.rvalueOp.value.toDBPointer()
				param.rvalueOp.width = param.rvalueOp.value.width
			else:
				# Translate the r-value to POINTER.
				try:
					ptr = param.rvalueOp.makeDBPointer()
				except (AwlSimBug, AwlSimError) as e:
					raise AwlSimError("Unable to transform "
						"operator '%s' to POINTER." %\
						str(param.rvalueOp))
				param.rvalueOp = AwlOperator(
					type = AwlOperator.IMM_PTR,
					width = ptr.width,
					value = ptr,
					insn = param.rvalueOp.insn)
			if param.rvalueOp.value.getArea() == Pointer.AREA_L:
				# L-stack access must be translated to VL.
				param.rvalueOp.value.setArea(Pointer.AREA_VL)
		elif param.lValueDataType.type == AwlDataType.TYPE_ANY:
			# ANY-pointer parameter.
			if param.rvalueOp.type == AwlOperator.IMM_PTR:
				# Make sure this is an ANY-pointer immediate (80 bit).
				if param.rvalueOp.width not in {32, 48, 80}:
					raise AwlSimError("Invalid pointer immediate "
						"assignment to ANY parameter.")
				param.rvalueOp.value = param.rvalueOp.value.toANYPointer()
				param.rvalueOp.width = param.rvalueOp.value.width
			elif param.rvalueOp.type == AwlOperator.MEM_L and\
			     param.rvalueOp.dataType is not None and\
			     param.rvalueOp.dataType.type == AwlDataType.TYPE_ANY:
				# r-value is an ANY pointer in L (as TEMP variable).
				# Forward it as-is to the FC.
				# The operator will be translated from MEM_L to MEM_VL
				# at call time.
				assert(param.rvalueOp.width == 80)
			else:
				# Translate the r-value to ANY.
				try:
					ptr = param.rvalueOp.makeANYPointer()
				except (AwlSimBug, AwlSimError) as e:
					raise AwlSimError("Unable to transform "
						"operator '%s' to ANY pointer." %\
						str(param.rvalueOp))
				param.rvalueOp = AwlOperator(
					type = AwlOperator.IMM_PTR,
					width = ptr.width,
					value = ptr,
					insn = param.rvalueOp.insn)
			if param.rvalueOp.type == AwlOperator.IMM_PTR and\
			   param.rvalueOp.value.getArea() == Pointer.AREA_L:
				# L-stack access must be translated to VL.
				param.rvalueOp.value.setArea(Pointer.AREA_VL)

	# Translate STRING immediates.
	# Converts STRING to CHAR, if required, or expands string lengths.
	def __translateParamString(self, param):
		if param.lValueDataType.type == AwlDataType.TYPE_CHAR:
			# CHAR parameter.
			if param.rvalueOp.type == AwlOperator.IMM_STR:
				# Translate single-character string immediates
				# to 8 bit integer immediates.
				if param.rvalueOp.width == (2 + 1) * 8:
					param.rvalueOp = AwlOperator(
						type = AwlOperator.IMM,
						width = 8,
						value = param.rvalueOp.value[2],
						insn = param.rvalueOp.insn)
		elif param.lValueDataType.type == AwlDataType.TYPE_STRING:
			# STRING parameter.
			if param.rvalueOp.type == AwlOperator.IMM_STR:
				if param.rvalueOp.width < param.lValueDataType.width:
					# Expand the string immediate length.
					# This is an awlsim extension.
					curLen = param.rvalueOp.width // 8
					newLen = param.lValueDataType.width // 8
					assert(curLen >= 2 and newLen >= 2)
					data = param.rvalueOp.value[:]
					data[0] = newLen - 2
					data.extend(b'\x00' * (newLen - curLen))
					param.rvalueOp.value = data
					param.rvalueOp.width = newLen * 8

	# Final translation of AwlParamAssign r-value operands.
	# Overrides the rvalueOp in place, if required.
	def translateParamAssignOper(self, param):
		self.__translateParamPointer(param)
		self.__translateParamString(param)

class AwlSymResolver(object):
	"Global and local symbol resolver."

	def __init__(self, cpu):
		self.cpu = cpu

	# Resolve classic symbols ("abc")
	def __resolveClassicSym(self, block, insn, oper):
		if oper.type == AwlOperator.SYMBOLIC:
			symbol = self.cpu.symbolTable.findByName(
				oper.value.identChain.getString())
			if not symbol:
				raise AwlSimError("Symbol \"%s\" not found in "
					"symbol table." %\
					oper.value.identChain.getString(),
					insn = insn)
			newOper = symbol.operator.dup()
			newOper.setInsn(oper.insn)
			return newOper
		return oper

	# Resolve symbolic OB/FB/FC/DB block name
	def resolveBlockName(self, blockTypeIds, blockName):
		if isString(blockName):
			symbol = self.cpu.symbolTable.findByName(blockName)
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
		# Check whether we need to do something.
		# Otherwise just return the source operator.
		if pointer:
			if oper.type != AwlOperator.NAMED_LOCAL_PTR:
				return oper
		else:
			if oper.type != AwlOperator.NAMED_LOCAL:
				return oper

		# Walk the ident chain to accumulate the sub-offsets
		# for the ARRAY accesses.
		parentStruct = None
		subOffset = AwlOffset()
		for i in range(len(oper.value.identChain)):
			isFirstElement = (i == 0)
			isLastElement = (i == len(oper.value.identChain) - 1)

			# Get the sub-chain and the interface field.
			chain = AwlDataIdentChain(oper.value.identChain[:i+1])
			dataType = block.interface.getFieldDataType(chain)

			# Sanity checks
			if dataType.type in {AwlDataType.TYPE_ARRAY,
					     AwlDataType.TYPE_STRING}:
				if isLastElement and\
				   not chain[-1].indices and\
				   oper.type != AwlOperator.NAMED_LOCAL_PTR and\
				   not allowWholeArrayAccess:
					raise AwlSimError("Cannot address array #%s "
						"without subscript list." %\
						chain.getString())
			else:
				if chain[-1].indices:
					raise AwlSimError("Trying to subscript array, "
						"but #%s is not an array." %\
						chain.getString())

			# Assign the struct to the UDT data type, if
			# not already done so.
			if dataType.type == AwlDataType.TYPE_UDT_X:
				try:
					udt = self.cpu.udts[dataType.index]
				except KeyError as e:
					raise AwlSimError("UDT %d not found on CPU" %\
						dataType.index)
				assert(dataType.struct is None or
				       dataType.struct is udt.struct)
				dataType.setStruct(udt.struct)

			# Add the struct field offset of this field to the subOffset.
			# Need to look it up in the parent struct.
			if not isFirstElement:
				assert(parentStruct)
				structFieldName = chain[-1].dup(withIndices=False).getString()
				structField = parentStruct.getField(structFieldName)
				subOffset += structField.offset

			# Add array offset to subOffset,
			# if this is an ARRAY or STRING element access.
			if chain[-1].indices:
				if dataType.type == AwlDataType.TYPE_ARRAY:
					# Calculate the array offset.
					arrayIndex = dataType.arrayIndicesCollapse(chain[-1].indices)
					elemWidth = dataType.arrayElementType.width
					bitOffset = arrayIndex * elemWidth
					byteOffset = bitOffset // 8
					bitOffset %= 8
				elif dataType.type == AwlDataType.TYPE_STRING:
					# Calculate the string offset.
					if len(chain[-1].indices) != 1:
						raise AwlSimError("Only one index is "
							"allowed in STRING indexing.")
					index = chain[-1].indices[0]
					maxIdx = dataType.width // 8 - 2
					if index < 1 or index > maxIdx:
						raise AwlSimError("STRING index %d is "
							"out of range 1-%d." %\
							(index, maxIdx))
					byteOffset = 2 + index - 1
					bitOffset = 0
				else:
					assert(0)
				# Add it to the accumulated offset.
				subOffset += AwlOffset(byteOffset, bitOffset)

			parentStruct = dataType.itemStruct

		# 'dataType' now is the type of last field in the identChain.
		# (The field that we eventually address).

		isWholeArrayAccess = ((dataType.type == AwlDataType.TYPE_ARRAY or\
				       dataType.type == AwlDataType.TYPE_STRING) and\
				      not oper.value.identChain[-1].indices)
		if dataType.type == AwlDataType.TYPE_ARRAY and\
		   not isWholeArrayAccess:
			# This is an array element access.
			accessDataType = dataType.arrayElementType
		elif dataType.type == AwlDataType.TYPE_STRING and\
		     not isWholeArrayAccess:
			# This is a string single character access.
			accessDataType = AwlDataType.makeByName("CHAR")
		else:
			# Non-array access or whole-array access.
			accessDataType = dataType
		# Store the access type and width in the operator.
		oper.dataType = accessDataType
		oper.width = accessDataType.width
		assert(oper.width > 0)

		# Store the sub-offset (might be zero).
		oper.value.subOffset = subOffset

		# If interface field is of compound data type access, mark
		# the operand as such.
		basicType = block.interface.getFieldDataType(chain, deep=False)
		oper.compound = basicType.compound

		fieldType = block.interface.getFieldType(oper.value.identChain)
		if block.interface.hasInstanceDB or\
		   fieldType == BlockInterfaceField.FTYPE_TEMP:
			# This is an FB or a TEMP access. Translate the operator
			# to a DI/TEMP access.
			newOper = block.interface.getOperatorForField(oper.value.identChain,
								      pointer)
			assert(newOper.width > 0)
			newOper.setInsn(oper.insn)
			newOper.compound = oper.compound
			newOper.dataType = oper.dataType
			return newOper
		else:
			# This is an FC. Accesses to local symbols
			# are resolved at runtime.
			# Just set interface index in the operator.
			# Pointer access (oper.type == NAMED_LOCAL_PTR) is resolved
			# later at runtime.
			identChain = oper.value.identChain.dup(withIndices = False)
			index = block.interface.getFieldByIdentChain(identChain).fieldIndex
			oper.interfaceIndex = index
		return oper

	# Resolve a symbolic DB name. Returns DB index number.
	def __resolveDBName(self, dbName):
		symbol = self.cpu.symbolTable.findByName(dbName)
		if not symbol:
			raise AwlSimError("Symbol \"%s\" specified as DB in "
				"fully qualified operator not found." %\
				dbName)
		if symbol.type.type != AwlDataType.TYPE_DB_X:
			raise AwlSimError("Symbol \"%s\" specified as DB in "
				"fully qualified operator is not a DB-symbol." %\
				dbName)
		return symbol.operator.value.byteOffset

	# Get offset and width of a DB field.
	def __dbVarToOffset(self, dbNumber, identChain, allowWholeArrayAccess=True):
		# Get the DB
		try:
			db = self.cpu.dbs[dbNumber]
		except KeyError as e:
			raise AwlSimError("DB %d specified in fully qualified "
				"operator does not exist." % dbNumber)

		# Get the data structure base field descriptor.
		# For arrays, this is the base name of the array.
		tmpIdentChain = identChain.dup()
		tmpIdentChain[-1] = tmpIdentChain[-1].dup(withIndices = False)
		field = db.struct.getField(tmpIdentChain.getString())
		if identChain[-1].indices is None:
			# Access without array indices.
			if field.dataType.type == AwlDataType.TYPE_ARRAY:
				# This is a whole-array access.
				#  e.g.  DB1.ARRAYVAR
				if not allowWholeArrayAccess:
					raise AwlSimError("Variable '%s' in fully qualified "
						"DB access is an ARRAY." %\
						identChain.getString())
		else:
			# This is an array field access.
			# (The original last ident chain field has indices.)
			if field.dataType.type not in {AwlDataType.TYPE_ARRAY,
						       AwlDataType.TYPE_STRING}:
				raise AwlSimError("Indexed variable '%s' in fully qualified "
					"DB access is not an ARRAY or STRING." %\
					oper.value.identChain.getString())
			# Get the actual data field.
			# (Don't remove indices from the last chain element.)
			field = db.struct.getField(identChain.getString())

		# Extract the offset data
		offset = field.offset.dup()
		width = field.bitSize
		dataType = field.dataType

		return offset, width, dataType

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
			oper.value.dbNumber = self.__resolveDBName(oper.value.dbName)

		# Get the offset data and the width of the field.
		offset, width, fieldDataType = self.__dbVarToOffset(oper.value.dbNumber,
								    oper.value.identChain,
								    allowWholeArrayAccess)
		offset.dbNumber = oper.value.dbNumber

		# Construct an absolute operator
		oper = AwlOperator(type = AwlOperator.MEM_DB,
				   width = width,
				   value = offset,
				   insn = oper.insn)
		# If this is a compound data type access, mark
		# the operand as such.
		oper.compound = fieldDataType.compound

		# Assign access data type.
		oper.dataType = fieldDataType

		return oper

	# Resolve named fully qualified pointers (P#DBx.VARx)
	# This is an awlsim extension.
	def __resolveNamedFQPointer(self, block, insn, oper, param=None):
		if oper.type != AwlOperator.IMM_PTR:
			return oper
		if oper.value.width > 0:
			return oper
		assert(isinstance(oper.value, SymbolicDBPointer))

		# Resolve the symbolic DB name, if needed
		assert(oper.value.dbNr or\
		       oper.value.dbSymbol is not None)
		if oper.value.dbSymbol is not None:
			oper.value.dbNr = self.__resolveDBName(oper.value.dbSymbol)

		# Get the offset data and the width of the field.
		offset, width, fieldDataType = self.__dbVarToOffset(oper.value.dbNr,
								    oper.value.identChain)

		# Write the pointer value.
		oper.value.setDWord(offset.toPointerValue() |\
				    (Pointer.AREA_DB << Pointer.AREA_SHIFT))

		# Create a resolved Pointer.
		if param and\
		   param.lValueDataType.type == AwlDataType.TYPE_POINTER:
			# Create a resolved DB-Pointer (48 bit).
			oper.value = oper.value.toDBPointer()
		elif param and\
		     param.lValueDataType.type == AwlDataType.TYPE_ANY:
			# Create a resolved ANY-Pointer (80 bit).
			oper.value = ANYPointer.makeByAutoType(
				dataType = fieldDataType,
				ptrValue = oper.value.toPointerValue(),
				dbNr = oper.value.toDBPointer().dbNr)
		else:
			# Create a resolved pointer (32 bit).
			oper.value = oper.value.toPointer()
		oper.dataType = fieldDataType
		oper.width = oper.value.width

		return oper

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
					oper = self.__resolveNamedFQPointer(block, insn, oper)
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
					oper = self.__resolveNamedFQPointer(block, insn, oper, param)
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

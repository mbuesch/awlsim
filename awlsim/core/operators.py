# -*- coding: utf-8 -*-
#
# AWL simulator - operators
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

from awlsim.common.datatypehelpers import * #+cimport

from awlsim.core.operatortypes import * #+cimport
from awlsim.core.datatypes import *
from awlsim.core.memory import * #+cimport
from awlsim.core.offset import * #+cimport
from awlsim.core.statusword import * #+cimport
from awlsim.core.util import *


class AwlOperator(object): #+cdef
	"""An AWL operator.
	An operator is an 'argument' to an instruction.
	For example MW 10 in:
	L  MW 10
	"""

	# Type to string map
	type2str = AwlOperatorTypes.type2str


	# Immediate integer.
	# Only used for IMM types.
	immediate = 0 #@nocy

	# Immediate bytes/bytearray.
	# Only used for IMM_DT type.
	immediateBytes = b"" #@nocy

	# Immediate pointer.
	# Only used for IMM_PTR type.
	pointer = None #@nocy

	# Extended-operator flag.
	isExtended = False #@nocy

	# Possible label index.
	labelIndex = None #@nocy

	# Interface index number.
	# May be set by the symbol resolver.
	interfaceIndex = None #@nocy

	# Compound data type flag.
	# Set to true for accesses > 32 bit or
	# arrays/structs or array/struct elements.
	compound = False #@nocy

	# The access data type (AwlDataType), if known.
	# Only set for resolved symbolic accesses.
	dataType = None #@nocy

#@cy	def __cinit__(self):
#@cy		self.immediate = 0
#@cy		self.immediateBytes = bytearray()
#@cy		self.pointer = None
#@cy		self.isExtended = False
#@cy		self.labelIndex = None
#@cy		self.interfaceIndex = None
#@cy		self.compound = False
#@cy		self.dataType = None

	def __init__(self, operType, width, value, insn): #@nocy
#@cy	def __init__(self, uint32_t operType, int32_t width, object value, AwlInsn insn):
		# operType -> The operator type ID number. See "Operator types" above.
		# width -> The bit width of the access.
		# value -> The value. May be an AwlOffset or a string (depends on type).
		# insn -> The instruction this operator is used in. May be None.
		self.operType, self.width, self.value, self.insn =\
			operType, width, value, insn

	def __eq__(self, other): #@nocy
#@cy	cdef __eq(self, AwlOperator other):
		return (self is other) or (\
			isinstance(other, AwlOperator) and\
			self.operType == other.operType and\
			self.width == other.width and\
			self.value == other.value and\
			super(AwlOperator, self).__eq__(other)\
		)

	def __ne__(self, other):		#@nocy
		return not self.__eq__(other)	#@nocy

#@cy	def __richcmp__(self, object other, int op):
#@cy		if op == 2: # __eq__
#@cy			return self.__eq(other)
#@cy		elif op == 3: # __ne__
#@cy			return not self.__eq(other)
#@cy		return False

	# Make a deep copy, except for "insn".
	def dup(self): #@nocy
#@cy	cpdef AwlOperator dup(self):
#@cy		cdef AwlOperator oper

		if self.value is None:
			dupValue = None
		elif isInteger(self.value):
			dupValue = self.value
		else:
			dupValue = self.value.dup()
		oper = AwlOperator(operType=self.operType,
				   width=self.width,
				   value=dupValue,
				   insn=self.insn)
		oper.pointer = self.pointer
		oper.immediate = self.immediate
		oper.immediateBytes = bytearray(self.immediateBytes)
		oper.isExtended = self.isExtended
		oper.labelIndex = self.labelIndex
		oper.interfaceIndex = self.interfaceIndex
		return oper

	def setInsn(self, newInsn):
		self.insn = newInsn

	def setExtended(self, isExtended):
		self.isExtended = isExtended

	def setLabelIndex(self, newLabelIndex):
		self.labelIndex = newLabelIndex

	def isImmediate(self): #@nocy
#@cy	cpdef _Bool isImmediate(self):
		return self.operType > AwlOperatorTypes._IMM_START and\
		       self.operType < AwlOperatorTypes._IMM_END

	def _raiseTypeError(self, actualType, expectedTypes):
		expectedTypes = [ self.type2str[t] for t in sorted(expectedTypes) ]
		raise AwlSimError("Invalid operator type. Got %s, but expected %s." %\
			(self.type2str[actualType],
			 listToHumanStr(expectedTypes)),
			insn=self.insn)

	def assertType(self, types, lowerLimit=None, upperLimit=None, widths=None):
		if self.operType == AwlOperatorTypes.NAMED_LOCAL or\
		   self.operType == AwlOperatorTypes.NAMED_LOCAL_PTR:
			return #FIXME we should check type for these, too.
		types = toSet(types)
		if not self.operType in types:
			self._raiseTypeError(self.operType, types)
		if lowerLimit is not None:
			if not self.isImmediate() or self.operType == AwlOperatorTypes.IMM_DT:
				raise AwlSimBug("Invalid operator type for lowerLimit check")
			if self.immediate < lowerLimit:
				raise AwlSimError("Operator value too small",
						  insn=self.insn)
		if upperLimit is not None:
			if not self.isImmediate() or self.operType == AwlOperatorTypes.IMM_DT:
				raise AwlSimBug("Invalid operator type for upperLimit check")
			if self.immediate > upperLimit:
				raise AwlSimError("Operator value too big",
						  insn=self.insn)
		if widths is not None:
			widths = toSet(widths)
			if not self.width in widths:
				raise AwlSimError("Invalid operator width. "
					"Got %d, but expected %s." %\
					(self.width, listToHumanStr(widths)))

	def checkDataTypeCompat(self, cpu, dataType):
		assert(isinstance(dataType, AwlDataType))

		if self.operType in (AwlOperatorTypes.NAMED_LOCAL,
				     AwlOperatorTypes.NAMED_LOCAL_PTR,
				     AwlOperatorTypes.NAMED_DBVAR,
				     AwlOperatorTypes.SYMBOLIC):
			# These are checked again after resolve.
			# So don't check them now.
			return

		def mismatch(dataType, oper, operWidth):
			raise AwlSimError("Data type '%s' of width %d bits "
				"is not compatible with operator '%s' "
				"of width %d bits." %\
				(str(dataType), dataType.width, str(oper), operWidth))

		if dataType.type == AwlDataType.TYPE_UDT_X:
			try:
				udt = cpu.udts[dataType.index]
				if udt._struct.getSize() * 8 != self.width:
					raise ValueError
			except (KeyError, ValueError) as e:
				mismatch(dataType, self, self.width)
		elif dataType.type in {AwlDataType.TYPE_POINTER,
				       AwlDataType.TYPE_ANY}:
			if self.operType == AwlOperatorTypes.IMM_PTR:
				if dataType.type == AwlDataType.TYPE_POINTER and\
				   self.width > 48:
					raise AwlSimError("Invalid immediate pointer "
						"assignment to POINTER type.")
			else:
				if self.isImmediate():
					raise AwlSimError("Invalid immediate "
						"assignment to '%s' type." %\
						str(dataType))
				# Try to make pointer from operator.
				# This will raise AwlSimError on failure.
				self.makePointer()
		elif dataType.type == AwlDataType.TYPE_CHAR:
			if self.operType == AwlOperatorTypes.IMM_STR:
				if self.width != (2 + 1) * 8:
					raise AwlSimError("String to CHAR parameter "
						"must be only one single character "
						"long.")
			else:
				if self.isImmediate():
					raise AwlSimError("Invalid immediate '%s'"
						"for CHAR data type." %\
						str(self))
				if self.width != dataType.width:
					mismatch(dataType, self, self.width)
		elif dataType.type == AwlDataType.TYPE_STRING:
			if self.operType == AwlOperatorTypes.IMM_STR:
				if self.width > dataType.width:
					mismatch(dataType, self, self.width)
			else:
				if self.isImmediate():
					raise AwlSimError("Invalid immediate '%s'"
						"for STRING data type." %\
						str(self))
				assert(self.width <= (254 + 2) * 8)
				assert(dataType.width <= (254 + 2) * 8)
				if dataType.width != (254 + 2) * 8:
					if self.width != dataType.width:
						mismatch(dataType, self, self.width)
		else:
			if self.width != dataType.width:
				mismatch(dataType, self, self.width)

	# Resolve this indirect operator to a direct operator.
	def resolve(self, store=True): #@nocy
#@cy	cpdef AwlOperator resolve(self, _Bool store=True):
		# This already is a direct operator.
		if self.operType == AwlOperatorTypes.NAMED_LOCAL:
			# This is a named-local access (#abc).
			# Resolve it to an interface-operator.
			return self.insn.cpu.callStackTop.getInterfIdxOper(self.interfaceIndex).resolve(store)
		return self

	# Make an area-spanning Pointer (32 bit) to this memory area.
	def makePointer(self):
		return Pointer(self.makePointerValue())

	# Make an area-spanning pointer value (32 bit) to this memory area.
	def makePointerValue(self): #@nocy
#@cy	cpdef uint32_t makePointerValue(self):
#@cy		cdef uint32_t area

		try:
			area = AwlIndirectOp.optype2area[self.operType]
		except KeyError as e:
			raise AwlSimError("Could not transform operator '%s' "
				"into a pointer." % str(self))
		return area | self.value.toPointerValue()

	# Make a DBPointer (48 bit) to this memory area.
	def makeDBPointer(self):
		return DBPointer(self.makePointerValue(),
				 self.value.dbNumber)

	# Make an ANY-pointer to this memory area.
	# Returns an ANYPointer().
	def makeANYPointer(self, areaShifted=None):
		ptrValue = self.makePointerValue()
		if areaShifted:
			ptrValue &= ~Pointer.AREA_MASK_S
			ptrValue |= areaShifted
		if ANYPointer.dataTypeIsSupported(self.dataType):
			return ANYPointer.makeByAutoType(dataType = self.dataType,
							 ptrValue = ptrValue,
							 dbNr = self.value.dbNumber)
		return ANYPointer.makeByTypeWidth(bitWidth = self.width,
						  ptrValue = ptrValue,
						  dbNr = self.value.dbNumber)

	def __repr__(self):
		if self.operType == AwlOperatorTypes.IMM:
			if self.width == 1:
				return "TRUE" if (self.immediate & 1) else "FALSE"
			elif self.width == 8:
				return str(byteToSignedPyInt(self.immediate))
			elif self.width == 16:
				return str(wordToSignedPyInt(self.immediate))
			elif self.width == 32:
				return "L#" + str(dwordToSignedPyInt(self.immediate))
		if self.operType == AwlOperatorTypes.IMM_REAL:
			return str(dwordToPyFloat(self.immediate))
		elif self.operType == AwlOperatorTypes.IMM_S5T:
			seconds = Timer.s5t_to_seconds(self.immediate)
			return "S5T#" + AwlDataType.formatTime(seconds)
		elif self.operType == AwlOperatorTypes.IMM_TIME:
			return "T#" + AwlDataType.formatTime(self.immediate / 1000.0)
		elif self.operType == AwlOperatorTypes.IMM_DATE:
			return "D#" #TODO
		elif self.operType == AwlOperatorTypes.IMM_TOD:
			return "TOD#" #TODO
		elif self.operType == AwlOperatorTypes.IMM_PTR:
			return self.pointer.toPointerString()
		elif self.operType == AwlOperatorTypes.IMM_STR:
			strLen = self.value[1]
			return "'" + self.value[2:2+strLen].decode(AwlSource.COMPAT_ENCODING) + "'"
		elif self.operType in (AwlOperatorTypes.MEM_A, AwlOperatorTypes.MEM_E,
				   AwlOperatorTypes.MEM_M, AwlOperatorTypes.MEM_L, AwlOperatorTypes.MEM_VL):
			pfx = self.type2str[self.operType]
			if self.width == 1:
				return "%s %d.%d" %\
					(pfx, self.value.byteOffset, self.value.bitOffset)
			elif self.width == 8:
				return "%sB %d" % (pfx, self.value.byteOffset)
			elif self.width == 16:
				return "%sW %d" % (pfx, self.value.byteOffset)
			elif self.width == 32:
				return "%sD %d" % (pfx, self.value.byteOffset)
			return self.makeANYPointer().toPointerString()
		elif self.operType == AwlOperatorTypes.MEM_DB:
			if self.value.dbNumber is None:
				dbPrefix = ""
			else:
				dbPrefix = "DB%d." % self.value.dbNumber
			if self.width == 1:
				return "%sDBX %d.%d" % (dbPrefix,
							self.value.byteOffset,
							self.value.bitOffset)
			elif self.width == 8:
				return "%sDBB %d" % (dbPrefix, self.value.byteOffset)
			elif self.width == 16:
				return "%sDBW %d" % (dbPrefix, self.value.byteOffset)
			elif self.width == 32:
				return "%sDBD %d" % (dbPrefix, self.value.byteOffset)
			return self.makeANYPointer().toPointerString()
		elif self.operType == AwlOperatorTypes.MEM_DI:
			if self.width == 1:
				return "DIX %d.%d" % (self.value.byteOffset, self.value.bitOffset)
			elif self.width == 8:
				return "DIB %d" % self.value.byteOffset
			elif self.width == 16:
				return "DIW %d" % self.value.byteOffset
			elif self.width == 32:
				return "DID %d" % self.value.byteOffset
			return self.makeANYPointer().toPointerString()
		elif self.operType == AwlOperatorTypes.MEM_T:
			return "T %d" % self.value.byteOffset
		elif self.operType == AwlOperatorTypes.MEM_Z:
			return "Z %d" % self.value.byteOffset
		elif self.operType == AwlOperatorTypes.MEM_PA:
			if self.width == 8:
				return "PAB %d" % self.value.byteOffset
			elif self.width == 16:
				return "PAW %d" % self.value.byteOffset
			elif self.width == 32:
				return "PAD %d" % self.value.byteOffset
			return self.makeANYPointer().toPointerString()
		elif self.operType == AwlOperatorTypes.MEM_PE:
			if self.width == 8:
				return "PEB %d" % self.value.byteOffset
			elif self.width == 16:
				return "PEW %d" % self.value.byteOffset
			elif self.width == 32:
				return "PED %d" % self.value.byteOffset
			return self.makeANYPointer().toPointerString()
		elif self.operType == AwlOperatorTypes.MEM_STW:
			return "__STW " + S7StatusWord.nr2name_german[self.value.bitOffset]
		elif self.operType == AwlOperatorTypes.LBL_REF:
			return self.value
		elif self.operType == AwlOperatorTypes.BLKREF_FC:
			return "FC %d" % self.value.byteOffset
		elif self.operType == AwlOperatorTypes.BLKREF_SFC:
			return "SFC %d" % self.value.byteOffset
		elif self.operType == AwlOperatorTypes.BLKREF_FB:
			return "FB %d" % self.value.byteOffset
		elif self.operType == AwlOperatorTypes.BLKREF_SFB:
			return "SFB %d" % self.value.byteOffset
		elif self.operType == AwlOperatorTypes.BLKREF_UDT:
			return "UDT %d" % self.value.byteOffset
		elif self.operType == AwlOperatorTypes.BLKREF_DB:
			return "DB %d" % self.value.byteOffset
		elif self.operType == AwlOperatorTypes.BLKREF_DI:
			return "DI %d" % self.value.byteOffset
		elif self.operType == AwlOperatorTypes.BLKREF_OB:
			return "OB %d" % self.value.byteOffset
		elif self.operType == AwlOperatorTypes.BLKREF_VAT:
			return "VAT %d" % self.value.byteOffset
		elif self.operType == AwlOperatorTypes.MULTI_FB:
			return "#FB<" + self.makeANYPointer(AwlIndirectOp.AREA_DI).toPointerString() + ">"
		elif self.operType == AwlOperatorTypes.MULTI_SFB:
			return "#SFB<" + self.makeANYPointer(AwlIndirectOp.AREA_DI).toPointerString() + ">"
		elif self.operType == AwlOperatorTypes.SYMBOLIC:
			return '"%s"' % self.value.identChain.getString()
		elif self.operType == AwlOperatorTypes.NAMED_LOCAL:
			return "#" + self.value.identChain.getString()
		elif self.operType == AwlOperatorTypes.NAMED_LOCAL_PTR:
			return "P##" + self.value.identChain.getString()
		elif self.operType == AwlOperatorTypes.NAMED_DBVAR:
			return str(self.value) # value is AwlOffset
		elif self.operType == AwlOperatorTypes.INDIRECT:
			assert(0) # Overloaded in AwlIndirectOp
		elif self.operType == AwlOperatorTypes.VIRT_ACCU:
			return "__ACCU %d" % self.value.byteOffset
		elif self.operType == AwlOperatorTypes.VIRT_AR:
			return "__AR %d" % self.value.byteOffset
		elif self.operType == AwlOperatorTypes.VIRT_DBR:
			return "__DBR %d" % self.value.byteOffset
		elif self.operType == AwlOperatorTypes.UNSPEC:
			return "__UNSPEC"
		try:
			return self.type2str[self.operType]
		except KeyError:
			assert(0)

class AwlIndirectOp(AwlOperator): #+cdef
	"""Indirect addressing operand.
	"""

	# Address register
	AR_NONE		= 0	# No address register
	AR_1		= 1	# Use AR1
	AR_2		= 2	# Use AR2

	# Pointer area constants
	AREA_MASK	= Pointer.AREA_MASK_S
	EXT_AREA_MASK	= Pointer.AREA_MASK_S | 0xFF00000000

	# Pointer area encodings
	AREA_NONE	= 0
	AREA_P		= Pointer.AREA_P << Pointer.AREA_SHIFT
	AREA_E		= Pointer.AREA_E << Pointer.AREA_SHIFT
	AREA_A		= Pointer.AREA_A << Pointer.AREA_SHIFT
	AREA_M		= Pointer.AREA_M << Pointer.AREA_SHIFT
	AREA_DB		= Pointer.AREA_DB << Pointer.AREA_SHIFT
	AREA_DI		= Pointer.AREA_DI << Pointer.AREA_SHIFT
	AREA_L		= Pointer.AREA_L << Pointer.AREA_SHIFT
	AREA_VL		= Pointer.AREA_VL << Pointer.AREA_SHIFT

	# Extended area encodings. Only used for internal purposes.
	# These are not used in the interpreted AWL code.
	EXT_AREA_T		= 0x01FF000000	# Timer
	EXT_AREA_Z		= 0x02FF000000	# Counter
	EXT_AREA_BLKREF_DB	= 0x03FF000000	# DB block reference
	EXT_AREA_BLKREF_DI	= 0x04FF000000	# DI block reference
	EXT_AREA_BLKREF_FB	= 0x05FF000000	# FB block reference
	EXT_AREA_BLKREF_FC	= 0x06FF000000	# FC block reference

	# Map for converting area code to operator type for fetch operations
	area2optype_fetch = {
		AREA_P			: AwlOperatorTypes.MEM_PE,
		AREA_E			: AwlOperatorTypes.MEM_E,
		AREA_A			: AwlOperatorTypes.MEM_A,
		AREA_M			: AwlOperatorTypes.MEM_M,
		AREA_DB			: AwlOperatorTypes.MEM_DB,
		AREA_DI			: AwlOperatorTypes.MEM_DI,
		AREA_L			: AwlOperatorTypes.MEM_L,
		AREA_VL			: AwlOperatorTypes.MEM_VL,
		EXT_AREA_T		: AwlOperatorTypes.MEM_T,
		EXT_AREA_Z		: AwlOperatorTypes.MEM_Z,
		EXT_AREA_BLKREF_DB	: AwlOperatorTypes.BLKREF_DB,
		EXT_AREA_BLKREF_DI	: AwlOperatorTypes.BLKREF_DI,
		EXT_AREA_BLKREF_FB	: AwlOperatorTypes.BLKREF_FB,
		EXT_AREA_BLKREF_FC	: AwlOperatorTypes.BLKREF_FC,
	}

	# Map for converting area code to operator type for store operations
	area2optype_store = area2optype_fetch.copy()
	area2optype_store[AREA_P] = AwlOperatorTypes.MEM_PA

	# Map for converting operator type to area code
	optype2area = pivotDict(area2optype_fetch)
	optype2area[AwlOperatorTypes.MEM_PA] = AREA_P
	optype2area[AwlOperatorTypes.MULTI_FB] = AREA_DI
	optype2area[AwlOperatorTypes.MULTI_SFB] = AREA_DI
	optype2area[AwlOperatorTypes.NAMED_DBVAR] = AREA_DB
	optype2area[AwlOperatorTypes.UNSPEC] = AREA_NONE

	def __init__(self, area, width, addressRegister, offsetOper, insn=None): #@nocy
#@cy	def __init__(self, uint64_t area, int32_t width, uint32_t addressRegister,
#@cy		     AwlOperator offsetOper, AwlInsn insn=None):
		# area -> The area code for this indirect operation.
		#         AREA_... or EXT_AREA_...
		#         This corresponds to the area code in AWL pointer format.
		# width -> The width (in bits) of the region that is being adressed.
		# addressRegister -> One of:
		#                    AR_NONE => This is a memory-indirect access.
		#                    AR_1 => This is a register-indirect access with AR1.
		#                    AR_2 => This is a register-indirect access with AR2.
		# offsetOper -> This is the AwlOperator for the offset.
		#               For memory-indirect access, this must be an AwlOperator
		#               with "type in __possibleOffsetOperTypes".
		#               For register-indirect access, this must be an AwlOperator
		#               with "type==IMM_PTR".
		# insn -> The instruction this operator is used in. May be None.
		AwlOperator.__init__(self,
				     operType=AwlOperatorTypes.INDIRECT,
				     width=width,
				     value=None,
				     insn=insn)
		self.area, self.addressRegister, self.offsetOper =\
			area, addressRegister, offsetOper

	# Make a deep copy, except for "insn".
	def dup(self): #@nocy
#@cy	cpdef AwlOperator dup(self):
		return AwlIndirectOp(area = self.area,
				     width = self.width,
				     addressRegister = self.addressRegister,
				     offsetOper = self.offsetOper.dup(),
				     insn = self.insn)

	def setInsn(self, newInsn):
		AwlOperator.setInsn(self, newInsn)
		self.offsetOper.setInsn(newInsn)

	def assertType(self, types, lowerLimit=None, upperLimit=None):
		types = toSet(types)
		if not self.area2optype_fetch[self.area] in types and\
		   not self.area2optype_store[self.area] in types:
			self._raiseTypeError(self.area2optype_fetch[self.area], types)
		assert(lowerLimit is None)
		assert(upperLimit is None)

	# Possible offset oper types for indirect access
	__possibleOffsetOperTypes = (AwlOperatorTypes.MEM_M,
				     AwlOperatorTypes.MEM_L,
				     AwlOperatorTypes.MEM_DB,
				     AwlOperatorTypes.MEM_DI)

	# Resolve this indirect operator to a direct operator.
	def resolve(self, store=True): #@nocy
#@cy	cpdef AwlOperator resolve(self, _Bool store=True):
#@cy		cdef _Bool bitwiseDirectOffset
#@cy		cdef AwlOffset directOffset
#@cy		cdef AwlOperator offsetOper
#@cy		cdef set possibleWidths
#@cy		cdef uint32_t offsetValue
#@cy		cdef uint64_t pointer
#@cy		cdef uint32_t optype

		bitwiseDirectOffset = True
		offsetOper = self.offsetOper
		# Construct the pointer
		if self.addressRegister == AwlIndirectOp.AR_NONE:
			# Memory-indirect access
			if self.area == AwlIndirectOp.AREA_NONE:
				raise AwlSimError("Area-spanning access not "
					"possible in indirect access without "
					"address register.")
			if self.area > AwlIndirectOp.AREA_MASK:
				# Is extended area
				possibleWidths = {8, 16, 32}
				bitwiseDirectOffset = False
			else:
				# Is standard area
				possibleWidths = {32,}
			if offsetOper.operType not in self.__possibleOffsetOperTypes:
				raise AwlSimError("Offset operator in indirect "
					"access is not a valid memory offset.")
			if offsetOper.width not in possibleWidths:
				raise AwlSimError("Offset operator in indirect "
					"access is not of %s bit width." %\
					listToHumanStr(possibleWidths))
			offsetValue = self.insn.cpu.fetch(offsetOper)
			pointer = (self.area | (offsetValue & 0x0007FFFF))
		else:
			# Register-indirect access
			if offsetOper.operType != AwlOperatorTypes.IMM_PTR:
				raise AwlSimError("Offset operator in "
					"register-indirect access is not a "
					"pointer immediate.")
			offsetValue = self.insn.cpu.fetch(offsetOper) & 0x0007FFFF
			if self.area == AwlIndirectOp.AREA_NONE:
				# Area-spanning access
				pointer = (self.insn.cpu.getAR(self.addressRegister).get() +\
					   offsetValue) & 0xFFFFFFFF
			else:
				# Area-internal access
				pointer = ((self.insn.cpu.getAR(self.addressRegister).get() +
					    offsetValue) & 0x0007FFFF) |\
					  self.area
		# Create a direct operator
		try:
			if store:
				optype = AwlIndirectOp.area2optype_store[
						pointer & AwlIndirectOp.EXT_AREA_MASK]
			else:
				optype = AwlIndirectOp.area2optype_fetch[
						pointer & AwlIndirectOp.EXT_AREA_MASK]
		except KeyError:
			raise AwlSimError("Invalid area code (%X hex) in indirect addressing" %\
				((pointer & AwlIndirectOp.EXT_AREA_MASK) >>\
				 Pointer.AREA_SHIFT))
		if bitwiseDirectOffset:
			# 'pointer' has pointer format
			directOffset = AwlOffset.fromPointerValue(pointer)
		else:
			# 'pointer' is a byte offset
			directOffset = AwlOffset(pointer & 0x0000FFFF)
		if self.width != 1 and directOffset.bitOffset:
			raise AwlSimError("Bit offset (lowest three bits) in %d-bit "
				"indirect addressing is not zero. "
				"(Computed offset is: %s)" %\
				(self.width, str(directOffset)))
		return AwlOperator(optype, self.width, directOffset, self.insn)

	def __pointerError(self):
		# This is a programming error.
		# The caller should resolve() the operator first.
		raise AwlSimBug("Can not transform indirect operator "
			"into a pointer. Resolve it first.")

	def makePointer(self):
		self.__pointerError()

	def makePointerValue(self): #@nocy
#@cy	cpdef uint32_t makePointerValue(self):
		self.__pointerError()

	def makeDBPointer(self):
		self.__pointerError()

	def makeANYPointer(self, areaShifted=None):
		self.__pointerError()

	def __repr__(self):
		return "__INDIRECT" #TODO

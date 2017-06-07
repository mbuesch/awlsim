# -*- coding: utf-8 -*-
#
# AWL simulator - User defined data types (UDT)
#
# Copyright 2014-2017 Michael Buesch <m@bues.ch>
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

from awlsim.core.util import *
from awlsim.core.blocks import * #+cimport
from awlsim.core.datastructure import * #+cimport

from awlsim.awlcompiler.translator import *


__all__ = [
	"UDT",
]


class UDTField(object): #+cdef
	"""User defined data type (UDT) data field."""

	def __init__(self, name, dataType, initBytes=None):
		# name -> The name string of the field, as defined
		#         in the block interface definition.
		# dataType -> AwlDataType instance.
		# initBytes -> bytes or bytearray of initialization data, or None.
		self.name = name
		self.dataType = dataType
		self.initBytes = initBytes

	def __repr__(self):
		if self.initBytes:
			return "%s : %s := %s" %\
				(self.name, str(self.dataType),
				 str(self.initBytes))
		return "%s : %s" % (self.name, str(self.dataType))

class StructRecursion(Exception):
	pass

class UDT(Block): #+cdef
	"""User defined data type (UDT) block."""

	# self._struct build status.
	EnumGen.start
	STRUCT_NOT_BUILT	= EnumGen.item # Structs not built, yet.
	STRUCT_BUILDING		= EnumGen.item # Currently building structs.
	STRUCT_BUILT		= EnumGen.item # Structs are completely built.
	EnumGen.end

	# Convert a RawAwlUDT() to UDT()
	@classmethod
	def makeFromRaw(cls, rawUDT):
		udt = cls(rawUDT.index)
		udt.setSourceRef(rawUDT.sourceRef, inheritRef = True)
		translator = AwlTranslator(cpu = None)
		for rawField in rawUDT.fields:
			name, dataType, initBytes =\
				translator.rawFieldTranslate(rawField)
			field = UDTField(name, dataType, initBytes)
			udt.addField(field)
		return udt

	def __init__(self, index):
		Block.__init__(self, index)
		# The list of UDTField()s
		self.fields = []
		self.fieldNameMap = {}
		# The built data structure.
		self._struct = AwlStruct()
		self.__structState = self.STRUCT_NOT_BUILT

	def addField(self, field):
		if field.name in self.fieldNameMap:
			raise AwlSimError("Data structure field name '%s' is ambiguous." %\
				field.name)
		self.fields.append(field)
		self.fieldNameMap[field.name] = field

	def __buildField(self, cpu, field):
		from awlsim.core.datatypes import AwlDataType

		if field.dataType.width < 0:
			# The size of the field is unknown, yet.
			# Try to resolve it.
			if field.dataType.type == AwlDataType.TYPE_UDT_X:
				# This UDT embeds another UDT.
				# Get the embedded UDT and build it.
				try:
					udt = cpu.udts[field.dataType.index]
				except KeyError:
					raise AwlSimError("The '%s' embeds "
						"a 'UDT %d', which does not "
						"exist." %\
						(str(self),
						 field.dataType.index))
				# Build the data structure of the embedded UDT.
				try:
					udt.buildDataStructure(cpu)
				except StructRecursion:
					raise AwlSimError("Recursion detected while "
						"trying to resolve embedded 'UDT %d' "
						"in '%s'." %\
						(field.dataType.index,
						 str(self)))
			else:
				raise AwlSimError("Unable to resolve the size "
					"of '%s' data field '%s'" %\
					(str(self), str(field)))
		# Insert the field into the data structure.
		# If the field is an embedded UDT, addField will handle it.
		self._struct.addFieldNaturallyAligned(cpu, field.name,
						      field.dataType,
						      field.initBytes)

	# Build self._struct out of self.fields
	def buildDataStructure(self, cpu):
		if self.__structState == self.STRUCT_BUILT:
			# We already built this block's interface structure.
			return
		if self.__structState == self.STRUCT_BUILDING:
			# Whoops, we recursed! This is bad.
			raise StructRecursion()
		self.__structState = self.STRUCT_BUILDING
		for field in self.fields:
			self.__buildField(cpu, field)
		# Sanity check
		if self._struct.getSize() == 0:
			# This is not supported by S7.
			# Awlsim _could_ support it, though.
			raise AwlSimError("UDTs with zero size "
				"are not supported. Please declare at least "
				"one variable in '%s'" % str(self))
		self.__structState = self.STRUCT_BUILT

	def __repr__(self):
		return "UDT %d" % self.index

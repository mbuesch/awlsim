# -*- coding: utf-8 -*-
#
# AWL simulator - blocks
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from awllabels import *
from awlstruct import *
from util import *


class BlockInterface(object):
	class Field(object):
		FTYPE_UNKNOWN	= -1
		FTYPE_IN	= 0
		FTYPE_OUT	= 1
		FTYPE_INOUT	= 2
		FTYPE_STAT	= 3
		FTYPE_TEMP	= 4

		def __init__(self, name, dataType, initialValue=None):
			self.name = name
			self.dataType = dataType
			self.fieldType = self.FTYPE_UNKNOWN
			self.initialValue = initialValue

	def __init__(self):
		self.struct = None
		self.fieldNameMap = {}
		self.fields_IN = []
		self.fields_OUT = []
		self.fields_INOUT = []
		self.fields_STAT = []
		self.fields_TEMP = []

	def __addField(self, field):
		if field.name in self.fieldNameMap:
			raise AwlSimError("Data structure name '%s' is ambiguous." %\
				field.name)
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

	def __buildField(self, field, isFirst):
		if isFirst:
			self.struct.addFieldAligned(field.name,
						    field.dataType.width, 2)
		else:
			self.struct.addFieldNaturallyAligned(field.name,
							     field.dataType.width)

	def buildDataStructure(self):
		self.struct = AwlStruct()
		for i, field in enumerate(self.fields_IN):
			self.__buildField(field, i==0)
		for i, field in enumerate(self.fields_OUT):
			self.__buildField(field, i==0)
		for i, field in enumerate(self.fields_INOUT):
			self.__buildField(field, i==0)
		for i, field in enumerate(self.fields_STAT):
			self.__buildField(field, i==0)

	def getFieldByName(self, name):
		try:
			return self.fieldNameMap[name]
		except KeyError:
			raise AwlSimError("Data structure field '%s' does not exist." %\
				name)

	@property
	def fieldCount(self):
		return len(self.fieldNameMap)

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
	pass

class FB(Block):
	def __init__(self, insns, index):
		Block.__init__(self, insns, index, FBInterface())

	def __repr__(self):
		return "FB %d" % self.index

class SFBInterface(FBInterface):
	pass

class SFB(Block):
	def __init__(self, index):
		Block.__init__(self, None, index, SFBInterface())

	def run(self, cpu, dbOper):
		pass # Reimplement this method

	def __repr__(self):
		return "SFB %d" % self.index

class FCInterface(BlockInterface):
	def addField_STAT(self, field):
		raise AwlSimError("Static VAR not possible in an FC")

class FC(Block):
	def __init__(self, insns, index):
		Block.__init__(self, insns, index, FCInterface())

	def __repr__(self):
		return "FC %d" % self.index

class SFCInterface(FCInterface):
	pass

class SFC(Block):
	def __init__(self, index):
		Block.__init__(self, None, index, SFCInterface())

	def run(self, cpu):
		pass # Reimplement this method

	def __repr__(self):
		return "SFC %d" % self.index

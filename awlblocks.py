# -*- coding: utf-8 -*-
#
# AWL simulator - blocks
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from awllabels import *
from util import *


class BlockInterface(object):
	class Field(object):
		def __init__(self, name, type, initialValue=None):
			self.name = name
			self.type = type
			self.initialValue = initialValue

	def __init__(self):
		self.fields_IN = []
		self.fields_OUT = []
		self.fields_INOUT = []
		self.fields_STAT = []
		self.fields_TEMP = []

	def addField_IN(self, field):
		self.fields_IN.append(field)

	def addField_OUT(self, field):
		self.fields_OUT.append(field)

	def addField_INOUT(self, field):
		self.fields_INOUT.append(field)

	def addField_STAT(self, field):
		self.fields_STAT.append(field)

	def addField_TEMP(self, field):
		self.fields_TEMP.append(field)

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

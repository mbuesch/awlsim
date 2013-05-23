# -*- coding: utf-8 -*-
#
# AWL simulator - datablocks
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from awlsim.util import *
from awlsim.operators import *
from awlsim.datatypes import *
from awlsim.datastructure import *


class DB(object):
	def __init__(self, index, codeBlock=None):
		self.index = index
		self.codeBlock = codeBlock	# The FB or FC, if this is an instance/bounce-DB.
		if self.codeBlock:
			# The data structure is declared by the interface.
			self.__struct = None
		else:
			self.__struct = AwlStruct()
		self.structInstance = None

	@property
	def struct(self):
		if self.codeBlock:
			return self.codeBlock.interface.struct
		return self.__struct

	def isInstanceDB(self):
		return bool(self.codeBlock)

	def allocate(self):
		self.structInstance = AwlStructInstance(self.struct)

	def fetch(self, operator):
		return AwlOperator.fetchFromByteArray(self.structInstance.dataBytes,
						      operator)

	def store(self, operator, value):
		AwlOperator.storeToByteArray(self.structInstance.dataBytes,
					     operator, value)

	def __repr__(self):
		return "DB %d" % self.index

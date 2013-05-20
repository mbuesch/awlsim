# -*- coding: utf-8 -*-
#
# AWL simulator - datablocks
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from util import *
from awloperators import *
from awldatatypes import *
from awlstruct import *


class DB(object):
	def __init__(self, index, fb=None):
		self.index = index
		self.fb = fb		# The FB, if this is an instance-DB.
		if fb:
			# The data structure is declared by the interface.
			self.__struct = None
		else:
			self.__struct = AwlStruct()
		self.structInstance = None

	@property
	def struct(self):
		if self.fb:
			return self.fb.interface.struct
		return self.__struct

	def isInstanceDB(self):
		return bool(self.fb)

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

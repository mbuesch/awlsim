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


class DBByte(GenericByte):
	def __init__(self, value=0):
		GenericByte.__init__(self, value)

class DB(object):
	class Field(object):
		def __init__(self, name, offset, size):
			self.name = name
			self.offset = offset
			self.size = size

	def __init__(self, index):
		self.index = index
		self.dataBytes = []
		self.fields = { }

	def addField(self, fieldData, size, name=None):
		#FIXME alignment
		# Allocate the data bytes and set field data (big endian)
		for i in range(size // 8 - 1, -1, -1):
			d = (fieldData >> (i * 8)) & 0xFF
			self.dataBytes.append(DBByte(d))
		# Create a named field for the data area.
		if name:
			f = self.Field(name,
				       len(self.dataBytes) - size,
				       size)
			self.fields[name] = f

	def fetch(self, operator):
		return AwlOperator.fetchFromByteArray(self.dataBytes,
						      operator)

	def store(self, operator, value):
		AwlOperator.storeToByteArray(self.dataBytes,
					     operator, value)

	def __repr__(self):
		return "DB %d" % self.index

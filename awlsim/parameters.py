# -*- coding: utf-8 -*-
#
# AWL simulator - call parameters
# Copyright 2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from awlsim.blocks import *
from awlsim.util import *


class AwlParamAssign(object):
	"Parameter assignment for CALL"

	DIR_UNKNOWN	= -1	# magic value: Unknown direction
	DIR_IN		= 0x1	# in-bitmask
	DIR_OUT		= 0x2	# out-bitmask

	def __init__(self, lvalueName, rvalueOp):
		self.lvalueName = lvalueName
		self.rvalueOp = rvalueOp
		self.direction = self.DIR_UNKNOWN

	def __setDirection(self, interface):
		self.direction = 0
		field = interface.getFieldByName(self.lvalueName)
		if field.fieldType == BlockInterface.Field.FTYPE_IN or\
		   field.fieldType == BlockInterface.Field.FTYPE_INOUT:
			self.direction |= self.DIR_IN
		if field.fieldType == BlockInterface.Field.FTYPE_OUT or\
		   field.fieldType == BlockInterface.Field.FTYPE_INOUT:
			self.direction |= self.DIR_OUT

	def isInbound(self, interface):
		if self.direction == self.DIR_UNKNOWN:
			self.__setDirection(interface)
		return self.direction & self.DIR_IN

	def isOutbound(self, interface):
		if self.direction == self.DIR_UNKNOWN:
			self.__setDirection(interface)
		return self.direction & self.DIR_OUT

	def __repr__(self):
		return "%s := %s" % (self.lvalueName, str(self.rvalueOp))

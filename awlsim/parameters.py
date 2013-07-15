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

	def __init__(self, lvalueName, rvalueOp):
		self.lvalueName = lvalueName
		self.rvalueOp = rvalueOp

	def __retTrue(self, interface):
		return True

	def __retFalse(self, interface):
		return False

	# Re-assign the isInbound() and isOutbound() methods
	# to methods return static values.
	def __reassignMethods(self, interface):
		self.isInbound, self.isOutbound = self.__retFalse, self.__retFalse
		field = interface.getFieldByName(self.lvalueName)
		if field.fieldType == BlockInterface.Field.FTYPE_IN or\
		   field.fieldType == BlockInterface.Field.FTYPE_INOUT:
			self.isInbound = self.__retTrue
		if field.fieldType == BlockInterface.Field.FTYPE_OUT or\
		   field.fieldType == BlockInterface.Field.FTYPE_INOUT:
			self.isOutbound = self.__retTrue

	def isInbound(self, interface):
		self.__reassignMethods(interface)
		# Call the re-assigned method
		return self.isInbound(None)

	def isOutbound(self, interface):
		self.__reassignMethods(interface)
		# Call the re-assigned method
		return self.isOutbound(None)

	def __repr__(self):
		return "%s := %s" % (self.lvalueName, str(self.rvalueOp))

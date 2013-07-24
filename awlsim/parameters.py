# -*- coding: utf-8 -*-
#
# AWL simulator - call parameters
#
# Copyright 2013 Michael Buesch <m@bues.ch>
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

from awlsim.datastructure import *
from awlsim.datablocks import *
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

	def __getLvalueStructField_static(self, interfaceDB):
		return self.__LvaluestructField

	# Get the AwlStructField corresponding to this parameter lvalue
	def getLvalueStructField(self, interfaceDB):
		self.__LvaluestructField = interfaceDB.structInstance.struct.getField(self.lvalueName)
		self.getLvalueStructField = self.__getLvalueStructField_static
		# Call the re-assigned method
		return self.getLvalueStructField(None)

	def __repr__(self):
		return "%s := %s" % (self.lvalueName, str(self.rvalueOp))

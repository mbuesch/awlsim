# -*- coding: utf-8 -*-
#
# AWL simulator - call parameters
#
# Copyright 2013-2014 Michael Buesch <m@bues.ch>
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
from awlsim.core.compat import *

from awlsim.core.datastructure import *
from awlsim.core.datablocks import *
from awlsim.core.blocks import *
from awlsim.core.util import *
from awlsim.core.dynattrs import *


class AwlParamAssign(DynAttrs):
	"Parameter assignment for CALL"

	dynAttrs = {
		# isInbound attribute is True, if this is an
		# IN or IN_OUT parameter assignment.
		"isInbound"	: lambda self, name: self.__isInbound(),

		# isOutbound attribute is True, if this is an
		# OUT or IN_OUT parameter assignment.
		"isOutbound"	: lambda self, name: self.__isOutbound(),

		# lValueStructField attribute is the AwlStructField corresponding
		# to this parameter's l-value.
		"lValueStructField"	: lambda self, name: self.__lValueStructField(),

		# interfaceFieldIndex attribute is the index number for the
		# parameter assignment l-value in the block interface refs.
		"interfaceFieldIndex"	: lambda self, name: self.__interfaceFieldIndex(),

		# scratchSpaceOp attribute holds the possible AwlOperator for
		# scratch space allocation.
		"scratchSpaceOp"	: None,
	}

	def __init__(self, lvalueName, rvalueOp):
		self.lvalueName = lvalueName
		self.rvalueOp = rvalueOp
		self.interface = None
		self.instanceDB = None

	def __isInbound(self):
		field = self.interface.getFieldByName(self.lvalueName)
		return field.fieldType == BlockInterfaceField.FTYPE_IN or\
		       field.fieldType == BlockInterfaceField.FTYPE_INOUT

	def __isOutbound(self):
		field = self.interface.getFieldByName(self.lvalueName)
		return field.fieldType == BlockInterfaceField.FTYPE_OUT or\
		       field.fieldType == BlockInterfaceField.FTYPE_INOUT

	def __lValueStructField(self):
		# Find the l-value struct field
		return self.instanceDB.structInstance.struct.getField(self.lvalueName)

	def __interfaceFieldIndex(self):
		# Find the index number for the l-value
		return self.interface.getFieldIndex(self.lvalueName)

	def __repr__(self):
		return "%s := %s" % (self.lvalueName, str(self.rvalueOp))

# -*- coding: utf-8 -*-
#
# AWL simulator - call parameters
#
# Copyright 2013-2017 Michael Buesch <m@bues.ch>
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

from awlsim.core.datastructure import * #+cimport
from awlsim.core.operatortypes import * #+cimport
from awlsim.core.operators import * #+cimport
from awlsim.core.datablocks import * #+cimport
from awlsim.core.blocks import * #+cimport
from awlsim.core.blockinterface import *
from awlsim.core.util import *


__all__ = [
	"AwlParamAssign",
]


class AwlParamAssign(object): #+cdef
	"""Parameter assignment for CALL.
	"""

	def __init__(self, lvalueName, rvalueOp):
		# A parameter assignment consists of an lvalue and an rvalue:
		#  LVALUE := RVALUE
		# 'lvalueName' is the name string of the lvalue.
		# 'rvalueOp' is the AwlOperator that represents the rvalue.
		self.lvalueName = lvalueName
		self.rvalueOp = rvalueOp

		# scratchSpaceOp attribute holds the possible AwlOperator for
		# scratch space allocation.
		# This element is assigned during runtime.
		self.scratchSpaceOp = make_AwlOperator(operType=AwlOperatorTypes.IMM,
						  width=32, offset=None,
						  insn=None)

		# 'interface' is the BlockInterface of the called block.
		# This element is assigned later in the translation phase
		# with a call to setInterface()
		self.interface = None

		# isInbound attribute is True, if this is an
		# IN or IN_OUT parameter assignment.
		# This element is assigned later in the translation phase
		# with a call to setInterface()
		self.isInbound = False

		# isOutbound attribute is True, if this is an
		# OUT or IN_OUT parameter assignment.
		# This element is assigned later in the translation phase
		# with a call to setInterface()
		self.isOutbound = False

		# lValueDataType attribute is the AwlDataType of the
		# parameter's l-value.
		# This element is assigned later in the translation phase
		# with a call to setInterface()
		self.lValueDataType = None

		# lValueStructField attribute is the AwlStructField corresponding
		# to this parameter's l-value.
		# This element is assigned later in the translation phase
		# with a call to setInterface()
		self.lValueStructField = None

		# interfaceFieldIndex attribute is the index number for the
		# parameter assignment l-value in the block interface refs.
		# This element is assigned later in the translation phase
		# with a call to setInterface()
		self.interfaceFieldIndex = -1

	def __eq__(self, other): #@nocy
#@cy	cpdef __eq(self, object other):
		return (self is other) or (\
			isinstance(other, AwlParamAssign) and\
			self.lvalueName == other.lvalueName and\
			self.rvalueOp == other.rvalueOp\
		)

#@cy	def __richcmp__(self, object other, int op):
#@cy		if op == 2: # __eq__
#@cy			return self.__eq(other)
#@cy		elif op == 3: # __ne__
#@cy			return not self.__eq(other)
#@cy		return False

	def __ne__(self, other):		#@nocy
		return not self.__eq__(other)	#@nocy

	def setInterface(self, interface):
		self.interface = interface
		self.isInbound = self.__isInbound()
		self.isOutbound = self.__isOutbound()
		self.lValueDataType = self.__lValueDataType()
		self.lValueStructField = self.__lValueStructField()
		self.interfaceFieldIndex = self.__interfaceFieldIndex()

		# Store a static reference to the finalOverride in the
		# struct field. This improves performance of CALLs.
		structField = self.lValueStructField
		if structField:
			structField.finalOverride = structField.getFinalOverride()

	def __isInbound(self):
		field = self.interface.getFieldByName(self.lvalueName)
		return field.fieldType == BlockInterfaceField.FTYPE_IN or\
		       field.fieldType == BlockInterfaceField.FTYPE_INOUT

	def __isOutbound(self):
		field = self.interface.getFieldByName(self.lvalueName)
		return field.fieldType == BlockInterfaceField.FTYPE_OUT or\
		       field.fieldType == BlockInterfaceField.FTYPE_INOUT

	def __lValueDataType(self):
		# Get the l-value data type
		return self.interface.getFieldByName(self.lvalueName).dataType

	def __lValueStructField(self):
		# Find the l-value struct field
		_struct = self.interface._struct
		if _struct:
			return _struct.getField(self.lvalueName)
		return None

	def __interfaceFieldIndex(self):
		# Find the index number for the l-value
		return self.interface.getFieldByName(self.lvalueName).fieldIndex

	def __repr__(self):
		return "%s := %s" % (self.lvalueName, str(self.rvalueOp))

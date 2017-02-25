# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - Operand element
#
# Copyright 2016-2017 Michael Buesch <m@bues.ch>
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

from awlsim.fupcompiler.fupcompiler_elem import *

#from awlsim.core.instructions.all_insns cimport * #@cy
from awlsim.core.instructions.all_insns import * #@nocy


class FupCompiler_ElemOper(FupCompiler_Elem):
	"""FUP compiler - Operand element.
	"""

	EnumGen.start
	SUBTYPE_LOAD		= EnumGen.item
	SUBTYPE_ASSIGN		= EnumGen.item
	EnumGen.end

	str2subtype = {
		"load"		: SUBTYPE_LOAD,
		"assign"	: SUBTYPE_ASSIGN,
	}

	@classmethod
	def parse(cls, grid, x, y, subType, content):
		try:
			subType = cls.str2subtype[subType]
			if subType == cls.SUBTYPE_LOAD:
				return FupCompiler_ElemOperLoad(grid=grid,
							        x=x, y=y,
							        content=content)
			elif subType == cls.SUBTYPE_ASSIGN:
				return FupCompiler_ElemOperAssign(grid=grid,
								  x=x, y=y,
								  content=content)
		except KeyError:
			pass
		return None

	def __init__(self, grid, x, y, subType, content):
		FupCompiler_Elem.__init__(self, grid=grid, x=x, y=y,
					  elemType=FupCompiler_Elem.TYPE_OPERAND,
					  subType=subType, content=content)

class FupCompiler_ElemOperLoad(FupCompiler_ElemOper):
	"""FUP compiler - Operand LOAD element.
	"""

	# Allow multiple compilations of LOAD operand.
	allowTrans_done2Running = True

	def __init__(self, grid, x, y, content):
		FupCompiler_ElemOper.__init__(self, grid=grid, x=x, y=y,
					      subType=FupCompiler_ElemOper.SUBTYPE_LOAD,
					      content=content)

		# Constructor class used for LOAD operand.
		self.__insnClass = None

	def setInsnClass(self, insnClass):
		self.__insnClass = insnClass

	def _doCompile(self):
		insns = []

		insnClass = self.__insnClass
		if not insnClass:
			# This shall never happen.
			raise AwlSimError("FUP LOAD: Load without a "
				"known instruction class.")

		# Translate the LOAD operand and create the
		# corresponding instruction.
		opDesc = self.opTrans.translateFromString(self.content)
		insns.append(insnClass(cpu=None, ops=[opDesc.operator]))

		return insns

class FupCompiler_ElemOperAssign(FupCompiler_ElemOper):
	"""FUP compiler - Operand ASSIGN element.
	"""

	def __init__(self, grid, x, y, content):
		FupCompiler_ElemOper.__init__(self, grid=grid, x=x, y=y,
					      subType=FupCompiler_ElemOper.SUBTYPE_ASSIGN,
					      content=content)

	def _doCompile(self):
		insns = []

		# Only one connection allowed per ASSIGN.
		if len(self.connections) != 1:
			raise AwlSimError("FUP ASSIGN: Invalid number of "
				"connections in '%s'." % (
				str(self)))

		# The connection must be input.
		conn = getany(self.connections)
		if not conn.dirIn or conn.dirOut or conn.pos != 0:
			raise AwlSimError("FUP ASSIGN: Invalid connection "
				"properties in '%s'." % (
				str(self)))

		# Compile the element connected to the input.
		connsOut = tuple(conn.getConnected(getOutputs=True))
		if len(connsOut) != 1:
			raise AwlSimError("FUP ASSIGN: Multiple outbound signals "
				"connected to '%s'." % (
				str(self)))
		otherElem = connsOut[0].elem
		if otherElem.compileState == self.NOT_COMPILED:
			insns.extend(otherElem.compile())
		else:
			insns.extend(otherElem._loadFromTemp(AwlInsn_U))

		# Create the ASSIGN instruction.
		opDesc = self.opTrans.translateFromString(self.content)
		insns.append(AwlInsn_ASSIGN(cpu=None, ops=[opDesc.operator]))

		insns.extend(otherElem._mayStoreToTemp())

		# Compile additional assign operators.
		# This is an optimization to avoid additional compilations
		# of the whole tree. We just assign the VKE once again.
		#FIXME this might lead to problems in evaluation order, if we have a branch with interleaved assigns and other elems.
		for otherElem in self.sorted(conn.getConnectedElems(viaIn=True)):
			if otherElem.elemType == self.TYPE_OPERAND and\
			   otherElem.subType == self.SUBTYPE_ASSIGN:
				otherElem.compileState = self.COMPILE_RUNNING
				opDesc = self.opTrans.translateFromString(otherElem.content)
				insns.append(AwlInsn_ASSIGN(cpu=None, ops=[opDesc.operator]))
				otherElem.compileState = self.COMPILE_DONE

		return insns

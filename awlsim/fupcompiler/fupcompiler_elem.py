# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - Element
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

from awlsim.common.xmlfactory import *
from awlsim.common.util import *

from awlsim.fupcompiler.fupcompiler_base import *
from awlsim.fupcompiler.fupcompiler_conn import *

from awlsim.awlcompiler.optrans import *

#from awlsim.core.instructions.all_insns cimport * #@cy
from awlsim.core.instructions.all_insns import * #@nocy


class FupCompiler_ElemFactory(XmlFactory):
	def parser_open(self, tag=None):
		self.inElem = False
		self.elem = None
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		if self.inElem:
			if self.elem and tag.name == "connections":
				self.parser_switchTo(FupCompiler_Conn.factory(elem=self.elem))
				return
		else:
			if tag.name == "element":
				self.inElem = True
				x = tag.getAttrInt("x")
				y = tag.getAttrInt("y")
				elemType = tag.getAttr("type")
				subType = tag.getAttr("subtype", None)
				content = tag.getAttr("content", None)
				self.elem = FupCompiler_Elem.parse(self.grid,
					x, y, elemType, subType, content)
				if not self.elem:
					raise self.Error("Failed to parse element")
				return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if self.inElem:
			if tag.name == "element":
				if self.elem:
					self.grid.addElem(self.elem)
				self.inElem = False
				self.elem = None
				return
		else:
			if tag.name == "elements":
				self.parser_finish()
				return
		XmlFactory.parser_endTag(self, tag)

class FupCompiler_Elem(FupCompiler_BaseObj):
	factory = FupCompiler_ElemFactory

	EnumGen.start
	TYPE_BOOLEAN		= EnumGen.item
	TYPE_OPERAND		= EnumGen.item
	EnumGen.end

	EnumGen.start
	SUBTYPE_AND		= EnumGen.item
	SUBTYPE_OR		= EnumGen.item
	SUBTYPE_XOR		= EnumGen.item
	SUBTYPE_LOAD		= EnumGen.item
	SUBTYPE_ASSIGN		= EnumGen.item
	EnumGen.end

	str2type = {
		"boolean"	: TYPE_BOOLEAN,
		"operand"	: TYPE_OPERAND,
	}

	str2subtype = {
		"and"		: SUBTYPE_AND,
		"or"		: SUBTYPE_OR,
		"xor"		: SUBTYPE_XOR,
		"load"		: SUBTYPE_LOAD,
		"assign"	: SUBTYPE_ASSIGN,
	}

	@classmethod
	def sorted(cls, elemList):
		"""Sort all elements from elemList in ascending order by Y position.
		The Y position in the diagram is the basic evaluation order.
		Also sort by X position as a secondary key.
		The sorted list is returned.
		"""
		if not elemList:
			return []
		yShift = max(e.x for e in elemList).bit_length()
		return sorted(elemList,
			      key=lambda e: (e.y << yShift) + e.x)

	@classmethod
	def parse(cls, grid, x, y, elemType, subType, content):
		try:
			elemType = cls.str2type[elemType]
			if subType:
				subType = cls.str2subtype[subType]
			else:
				subType = None
		except KeyError:
			return None
		return cls(grid, x, y, elemType, subType, content)

	def __init__(self, grid, x, y, elemType, subType, content):
		FupCompiler_BaseObj.__init__(self)
		self.grid = grid			# FupCompiler_Grid
		self.x = x				# X coordinate
		self.y = y				# Y coordinate
		self.elemType = elemType		# TYPE_...
		self.subType = subType			# SUBTYPE_... or None
		self.content = content or ""		# content string
		self.connections = set()		# FupCompiler_Conn

		# If this field has already been compiled and the result is
		# stored in a temp-field, this is the name of that field.
		self.resultVkeVarName = None

		if elemType == self.TYPE_OPERAND and\
		   subType == self.SUBTYPE_LOAD:
			# Allow multiple compilations of LOAD operand.
			self.allowTrans_done2Running = True

	def addConn(self, conn):
		self.connections.add(conn)
		return True

	def __compile_OPERAND_ASSIGN(self):
		opTrans = self.grid.compiler.opTrans
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
		connOut = [ c for c in conn.getConnected() if c.dirOut ]
		if len(connOut) != 1:
			raise AwlSimError("FUP ASSIGN: Multiple outbound signals "
				"connected to '%s'." % (
				str(self)))
		insns.extend(connOut[0].elem.compile())

		# Create the ASSIGN instruction.
		opDesc = opTrans.translateFromString(self.content)
		insns.append(AwlInsn_ASSIGN(cpu=None, ops=[opDesc.operator]))

		# Compile additional assign operators.
		# This is an optimization to avoid additional compilations
		# of the whole tree. We just assign the VKE once again.
		otherElems = [ c.elem for c in conn.getConnected() if c.dirIn ]
		for otherElem in self.sorted(otherElems):
			if otherElem.elemType == self.TYPE_OPERAND and\
			   otherElem.subType == self.SUBTYPE_ASSIGN:
				otherElem.compileState = self.COMPILE_RUNNING
				opDesc = opTrans.translateFromString(otherElem.content)
				insns.append(AwlInsn_ASSIGN(cpu=None, ops=[opDesc.operator]))
				otherElem.compileState = self.COMPILE_DONE

		return insns

	__operandTable = {
		SUBTYPE_ASSIGN		: __compile_OPERAND_ASSIGN,
	}

	def __compile_OPERAND(self):
		try:
			handler = self.__operandTable[self.subType]
		except KeyError:
			raise AwlSimError("FUP compiler: Unknown element "
				"subtype OPERAND/%d" % self.subType)
		return handler(self)

	def __compile_BOOLEAN_generic(self, insnClass, insnBranchClass):
		opTrans = self.grid.compiler.opTrans
		insns = []
		for conn in sorted(self.connections, key=lambda c: c.pos):
			if not conn.dirIn:
				continue
			for otherElem in conn.getConnectedElems(viaOut=True):
				if otherElem.elemType == self.TYPE_OPERAND and\
				   otherElem.subType == self.SUBTYPE_LOAD:
					otherElem.compileState = self.COMPILE_RUNNING
					opDesc = opTrans.translateFromString(otherElem.content)
					insns.append(insnClass(cpu=None, ops=[opDesc.operator]))
					otherElem.compileState = self.COMPILE_DONE
				elif otherElem.elemType == self.TYPE_BOOLEAN:
					# The other element we get the signal from
					# is a boolean element. Compile this to get its
					# resulting VKE.
					if otherElem.compileState == self.NOT_COMPILED:
						insns.append(insnBranchClass(cpu=None))
						insns.extend(otherElem.compile())
						# Check if we need to save the result
						# for other element inputs.
						if any(c.dirIn and c is not conn
						       for c in otherElem.connections):
							# There are other in-connections connected
							# to the "otherElem". Allocate a TEMP variable
							# and store the result.
							varName = self.grid.compiler.interf.allocTEMP("BOOL")
							opDesc = opTrans.translateFromString("#" + varName)
							insns.append(AwlInsn_ASSIGN(cpu=None,
										    ops=[opDesc.operator]))
							otherElem.resultVkeVarName = varName
						insns.append(AwlInsn_BEND(cpu=None))
					else:
						# otherElem has already been compiled and the result has
						# been stored in TEMP. Use the stored result.
						varName = otherElem.resultVkeVarName
						if not varName:
							raise AwlSimError("FUP compiler: Result of a "
								"compiled element has not been stored "
								"to a TEMP variable.")
						opDesc = opTrans.translateFromString("#" + varName)
						insns.append(insnClass(cpu=None, ops=[opDesc.operator]))
				else:
					raise AwlSimError("FUP compiler: Invalid "
						"element '%s' connected to '%s'." % (
						str(otherElem), str(self)))
		return insns

	def __compile_BOOLEAN_AND(self):
		return self.__compile_BOOLEAN_generic(AwlInsn_U, AwlInsn_UB)

	def __compile_BOOLEAN_OR(self):
		return self.__compile_BOOLEAN_generic(AwlInsn_O, AwlInsn_OB)

	def __compile_BOOLEAN_XOR(self):
		return self.__compile_BOOLEAN_generic(AwlInsn_X, AwlInsn_XB)

	__booleanTable = {
		SUBTYPE_AND		: __compile_BOOLEAN_AND,
		SUBTYPE_OR		: __compile_BOOLEAN_OR,
		SUBTYPE_XOR		: __compile_BOOLEAN_XOR,
	}

	def __compile_BOOLEAN(self):
		try:
			handler = self.__booleanTable[self.subType]
		except KeyError:
			raise AwlSimError("FUP compiler: Unknown element "
				"subtype BOOLEAN/%d" % self.subType)
		return handler(self)

	__typeTable = {
		TYPE_OPERAND		: __compile_OPERAND,
		TYPE_BOOLEAN		: __compile_BOOLEAN,
	}

	def compile(self):
		if self.compileState == self.COMPILE_DONE:
			# This may happen, if we already handled the element.
			# See multi-ASSIGN handling.
			return []
		self.compileState = self.COMPILE_RUNNING

		try:
			handler = self.__typeTable[self.elemType]
		except KeyError:
			raise AwlSimError("FUP compiler: Unknown element "
				"type %d" % self.elemType)
		result = handler(self)

		self.compileState = self.COMPILE_DONE
		return result

	def __repr__(self):
		return "FupCompiler_Elem(grid, x=%d, y=%d, elemType=%d, "\
			"subType=%d, content=%s)" % (
			self.x, self.y, self.elemType, self.subType, self.content)

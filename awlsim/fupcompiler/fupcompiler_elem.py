# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - Element
#
# Copyright 2016 Michael Buesch <m@bues.ch>
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

#from awlsim.core.instructions.all_insns cimport * #@cy
from awlsim.core.instructions.all_insns import * #@nocy
from awlsim.core.optrans import *


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
			content = content or None
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
		self.content = content			# content string or None
		self.connections = set()		# FupCompiler_Conn

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
		for conn in self.connections:
			if not conn.dirIn:
				continue
			for otherConn in conn.getConnected():
				if not otherConn.dirOut:
					continue
				otherElem = otherConn.elem
				if otherElem.elemType == self.TYPE_OPERAND and\
				   otherElem.subType == self.SUBTYPE_LOAD:
					otherElem.compileState = self.COMPILE_RUNNING
					opDesc = opTrans.translateFromString(otherElem.content)
					insns.append(insnClass(cpu=None, ops=[opDesc.operator]))
					otherElem.compileState = self.COMPILE_DONE
				elif otherElem.elemType == self.TYPE_BOOLEAN:
					insns.append(insnBranchClass(cpu=None))
					insns.extend(otherElem.compile())
					insns.append(AwlInsn_BEND(cpu=None))
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

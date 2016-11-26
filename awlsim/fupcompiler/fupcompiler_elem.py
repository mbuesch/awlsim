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
	def parser_open(self):
		self.inElem = False
		self.elem = None
		XmlFactory.parser_open(self)

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

	def __compile_ASSIGN(self):
		insns = []
		if len(self.connections) != 1:
			raise AwlSimError("FUP ASSIGN: Invalid number of connections")
		conn = getany(self.connections)
		if not conn.dirIn or conn.dirOut or conn.pos != 0:
			raise AwlSimError("FUP ASSIGN: Invalid connection properties")
		wire = self.grid.getWire(conn.wireId)
		if not wire:
			raise AwlSimError("FUP ASSIGN: Wire does not exist")
		pass#TODO
		opDesc = self.grid.compiler.opTrans.translateFromString(self.content)
		insns.append(AwlInsn_ASSIGN(cpu=None, ops=[opDesc.operator]))
		print("ASSIGN", insns)
		return insns

	def compile(self):
		if self.elemType == self.TYPE_OPERAND:
			if self.subType == self.SUBTYPE_ASSIGN:
				return self.__compile_ASSIGN()
		assert(0)

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

	str2type = {
		"boolean"	: TYPE_BOOLEAN,
		"operand"	: TYPE_OPERAND,
	}

	@classmethod
	def sorted(cls, elems):
		"""Sort all elements from 'elems' sequence in ascending order by Y position.
		The Y position in the diagram is the basic evaluation order.
		Also sort by X position as a secondary key.
		The sorted list is returned.
		"""
		elems = tuple(elems)
		try:
			yShift = max(e.x for e in elems).bit_length()
		except ValueError:
			return []
		return sorted(elems,
			      key=lambda e: (e.y << yShift) + e.x)

	@classmethod
	def parse(cls, grid, x, y, elemType, subType, content):
		from awlsim.fupcompiler.fupcompiler_elembool import FupCompiler_ElemBool
		from awlsim.fupcompiler.fupcompiler_elemoper import FupCompiler_ElemOper
		try:
			elemType = cls.str2type[elemType]
			if elemType == cls.TYPE_BOOLEAN:
				return FupCompiler_ElemBool.parse(grid=grid,
								  x=x, y=y,
								  subType=subType,
								  content=content)
			elif elemType == cls.TYPE_OPERAND:
				return FupCompiler_ElemOper.parse(grid=grid,
								  x=x, y=y,
								  subType=subType,
								  content=content)
		except KeyError:
			pass
		return None

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
		self.__resultVkeVarName = None

	@property
	def opTrans(self):
		return self.grid.compiler.opTrans

	def addConn(self, conn):
		self.connections.add(conn)
		return True

	@property
	def inConnections(self):
		"""Get all input connections.
		"""
		for conn in self.connections:
			if conn.dirIn:
				yield conn

	@property
	def outConnections(self):
		"""Get all output connections.
		"""
		for conn in self.connections:
			if conn.dirOut:
				yield conn

	def _mayStoreToTemp(self):
		insns = []

		# Check if we need to save the result
		# for other element inputs.
		# This is the case, if we have more than one input connection
		# to 'otherElem's output connection.
		if any(len(tuple(c.getConnected(getInputs=True))) > 1
		       for c in self.outConnections):
			varName = self.grid.compiler.interf.allocTEMP("BOOL")
			opDesc = self.opTrans.translateFromString("#" + varName)
			insns.append(AwlInsn_ASSIGN(cpu=None,
						    ops=[opDesc.operator]))
			self.__resultVkeVarName = varName

		return insns

	def _loadFromTemp(self, insnClass):
		insns = []

		# otherElem has already been compiled and the result has
		# been stored in TEMP. Use the stored result.
		assert(self.compileState != self.NOT_COMPILED)
		varName = self.__resultVkeVarName
		if not varName:
			raise AwlSimError("FUP compiler: Result of a "
				"compiled element has not been stored "
				"to a TEMP variable.")
		opDesc = self.opTrans.translateFromString("#" + varName)
		insns.append(insnClass(cpu=None, ops=[opDesc.operator]))

		return insns

	def _doCompile(self):
		raise NotImplementedError

	def compile(self):
		self.compileState = self.COMPILE_RUNNING
		result = self._doCompile()
		self.compileState = self.COMPILE_DONE
		return result

	def __repr__(self):
		return "FupCompiler_Elem(grid, x=%d, y=%d, elemType=%d, "\
			"subType=%d, content=%s)" % (
			self.x, self.y, self.elemType, self.subType, self.content)

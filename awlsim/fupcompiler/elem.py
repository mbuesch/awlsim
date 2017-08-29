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

from awlsim.fupcompiler.base import *
from awlsim.fupcompiler.conn import *

from awlsim.awlcompiler.optrans import *

from awlsim.core.instructions.all_insns import * #+cimport


class FupCompiler_ElemFactory(XmlFactory):
	CONTAINER_TAG	= "elements"

	def parser_open(self, tag=None):
		self.inElem = False
		self.elem = None
		self.subelemsFakeGrid = None
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		if self.inElem:
			if self.elem and tag.name == "connections":
				self.parser_switchTo(FupCompiler_Conn.factory(elem=self.elem))
				return
			if self.elem and tag.name == "subelements":
				from awlsim.fupcompiler.grid import FupCompiler_Grid
				if self.subelemsFakeGrid:
					raise self.Error("Found multiple <subelements> tags "
						"inside of boolean <element>.")
				self.subelemsFakeGrid = FupCompiler_Grid(None)
				self.parser_switchTo(FupCompiler_Elem.factory(grid=self.subelemsFakeGrid,
									      CONTAINER_TAG="subelements"))
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
					raise self.Error("Failed to parse element "
						"type '%s'%s at x=%d y=%d" % (
						elemType,
						"" if subType is None else (" subtype '%s'" % subType),
						x, y))
				return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if self.inElem:
			if tag.name == "element":
				if self.elem:
					if self.subelemsFakeGrid and\
					   self.subelemsFakeGrid.elems:
						self.elem.subElems = self.subelemsFakeGrid.elems.copy()
						for e in self.elem.subElems:
							e.grid = self.grid
						self.subelemsFakeGrid = None
					self.grid.addElem(self.elem)
				self.inElem = False
				self.elem = None
				return
		else:
			if tag.name == self.CONTAINER_TAG:
				self.parser_finish()
				return
		XmlFactory.parser_endTag(self, tag)

class FupCompiler_Elem(FupCompiler_BaseObj):
	factory = FupCompiler_ElemFactory

	ELEM_NAME = "FUP-element"

	EnumGen.start
	TYPE_BOOLEAN		= EnumGen.item
	TYPE_OPERAND		= EnumGen.item
	TYPE_MOVE		= EnumGen.item
	TYPE_ARITH		= EnumGen.item
	TYPE_COMMENT		= EnumGen.item
	EnumGen.end

	str2type = {
		"boolean"	: TYPE_BOOLEAN,
		"operand"	: TYPE_OPERAND,
		"move"		: TYPE_MOVE,
		"arithmetic"	: TYPE_ARITH,
		"comment"	: TYPE_COMMENT,
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
		from awlsim.fupcompiler.elembool import FupCompiler_ElemBool
		from awlsim.fupcompiler.elemoper import FupCompiler_ElemOper
		from awlsim.fupcompiler.elemmove import FupCompiler_ElemMove
		from awlsim.fupcompiler.elemarith import FupCompiler_ElemArith
		from awlsim.fupcompiler.elemcomment import FupCompiler_ElemComment
		try:
			elemType = cls.str2type[elemType]
			type2class = {
				cls.TYPE_BOOLEAN	: FupCompiler_ElemBool,
				cls.TYPE_OPERAND	: FupCompiler_ElemOper,
				cls.TYPE_MOVE		: FupCompiler_ElemMove,
				cls.TYPE_ARITH		: FupCompiler_ElemArith,
				cls.TYPE_COMMENT	: FupCompiler_ElemComment,
			}
			elemClass = None
			with contextlib.suppress(KeyError):
				elemClass = type2class[elemType]
			if elemClass:
				return elemClass.parse(grid=grid,
						       x=x, y=y,
						       subType=subType,
						       content=content)
		except KeyError:
			pass
		return None

	def __init__(self, grid, x, y, elemType, subType, content, virtual=False):
		FupCompiler_BaseObj.__init__(self)
		self.grid = grid			# FupCompiler_Grid
		self.x = x				# X coordinate
		self.y = y				# Y coordinate
		self.elemType = elemType		# TYPE_...
		self.subType = subType			# SUBTYPE_... or None
		self.content = content or ""		# content string
		self.connections = set()		# FupCompiler_Conn
		self.virtual = bool(virtual)		# Flag: Virtual element
		self.subElems = set()			# Set of sub-elements (if any)

		# This dict contains the values of the connections,
		# if this element has already been compiled.
		# Dict key is FupCompiler_Conn and value is the TEMP var name string.
		self.__tempVarNames = {}

		if virtual:
			self.forceCompileState(self.COMPILE_PREPROCESSED)

	@property
	def compiler(self):
		if self.grid:
			return self.grid.compiler
		return None

	def isType(self, elemType, subType=None):
		"""Check the TYPE and SUBTYPE of this element.
		If 'subType' is None, the subType is not checked.
		Both elemType or subType may be iterables. In this case
		all types from the iterable are allowed.
		True is returned, if the types match.
		"""
		elemTypes = toList(elemType)
		if subType is None:
			return self.elemType in elemTypes
		subTypes = toList(subType)
		return self.elemType in elemTypes and\
		       self.subType in subTypes

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

	def connIsOptional(self, conn):
		"""Check if a connection is optional.
		The default implementation always returns False.
		"""
		return False

	def getConnType(self, conn):
		"""Get the type of a connection.
		The default implementation always returns VKE based type.
		"""
		return FupCompiler_Conn.TYPE_VKE

	def getConnByText(self, connText,
			  searchInputs=False, searchOutputs=False,
			  caseSensitive=False):
		"""Get connections by name.
		Search in inputs, if 'searchInputs' is True.
		Search in outputs, if 'searchOutputs' is True.
		Returns a generator over the found connections.
		"""
		for conn in self.connections:
			if not strEqual(connText, conn.text, caseSensitive):
				continue
			if searchInputs and conn.dirIn:
				yield conn
			if searchOutputs and conn.dirOut:
				yield conn

	def getUniqueConnByText(self, connText,
				searchInputs=False, searchOutputs=False,
				caseSensitive=False):
		"""Get a unique connection by name.
		Search in inputs, if 'searchInputs' is True.
		Search in outputs, if 'searchOutputs' is True.
		This raises FupElemError, if the connection is not unique.
		Returns the FupCompiler_Conn() or None if not found.
		"""
		connections = list(self.getConnByText(connText,
						      searchInputs,
						      searchOutputs,
						      caseSensitive))
		if len(connections) <= 0:
			return None
		if len(connections) > 1:
			raise FupElemError("The element '%s' "
				"has multiple connections with the "
				"same name '%s'." % (
				str(self), connText),
				self)
		return connections[0]

	MAIN_RESULT = 42

	def _storeToTemp(self, dataTypeName, insnClass, connections=MAIN_RESULT):
		insns = []

		if connections or\
		   connections is self.MAIN_RESULT:
			varName = self.grid.compiler.interf.allocTEMP(dataTypeName,
								      elem=self)
			opDesc = self.opTrans.translateFromString("#" + varName)
			insns.append(self.newInsn(insnClass,
						  ops=[opDesc.operator]))
			if connections is self.MAIN_RESULT:
				self.__tempVarNames[self.MAIN_RESULT] = varName
			else:
				for conn in connections:
					self.__tempVarNames[conn] = varName

		return insns

	def _loadFromTemp(self, insnClass, conn=MAIN_RESULT):
		insns = []

		# otherElem has already been compiled and the result has
		# been stored in TEMP. Use the stored result.
		assert(not self.needCompile)
		try:
			varName = self.__tempVarNames[conn]
		except KeyError as e:
			if conn and conn != self.MAIN_RESULT and conn.text:
				connText = "The output %s" % conn.text
			else:
				connText = "The result"
			raise FupElemError("%s of the "
				"compiled element %s has not been stored "
				"to a TEMP variable." % (
				connText, str(self)),
				self)
		opDesc = self.opTrans.translateFromString("#" + varName)
		insns.append(self.newInsn(insnClass, ops=[opDesc.operator]))

		return insns

	def compileConn(self, conn, desiredTarget, inverted=False):
		"""Compile this element
		and get the value corresponding to the given connection.
		The desiredTarget is one of FupCompiler_Conn.TARGET_...
		If 'inverted' is True, the result will be stored inverted.
		Inversion is only possible for VKE based targets.
		The default implementation raises an exception.
		Override this method, if required.
		"""
		raise FupElemError("Do not know how to "
			"compile the connection %s of element %s." % (
			str(conn), str(self)),
			self)

	def _doPreprocess(self):
		"""Element preprocessor.
		Defaults to no preprocessing.
		Override this method, if required.
		"""
		pass

	def _doCompile(self):
		"""Element compiler.
		Override this.
		"""
		raise NotImplementedError

	def preprocess(self):
		"""Main element preprocessor entry point.
		Do not override this. Override _doPreprocess instead.
		"""
		self.compileState = self.COMPILE_PREPROCESSING

		# Preprocess the elements connected to the in-connections first.
		for conn in self.inConnections:
			for elem in conn.getConnectedElems(viaOut=True):
				if elem.needPreprocess:
					elem.preprocess()

		# Preprocess this element
		self._doPreprocess()

		self.compileState = self.COMPILE_PREPROCESSED

	def compile(self):
		"""Main element compiler entry point.
		Do not override this. Override _doCompile instead.
		"""
		self.compileState = self.COMPILE_RUNNING
		result = self._doCompile()
		self.compileState = self.COMPILE_DONE
		return result

	def newInsn(self, insnClass, ops=[]):
		"""Wrapper: Call the compiler method to create an instruction.
		"""
		return self.grid.compiler.newInsn(self, insnClass, ops)

	def newInsn_JMP(self, insnClass, labelStr):
		"""Wrapper: Call the compiler method to create a jump instruction.
		"""
		return self.grid.compiler.newInsn_JMP(self, insnClass, labelStr)

	def newInsn_NOP(self, labelStr=None):
		"""Wrapper: Call the compiler method to create a NOP instruction.
		"""
		return self.grid.compiler.newInsn_NOP(self, labelStr)

	def newInsn_LOAD_BIE(self, insnClass):
		"""Wrapper: Call the compiler method to create a BIE load instruction.
		"""
		return self.grid.compiler.newInsn_LOAD_BIE(self, insnClass)

	def __repr__(self):
		return "FupCompiler_Elem(grid, x=%d, y=%d, elemType=%d, "\
			"subType=%s, content=\"%s\", virtual=%s)" % (
			self.x, self.y, self.elemType,
			str(self.subType), self.content,
			str(self.virtual))

	def toStr(self, extra=()):
		values = []
		if self.x >= 0 and self.y >= 0:
			values.append("x%d/y%d" % (
				self.x + 1,
				self.y + 1))
		if self.virtual:
			values.append("VIRTUAL")
		if self.content.strip():
			values.append("'%s'" % self.content)
		values.extend(extra)
		return "%s(%s)" % (self.ELEM_NAME, ", ".join(values))

	def __str__(self):
		return self.toStr()

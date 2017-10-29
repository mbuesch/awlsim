# -*- coding: utf-8 -*-
#
# AWL simulator - FUP - Arithmetic element classes
#
# Copyright 2017 Michael Buesch <m@bues.ch>
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

from awlsim.gui.fup.fup_base import *
from awlsim.gui.fup.fup_elem import *
from awlsim.gui.fup.fup_elemoperand import *


class FupElem_ARITH_factory(FupElem_factory):
	def parser_open(self, tag):
		assert(tag)
		x = tag.getAttrInt("x")
		y = tag.getAttrInt("y")
		subType = tag.getAttr("subtype")
		uuid = tag.getAttr("uuid", None)
		elemClass = {
			FupElem_ARITH_ADD_I.OP_SYM_NAME	: FupElem_ARITH_ADD_I,
			FupElem_ARITH_SUB_I.OP_SYM_NAME	: FupElem_ARITH_SUB_I,
			FupElem_ARITH_MUL_I.OP_SYM_NAME	: FupElem_ARITH_MUL_I,
			FupElem_ARITH_DIV_I.OP_SYM_NAME	: FupElem_ARITH_DIV_I,
			FupElem_ARITH_ADD_D.OP_SYM_NAME	: FupElem_ARITH_ADD_D,
			FupElem_ARITH_SUB_D.OP_SYM_NAME	: FupElem_ARITH_SUB_D,
			FupElem_ARITH_MUL_D.OP_SYM_NAME	: FupElem_ARITH_MUL_D,
			FupElem_ARITH_DIV_D.OP_SYM_NAME	: FupElem_ARITH_DIV_D,
			FupElem_ARITH_MOD_D.OP_SYM_NAME	: FupElem_ARITH_MOD_D,
			FupElem_ARITH_ADD_R.OP_SYM_NAME	: FupElem_ARITH_ADD_R,
			FupElem_ARITH_SUB_R.OP_SYM_NAME	: FupElem_ARITH_SUB_R,
			FupElem_ARITH_MUL_R.OP_SYM_NAME	: FupElem_ARITH_MUL_R,
			FupElem_ARITH_DIV_R.OP_SYM_NAME	: FupElem_ARITH_DIV_R,
		}.get(subType)
		if not elemClass:
			raise self.Error("Arithmetic subtype '%s' is not known "
				"to the element parser." % (
				subType))
		self.elem = elemClass(x=x, y=y, nrInputs=0, uuid=uuid)
		self.elem.grid = self.grid
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		if tag.name == "connections":
			self.parser_switchTo(FupConn.factory(elem=self.elem))
			return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if tag.name == "element":
			# Insert the element into the grid.
			if not self.grid.placeElem(self.elem):
				raise self.Error("<element> caused "
					"a grid collision.")
			self.parser_finish()
			return
		XmlFactory.parser_endTag(self, tag)

	def composer_getTags(self):
		elem = self.elem

		connTags = []
		for inp in elem.inputs:
			connTags.extend(inp.factory(conn=inp).composer_getTags())
		for out in elem.outputs:
			connTags.extend(out.factory(conn=out).composer_getTags())

		return [
			self.Tag(name="element",
				attrs={
					"type" : "arithmetic",
					"subtype" : elem.OP_SYM_NAME,
					"x" : str(elem.x),
					"y" : str(elem.y),
					"uuid" : str(elem.uuid),
				},
				tags=[
					self.Tag(name="connections",
						 tags=connTags),
				])
		]

class FupElem_ARITH(FupElem):
	"""Arithmetic FUP/FBD element base class"""

	factory			= FupElem_ARITH_factory

	FIXED_INPUTS		= [ "EN", ]
	FIXED_OUTPUTS		= [ "ENO", ]
	OPTIONAL_CONNS		= { "EN", "REM", "==0", "<>0", ">0", "<0",
				    ">=0", "<=0", "OV", "UO", "ENO", }
	BLANK_CONNS		= { "IN", "OUT", }
	HAVE_REMAINDER		= False

	# Sequence of special connections.
	__CONN_IN_SEQUENCE	= ( "EN", )
	__CONN_OUT_SEQUENCE	= ( "REM", "==0", "<>0", ">0", "<0",
				    ">=0", "<=0", "OV", "UO", "ENO", )

	def __init__(self, x, y, nrInputs=2, nrOutputs=1, uuid=None):
		FupElem.__init__(self, x, y, uuid=uuid)

		self.inputs = [ FupConnIn(self, text=text)
				for text in self.FIXED_INPUTS ]
		self.inputs.extend( FupConnIn(self, text=("IN%d" % i))
				    for i in range(nrInputs) )

		self.outputs = [ FupConnOut(self, text=("OUT%d" % i))
				 for i in range(nrOutputs) ]
		self.outputs.extend(FupConnOut(self, text=text)
				    for text in self.FIXED_OUTPUTS )

		self.__renumberConns()

	def __renumberConns(self):
		i = 0
		for conn in self.inputs:
			if not conn.text or conn.text.startswith("IN"):
				conn.text = "IN%d" % i
				i += 1
		i = 0
		for conn in self.outputs:
			if not conn.text or conn.text.startswith("OUT"):
				conn.text = "OUT%d" % i
				i += 1

	def __inferInInsertIndex(self, conn):
		beforeIndex = len(self.inputs)
		return beforeIndex

	def __inferOutInsertIndex(self, conn):
		connText = conn.text.upper()
		connOutSeq = self.__CONN_OUT_SEQUENCE
		if connText in connOutSeq:
			# This is one of the special outputs.
			# Add it to its fixed position (see connOutSeq).
			if connText in (c.text.upper() for c in self.outputs):
				return -1 # We already have this one.
			beforeIndex = len(self.outputs)
			for idx, c in enumerate(self.outputs):
				if c.text.upper() not in connOutSeq:
					continue
				if connOutSeq.index(connText) <\
				   connOutSeq.index(c.text.upper()):
					beforeIndex = idx
					break
		else:
			# This is a regular OUTx output.
			# Add it just before the special outputs.
			beforeIndex = len(self.outputs)
			for idx, c in enumerate(self.outputs):
				if c.text.upper() in connOutSeq:
					beforeIndex = idx
					break
		return beforeIndex

	# Overridden method. For documentation see base class.
	def insertConn(self, beforeIndex, conn):
		if not conn:
			return False
		if conn.IN:
			if beforeIndex is None:
				beforeIndex = self.__inferInInsertIndex(conn)
			if beforeIndex <= 0:
				return False
		else:
			if beforeIndex is None:
				beforeIndex = self.__inferOutInsertIndex(conn)
				if beforeIndex < 0:
					return False
		ok = FupElem.insertConn(self, beforeIndex, conn)
		if ok:
			self.__renumberConns()
		return ok

	# Overridden method. For documentation see base class.
	def getAreaViaPixCoord(self, pixelX, pixelY):
		if self.grid:
			cellWidth = self.grid.cellPixWidth
			cellHeight = self.grid.cellPixHeight
			totalWidth = cellWidth
			totalHeight = cellHeight * self.height
			xpad, ypad = self._xpadding, self._ypadding
			if pixelY >= ypad and\
			   pixelY < totalHeight - ypad:
				if pixelX < xpad:
					# inputs
					idx = pixelY // cellHeight
					lastIdx = len(self.inputs) - 1
					if idx <= lastIdx:
						return self.AREA_INPUT, idx
				elif pixelX >= totalWidth - xpad:
					# outputs
					idx = pixelY // cellHeight
					firstIdx = self.height - len(self.outputs)
					if idx >= firstIdx:
						idx -= firstIdx
						return self.AREA_OUTPUT, idx
				else:
					# body
					return self.AREA_BODY, 0
		return self.AREA_NONE, 0

	# Overridden method. For documentation see base class.
	def getConnRelCoords(self, conn):
		x, y = 0, -1
		if conn.IN:
			y = self.inputs.index(conn)
		elif conn.OUT:
			y = self.outputs.index(conn)
			if y >= 0:
				y = self.height - len(self.outputs) + y
		if x >= 0 and y >= 0:
			return x, y
		return FupElem.getConnRelCoords(self, conn)

	# Overridden method. For documentation see base class.
	@property
	def height(self):
		return max(len(self.inputs),
			   len(self.outputs))

	# Overridden method. For documentation see base class.
	def draw(self, painter):
		grid = self.grid
		if not grid:
			return
		cellWidth = grid.cellPixWidth
		cellHeight = grid.cellPixHeight
		xpad, ypad = self._xpadding, self._ypadding
		elemHeight = cellHeight * self.height
		elemWidth = cellWidth
		selected = self.selected

		# Draw body
		painter.setPen(self._outlineSelPen if selected
			       else self._outlinePen)
		painter.setBrush(self._bgSelBrush if selected
				 else self._bgBrush)
		(tlX, tlY), (trX, trY), (blX, blY), (brX, brY) = self._calcBodyBox()
		painter.drawRoundedRect(tlX, tlY,
					trX - tlX, blY - tlY,
					self.BODY_CORNER_RADIUS,
					self.BODY_CORNER_RADIUS)

		# Draw inputs
		painter.setBrush(self._bgSelBrush if selected
				 else self._bgBrush)
		painter.setFont(self.getFont(8))
		for i, conn in enumerate(self.inputs):
			cellIdx = i

			connPen = self._connPen\
				if (conn.isConnected or conn.text in self.OPTIONAL_CONNS)\
				else self._connOpenPen

			x = conn.drawOffset
			y = (cellIdx * cellHeight) + (cellHeight // 2)
			painter.setPen(connPen)
			painter.drawLine(x, y, xpad, y)

			if conn.text and\
			   not any(conn.text.startswith(b) for b in self.BLANK_CONNS):
				painter.setPen(connPen)
				x = xpad + 2
				y = (cellIdx * cellHeight)
				painter.drawText(x, y,
						 elemWidth - xpad - 2, cellHeight,
						 Qt.AlignLeft | Qt.AlignVCenter,
						 conn.text)

		# Draw outputs
		painter.setFont(self.getFont(8))
		for i, conn in enumerate(self.outputs):
			cellIdx = self.height - len(self.outputs) + i

			connPen = self._connPen\
				if (conn.isConnected or conn.text in self.OPTIONAL_CONNS)\
				else self._connOpenPen

			x = cellWidth - conn.drawOffset
			y = (cellIdx * cellHeight) + (cellHeight // 2)
			painter.setPen(connPen)
			painter.setBrush(self._bgSelBrush if selected
					 else self._bgBrush)
			painter.drawLine(cellWidth - xpad, y,
					 x, y)

			if conn.text and\
			   not any(conn.text.startswith(b) for b in self.BLANK_CONNS):
				x = 0
				y = (cellIdx * cellHeight)
				painter.drawText(x, y,
						 elemWidth - xpad - 2, cellHeight,
						 Qt.AlignRight | Qt.AlignVCenter,
						 conn.text)

		# Draw symbol text
		painter.setPen(self._outlineSelPen if selected
			       else self._outlinePen)
		painter.setBrush(self._bgSelBrush if selected
				 else self._bgBrush)
		painter.setFont(self.getFont(12, bold=True))
		painter.drawText(0, 0,
				 int(round(elemWidth * 0.75)), elemHeight,
				 Qt.AlignVCenter | Qt.AlignHCenter,
				 self.OP_SYM)

	# Overridden method. For documentation see base class.
	def prepareContextMenu(self, menu, area=None, conn=None):
		menu.enableAddInput(True)
		menu.enableAddOutput(True)
		if conn:
			normalInputs = [ c for c in self.inputs
					 if c.text.upper() not in self.__CONN_IN_SEQUENCE ]
			normalOutputs = [ c for c in self.outputs
					  if c.text.upper() not in self.__CONN_OUT_SEQUENCE ]
			if conn.IN:
				if conn.text.upper() != "EN":
					menu.enableRemoveConn(len(normalInputs) > 2)
			else:
				if conn.text.upper() != "ENO":
					if conn.text.upper() in self.__CONN_OUT_SEQUENCE:
						menu.enableRemoveConn(True)
					else:
						menu.enableRemoveConn(len(normalOutputs) > 1)
			menu.enableDisconnWire(conn.isConnected)
		if not conn or conn.OUT:
			existing = set(c.text.upper() for c in self.outputs)
			if "REM" not in existing and self.HAVE_REMAINDER:
				menu.enableCustomAction(0, True, text="Add REMainder output")
			if "==0" not in existing:
				menu.enableCustomAction(1, True, text="Add ==0 output")
			if "<>0" not in existing:
				menu.enableCustomAction(2, True, text="Add <>0 output")
			if ">0" not in existing:
				menu.enableCustomAction(3, True, text="Add >0 output")
			if "<0" not in existing:
				menu.enableCustomAction(4, True, text="Add <0 output")
			if ">=0" not in existing:
				menu.enableCustomAction(5, True, text="Add >=0 output")
			if "<=0" not in existing:
				menu.enableCustomAction(6, True, text="Add <=0 output")
			if "OV" not in existing:
				menu.enableCustomAction(7, True, text="Add OV output")
			if "UO" not in existing:
				menu.enableCustomAction(8, True, text="Add UO output")

	def __addStateOutput(self, name):
		return self.addConn(FupConnOut(text=name))

	def __handleAddREM(self, index):
		return self.__addStateOutput("REM")

	def __handleAddEQ0(self, index):
		return self.__addStateOutput("==0")

	def __handleAddNE0(self, index):
		return self.__addStateOutput("<>0")

	def __handleAddGT0(self, index):
		return self.__addStateOutput(">0")

	def __handleAddLT0(self, index):
		return self.__addStateOutput("<0")

	def __handleAddGE0(self, index):
		return self.__addStateOutput(">=0")

	def __handleAddLE0(self, index):
		return self.__addStateOutput("<=0")

	def __handleAddOV(self, index):
		return self.__addStateOutput("OV")

	def __handleAddUO(self, index):
		return self.__addStateOutput("UO")

	CUSTOM_ACTIONS = (
		__handleAddREM,		# index 0
		__handleAddEQ0,		# index 1
		__handleAddNE0,		# index 2
		__handleAddGT0,		# index 3
		__handleAddLT0,		# index 4
		__handleAddGE0,		# index 5
		__handleAddLE0,		# index 6
		__handleAddOV,		# index 7
		__handleAddUO,		# index 8
	)

class FupElem_ARITH_ADD_I(FupElem_ARITH):
	"""+I FUP/FBD element"""

	OP_SYM			= "+I"
	OP_SYM_NAME		= "add-int"	# XML ABI name

class FupElem_ARITH_SUB_I(FupElem_ARITH):
	"""-I FUP/FBD element"""

	OP_SYM			= "-I"
	OP_SYM_NAME		= "sub-int"	# XML ABI name

class FupElem_ARITH_MUL_I(FupElem_ARITH):
	"""*I FUP/FBD element"""

	OP_SYM			= "*I"
	OP_SYM_NAME		= "mul-int"	# XML ABI name

class FupElem_ARITH_DIV_I(FupElem_ARITH):
	"""/I FUP/FBD element"""

	OP_SYM			= "/I"
	OP_SYM_NAME		= "div-int"	# XML ABI name
	HAVE_REMAINDER		= True

class FupElem_ARITH_ADD_D(FupElem_ARITH):
	"""+D FUP/FBD element"""

	OP_SYM			= "+D"
	OP_SYM_NAME		= "add-dint"	# XML ABI name

class FupElem_ARITH_SUB_D(FupElem_ARITH):
	"""-D FUP/FBD element"""

	OP_SYM			= "-D"
	OP_SYM_NAME		= "sub-dint"	# XML ABI name

class FupElem_ARITH_MUL_D(FupElem_ARITH):
	"""*D FUP/FBD element"""

	OP_SYM			= "*D"
	OP_SYM_NAME		= "mul-dint"	# XML ABI name

class FupElem_ARITH_DIV_D(FupElem_ARITH):
	"""/D FUP/FBD element"""

	OP_SYM			= "/D"
	OP_SYM_NAME		= "div-dint"	# XML ABI name

class FupElem_ARITH_MOD_D(FupElem_ARITH):
	"""MOD FUP/FBD element"""

	OP_SYM			= "MOD"
	OP_SYM_NAME		= "mod-dint"	# XML ABI name

class FupElem_ARITH_ADD_R(FupElem_ARITH):
	"""+R FUP/FBD element"""

	OP_SYM			= "+R"
	OP_SYM_NAME		= "add-real"	# XML ABI name

class FupElem_ARITH_SUB_R(FupElem_ARITH):
	"""-R FUP/FBD element"""

	OP_SYM			= "-R"
	OP_SYM_NAME		= "sub-real"	# XML ABI name

class FupElem_ARITH_MUL_R(FupElem_ARITH):
	"""*R FUP/FBD element"""

	OP_SYM			= "*R"
	OP_SYM_NAME		= "mul-real"	# XML ABI name

class FupElem_ARITH_DIV_R(FupElem_ARITH):
	"""/R FUP/FBD element"""

	OP_SYM			= "/R"
	OP_SYM_NAME		= "div-real"	# XML ABI name

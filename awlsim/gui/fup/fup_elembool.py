# -*- coding: utf-8 -*-
#
# AWL simulator - FUP - Boolean element classes
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

from awlsim.gui.fup.fup_base import *
from awlsim.gui.fup.fup_elem import *
from awlsim.gui.fup.fup_elemoperand import *


class FupElem_BOOLEAN_factory(FupElem_factory):
	def parser_open(self, tag):
		assert(tag)
		x = tag.getAttrInt("x")
		y = tag.getAttrInt("y")
		subType = tag.getAttr("subtype")
		uuid = tag.getAttr("uuid", None)
		elemClass = {
			FupElem_AND.OP_SYM_NAME	: FupElem_AND,
			FupElem_OR.OP_SYM_NAME	: FupElem_OR,
			FupElem_XOR.OP_SYM_NAME	: FupElem_XOR,
			FupElem_S.OP_SYM_NAME	: FupElem_S,
			FupElem_R.OP_SYM_NAME	: FupElem_R,
			FupElem_SR.OP_SYM_NAME	: FupElem_SR,
			FupElem_RS.OP_SYM_NAME	: FupElem_RS,
			FupElem_FP.OP_SYM_NAME	: FupElem_FP,
			FupElem_FN.OP_SYM_NAME	: FupElem_FN,
		}.get(subType)
		if not elemClass:
			raise self.Error("Boolean subtype '%s' is not known "
				"to the element parser." % (
				subType))
		self.elem = elemClass(
			x=x, y=y, nrInputs=0, uuid=uuid)
		self.elem.grid = self.grid
		self.subelemsFakeGrid = None
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		if tag.name == "connections":
			self.parser_switchTo(FupConn.factory(elem=self.elem))
			return
		if tag.name == "subelements":
			from awlsim.gui.fup.fup_grid import FupGridStub
			if self.subelemsFakeGrid:
				raise self.Error("Found multiple <subelements> tags "
					"inside of boolean <element>.")
			self.subelemsFakeGrid = FupGridStub()
			self.parser_switchTo(FupElem.factory(grid=self.subelemsFakeGrid,
							     CONTAINER_TAG="subelements"))
			return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if tag.name == "element":
			# Add body element
			if self.elem.WITH_BODY_OPERATOR:
				subelements = self.subelemsFakeGrid.elements
				if subelements:
					if len(subelements) != 1 or\
					   not isinstance(subelements[0], FupElem_EmbeddedOper):
						raise self.Error("Only one subelement of type "
							"'embedded operand' supported in "
							"boolean <element>.")
					del self.elem.bodyOper
					self.elem.bodyOper = subelements[0]
					self.elem.bodyOper.parentElem = self.elem
					del self.elem.bodyOper.grid
			else:
				if self.subelemsFakeGrid:
					raise self.Error("<subelements> is not "
						"supported for %s." % (
						str(self.elem)))
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

		subElemTags = []
		if elem.WITH_BODY_OPERATOR:
			bodyOper = elem.bodyOper
			subElemTags.extend(bodyOper.factory(elem=bodyOper).composer_getTags())

		return [
			self.Tag(name="element",
				attrs={
					"type" : "boolean",
					"subtype" : elem.OP_SYM_NAME,
					"x" : str(elem.x),
					"y" : str(elem.y),
					"uuid" : str(elem.uuid),
				},
				tags=[
					self.Tag(name="connections",
						 tags=connTags),
					self.Tag(name="subelements",
						 tags=subElemTags),
				])
		]

class FupElem_BOOLEAN(FupElem):
	"""Boolean FUP/FBD element base class"""

	factory			= FupElem_BOOLEAN_factory

	FIXED_INPUTS		= None
	FIXED_OUTPUTS		= [ "Q", ]
	WITH_BODY_OPERATOR	= False
	OPTIONAL_CONNS		= set()
	BLANK_CONNS		= { "Q", }

	def __init__(self, x, y, nrInputs=2, uuid=None):
		FupElem.__init__(self, x, y, uuid=uuid)

		if self.FIXED_INPUTS is None:
			self.inputs = [ FupConnIn(self)
					for i in range(nrInputs) ]
		else:
			self.inputs = [ FupConnIn(self, text=text)
					for text in self.FIXED_INPUTS ]

		if self.FIXED_OUTPUTS is None:
			self.outputs = []
		else:
			self.outputs = [ FupConnOut(self, text=text)
					 for text in self.FIXED_OUTPUTS ]

		if self.WITH_BODY_OPERATOR:
			self.bodyOper = FupElem_EmbeddedOper(parentElem=self)

	# Overridden method. For documentation see base class.
	def insertConn(self, beforeIndex, conn):
		if conn and conn.OUT:
			return False
		return FupElem.insertConn(self, beforeIndex, conn)

	# Overridden method. For documentation see base class.
	def addConn(self, conn):
		if conn and conn.OUT:
			return False
		return FupElem.addConn(self, conn)

	# Overridden method. For documentation see base class.
	def getAreaViaPixCoord(self, pixelX, pixelY):
		if self.grid:
			cellWidth = self.grid.cellPixWidth
			cellHeight = self.grid.cellPixHeight
			totalWidth = cellWidth
			totalHeight = cellHeight * self.height
			xpad, ypad = self._xpadding, self._ypadding
			if self.WITH_BODY_OPERATOR:
				if pixelY >= ypad and pixelY < cellHeight and\
				   pixelX >= xpad and pixelX < cellWidth - xpad:
					return self.AREA_BODYOPER, 0
				yInBodyRange = pixelY >= cellHeight + ypad and\
					       pixelY < totalHeight - ypad
			else:
				yInBodyRange = pixelY >= ypad and\
					       pixelY < totalHeight - ypad
			if yInBodyRange:
				if pixelX < xpad:
					# inputs
					idx = pixelY // cellHeight
					if self.WITH_BODY_OPERATOR:
						idx -= 1
					return self.AREA_INPUT, idx
				elif pixelX >= totalWidth - xpad:
					# outputs
					if pixelY >= totalHeight - cellHeight:
						return self.AREA_OUTPUT, 0
				else:
					# body
					return self.AREA_BODY, 0
		return self.AREA_NONE, 0

	# Overridden method. For documentation see base class.
	def getConnRelCoords(self, conn):
		x, y = 0, -1
		if conn.IN:
			y = self.inputs.index(conn)
			if self.WITH_BODY_OPERATOR and y >= 0:
				y += 1
		elif conn.OUT:
			y = self.outputs.index(conn)
			if y >= 0:
				y = self.height - 1
		if x >= 0 and y >= 0:
			return x, y
		return FupElem.getConnRelCoords(self, conn)

	# Overridden method. For documentation see base class.
	@property
	def height(self):
		return len(self.inputs) +\
			(1 if self.WITH_BODY_OPERATOR else 0)

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
		notR = int(round(3 * grid.zoom))
		notD = notR * 2

		# Draw body
		painter.setPen(self._outlineSelPen if selected
			       else self._outlinePen)
		painter.setBrush(self._bgSelBrush if selected
				 else self._bgBrush)
		(tlX, tlY), (trX, trY), (blX, blY), (brX, brY) = self._calcBodyBox()
		if self.WITH_BODY_OPERATOR:
			offset = cellHeight
		else:
			offset = 0
		painter.drawRoundedRect(tlX, tlY + offset,
					trX - tlX, blY - (tlY + offset),
					self.BODY_CORNER_RADIUS,
					self.BODY_CORNER_RADIUS)

		# Draw inputs
		painter.setBrush(self._bgSelBrush if selected
				 else self._bgBrush)
		painter.setFont(self.getFont(8))
		for i, conn in enumerate(self.inputs):
			cellIdx = i
			if self.WITH_BODY_OPERATOR:
				cellIdx += 1

			connPen = self._connPen\
				if (conn.isConnected or conn.text in self.OPTIONAL_CONNS)\
				else self._connOpenPen

			x = conn.drawOffset
			y = (cellIdx * cellHeight) + (cellHeight // 2)
			painter.setPen(connPen)
			painter.drawLine(x, y, xpad, y)
			if conn.inverted:
				painter.setPen(self._connInvSelPen
					       if selected else
					       self._connInvPen)
				painter.drawEllipse(xpad - notD, y - notR,
						    notD, notD)
			if conn.text and conn.text not in self.BLANK_CONNS:
				painter.setPen(connPen)
				x = xpad + 2
				y = (cellIdx * cellHeight)
				painter.drawText(x, y,
						 elemWidth - xpad - 2, cellHeight,
						 Qt.AlignLeft | Qt.AlignVCenter,
						 conn.text)

		# Draw output
		if self.outputs:
			assert(len(self.outputs) == 1)
			conn = self.outputs[0]

			connPen = self._connPen\
				if (conn.isConnected or conn.text in self.OPTIONAL_CONNS)\
				else self._connOpenPen

			x = cellWidth - conn.drawOffset
			y = elemHeight - (cellHeight // 2)
			painter.setPen(connPen)
			painter.setBrush(self._bgSelBrush if selected
					 else self._bgBrush)
			painter.drawLine(cellWidth - xpad, y,
					 x, y)
			if conn.inverted:
				painter.setPen(self._connInvSelPen
					       if selected else
					       self._connInvPen)
				painter.drawEllipse(cellWidth - xpad, y - notR,
						    notD, notD)
			if conn.text and conn.text not in self.BLANK_CONNS:
				painter.setPen(connPen)
				painter.setFont(self.getFont(8))
				x = 0
				y = elemHeight - cellHeight
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
		if self.WITH_BODY_OPERATOR:
			y, h = cellHeight, elemHeight - cellHeight
		else:
			y, h = 0, elemHeight
		painter.drawText(0, y,
				 elemWidth, h,
				 Qt.AlignVCenter | Qt.AlignHCenter,
				 self.OP_SYM)

		# Draw body operator
		if self.WITH_BODY_OPERATOR:
			self.bodyOper.draw(painter)

	# Overridden method. For documentation see base class.
	def edit(self, parentWidget):
		if self.WITH_BODY_OPERATOR:
			return self.bodyOper.edit(parentWidget)
		return False

	# Overridden method. For documentation see base class.
	def expand(self, expand=True, area=None):
		if self.WITH_BODY_OPERATOR and\
		   (not expand or area == self.AREA_BODYOPER):
			changed = self.bodyOper.expand(expand)
			self.expanded = self.bodyOper.expanded
			return changed
		return False

	# Overridden method. For documentation see base class.
	def prepareContextMenu(self, menu, area=None, conn=None):
		if self.WITH_BODY_OPERATOR:
			menu.enableEdit(True)
		menu.enableInvertConn(True)
		menu.enableAddInput(self.FIXED_INPUTS is None)
		menu.enableRemoveConn(conn is not None and conn.IN and len(self.inputs) > 1)
		menu.enableDisconnWire(conn is not None and conn.isConnected)

	# Overridden method. For documentation see base class.
	def setConnInverted(self, conn, inverted=True):
		if conn in self.inputs or conn in self.outputs:
			conn.inverted = inverted
			return True
		return False

class FupElem_AND(FupElem_BOOLEAN):
	"""AND FUP/FBD element"""

	OP_SYM			= "&"
	OP_SYM_NAME		= "and"	# XML ABI name

class FupElem_OR(FupElem_BOOLEAN):
	"""OR FUP/FBD element"""

	OP_SYM			= ">=1"
	OP_SYM_NAME		= "or"	# XML ABI name

class FupElem_XOR(FupElem_BOOLEAN):
	"""XOR FUP/FBD element"""

	OP_SYM			= "X"
	OP_SYM_NAME		= "xor"	# XML ABI name

class FupElem_S(FupElem_BOOLEAN):
	"""SET FUP/FBD element"""

	OP_SYM			= "S"
	OP_SYM_NAME		= "s" # XML ABI name

	FIXED_INPUTS		= [ "S", ]
	FIXED_OUTPUTS		= [ "Q", ]
	WITH_BODY_OPERATOR	= True
	OPTIONAL_CONNS		= { "Q", }
	BLANK_CONNS		= { "S", "Q", }

class FupElem_R(FupElem_BOOLEAN):
	"""RESET FUP/FBD element"""

	OP_SYM			= "R"
	OP_SYM_NAME		= "r" # XML ABI name

	FIXED_INPUTS		= [ "R", ]
	FIXED_OUTPUTS		= [ "Q", ]
	WITH_BODY_OPERATOR	= True
	OPTIONAL_CONNS		= { "Q", }
	BLANK_CONNS		= { "R", "Q", }

class FupElem_SR(FupElem_BOOLEAN):
	"""SR flip-flop FUP/FBD element"""

	OP_SYM			= "SR"
	OP_SYM_NAME		= "sr" # XML ABI name

	FIXED_INPUTS		= [ "S", "R", ]
	FIXED_OUTPUTS		= [ "Q", ]
	WITH_BODY_OPERATOR	= True
	OPTIONAL_CONNS		= { "R", "Q", }
	BLANK_CONNS		= set()

class FupElem_RS(FupElem_BOOLEAN):
	"""RS flip-flop FUP/FBD element"""

	OP_SYM			= "RS"
	OP_SYM_NAME		= "rs" # XML ABI name

	FIXED_INPUTS		= [ "R", "S", ]
	FIXED_OUTPUTS		= [ "Q", ]
	WITH_BODY_OPERATOR	= True
	OPTIONAL_CONNS		= { "S", "Q", }
	BLANK_CONNS		= set()

class FupElem_FP(FupElem_BOOLEAN):
	"""Positive edge FUP/FBD element"""

	OP_SYM			= "FP"
	OP_SYM_NAME		= "fp" # XML ABI name

	FIXED_INPUTS		= [ "IN", ]
	FIXED_OUTPUTS		= [ "Q", ]
	WITH_BODY_OPERATOR	= True
	OPTIONAL_CONNS		= set()
	BLANK_CONNS		= { "IN", "Q", }

class FupElem_FN(FupElem_FP):
	"""Negative edge FUP/FBD element"""

	OP_SYM			= "FN"
	OP_SYM_NAME		= "fn" # XML ABI name

# -*- coding: utf-8 -*-
#
# AWL simulator - FUP - Operand element classes
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


class FupElem_OPERAND_factory(FupElem_factory):
	def parser_open(self, tag):
		assert(tag)
		x = tag.getAttrInt("x")
		y = tag.getAttrInt("y")
		subType = tag.getAttr("subtype")
		content = tag.getAttr("content", "")
		uuid = tag.getAttr("uuid", None)
		elemClass = {
			FupElem_LOAD.OP_SYM_NAME : FupElem_LOAD,
			FupElem_ASSIGN.OP_SYM_NAME : FupElem_ASSIGN,
			FupElem_EmbeddedOper.OP_SYM_NAME : FupElem_EmbeddedOper,
		}.get(subType)
		if not elemClass:
			raise self.Error("Operand subtype '%s' is not known "
				"to the element parser." % (
				subType))
		self.elem = elemClass(x=x, y=y,
			contentText=content,
			uuid=uuid)
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
		connTags = []
		for inp in self.elem.inputs:
			connTags.extend(inp.factory(conn=inp).composer_getTags())
		for out in self.elem.outputs:
			connTags.extend(out.factory(conn=out).composer_getTags())
		return [
			self.Tag(name="element",
				attrs={
					"type" : "operand",
					"subtype" : self.elem.OP_SYM_NAME,
					"x" : str(self.elem.x),
					"y" : str(self.elem.y),
					"content" : self.elem.contentText,
					"uuid" : str(self.elem.uuid),
				},
				tags=[
					self.Tag(name="connections",
						 tags=connTags),
				])
		]

class FupElem_OPERAND(FupElem):
	"""Generic operand element"""

	factory = FupElem_OPERAND_factory

	BODY_CORNER_RADIUS	= 2
	EXPAND_WHEN_SELECTED	= True

	def __init__(self, x, y, contentText="", uuid=None):
		FupElem.__init__(self, x, y, uuid=uuid)

		self._continuePen = QPen(QBrush(), 1, Qt.DotLine)
		self._continuePen.setColor(QColor("#000000"))

		self.contentText = contentText
		self.partialContent = False

	@property
	def _xpadding(self):
		if self.grid:
			return self.grid.cellPixWidth // 12
		return 0

	# Overridden method. For documentation see base class.
	def getAreaViaPixCoord(self, pixelX, pixelY):
		if self.grid:
			cellWidth = self.grid.cellPixWidth
			cellHeight = self.grid.cellPixHeight
			totalWidth = cellWidth
			totalHeight = cellHeight * self.height
			xpad, ypad = self._xpadding, self._ypadding
			if pixelY >= ypad and pixelY < totalHeight - ypad:
				if pixelX < xpad:
					# inputs
					if self.inputs and\
					   pixelY >= totalHeight - cellHeight:
						return self.AREA_INPUT, 0
				elif pixelX >= totalWidth - xpad:
					# outputs
					if self.outputs and\
					   pixelY >= totalHeight - cellHeight:
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
		elif conn.OUT:
			y = self.outputs.index(conn)
		if y >= 0:
			y = self.height - 1
		if x >= 0 and y >= 0:
			return x, y
		return FupElem.getConnRelCoords(self, conn)

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

		selected, expanded = self.selected, self.expanded

		# Draw body
		painter.setPen(self._noPen)
		painter.setBrush(self._bgSelBrush if selected
				 else self._bgBrush)
		(tlX, tlY), (trX, trY), (blX, blY), (brX, brY) = self._calcBodyBox()
		w, h = trX - tlX, blY - tlY	# width / height
		bodyRect = QRect(tlX, tlY, w, h)
		painter.drawRoundedRect(bodyRect,
					self.BODY_CORNER_RADIUS,
					self.BODY_CORNER_RADIUS)

		# Draw the text
		text = self.contentText
		if text:
			if self.EXPAND_WHEN_SELECTED:
				drawExpanded = selected or expanded
			else:
				drawExpanded = expanded
			painter.setFont(self.getFont(8))
			painter.setPen(self._textPen)
			if drawExpanded:
				textFlags = Qt.TextWrapAnywhere | Qt.AlignLeft | Qt.AlignTop
				textMaxRect = bodyRect.translated(0, 0)
				textMaxRect.setHeight(grid.height * cellHeight)
				textRect = painter.boundingRect(textMaxRect, textFlags, text)
				actTextRect = textRect
			else:
				textFlags = Qt.TextWrapAnywhere | Qt.AlignHCenter | Qt.AlignTop
				textRect = bodyRect
				actTextRect = painter.boundingRect(bodyRect, textFlags, text)
			if drawExpanded:
				painter.setBrush(self._bgSelBrush if selected
						 else self._bgBrush)
				painter.setPen(self._noPen)
				painter.drawRect(actTextRect)
			painter.setPen(self._textPen)
			painter.drawText(textRect, textFlags, text)
			if not bodyRect.contains(actTextRect):
				if not drawExpanded:
					# Draw continuation
					painter.setPen(self._continuePen)
					painter.drawLine(xpad, cellHeight - 1,
							 cellWidth - xpad - 1, cellHeight - 1)
					painter.drawLine(cellWidth - xpad - 1, ypad,
							 cellWidth - xpad - 1, cellHeight - 1 - ypad)
				self.partialContent = True
			else:
				self.partialContent = False

	# Overridden method. For documentation see base class.
	def edit(self, parentWidget):
		text, ok = QInputDialog.getText(parentWidget,
			"Change operand",
			"Change operand",
			QLineEdit.Normal,
			self.contentText)
		if ok:
			# Try to find the field in the interface and use the
			# actual interface field name. But only do this, if
			# the name does not start with a space. This way the user
			# can disable this automatic matching.
			if not text.startswith(" "):
				field = self.grid.interfDef.findByName(text)
				if field:
					# Found it. Use the actual name.
					text = "#" + field.name
			self.contentText = text
			return True
		return False

	# Overridden method. For documentation see base class.
	def expand(self, expand=True, area=None):
		if not self.partialContent and expand:
			return False
		if expand != self.expanded:
			self.expanded = expand
			return True
		return False

	# Overridden method. For documentation see base class.
	def prepareContextMenu(self, menu, area=None, conn=None):
		menu.enableEdit(True)

class FupElem_ASSIGN(FupElem_OPERAND):
	"""Assignment operand element"""

	OP_SYM		= "assign"
	OP_SYM_NAME	= "assign"	# XML ABI name

	def __init__(self, x, y, contentText="", uuid=None):
		FupElem_OPERAND.__init__(self, x, y, contentText, uuid=uuid)

		self.inputs = [ FupConnIn(self) ]

	# Overridden method. For documentation see base class.
	def draw(self, painter):
		if not self.grid:
			return
		cellWidth = self.grid.cellPixWidth
		cellHeight = self.grid.cellPixHeight
		xpad, ypad = self._xpadding, self._ypadding
		elemHeight = cellHeight * self.height
		elemWidth = cellWidth

		# Draw body
		FupElem_OPERAND.draw(self, painter)

		# Draw input connection
		y = elemHeight - (cellHeight // 2)
		painter.setPen(self._connPen
			       if len(self.inputs) and self.inputs[0].wire
			       else self._connOpenPen)
		painter.drawLine(0, y, xpad, y)

class FupElem_LOAD(FupElem_OPERAND):
	"""Load/read operand element"""

	OP_SYM		= "load"
	OP_SYM_NAME	= "load"	# XML ABI name

	def __init__(self, x, y, contentText="", uuid=None):
		FupElem_OPERAND.__init__(self, x, y, contentText, uuid=uuid)

		self.outputs = [ FupConnOut(self) ]

	# Overridden method. For documentation see base class.
	def draw(self, painter):
		if not self.grid:
			return
		cellWidth = self.grid.cellPixWidth
		cellHeight = self.grid.cellPixHeight
		xpad = self._xpadding
		ypad = self._ypadding
		elemHeight = cellHeight * self.height
		elemWidth = cellWidth

		# Draw body
		FupElem_OPERAND.draw(self, painter)

		# Draw output connection
		y = elemHeight - (cellHeight // 2)
		painter.setPen(self._connPen
			       if len(self.outputs) and self.outputs[0].wire
			       else self._connOpenPen)
		painter.drawLine(cellWidth - xpad, y,
				 cellWidth, y)

class FupElem_EmbeddedOper(FupElem_OPERAND):
	"""Embedded operand element.
	This is NOT an actual element.
	It is used embedded in other elements only.
	"""

	OP_SYM			= "embedded"
	OP_SYM_NAME		= "embedded"	# XML ABI name
	EXPAND_WHEN_SELECTED	= False

	def __init__(self, x=0, y=0, contentText="", parentElem=None, uuid=None):
		FupElem_OPERAND.__init__(self, x, y, contentText, uuid=uuid)
		self.parentElem = parentElem
		self.__grid = None

	@property
	def grid(self):
		if self.__grid:
			return self.__grid
		if self.parentElem:
			return self.parentElem.grid
		return None

	@grid.setter
	def grid(self, grid):
		self.__grid = grid

	@grid.deleter
	def grid(self):
		self.__grid = None

	@property
	def selected(self):
		if self.parentElem:
			return self.parentElem.selected
		return False

# -*- coding: utf-8 -*-
#
# AWL simulator - FUP - Operand element classes
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

from awlsim.gui.fup.fup_base import *
from awlsim.gui.fup.fup_elem import *


class FupElem_OPERAND_factory(FupElem_factory):
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
				},
				tags=[
					self.Tag(name="connections",
						 tags=connTags),
				])
		]

class FupElem_OPERAND(FupElem):
	"""Generic operand element"""

	factory = FupElem_OPERAND_factory

	def __init__(self, x, y, contentText=""):
		FupElem.__init__(self, x, y)

		self._continuePen = QPen(QBrush(), 1, Qt.DotLine)
		self._continuePen.setColor(QColor("#000000"))

		self.contentText = contentText
		self.partialContent = False

	@property
	def _xpadding(self):
		if self.grid:
			return self.grid.cellPixWidth // 12
		return 0

	def getAreaViaPixCoord(self, pixelX, pixelY):
		if self.grid:
			cellWidth = self.grid.cellPixWidth
			cellHeight = self.grid.cellPixHeight
			totalWidth = cellWidth
			totalHeight = cellHeight * self.height
			xpad, ypad = self._xpadding, self._ypadding
			if pixelY > ypad and pixelY < totalHeight - ypad:
				if pixelX < xpad:
					# inputs
					if self.inputs and\
					   pixelY >= totalHeight - cellHeight:
						return self.AREA_INPUT, 0
				elif pixelX > totalWidth - xpad:
					# outputs
					if self.outputs and\
					   pixelY >= totalHeight - cellHeight:
						return self.AREA_OUTPUT, 0
				else:
					# body
					return self.AREA_BODY, 0
		return self.AREA_NONE, 0

	def getConnRelPixCoords(self, conn):
		if self.grid:
			cellHeight = self.grid.cellPixHeight
			cellWidth = self.grid.cellPixWidth
			if isinstance(conn, FupConnIn):
				idx = self.inputs.index(conn)
				if idx >= 0:
					idx = self.height - 1
					x = FupConn.CONN_OFFS
			elif isinstance(conn, FupConnOut):
				idx = self.outputs.index(conn)
				if idx >= 0:
					idx = self.height - 1
					x = cellWidth - FupConn.CONN_OFFS
			if idx >= 0:
				y = (idx * cellHeight) + (cellHeight // 2)
				return x, y
		return FupElem.getConnRelPixCoords(self, conn)

	def draw(self, painter):
		if not self.grid:
			return
		cellWidth = self.grid.cellPixWidth
		cellHeight = self.grid.cellPixHeight
		xpad, ypad = self._xpadding, self._ypadding
		elemHeight = cellHeight * self.height
		elemWidth = cellWidth

		selected, expanded = self.selected, self.expanded

		# Draw body
		painter.setPen(self._noPen)
		painter.setBrush(self._bgSelBrush if selected\
				 else self._bgBrush)
		bodyRect = QRect(xpad, ypad,
				 elemWidth - 2 * xpad,
				 elemHeight - 2 * ypad)
		painter.drawRect(bodyRect)

		# Draw the text
		text = self.contentText
		if text:
			font = getDefaultFixedFont()
			font.setPointSize(8)
			painter.setFont(font)
			painter.setPen(self._textPen)
			if selected or expanded:
				textFlags = Qt.TextWrapAnywhere | Qt.AlignLeft | Qt.AlignTop
				textMaxRect = bodyRect.translated(0, 0)
				textMaxRect.setHeight(self.grid.height * cellHeight)
				textRect = painter.boundingRect(textMaxRect, textFlags, text)
				actTextRect = textRect
			else:
				textFlags = Qt.TextWrapAnywhere | Qt.AlignHCenter | Qt.AlignTop
				textRect = bodyRect
				actTextRect = painter.boundingRect(bodyRect, textFlags, text)
			if selected or expanded:
				painter.setBrush(self._bgSelBrush if selected\
						 else self._bgBrush)
				painter.setPen(self._noPen)
				painter.drawRect(actTextRect)
			painter.setPen(self._textPen)
			painter.drawText(textRect, textFlags, text)
			if not bodyRect.contains(actTextRect):
				if not selected and not expanded:
					# Draw continuation
					painter.setPen(self._continuePen)
					painter.drawLine(xpad, cellHeight - 1,
							 cellWidth - xpad - 1, cellHeight - 1)
					painter.drawLine(cellWidth - xpad - 1, ypad,
							 cellWidth - xpad - 1, cellHeight - 1 - ypad)
				self.partialContent = True
			else:
				self.partialContent = False

	def edit(self, parentWidget):
		text, ok = QInputDialog.getText(parentWidget,
			"Change operand",
			"Change operand",
			QLineEdit.Normal,
			self.contentText)
		if ok:
			self.contentText = text
			return True
		return False

	def expand(self, expand=True):
		if not self.partialContent and expand:
			return False
		if expand != self.expanded:
			self.expanded = expand
			return True
		return False

	def prepareContextMenu(self, menu):
		menu.enableEdit(True)

class FupElem_ASSIGN(FupElem_OPERAND):
	"""Assignment operand element"""

	OP_SYM		= "assign"
	OP_SYM_NAME	= "assign"	# XML ABI name

	def __init__(self, x, y, contentText=""):
		FupElem_OPERAND.__init__(self, x, y, contentText)

		self.inputs = [ FupConnIn(self) ]

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

	def __init__(self, x, y, contentText=""):
		FupElem_OPERAND.__init__(self, x, y, contentText)

		self.outputs = [ FupConnOut(self) ]

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

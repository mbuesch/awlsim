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
				},
				tags=[
					self.Tag(name="connections",
						 tags=connTags),
				])
		]

class FupElem_OPERAND(FupElem):
	"""Generic operand element"""

	factory = FupElem_OPERAND_factory

	def __init__(self, x, y):
		FupElem.__init__(self, x, y)

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

		# Draw body
		painter.setPen(self._outlineSelPen if self.selected
			       else self._outlinePen)
		painter.setBrush(self._bgBrush)
		polygon = QPolygon((QPoint(xpad, ypad),
				    QPoint(elemWidth - xpad, ypad),
				    QPoint(elemWidth - xpad, elemHeight - ypad),
				    QPoint(xpad, elemHeight - ypad)))
		painter.drawPolygon(polygon, Qt.OddEvenFill)

class FupElem_ASSIGN(FupElem_OPERAND):
	"""Assignment operand element"""

	OP_SYM		= "assign"
	OP_SYM_NAME	= "assign"	# XML ABI name

	def __init__(self, x, y):
		FupElem_OPERAND.__init__(self, x, y)

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

	def __init__(self, x, y):
		FupElem_OPERAND.__init__(self, x, y)

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

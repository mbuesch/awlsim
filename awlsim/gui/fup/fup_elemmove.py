# -*- coding: utf-8 -*-
#
# AWL simulator - FUP - Move box
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


class FupElem_MOVE_factory(FupElem_factory):
	def parser_open(self, tag):
		assert(tag)
		x = tag.getAttrInt("x")
		y = tag.getAttrInt("y")
		uuid = tag.getAttr("uuid", None)
		self.elem = FupElem_MOVE(x=x, y=y,
					 nrOutputs=0,
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
					"type" : "move",
					"x" : str(self.elem.x),
					"y" : str(self.elem.y),
					"uuid" : str(self.elem.uuid),
				},
				tags=[
					self.Tag(name="connections",
						 tags=connTags),
				])
		]

class FupElem_MOVE(FupElem):
	"""FUP/FBD move box.
	"""

	factory = FupElem_MOVE_factory

	def __init__(self, x, y, nrOutputs=1, uuid=None):
		FupElem.__init__(self, x, y, uuid=uuid)

		self.inputs = [ FupConnIn(self), # EN
				FupConnIn(self), # IN
		]

		nrOutputs += 1 # Add ENO
		self.outputs = [ FupConnOut(self)
				 for i in range(nrOutputs) ]

		self.__genConnText()

	def __genConnText(self):
		assert(len(self.inputs) == 2)
		self.inputs[0].text = "EN"
		self.inputs[1].text = "IN"

		for i, conn in enumerate(self.outputs):
			if i >= len(self.outputs) - 1:
				conn.text = "ENO"
			else:
				conn.text = "OUT%d" % i

	# Overridden method. For documentation see base class.
	def insertConn(self, beforeIndex, conn):
		if conn:
			if conn.IN:
				return False
			if FupElem.insertConn(self, beforeIndex, conn):
				self.__genConnText()
				return True
			return False
		return False

	# Overridden method. For documentation see base class.
	def addConn(self, conn):
		if conn and conn.IN:
			return False
		return self.insertConn(len(self.outputs) - 1, conn)

	# Overridden method. For documentation see base class.
	def removeConn(self, conn):
		if conn:
			if conn.IN:
				return False
			if len(self.outputs) <= 2:
				return False
		if FupElem.removeConn(self, conn):
			self.__genConnText()
			return True
		return False

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
					idx = (pixelY // cellHeight) - 1
					if idx >= 0 and idx < len(self.inputs):
						return self.AREA_INPUT, idx
				elif pixelX >= totalWidth - xpad:
					# outputs
					idx = (pixelY // cellHeight) - 1
					if idx >= 0 and idx < len(self.outputs):
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
			if y >= 0:
				y += 1
		elif conn.OUT:
			y = self.outputs.index(conn)
			if y >= 0:
				y += 1
		if x >= 0 and y >= 0:
			return x, y
		return FupElem.getConnRelCoords(self, conn)

	# Overridden method. For documentation see base class.
	@property
	def height(self):
		return max(len(self.inputs), len(self.outputs)) + 1

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
		painter.setFont(self.getFont(8))
		for i, conn in enumerate(self.inputs):
			cellIdx = i + 1 # skip header

			x = conn.drawOffset
			y = (cellIdx * cellHeight) + (cellHeight // 2)
			if conn.isConnected or conn.text == "EN":
				painter.setPen(self._connPen)
			else:
				painter.setPen(self._connOpenPen)
			painter.drawLine(x, y, xpad, y)

			x = xpad + 2
			y = (cellIdx * cellHeight)
			painter.drawText(x, y,
					 elemWidth, cellHeight,
					 Qt.AlignLeft | Qt.AlignVCenter,
					 conn.text)

		# Draw outputs
		painter.setFont(self.getFont(8))
		for i, conn in enumerate(self.outputs):
			cellIdx = i + 1 # skip header

			x = cellWidth - conn.drawOffset
			y = (cellIdx * cellHeight) + (cellHeight // 2)
			if conn.isConnected or conn.text == "ENO":
				painter.setPen(self._connPen)
			else:
				painter.setPen(self._connOpenPen)
			painter.drawLine(cellWidth - xpad, y,
					 x, y)

			x = 0
			y = (cellIdx * cellHeight)
			painter.drawText(x, y,
					 elemWidth - xpad - 2, cellHeight,
					 Qt.AlignRight | Qt.AlignVCenter,
					 conn.text)

		# Draw element descriptor text
		painter.setFont(self.getFont(9, bold=True))
		painter.setPen(self._outlineSelPen if selected
			       else self._outlinePen)
		painter.drawText(0, 0,
				 elemWidth, cellHeight,
				 Qt.AlignHCenter | Qt.AlignVCenter,
				 "move")

	# Overridden method. For documentation see base class.
	def prepareContextMenu(self, menu, area=None, conn=None):
		menu.enableAddOutput(True)
		menu.enableRemoveConn(conn is not None and conn.OUT and len(self.outputs) > 2)
		menu.enableDisconnWire(conn is not None and conn.isConnected)

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
		elemClass = {
			FupElem_ARITH_ADD_I.OP_SYM_NAME	: FupElem_ARITH_ADD_I,
			FupElem_ARITH_SUB_I.OP_SYM_NAME	: FupElem_ARITH_SUB_I,
			FupElem_ARITH_MUL_I.OP_SYM_NAME	: FupElem_ARITH_MUL_I,
			FupElem_ARITH_DIV_I.OP_SYM_NAME	: FupElem_ARITH_DIV_I,
			FupElem_ARITH_ADD_D.OP_SYM_NAME	: FupElem_ARITH_ADD_D,
			FupElem_ARITH_SUB_D.OP_SYM_NAME	: FupElem_ARITH_SUB_D,
			FupElem_ARITH_MUL_D.OP_SYM_NAME	: FupElem_ARITH_MUL_D,
			FupElem_ARITH_DIV_D.OP_SYM_NAME	: FupElem_ARITH_DIV_D,
		}.get(subType)
		if not elemClass:
			raise self.Error("Arithmetic subtype '%s' is not known "
				"to the element parser." % (
				subType))
		self.elem = elemClass(x=x, y=y, nrInputs=0)
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
				},
				tags=[
					self.Tag(name="connections",
						 tags=connTags),
				])
		]

class FupElem_ARITH(FupElem):
	"""Arithmetic FUP/FBD element base class"""

	factory			= FupElem_ARITH_factory

	FIXED_INPUTS		= None
	FIXED_OUTPUTS		= [ "OUT", ]
	OPTIONAL_CONNS		= set()
	BLANK_CONNS		= { "OUT", }

	def __init__(self, x, y, nrInputs=2):
		FupElem.__init__(self, x, y)

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
			if pixelY >= ypad and\
			   pixelY < totalHeight - ypad:
				if pixelX < xpad:
					# inputs
					idx = pixelY // cellHeight
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
		return len(self.inputs)

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
		notR = 3
		notD = notR * 2

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
		painter.setFont(getDefaultFixedFont(8))
		for i, conn in enumerate(self.inputs):
			cellIdx = i

			connPen = self._connPen\
				if (conn.isConnected or conn.text in self.OPTIONAL_CONNS)\
				else self._connOpenPen

			x = conn.CONN_OFFS if conn.isConnected else 0
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

			x = (cellWidth - conn.CONN_OFFS) if conn.isConnected\
			    else cellWidth
			y = elemHeight - (cellHeight // 2)
			painter.setPen(connPen)
			painter.setBrush(self._bgSelBrush if selected
					 else self._bgBrush)
			painter.drawLine(cellWidth - xpad, y,
					 cellWidth, y)
			if conn.inverted:
				painter.setPen(self._connInvSelPen
					       if selected else
					       self._connInvPen)
				painter.drawEllipse(cellWidth - xpad, y - notR,
						    notD, notD)
			if conn.text and conn.text not in self.BLANK_CONNS:
				painter.setPen(connPen)
				painter.setFont(getDefaultFixedFont(8))
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
		painter.setFont(getDefaultFixedFont(11))
		painter.drawText(0, 0,
				 elemWidth, elemHeight,
				 Qt.AlignVCenter | Qt.AlignHCenter,
				 self.OP_SYM)

	# Overridden method. For documentation see base class.
	def prepareContextMenu(self, menu, area=None, conn=None):
		menu.enableInvertConn(True)
		menu.enableAddInput(self.FIXED_INPUTS is None)
		menu.enableRemoveConn(conn is not None and conn.IN and len(self.inputs) > 2)
		menu.enableDisconnWire(conn is not None and conn.isConnected)

	# Overridden method. For documentation see base class.
	def setConnInverted(self, conn, inverted=True):
		if conn in self.inputs or conn in self.outputs:
			conn.inverted = inverted
			return True
		return False

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

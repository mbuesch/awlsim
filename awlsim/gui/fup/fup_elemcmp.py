# -*- coding: utf-8 -*-
#
# AWL simulator - FUP - Compare element classes
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


class FupElem_CMP_factory(FupElem_factory):
	def parser_open(self, tag):
		assert(tag)
		x = tag.getAttrInt("x")
		y = tag.getAttrInt("y")
		subType = tag.getAttr("subtype")
		uuid = tag.getAttr("uuid", None)
		elemClass = {
			FupElem_CMP_EQ_I.OP_SYM_NAME	: FupElem_CMP_EQ_I,
			FupElem_CMP_NE_I.OP_SYM_NAME	: FupElem_CMP_NE_I,
			FupElem_CMP_GT_I.OP_SYM_NAME	: FupElem_CMP_GT_I,
			FupElem_CMP_LT_I.OP_SYM_NAME	: FupElem_CMP_LT_I,
			FupElem_CMP_GE_I.OP_SYM_NAME	: FupElem_CMP_GE_I,
			FupElem_CMP_LE_I.OP_SYM_NAME	: FupElem_CMP_LE_I,
			FupElem_CMP_EQ_D.OP_SYM_NAME	: FupElem_CMP_EQ_D,
			FupElem_CMP_NE_D.OP_SYM_NAME	: FupElem_CMP_NE_D,
			FupElem_CMP_GT_D.OP_SYM_NAME	: FupElem_CMP_GT_D,
			FupElem_CMP_LT_D.OP_SYM_NAME	: FupElem_CMP_LT_D,
			FupElem_CMP_GE_D.OP_SYM_NAME	: FupElem_CMP_GE_D,
			FupElem_CMP_LE_D.OP_SYM_NAME	: FupElem_CMP_LE_D,
			FupElem_CMP_EQ_R.OP_SYM_NAME	: FupElem_CMP_EQ_R,
			FupElem_CMP_NE_R.OP_SYM_NAME	: FupElem_CMP_NE_R,
			FupElem_CMP_GT_R.OP_SYM_NAME	: FupElem_CMP_GT_R,
			FupElem_CMP_LT_R.OP_SYM_NAME	: FupElem_CMP_LT_R,
			FupElem_CMP_GE_R.OP_SYM_NAME	: FupElem_CMP_GE_R,
			FupElem_CMP_LE_R.OP_SYM_NAME	: FupElem_CMP_LE_R,
		}.get(subType)
		if not elemClass:
			raise self.Error("Compare subtype '%s' is not known "
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
					"type" : "compare",
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

class FupElem_CMP(FupElem):
	"""Compare FUP/FBD element base class"""

	factory			= FupElem_CMP_factory

	FIXED_INPUTS		= [ "EN", ]
	FIXED_OUTPUTS		= [ "ENO", ]
	OPTIONAL_CONNS		= { "EN", "ENO", }
	BLANK_CONNS		= { "IN", "OUT", }

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

	# Overridden method. For documentation see base class.
	def insertConn(self, beforeIndex, conn):
		if not conn:
			return False
		if conn.IN:
			return False
		else:
			if beforeIndex is None:
				beforeIndex = len(self.outputs) - 1
			if beforeIndex < 0 or beforeIndex >= len(self.inputs):
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
				 elemWidth, elemHeight,
				 Qt.AlignVCenter | Qt.AlignHCenter,
				 self.OP_SYM)

	# Overridden method. For documentation see base class.
	def prepareContextMenu(self, menu, area=None, conn=None):
		menu.enableAddOutput(True)
		if conn:
			if conn.OUT:
				if conn.text.upper() != "ENO":
					menu.enableRemoveConn(len(self.outputs) > 2)
			menu.enableDisconnWire(conn.isConnected)

class FupElem_CMP_EQ_I(FupElem_CMP):
	"""==I FUP/FBD element"""

	OP_SYM			= "==I"
	OP_SYM_NAME		= "eq-int"	# XML ABI name

class FupElem_CMP_NE_I(FupElem_CMP):
	"""<>I FUP/FBD element"""

	OP_SYM			= "<>I"
	OP_SYM_NAME		= "ne-int"	# XML ABI name

class FupElem_CMP_GT_I(FupElem_CMP):
	""">I FUP/FBD element"""

	OP_SYM			= ">I"
	OP_SYM_NAME		= "gt-int"	# XML ABI name

class FupElem_CMP_LT_I(FupElem_CMP):
	"""<I FUP/FBD element"""

	OP_SYM			= "<I"
	OP_SYM_NAME		= "lt-int"	# XML ABI name

class FupElem_CMP_GE_I(FupElem_CMP):
	""">=I FUP/FBD element"""

	OP_SYM			= ">=I"
	OP_SYM_NAME		= "ge-int"	# XML ABI name

class FupElem_CMP_LE_I(FupElem_CMP):
	"""<=I FUP/FBD element"""

	OP_SYM			= "<=I"
	OP_SYM_NAME		= "le-int"	# XML ABI name

class FupElem_CMP_EQ_D(FupElem_CMP):
	"""==D FUP/FBD element"""

	OP_SYM			= "==D"
	OP_SYM_NAME		= "eq-dint"	# XML ABI name

class FupElem_CMP_NE_D(FupElem_CMP):
	"""<>D FUP/FBD element"""

	OP_SYM			= "<>D"
	OP_SYM_NAME		= "ne-dint"	# XML ABI name

class FupElem_CMP_GT_D(FupElem_CMP):
	""">D FUP/FBD element"""

	OP_SYM			= ">D"
	OP_SYM_NAME		= "gt-dint"	# XML ABI name

class FupElem_CMP_LT_D(FupElem_CMP):
	"""<D FUP/FBD element"""

	OP_SYM			= "<D"
	OP_SYM_NAME		= "lt-dint"	# XML ABI name

class FupElem_CMP_GE_D(FupElem_CMP):
	""">=D FUP/FBD element"""

	OP_SYM			= ">=D"
	OP_SYM_NAME		= "ge-dint"	# XML ABI name

class FupElem_CMP_LE_D(FupElem_CMP):
	"""<=D FUP/FBD element"""

	OP_SYM			= "<=D"
	OP_SYM_NAME		= "le-dint"	# XML ABI name

class FupElem_CMP_EQ_R(FupElem_CMP):
	"""==R FUP/FBD element"""

	OP_SYM			= "==R"
	OP_SYM_NAME		= "eq-real"	# XML ABI name

class FupElem_CMP_NE_R(FupElem_CMP):
	"""<>R FUP/FBD element"""

	OP_SYM			= "<>R"
	OP_SYM_NAME		= "ne-real"	# XML ABI name

class FupElem_CMP_GT_R(FupElem_CMP):
	""">R FUP/FBD element"""

	OP_SYM			= ">R"
	OP_SYM_NAME		= "gt-real"	# XML ABI name

class FupElem_CMP_LT_R(FupElem_CMP):
	"""<R FUP/FBD element"""

	OP_SYM			= "<R"
	OP_SYM_NAME		= "lt-real"	# XML ABI name

class FupElem_CMP_GE_R(FupElem_CMP):
	""">=R FUP/FBD element"""

	OP_SYM			= ">=R"
	OP_SYM_NAME		= "ge-real"	# XML ABI name

class FupElem_CMP_LE_R(FupElem_CMP):
	"""<=R FUP/FBD element"""

	OP_SYM			= "<=R"
	OP_SYM_NAME		= "le-real"	# XML ABI name

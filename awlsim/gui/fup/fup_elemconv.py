# -*- coding: utf-8 -*-
#
# AWL simulator - FUP - Value conversion boxes
#
# Copyright 2017-2018 Michael Buesch <m@bues.ch>
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
#from awlsim.common.cython_support cimport * #@cy
from awlsim.common.compat import *

from awlsim.common.xmlfactory import *

from awlsim.gui.fup.fup_base import *
from awlsim.gui.fup.fup_elem import *
from awlsim.gui.fup.fup_elemoperand import *


class FupElem_CONV_factory(FupElem_factory):
	def parser_open(self, tag):
		assert(tag)
		x = tag.getAttrInt("x")
		y = tag.getAttrInt("y")
		subType = tag.getAttr("subtype")
		uuid = tag.getAttr("uuid", None)
		enabled = tag.getAttrBool("enabled", True)
		elemClass = {
			FupElem_CONV_BTI.OP_SYM_NAME : FupElem_CONV_BTI,
			FupElem_CONV_ITB.OP_SYM_NAME : FupElem_CONV_ITB,
			FupElem_CONV_BTD.OP_SYM_NAME : FupElem_CONV_BTD,
			FupElem_CONV_ITD.OP_SYM_NAME : FupElem_CONV_ITD,
			FupElem_CONV_DTB.OP_SYM_NAME : FupElem_CONV_DTB,
			FupElem_CONV_DTR.OP_SYM_NAME : FupElem_CONV_DTR,
			FupElem_CONV_INVI.OP_SYM_NAME : FupElem_CONV_INVI,
			FupElem_CONV_INVD.OP_SYM_NAME : FupElem_CONV_INVD,
			FupElem_CONV_NEGI.OP_SYM_NAME : FupElem_CONV_NEGI,
			FupElem_CONV_NEGD.OP_SYM_NAME : FupElem_CONV_NEGD,
			FupElem_CONV_NEGR.OP_SYM_NAME : FupElem_CONV_NEGR,
			FupElem_CONV_TAW.OP_SYM_NAME : FupElem_CONV_TAW,
			FupElem_CONV_TAD.OP_SYM_NAME : FupElem_CONV_TAD,
			FupElem_CONV_RND.OP_SYM_NAME : FupElem_CONV_RND,
			FupElem_CONV_TRUNC.OP_SYM_NAME : FupElem_CONV_TRUNC,
			FupElem_CONV_RNDP.OP_SYM_NAME : FupElem_CONV_RNDP,
			FupElem_CONV_RNDN.OP_SYM_NAME : FupElem_CONV_RNDN,
		}.get(subType)
		if not elemClass:
			raise self.Error("Conversion subtype '%s' is not known "
				"to the element parser." % (
				subType))
		self.elem = elemClass(x=x, y=y, uuid=uuid, enabled=enabled)
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
					"type" : "convert",
					"subtype" : str(elem.OP_SYM_NAME),
					"x" : str(elem.x),
					"y" : str(elem.y),
					"uuid" : str(elem.uuid),
					"enabled" : "0" if not elem.enabled else "",
				},
				tags=[
					self.Tag(name="connections",
						 tags=connTags),
				])
		]

class FupElem_CONV(FupElem):
	"""FUP/FBD move box.
	"""

	factory = FupElem_CONV_factory

	def __init__(self, x, y, **kwargs):
		FupElem.__init__(self, x, y, **kwargs)

		self.inputs = [ FupConnIn(self, text="IN"), ]
		self.outputs = [ FupConnOut(self, text="OUT0"), ]

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
					idx = pixelY // cellHeight
					if idx >= 0 and idx < len(self.inputs):
						return self.AREA_INPUT, idx
				elif pixelX >= totalWidth - xpad:
					# outputs
					idx = pixelY // cellHeight
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
		elif conn.OUT:
			y = self.outputs.index(conn)
		if x >= 0 and y >= 0:
			return x, y
		return FupElem.getConnRelCoords(self, conn)

	# Overridden method. For documentation see base class.
	@property
	def height(self):
		return max(len(self.inputs), len(self.outputs))

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
		for i, conn in enumerate(self.inputs):
			x = conn.drawOffset
			y = (i * cellHeight) + (cellHeight // 2)
			if conn.isConnected:
				painter.setPen(self._connPen)
			else:
				painter.setPen(self._connOpenPen)
			painter.drawLine(x, y, xpad, y)

		# Draw outputs
		for i, conn in enumerate(self.outputs):
			x = cellWidth - conn.drawOffset
			y = (i * cellHeight) + (cellHeight // 2)
			if conn.isConnected:
				painter.setPen(self._connPen)
			else:
				painter.setPen(self._connOpenPen)
			painter.drawLine(cellWidth - xpad, y,
					 x, y)

		# Draw element descriptor text
		painter.setFont(self.getFont(9, bold=True))
		painter.setPen(self._outlineSelPen if selected
			       else self._outlinePen)
		painter.drawText(0, 0,
				 elemWidth, cellHeight,
				 Qt.AlignHCenter | Qt.AlignVCenter,
				 self.OP_SYM)

		# Draw disable-marker
		self._drawDisableMarker(painter)

	# Overridden method. For documentation see base class.
	def prepareContextMenu(self, menu, area=None, conn=None):
		menu.enableDisconnWire(conn is not None and conn.isConnected)

class FupElem_CONV_BTI(FupElem_CONV):
	"""BTI FUP/FBD element"""

	OP_SYM			= "BCD->I"
	OP_SYM_NAME		= "bti" # XML ABI name

class FupElem_CONV_ITB(FupElem_CONV):
	"""ITB FUP/FBD element"""

	OP_SYM			= "I->BCD"
	OP_SYM_NAME		= "itb" # XML ABI name

class FupElem_CONV_BTD(FupElem_CONV):
	"""BTD FUP/FBD element"""

	OP_SYM			= "BCD->D"
	OP_SYM_NAME		= "btd" # XML ABI name

class FupElem_CONV_ITD(FupElem_CONV):
	"""ITD FUP/FBD element"""

	OP_SYM			= "I->D"
	OP_SYM_NAME		= "itd" # XML ABI name

class FupElem_CONV_DTB(FupElem_CONV):
	"""DTB FUP/FBD element"""

	OP_SYM			= "D->BCD"
	OP_SYM_NAME		= "dtb" # XML ABI name

class FupElem_CONV_DTR(FupElem_CONV):
	"""DTR FUP/FBD element"""

	OP_SYM			= "D->R"
	OP_SYM_NAME		= "dtr" # XML ABI name

class FupElem_CONV_INVI(FupElem_CONV):
	"""INVI FUP/FBD element"""

	OP_SYM			= "inv I"
	OP_SYM_NAME		= "invi" # XML ABI name

class FupElem_CONV_INVD(FupElem_CONV):
	"""INVD FUP/FBD element"""

	OP_SYM			= "inv D"
	OP_SYM_NAME		= "invd" # XML ABI name

class FupElem_CONV_NEGI(FupElem_CONV):
	"""NEGI FUP/FBD element"""

	OP_SYM			= "neg I"
	OP_SYM_NAME		= "negi" # XML ABI name

class FupElem_CONV_NEGD(FupElem_CONV):
	"""NEGD FUP/FBD element"""

	OP_SYM			= "neg D"
	OP_SYM_NAME		= "negd" # XML ABI name

class FupElem_CONV_NEGR(FupElem_CONV):
	"""NEGR FUP/FBD element"""

	OP_SYM			= "neg R"
	OP_SYM_NAME		= "negr" # XML ABI name

class FupElem_CONV_TAW(FupElem_CONV):
	"""TAW FUP/FBD element"""

	OP_SYM			= "swap W"
	OP_SYM_NAME		= "taw" # XML ABI name

class FupElem_CONV_TAD(FupElem_CONV):
	"""TAD FUP/FBD element"""

	OP_SYM			= "swap D"
	OP_SYM_NAME		= "tad" # XML ABI name

class FupElem_CONV_RND(FupElem_CONV):
	"""RND FUP/FBD element"""

	OP_SYM			= "round"
	OP_SYM_NAME		= "rnd" # XML ABI name

class FupElem_CONV_TRUNC(FupElem_CONV):
	"""TRUNC FUP/FBD element"""

	OP_SYM			= "trunc"
	OP_SYM_NAME		= "trunc" # XML ABI name

class FupElem_CONV_RNDP(FupElem_CONV):
	"""RND+ FUP/FBD element"""

	OP_SYM			= "round+"
	OP_SYM_NAME		= "rndp" # XML ABI name

class FupElem_CONV_RNDN(FupElem_CONV):
	"""RND- FUP/FBD element"""

	OP_SYM			= "round-"
	OP_SYM_NAME		= "rndn" # XML ABI name

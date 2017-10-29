# -*- coding: utf-8 -*-
#
# AWL simulator - FUP - Comment element class
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


class FupElem_COMMENT_factory(FupElem_factory):
	def parser_open(self, tag):
		assert(tag)
		x = tag.getAttrInt("x")
		y = tag.getAttrInt("y")
		content = tag.getAttr("content", "")
		uuid = tag.getAttr("uuid", None)
		self.elem = FupElem_COMMENT(x=x, y=y,
					    contentText=content,
					    uuid=uuid)
		self.elem.grid = self.grid
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
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
		return [
			self.Tag(name="element",
				attrs={
					"type" : "comment",
					"x" : str(self.elem.x),
					"y" : str(self.elem.y),
					"content" : self.elem.contentText,
					"uuid" : str(self.elem.uuid),
				}
			)
		]

class FupElem_COMMENT(FupElem):
	"""Comment element.
	"""

	factory = FupElem_COMMENT_factory

	BODY_CORNER_RADIUS	= 4

	def __init__(self, x, y, contentText="", uuid=None):
		FupElem.__init__(self, x, y, uuid=uuid)

		self._continuePen = QPen(QBrush(), 1, Qt.DotLine)
		self._continuePen.setColor(QColor("#000000"))

		self._bgBrush = QBrush(QColor("#FFFFE0"))

		self.contentText = contentText
		self.partialContent = False

	@property
	def _xpadding(self):
		return 1

	@property
	def _ypadding(self):
		return 1

	# Overridden method. For documentation see base class.
	def getAreaViaPixCoord(self, pixelX, pixelY):
		return self.AREA_BODY, 0

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
			painter.setFont(self.getFont(8))
			painter.setPen(self._textPen)
			if expanded:
				textFlags = Qt.TextWrapAnywhere | Qt.AlignLeft | Qt.AlignTop
				textMaxRect = bodyRect.translated(0, 0)
				textMaxRect.setHeight(grid.height * cellHeight)
				textMaxRect.setWidth(grid.width * cellWidth)
				textRect = painter.boundingRect(textMaxRect, textFlags, text)
				actTextRect = textRect
			else:
				textFlags = Qt.TextWrapAnywhere | Qt.AlignHCenter | Qt.AlignTop
				textRect = bodyRect
				actTextRect = painter.boundingRect(bodyRect, textFlags, text)
			if expanded:
				painter.setBrush(self._bgSelBrush if selected
						 else self._bgBrush)
				painter.setPen(self._noPen)
				painter.drawRect(actTextRect)
			painter.setPen(self._textPen)
			painter.drawText(textRect, textFlags, text)
			if not bodyRect.contains(actTextRect):
				if not expanded:
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
		text, ok = QInputDialog.getMultiLineText(parentWidget,
			"Change comment",
			"Comment",
			self.contentText)
		if ok:
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

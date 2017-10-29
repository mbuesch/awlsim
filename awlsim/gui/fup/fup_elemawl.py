# -*- coding: utf-8 -*-
#
# AWL simulator - FUP - Inline AWL element classes
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

from awlsim.gui.editwidget import *


class FupElem_AWL_factory(FupElem_factory):
	def parser_open(self, tag):
		assert(tag)
		x = tag.getAttrInt("x")
		y = tag.getAttrInt("y")
		content = tag.getAttr("content", "")
		uuid = tag.getAttr("uuid", None)
		self.elem = FupElem_AWL(x=x, y=y,
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
					"type" : "awl",
					"x" : str(self.elem.x),
					"y" : str(self.elem.y),
					"content" : self.elem.contentText,
					"uuid" : str(self.elem.uuid),
				}
			)
		]

class FupElem_AWL(FupElem):
	"""Inline-AWL FUP/FBD element"""

	factory			= FupElem_AWL_factory

	def __init__(self, x, y, contentText="", uuid=None):
		FupElem.__init__(self, x, y, uuid=uuid)
		self.contentText = contentText

		self._lightTextPen = QPen(QColor("#707070"))
		self._lightTextPen.setWidth(0)

	# Overridden method. For documentation see base class.
	def getAreaViaPixCoord(self, pixelX, pixelY):
		return self.AREA_BODY, 0

	# Overridden method. For documentation see base class.
	@property
	def height(self):
		return 3

	# Overridden method. For documentation see base class.
	@property
	def width(self):
		return 2

	# Overridden method. For documentation see base class.
	def draw(self, painter):
		grid = self.grid
		if not grid:
			return
		cellWidth = grid.cellPixWidth
		cellHeight = grid.cellPixHeight
		xpad, ypad = self._xpadding, self._ypadding
		elemHeight = cellHeight * self.height
		elemWidth = cellWidth * self.width
		selected = self.selected
		expanded = self.expanded and not selected

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

		# Draw content text
		text = self.contentText
		if text:
			bodyRect = QRect(2 * xpad, 2 * ypad,
					 elemWidth - 4 * xpad, elemHeight - 4 * ypad)
			textRect = bodyRect
			textFlags = Qt.AlignLeft | Qt.AlignTop
			if expanded:
				textMaxRect = bodyRect.translated(0, 0)
				textMaxRect.setHeight(grid.height * cellHeight)
				textMaxRect.setWidth(grid.width * cellWidth)
				textRect = painter.boundingRect(textMaxRect, textFlags, text)
				if textRect.width() < bodyRect.width():
					textRect.setWidth(bodyRect.width())

				painter.setBrush(self._bgSelBrush if selected
						 else self._bgBrush)
				painter.setPen(self._noPen)
				painter.drawRect(textRect)
			painter.setPen(self._textPen if expanded
				       else self._lightTextPen)
			painter.setFont(self.getFont(8))
			painter.drawText(textRect, textFlags, text)

		# Draw symbol text
		if not expanded:
			painter.setPen(self._outlineSelPen if selected
				       else self._outlinePen)
			painter.setBrush(self._bgSelBrush if selected
					 else self._bgBrush)
			painter.setFont(self.getFont(16, bold=True))
			painter.drawText(0, 0,
					 elemWidth, elemHeight,
					 Qt.AlignVCenter | Qt.AlignHCenter,
					 "AWL")

	# Overridden method. For documentation see base class.
	def edit(self, parentWidget):
		dlg = EditDialog(parentWidget,
				 readOnly=False, withHeader=False, withCpuStats=False,
				 okButton=True, cancelButton=True)
		dlg.setWindowTitle("Inline AWL code")
		source = AwlSource(sourceBytes=self.contentText.encode(
					AwlSource.ENCODING,
					"ignore"))
		dlg.edit.setSource(source)
		if dlg.exec_() == QDialog.Accepted:
			source = dlg.edit.getSource()
			self.contentText = source.sourceText
			return True
		return False

	# Overridden method. For documentation see base class.
	def expand(self, expand=True, area=None):
		if expand != self.expanded:
			self.expanded = expand
			return True
		return False

	# Overridden method. For documentation see base class.
	def prepareContextMenu(self, menu, area=None, conn=None):
		menu.enableEdit(True)

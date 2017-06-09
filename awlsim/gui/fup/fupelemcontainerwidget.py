# -*- coding: utf-8 -*-
#
# AWL simulator - FUP element container widget
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

from awlsim.gui.icons import *
from awlsim.gui.util import *


class FupElemItemClass(QTreeWidgetItem):
	def __init__(self, text, iconName):
		QTreeWidgetItem.__init__(self, [text])
		self.setIcon(0, getIcon(iconName))

class FupElemItem(QTreeWidgetItem):
	def __init__(self, text, iconName, mimeType, mimeData):
		QTreeWidgetItem.__init__(self, [text])
		self.mimeType = mimeType
		self.mimeData = mimeData
		self.setIcon(0, getIcon(iconName))

class FupElemContainerWidget(QTreeWidget):
	def __init__(self, parent=None):
		QTreeWidget.__init__(self, parent)

		self.setDragEnabled(True)
		self.setHeaderLabels(["Elements"])

		elemMimeType = "application/x-awlsim-fup-elem"

		itemBool = FupElemItemClass("Boolean", "stdlib")
		itemBoolU = FupElemItem("[&]  and", "new", elemMimeType, b"bool-and")
		itemBool.addChild(itemBoolU)
		itemBoolO = FupElemItem("[>=1]  or", "new", elemMimeType, b"bool-or")
		itemBool.addChild(itemBoolO)
		itemBoolX = FupElemItem("[X]  xor", "new", elemMimeType, b"bool-xor")
		itemBool.addChild(itemBoolX)

		itemMove = FupElemItemClass("Move", "stdlib")
		itemMoveL = FupElemItem("[L]  load", "new", elemMimeType, b"move-load")
		itemMove.addChild(itemMoveL)
		itemMoveA = FupElemItem("[=]  assign", "new", elemMimeType, b"move-assign")
		itemMove.addChild(itemMoveA)
		itemMoveMove = FupElemItem("-[=]-  move box", "new", elemMimeType, b"move-box")
		itemMove.addChild(itemMoveMove)

		itemArithI = FupElemItemClass("Int arithmetic", "stdlib")
		itemArithR = FupElemItemClass("Real arithmetic", "stdlib")

		self.addTopLevelItem(itemBool)
		itemBool.setExpanded(True)
		self.addTopLevelItem(itemMove)
		itemMove.setExpanded(True)
		self.addTopLevelItem(itemArithI)
		self.addTopLevelItem(itemArithR)

		self.itemDoubleClicked.connect(self.handleItemDoubleClick)

	def startDrag(self, supportedActions):
		item = self.currentItem()
		if not isinstance(item, FupElemItem):
			return

		#TODO the XML format shall be used instead
		mimeData = QMimeData()
		mimeData.setData(item.mimeType, item.mimeData)

		pixmap = item.icon(0).pixmap(32, 32)

		drag = QDrag(self)
		drag.setMimeData(mimeData)
		drag.setHotSpot(QPoint(pixmap.width() // 2,
				       pixmap.height() // 2))
		drag.setPixmap(pixmap)
		drag.exec_(Qt.CopyAction)

	def handleItemDoubleClick(self, item, column):
		if not isinstance(item, FupElemItem):
			return
		pass#TODO

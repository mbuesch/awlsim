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

from awlsim.gui.fup.fup_elembool import *
from awlsim.gui.fup.fup_elemmove import *
from awlsim.gui.fup.fup_elemarith import *
from awlsim.gui.fup.fup_elemcomment import *


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
	"""FUP element container tree widget.
	"""

	@staticmethod
	def elemToXml(elem):
		xmlBytes = elem.factory(elem=elem).compose()
		return xmlBytes

	def __init__(self, parent=None):
		QTreeWidget.__init__(self, parent)

		self.setDragEnabled(True)
		self.setHeaderLabels(["Elements"])

		elemMimeType = "application/x-awlsim-fup-elem"

		itemComment = FupElemItem("[...]  Comment", "new", elemMimeType,
					  self.elemToXml(FupElem_COMMENT(-1, -1)))
		self.addTopLevelItem(itemComment)

		itemBool = FupElemItemClass("Boolean", "stdlib")
		itemBoolU = FupElemItem("[&]  and", "new", elemMimeType,
					self.elemToXml(FupElem_AND(-1, -1)))
		itemBool.addChild(itemBoolU)
		itemBoolO = FupElemItem("[>=1]  or", "new", elemMimeType,
					self.elemToXml(FupElem_OR(-1, -1)))
		itemBool.addChild(itemBoolO)
		itemBoolX = FupElemItem("[X]  xor", "new", elemMimeType,
					self.elemToXml(FupElem_XOR(-1, -1)))
		itemBool.addChild(itemBoolX)
		itemBoolS = FupElemItem("[S]  set", "new", elemMimeType,
					self.elemToXml(FupElem_S(-1, -1)))
		itemBool.addChild(itemBoolS)
		itemBoolR = FupElemItem("[R]  reset", "new", elemMimeType,
					self.elemToXml(FupElem_R(-1, -1)))
		itemBool.addChild(itemBoolR)
		itemBoolSR = FupElemItem("[SR]  SR flip-flop", "new", elemMimeType,
					self.elemToXml(FupElem_SR(-1, -1)))
		itemBool.addChild(itemBoolSR)
		itemBoolRS = FupElemItem("[RS]  RS flip-flop", "new", elemMimeType,
					self.elemToXml(FupElem_RS(-1, -1)))
		itemBool.addChild(itemBoolRS)
		itemBoolFP = FupElemItem("[FP]  positive edge", "new", elemMimeType,
					self.elemToXml(FupElem_FP(-1, -1)))
		itemBool.addChild(itemBoolFP)
		itemBoolFN = FupElemItem("[FN]  negative edge", "new", elemMimeType,
					self.elemToXml(FupElem_FN(-1, -1)))
		itemBool.addChild(itemBoolFN)

		itemMove = FupElemItemClass("Move", "stdlib")
		itemMoveL = FupElemItem("[L]  load", "new", elemMimeType,
					self.elemToXml(FupElem_LOAD(-1, -1)))
		itemMove.addChild(itemMoveL)
		itemMoveA = FupElemItem("[=]  assign", "new", elemMimeType,
					self.elemToXml(FupElem_ASSIGN(-1, -1)))
		itemMove.addChild(itemMoveA)
		itemMoveMove = FupElemItem("-[=]-  move box", "new", elemMimeType,
					   self.elemToXml(FupElem_MOVE(-1, -1)))
		itemMove.addChild(itemMoveMove)

		itemArithI = FupElemItemClass("Int arithmetic", "stdlib")
		itemArithADDI = FupElemItem("[+I]  INT addition", "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_ADD_I(-1, -1)))
		itemArithI.addChild(itemArithADDI)
		itemArithSUBI = FupElemItem("[-I]  INT subtraction", "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_SUB_I(-1, -1)))
		itemArithI.addChild(itemArithSUBI)
		itemArithMULI = FupElemItem("[*I]  INT multiplication", "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_MUL_I(-1, -1)))
		itemArithI.addChild(itemArithMULI)
		itemArithDIVI = FupElemItem("[/I]  INT division", "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_DIV_I(-1, -1)))
		itemArithI.addChild(itemArithDIVI)
		itemArithADDD = FupElemItem("[+D]  DINT addition", "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_ADD_D(-1, -1)))
		itemArithI.addChild(itemArithADDD)
		itemArithSUBD = FupElemItem("[-D]  DINT subtraction", "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_SUB_D(-1, -1)))
		itemArithI.addChild(itemArithSUBD)
		itemArithMULD = FupElemItem("[*D]  DINT multiplication", "new", elemMimeType,
					   self.elemToXml(FupElem_ARITH_MUL_D(-1, -1)))
		itemArithI.addChild(itemArithMULD)
		itemArithDIVD = FupElemItem("[/D]  DINT division", "new", elemMimeType,
					   self.elemToXml(FupElem_ARITH_DIV_D(-1, -1)))
		itemArithI.addChild(itemArithDIVD)

		itemArithR = FupElemItemClass("Real arithmetic", "stdlib")
		itemArithADDR = FupElemItem("[+R]  REAL addition", "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_ADD_R(-1, -1)))
		itemArithR.addChild(itemArithADDR)
		itemArithSUBR = FupElemItem("[-R]  REAL subtraction", "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_SUB_R(-1, -1)))
		itemArithR.addChild(itemArithSUBR)
		itemArithMULR = FupElemItem("[*R]  REAL multiplication", "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_MUL_R(-1, -1)))
		itemArithR.addChild(itemArithMULR)
		itemArithDIVR = FupElemItem("[/R]  REAL division", "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_DIV_R(-1, -1)))
		itemArithR.addChild(itemArithDIVR)

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

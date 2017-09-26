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
from awlsim.gui.fup.fup_elemcmp import *
from awlsim.gui.fup.fup_elemcomment import *
from awlsim.gui.fup.fup_elemawl import *


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

		itemArithI = FupElemItemClass("INT", "stdlib")
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

		itemArithD = FupElemItemClass("DINT", "stdlib")
		itemArithADDD = FupElemItem("[+D]  DINT addition", "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_ADD_D(-1, -1)))
		itemArithD.addChild(itemArithADDD)
		itemArithSUBD = FupElemItem("[-D]  DINT subtraction", "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_SUB_D(-1, -1)))
		itemArithD.addChild(itemArithSUBD)
		itemArithMULD = FupElemItem("[*D]  DINT multiplication", "new", elemMimeType,
					   self.elemToXml(FupElem_ARITH_MUL_D(-1, -1)))
		itemArithD.addChild(itemArithMULD)
		itemArithDIVD = FupElemItem("[/D]  DINT division", "new", elemMimeType,
					   self.elemToXml(FupElem_ARITH_DIV_D(-1, -1)))
		itemArithD.addChild(itemArithDIVD)
		itemArithMODD = FupElemItem("[MOD]  DINT modulo", "new", elemMimeType,
					   self.elemToXml(FupElem_ARITH_MOD_D(-1, -1)))
		itemArithD.addChild(itemArithMODD)

		itemArithR = FupElemItemClass("REAL", "stdlib")
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

		itemCmpI = FupElemItemClass("INT", "stdlib")
		itemCmpEQI = FupElemItem("[==I]  INT equal", "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_EQ_I(-1, -1)))
		itemCmpI.addChild(itemCmpEQI)
		itemCmpNEI = FupElemItem("[<>I]  INT not equal", "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_NE_I(-1, -1)))
		itemCmpI.addChild(itemCmpNEI)
		itemCmpGTI = FupElemItem("[>I]  INT greater than", "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_GT_I(-1, -1)))
		itemCmpI.addChild(itemCmpGTI)
		itemCmpLTI = FupElemItem("[<I]  INT less than", "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_LT_I(-1, -1)))
		itemCmpI.addChild(itemCmpLTI)
		itemCmpGEI = FupElemItem("[>=I]  INT greater or equal", "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_GE_I(-1, -1)))
		itemCmpI.addChild(itemCmpGEI)
		itemCmpLEI = FupElemItem("[<=I]  INT less or equal", "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_LE_I(-1, -1)))
		itemCmpI.addChild(itemCmpLEI)

		itemCmpD = FupElemItemClass("DINT", "stdlib")
		itemCmpEQD = FupElemItem("[==D]  DINT equal", "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_EQ_D(-1, -1)))
		itemCmpD.addChild(itemCmpEQD)
		itemCmpNED = FupElemItem("[<>D]  DINT not equal", "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_NE_D(-1, -1)))
		itemCmpD.addChild(itemCmpNED)
		itemCmpGTD = FupElemItem("[>D]  DINT greater than", "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_GT_D(-1, -1)))
		itemCmpD.addChild(itemCmpGTD)
		itemCmpLTD = FupElemItem("[<D]  DINT less than", "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_LT_D(-1, -1)))
		itemCmpD.addChild(itemCmpLTD)
		itemCmpGED = FupElemItem("[>=D]  DINT greater or equal", "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_GE_D(-1, -1)))
		itemCmpD.addChild(itemCmpGED)
		itemCmpLED = FupElemItem("[<=D]  DINT less or equal", "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_LE_D(-1, -1)))
		itemCmpD.addChild(itemCmpLED)

		itemCmpR = FupElemItemClass("REAL", "stdlib")
		itemCmpEQR = FupElemItem("[==R]  REAL equal", "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_EQ_R(-1, -1)))
		itemCmpR.addChild(itemCmpEQR)
		itemCmpNER = FupElemItem("[<>R]  REAL not equal", "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_NE_R(-1, -1)))
		itemCmpR.addChild(itemCmpNER)
		itemCmpGTR = FupElemItem("[>R]  REAL greater than", "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_GT_R(-1, -1)))
		itemCmpR.addChild(itemCmpGTR)
		itemCmpLTR = FupElemItem("[<R]  REAL less than", "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_LT_R(-1, -1)))
		itemCmpR.addChild(itemCmpLTR)
		itemCmpGER = FupElemItem("[>=R]  REAL greater or equal", "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_GE_R(-1, -1)))
		itemCmpR.addChild(itemCmpGER)
		itemCmpLER = FupElemItem("[<=R]  REAL less or equal", "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_LE_R(-1, -1)))
		itemCmpR.addChild(itemCmpLER)

		itemAWL = FupElemItem("[AWL]  Inline AWL code", "new", elemMimeType,
				      self.elemToXml(FupElem_AWL(-1, -1)))

		itemArith = FupElemItemClass("Arithmetic", "stdlib")
		itemArith.addChild(itemArithI)
		itemArith.addChild(itemArithD)
		itemArith.addChild(itemArithR)
		itemCmp = FupElemItemClass("Compare", "stdlib")
		itemCmp.addChild(itemCmpI)
		itemCmp.addChild(itemCmpD)
		itemCmp.addChild(itemCmpR)

		self.addTopLevelItem(itemComment)
		self.addTopLevelItem(itemBool)
		itemBool.setExpanded(True)
		self.addTopLevelItem(itemMove)
		self.addTopLevelItem(itemArith)
		itemArith.setExpanded(True)
		self.addTopLevelItem(itemCmp)
		itemCmp.setExpanded(True)
		self.addTopLevelItem(itemAWL)

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

# -*- coding: utf-8 -*-
#
# AWL simulator - FUP element container widget
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

from awlsim.common.locale import _

from awlsim.gui.icons import *
from awlsim.gui.util import *

from awlsim.gui.fup.fup_elembool import *
from awlsim.gui.fup.fup_elemmove import *
from awlsim.gui.fup.fup_elemconv import *
from awlsim.gui.fup.fup_elemcount import *
from awlsim.gui.fup.fup_elemtime import *
from awlsim.gui.fup.fup_elemarith import *
from awlsim.gui.fup.fup_elemshift import *
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

		elemMimeType = "application/x-awlsim-xml-fup-elem"

		# Comment element
		itemComment = FupElemItem(_("[...]  Comment"), "new", elemMimeType,
					  self.elemToXml(FupElem_COMMENT(-1, -1)))

		# Boolean elements
		itemBool = FupElemItemClass(_("Boolean"), "stdlib")
		itemBoolU = FupElemItem(_("[&]  and"), "new", elemMimeType,
					self.elemToXml(FupElem_AND(-1, -1)))
		itemBool.addChild(itemBoolU)
		itemBoolO = FupElemItem(_("[>=1]  or"), "new", elemMimeType,
					self.elemToXml(FupElem_OR(-1, -1)))
		itemBool.addChild(itemBoolO)
		itemBoolX = FupElemItem(_("[X]  xor"), "new", elemMimeType,
					self.elemToXml(FupElem_XOR(-1, -1)))
		itemBool.addChild(itemBoolX)
		itemBoolS = FupElemItem(_("[S]  set"), "new", elemMimeType,
					self.elemToXml(FupElem_S(-1, -1)))
		itemBool.addChild(itemBoolS)
		itemBoolR = FupElemItem(_("[R]  reset"), "new", elemMimeType,
					self.elemToXml(FupElem_R(-1, -1)))
		itemBool.addChild(itemBoolR)
		itemBoolSR = FupElemItem(_("[SR]  SR flip-flop"), "new", elemMimeType,
					self.elemToXml(FupElem_SR(-1, -1)))
		itemBool.addChild(itemBoolSR)
		itemBoolRS = FupElemItem(_("[RS]  RS flip-flop"), "new", elemMimeType,
					self.elemToXml(FupElem_RS(-1, -1)))
		itemBool.addChild(itemBoolRS)
		itemBoolFP = FupElemItem(_("[FP]  positive edge"), "new", elemMimeType,
					self.elemToXml(FupElem_FP(-1, -1)))
		itemBool.addChild(itemBoolFP)
		itemBoolFN = FupElemItem(_("[FN]  negative edge"), "new", elemMimeType,
					self.elemToXml(FupElem_FN(-1, -1)))
		itemBool.addChild(itemBoolFN)

		# Counters
		itemC = FupElemItemClass(_("Counters"), "stdlib")
		itemCUD = FupElemItem(_("[CUD]  Counter"), "new", elemMimeType,
				      self.elemToXml(FupElem_CUD(-1, -1)))
		itemC.addChild(itemCUD)
		itemCU = FupElemItem(_("[CU]  Counter up"), "new", elemMimeType,
				     self.elemToXml(FupElem_CU(-1, -1)))
		itemC.addChild(itemCU)
		itemCUO = FupElemItem(_("[CUo]  Counter up-only"), "new", elemMimeType,
				      self.elemToXml(FupElem_CUO(-1, -1)))
		itemC.addChild(itemCUO)
		itemCD = FupElemItem(_("[CD]  Counter down"), "new", elemMimeType,
				     self.elemToXml(FupElem_CD(-1, -1)))
		itemC.addChild(itemCD)
		itemCDO = FupElemItem(_("[CDo]  Counter down-only"), "new", elemMimeType,
				      self.elemToXml(FupElem_CDO(-1, -1)))
		itemC.addChild(itemCDO)
		itemCSO = FupElemItem(_("[CSo]  Counter set"), "new", elemMimeType,
				      self.elemToXml(FupElem_CSO(-1, -1)))
		itemC.addChild(itemCSO)

		# Timers
		itemT = FupElemItemClass(_("Timers"), "stdlib")
		itemTSI = FupElemItem(_("[SP]  Pulse"), "new", elemMimeType,
				      self.elemToXml(FupElem_T_SI(-1, -1)))
		itemT.addChild(itemTSI)
		itemTSV = FupElemItem(_("[SE]  Extended pulse"), "new", elemMimeType,
				      self.elemToXml(FupElem_T_SV(-1, -1)))
		itemT.addChild(itemTSV)
		itemTSE = FupElemItem(_("[SD]  On-delay"), "new", elemMimeType,
				      self.elemToXml(FupElem_T_SE(-1, -1)))
		itemT.addChild(itemTSE)
		itemTSS = FupElemItem(_("[SS]  Extended on-delay"), "new", elemMimeType,
				      self.elemToXml(FupElem_T_SS(-1, -1)))
		itemT.addChild(itemTSS)
		itemTSA = FupElemItem(_("[SF]  Off-delay"), "new", elemMimeType,
				      self.elemToXml(FupElem_T_SA(-1, -1)))
		itemT.addChild(itemTSA)

		# Move and convert elements
		itemMove = FupElemItemClass(_("Move / convert"), "stdlib")
		itemMoveL = FupElemItem(_("[L]  load"), "new", elemMimeType,
					self.elemToXml(FupElem_LOAD(-1, -1)))
		itemMove.addChild(itemMoveL)
		itemMoveA = FupElemItem(_("[=]  assign"), "new", elemMimeType,
					self.elemToXml(FupElem_ASSIGN(-1, -1)))
		itemMove.addChild(itemMoveA)
		itemMoveMove = FupElemItem(_("-[=]-  move box"), "new", elemMimeType,
					   self.elemToXml(FupElem_MOVE(-1, -1)))
		itemMove.addChild(itemMoveMove)

		# INT convert elements
		itemConvI = FupElemItemClass(_("INT / DINT"), "stdlib")
		itemConvITD = FupElemItem(_("[I->D]  INT to DINT"), "new", elemMimeType,
					   self.elemToXml(FupElem_CONV_ITD(-1, -1)))
		itemConvI.addChild(itemConvITD)
		itemConvNEGI = FupElemItem(_("[neg I]  negate INT"), "new", elemMimeType,
					   self.elemToXml(FupElem_CONV_NEGI(-1, -1)))
		itemConvI.addChild(itemConvNEGI)
		itemConvNEGD = FupElemItem(_("[neg D]  negate DINT"), "new", elemMimeType,
					   self.elemToXml(FupElem_CONV_NEGD(-1, -1)))
		itemConvI.addChild(itemConvNEGD)
		itemConvINVI = FupElemItem(_("[inv I]  bitwise invert INT"), "new", elemMimeType,
					   self.elemToXml(FupElem_CONV_INVI(-1, -1)))
		itemConvI.addChild(itemConvINVI)
		itemConvINVD = FupElemItem(_("[inv D]  bitwise invert DINT"), "new", elemMimeType,
					   self.elemToXml(FupElem_CONV_INVD(-1, -1)))
		itemConvI.addChild(itemConvINVD)
		itemMove.addChild(itemConvI)

		# REAL convert elements
		itemConvR = FupElemItemClass(_("REAL"), "stdlib")
		itemConvDTR = FupElemItem(_("[D->R]  DINT to REAL"), "new", elemMimeType,
					   self.elemToXml(FupElem_CONV_DTR(-1, -1)))
		itemConvR.addChild(itemConvDTR)
		itemConvNEGR = FupElemItem(_("[neg R]  negate REAL"), "new", elemMimeType,
					   self.elemToXml(FupElem_CONV_NEGR(-1, -1)))
		itemConvR.addChild(itemConvNEGR)
		itemConvRND = FupElemItem(_("[round]  round REAL"), "new", elemMimeType,
					   self.elemToXml(FupElem_CONV_RND(-1, -1)))
		itemConvR.addChild(itemConvRND)
		itemConvTRUNC = FupElemItem(_("[trunc]  truncate REAL"), "new", elemMimeType,
					   self.elemToXml(FupElem_CONV_TRUNC(-1, -1)))
		itemConvR.addChild(itemConvTRUNC)
		itemConvRNDP = FupElemItem(_("[round+]  round REAL to pos."), "new", elemMimeType,
					   self.elemToXml(FupElem_CONV_RNDP(-1, -1)))
		itemConvR.addChild(itemConvRNDP)
		itemConvRNDN = FupElemItem(_("[round-]  round REAL to neg."), "new", elemMimeType,
					   self.elemToXml(FupElem_CONV_RNDN(-1, -1)))
		itemConvR.addChild(itemConvRNDN)
		itemMove.addChild(itemConvR)

		# BCD convert elements
		itemConvB = FupElemItemClass(_("BCD"), "stdlib")
		itemConvBTI = FupElemItem(_("[BCD->I]  BCD to INT"), "new", elemMimeType,
					   self.elemToXml(FupElem_CONV_BTI(-1, -1)))
		itemConvB.addChild(itemConvBTI)
		itemConvBTD = FupElemItem(_("[BCD->D]  BCD to DINT"), "new", elemMimeType,
					   self.elemToXml(FupElem_CONV_BTD(-1, -1)))
		itemConvB.addChild(itemConvBTD)
		itemConvITB = FupElemItem(_("[I->BCD]  INT to BCD"), "new", elemMimeType,
					   self.elemToXml(FupElem_CONV_ITB(-1, -1)))
		itemConvB.addChild(itemConvITB)
		itemConvDTB = FupElemItem(_("[D->BCD]  DINT to BCD"), "new", elemMimeType,
					   self.elemToXml(FupElem_CONV_DTB(-1, -1)))
		itemConvB.addChild(itemConvDTB)
		itemMove.addChild(itemConvB)

		# Byteorder convert elements
		itemConvOrd = FupElemItemClass(_("Byte order"), "stdlib")
		itemConvTAW = FupElemItem(_("[swap W]  swap WORD order"), "new", elemMimeType,
					   self.elemToXml(FupElem_CONV_TAW(-1, -1)))
		itemConvOrd.addChild(itemConvTAW)
		itemConvTAD = FupElemItem(_("[swap D]  swap DWORD order"), "new", elemMimeType,
					   self.elemToXml(FupElem_CONV_TAD(-1, -1)))
		itemConvOrd.addChild(itemConvTAD)
		itemMove.addChild(itemConvOrd)

		# INT arithmetic elements
		itemArithI = FupElemItemClass(_("INT"), "stdlib")
		itemArithADDI = FupElemItem(_("[+I]  INT addition"), "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_ADD_I(-1, -1)))
		itemArithI.addChild(itemArithADDI)
		itemArithSUBI = FupElemItem(_("[-I]  INT subtraction"), "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_SUB_I(-1, -1)))
		itemArithI.addChild(itemArithSUBI)
		itemArithMULI = FupElemItem(_("[*I]  INT multiplication"), "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_MUL_I(-1, -1)))
		itemArithI.addChild(itemArithMULI)
		itemArithDIVI = FupElemItem(_("[/I]  INT division"), "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_DIV_I(-1, -1)))
		itemArithI.addChild(itemArithDIVI)

		# DINT arithmetic elements
		itemArithD = FupElemItemClass(_("DINT"), "stdlib")
		itemArithADDD = FupElemItem(_("[+D]  DINT addition"), "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_ADD_D(-1, -1)))
		itemArithD.addChild(itemArithADDD)
		itemArithSUBD = FupElemItem(_("[-D]  DINT subtraction"), "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_SUB_D(-1, -1)))
		itemArithD.addChild(itemArithSUBD)
		itemArithMULD = FupElemItem(_("[*D]  DINT multiplication"), "new", elemMimeType,
					   self.elemToXml(FupElem_ARITH_MUL_D(-1, -1)))
		itemArithD.addChild(itemArithMULD)
		itemArithDIVD = FupElemItem(_("[/D]  DINT division"), "new", elemMimeType,
					   self.elemToXml(FupElem_ARITH_DIV_D(-1, -1)))
		itemArithD.addChild(itemArithDIVD)
		itemArithMODD = FupElemItem(_("[MOD]  DINT modulo"), "new", elemMimeType,
					   self.elemToXml(FupElem_ARITH_MOD_D(-1, -1)))
		itemArithD.addChild(itemArithMODD)

		# REAL arithmetic elements
		itemArithR = FupElemItemClass(_("REAL"), "stdlib")
		itemArithADDR = FupElemItem(_("[+R]  REAL addition"), "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_ADD_R(-1, -1)))
		itemArithR.addChild(itemArithADDR)
		itemArithSUBR = FupElemItem(_("[-R]  REAL subtraction"), "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_SUB_R(-1, -1)))
		itemArithR.addChild(itemArithSUBR)
		itemArithMULR = FupElemItem(_("[*R]  REAL multiplication"), "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_MUL_R(-1, -1)))
		itemArithR.addChild(itemArithMULR)
		itemArithDIVR = FupElemItem(_("[/R]  REAL division"), "new", elemMimeType,
					    self.elemToXml(FupElem_ARITH_DIV_R(-1, -1)))
		itemArithR.addChild(itemArithDIVR)

		# Shift WORD elements
		itemShiftW = FupElemItemClass(_("WORD / INT"), "stdlib")
		itemShiftSSI = FupElemItem(_("[SSI >>]  Signed INT right shift"), "new", elemMimeType,
					   self.elemToXml(FupElem_SSI(-1, -1)))
		itemShiftW.addChild(itemShiftSSI)
		itemShiftSRW = FupElemItem(_("[SRW >>]  WORD right shift"), "new", elemMimeType,
					   self.elemToXml(FupElem_SRW(-1, -1)))
		itemShiftW.addChild(itemShiftSRW)
		itemShiftSLW = FupElemItem(_("[SLW <<]  WORD left shift"), "new", elemMimeType,
					   self.elemToXml(FupElem_SLW(-1, -1)))
		itemShiftW.addChild(itemShiftSLW)

		# Shift DWORD elements
		itemShiftD = FupElemItemClass(_("DWORD / DINT"), "stdlib")
		itemShiftSSD = FupElemItem(_("[SSD >>]  Signed DINT right shift"), "new", elemMimeType,
					   self.elemToXml(FupElem_SSD(-1, -1)))
		itemShiftD.addChild(itemShiftSSD)
		itemShiftSRD = FupElemItem(_("[SRD >>]  DWORD right shift"), "new", elemMimeType,
					   self.elemToXml(FupElem_SRD(-1, -1)))
		itemShiftD.addChild(itemShiftSRD)
		itemShiftSLD = FupElemItem(_("[SLD <<]  DWORD left shift"), "new", elemMimeType,
					   self.elemToXml(FupElem_SLD(-1, -1)))
		itemShiftD.addChild(itemShiftSLD)
		itemShiftRLD = FupElemItem(_("[RLD <<]  DWORD rotate left"), "new", elemMimeType,
					   self.elemToXml(FupElem_RLD(-1, -1)))
		itemShiftD.addChild(itemShiftRLD)
		itemShiftRRD = FupElemItem(_("[RRD <<]  DWORD rotate right"), "new", elemMimeType,
					   self.elemToXml(FupElem_RRD(-1, -1)))
		itemShiftD.addChild(itemShiftRRD)

		# Compare INT elements
		itemCmpI = FupElemItemClass(_("INT"), "stdlib")
		itemCmpEQI = FupElemItem(_("[==I]  INT equal"), "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_EQ_I(-1, -1)))
		itemCmpI.addChild(itemCmpEQI)
		itemCmpNEI = FupElemItem(_("[<>I]  INT not equal"), "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_NE_I(-1, -1)))
		itemCmpI.addChild(itemCmpNEI)
		itemCmpGTI = FupElemItem(_("[>I]  INT greater than"), "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_GT_I(-1, -1)))
		itemCmpI.addChild(itemCmpGTI)
		itemCmpLTI = FupElemItem(_("[<I]  INT less than"), "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_LT_I(-1, -1)))
		itemCmpI.addChild(itemCmpLTI)
		itemCmpGEI = FupElemItem(_("[>=I]  INT greater or equal"), "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_GE_I(-1, -1)))
		itemCmpI.addChild(itemCmpGEI)
		itemCmpLEI = FupElemItem(_("[<=I]  INT less or equal"), "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_LE_I(-1, -1)))
		itemCmpI.addChild(itemCmpLEI)

		# Compare DINT elements
		itemCmpD = FupElemItemClass(_("DINT"), "stdlib")
		itemCmpEQD = FupElemItem(_("[==D]  DINT equal"), "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_EQ_D(-1, -1)))
		itemCmpD.addChild(itemCmpEQD)
		itemCmpNED = FupElemItem(_("[<>D]  DINT not equal"), "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_NE_D(-1, -1)))
		itemCmpD.addChild(itemCmpNED)
		itemCmpGTD = FupElemItem(_("[>D]  DINT greater than"), "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_GT_D(-1, -1)))
		itemCmpD.addChild(itemCmpGTD)
		itemCmpLTD = FupElemItem(_("[<D]  DINT less than"), "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_LT_D(-1, -1)))
		itemCmpD.addChild(itemCmpLTD)
		itemCmpGED = FupElemItem(_("[>=D]  DINT greater or equal"), "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_GE_D(-1, -1)))
		itemCmpD.addChild(itemCmpGED)
		itemCmpLED = FupElemItem(_("[<=D]  DINT less or equal"), "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_LE_D(-1, -1)))
		itemCmpD.addChild(itemCmpLED)

		# Compare REAL elements
		itemCmpR = FupElemItemClass(_("REAL"), "stdlib")
		itemCmpEQR = FupElemItem(_("[==R]  REAL equal"), "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_EQ_R(-1, -1)))
		itemCmpR.addChild(itemCmpEQR)
		itemCmpNER = FupElemItem(_("[<>R]  REAL not equal"), "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_NE_R(-1, -1)))
		itemCmpR.addChild(itemCmpNER)
		itemCmpGTR = FupElemItem(_("[>R]  REAL greater than"), "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_GT_R(-1, -1)))
		itemCmpR.addChild(itemCmpGTR)
		itemCmpLTR = FupElemItem(_("[<R]  REAL less than"), "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_LT_R(-1, -1)))
		itemCmpR.addChild(itemCmpLTR)
		itemCmpGER = FupElemItem(_("[>=R]  REAL greater or equal"), "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_GE_R(-1, -1)))
		itemCmpR.addChild(itemCmpGER)
		itemCmpLER = FupElemItem(_("[<=R]  REAL less or equal"), "new", elemMimeType,
					 self.elemToXml(FupElem_CMP_LE_R(-1, -1)))
		itemCmpR.addChild(itemCmpLER)

		# Inline-AWL element
		prog = "// Enter your AWL/STL program code here...\n\n"
		itemAWL = FupElemItem(_("[AWL]  Inline AWL code"), "new", elemMimeType,
				      self.elemToXml(FupElem_AWL(-1, -1,
				      contentText=prog)))

		# Main groups
		itemArith = FupElemItemClass(_("Arithmetic"), "stdlib")
		itemArith.addChild(itemArithI)
		itemArith.addChild(itemArithD)
		itemArith.addChild(itemArithR)
		itemShift = FupElemItemClass(_("Shift"), "stdlib")
		itemShift.addChild(itemShiftW)
		itemShift.addChild(itemShiftD)
		itemCmp = FupElemItemClass(_("Compare"), "stdlib")
		itemCmp.addChild(itemCmpI)
		itemCmp.addChild(itemCmpD)
		itemCmp.addChild(itemCmpR)

		# Top level tree items
		self.addTopLevelItem(itemComment)
		self.addTopLevelItem(itemBool)
		itemBool.setExpanded(True)
		self.addTopLevelItem(itemMove)
		self.addTopLevelItem(itemC)
		self.addTopLevelItem(itemT)
		self.addTopLevelItem(itemArith)
		itemArith.setExpanded(True)
		self.addTopLevelItem(itemShift)
		itemShift.setExpanded(True)
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

# -*- coding: utf-8 -*-
#
# AWL simulator - GUI edit widget
#
# Copyright 2012-2016 Michael Buesch <m@bues.ch>
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

from awlsim.gui.util import *
from awlsim.gui.cpuwidget import *
from awlsim.gui.sourcecodeedit import *


class EditSubWidget(QWidget):
	needRepaint = Signal(QPaintEvent)
	wasScrolled = Signal(QWheelEvent)
	contextMenuReq = Signal(QPoint)

	def __init__(self, editWidget):
		QWidget.__init__(self, editWidget)
		self.editWidget = editWidget

	def paintEvent(self, ev):
		self.needRepaint.emit(ev)
		ev.accept()

	def wheelEvent(self, ev):
		self.wasScrolled.emit(ev)

	def getPainter(self):
		p = QPainter(self)
		p.setFont(self.font())
		return p

	def contextMenuEvent(self, ev):
		QWidget.contextMenuEvent(self, ev)
		self.contextMenuReq.emit(ev.globalPos())

class HeaderSubWidget(EditSubWidget):
	def __init__(self, editWidget):
		EditSubWidget.__init__(self, editWidget)

	def sizeHint(self):
		return QSize(0, self.editWidget.headerHeight())

class LineNumSubWidget(EditSubWidget):
	def __init__(self, editWidget):
		EditSubWidget.__init__(self, editWidget)

	def sizeHint(self):
		return QSize(self.editWidget.lineNumWidgetWidth(), 0)

class CpuStatsSubWidget(EditSubWidget):
	def __init__(self, editWidget):
		EditSubWidget.__init__(self, editWidget)

	def sizeHint(self):
		return QSize(self.editWidget.cpuStatsWidgetWidth(), 0)

	def getBanner(self, showFlg):
		ret = []
		if showFlg & CpuStatsEntry.SHOW_NER:
			ret.append("/FC")
		if showFlg & CpuStatsEntry.SHOW_VKE:
			ret.append("RLO")
		if showFlg & CpuStatsEntry.SHOW_STA:
			ret.append("STA")
		if showFlg & CpuStatsEntry.SHOW_OR:
			ret.append("OR")
		if showFlg & CpuStatsEntry.SHOW_OS:
			ret.append("OS")
		if showFlg & CpuStatsEntry.SHOW_OV:
			ret.append("OV")
		if showFlg & CpuStatsEntry.SHOW_A0:
			ret.append("CC0")
		if showFlg & CpuStatsEntry.SHOW_A1:
			ret.append("CC1")
		if showFlg & CpuStatsEntry.SHOW_BIE:
			ret.append("BR")
		if showFlg & CpuStatsEntry.SHOW_STW:
			ret.append("STW        ")
		if showFlg & CpuStatsEntry.SHOW_ACCU1:
			ret.append("ACCU 1  ")
		if showFlg & CpuStatsEntry.SHOW_ACCU2:
			ret.append("ACCU 2  ")
		if showFlg & CpuStatsEntry.SHOW_ACCU3:
			ret.append("ACCU 3  ")
		if showFlg & CpuStatsEntry.SHOW_ACCU4:
			ret.append("ACCU 4  ")
		if showFlg & CpuStatsEntry.SHOW_AR1:
			ret.append("AR 1    ")
		if showFlg & CpuStatsEntry.SHOW_AR2:
			ret.append("AR 2    ")
		if showFlg & CpuStatsEntry.SHOW_DBREG:
			ret.append("DB   ")
		if showFlg & CpuStatsEntry.SHOW_DIREG:
			ret.append("DI   ")
		return "  ".join(ret)

class CpuStatsEntry(object):
	EnumGen.start
	SHOW_NER	= EnumGen.bitmask
	SHOW_VKE	= EnumGen.bitmask
	SHOW_STA	= EnumGen.bitmask
	SHOW_OR		= EnumGen.bitmask
	SHOW_OS		= EnumGen.bitmask
	SHOW_OV		= EnumGen.bitmask
	SHOW_A0		= EnumGen.bitmask
	SHOW_A1		= EnumGen.bitmask
	SHOW_BIE	= EnumGen.bitmask
	SHOW_STW	= EnumGen.bitmask
	SHOW_ACCU1	= EnumGen.bitmask
	SHOW_ACCU2	= EnumGen.bitmask
	SHOW_ACCU3	= EnumGen.bitmask
	SHOW_ACCU4	= EnumGen.bitmask
	SHOW_AR1	= EnumGen.bitmask
	SHOW_AR2	= EnumGen.bitmask
	SHOW_DBREG	= EnumGen.bitmask
	SHOW_DIREG	= EnumGen.bitmask
	EnumGen.end

	def __init__(self, stamp, insnDumpMsg):
		self.stamp = stamp
		self.insnDumpMsg = insnDumpMsg
		self.obsolete = False
		self.pruned = False

	def getText(self, showFlg):
		if self.pruned:
			return "[ ... ]"
		insnDumpMsg = self.insnDumpMsg
		ret = []
		if showFlg & self.SHOW_NER:
			ret.append("%d  " % ((insnDumpMsg.stw >> 0) & 1))
		if showFlg & self.SHOW_VKE:
			ret.append("%d  " % ((insnDumpMsg.stw >> 1) & 1))
		if showFlg & self.SHOW_STA:
			ret.append("%d  " % ((insnDumpMsg.stw >> 2) & 1))
		if showFlg & self.SHOW_OR:
			ret.append("%d " % ((insnDumpMsg.stw >> 3) & 1))
		if showFlg & self.SHOW_OS:
			ret.append("%d " % ((insnDumpMsg.stw >> 4) & 1))
		if showFlg & self.SHOW_OV:
			ret.append("%d " % ((insnDumpMsg.stw >> 5) & 1))
		if showFlg & self.SHOW_A0:
			ret.append("%d  " % ((insnDumpMsg.stw >> 6) & 1))
		if showFlg & self.SHOW_A1:
			ret.append("%d  " % ((insnDumpMsg.stw >> 7) & 1))
		if showFlg & self.SHOW_BIE:
			ret.append("%d " % ((insnDumpMsg.stw >> 8) & 1))
		if showFlg & self.SHOW_STW:
			stw = []
			for i in range(S7StatusWord.NR_BITS - 1, -1, -1):
				stw.append('1' if ((insnDumpMsg.stw >> i) & 1) else '0')
				if i % 4 == 0 and i:
					stw.append('_')
			ret.append("".join(stw))
		if showFlg & self.SHOW_ACCU1:
			ret.append("%08X" % insnDumpMsg.accu1)
		if showFlg & self.SHOW_ACCU2:
			ret.append("%08X" % insnDumpMsg.accu2)
		if showFlg & self.SHOW_ACCU3:
			ret.append("%08X" % insnDumpMsg.accu3)
		if showFlg & self.SHOW_ACCU4:
			ret.append("%08X" % insnDumpMsg.accu4)
		if showFlg & self.SHOW_AR1:
			ret.append("%08X" % insnDumpMsg.ar1)
		if showFlg & self.SHOW_AR2:
			ret.append("%08X" % insnDumpMsg.ar2)
		if showFlg & self.SHOW_DBREG:
			if insnDumpMsg.db:
				dbreg = str(insnDumpMsg.db)
				dbreg += " " * (5 - len(dbreg))
				ret.append(dbreg)
			else:
				ret.append("--   ")
		if showFlg & self.SHOW_DIREG:
			if insnDumpMsg.db:
				direg = str(insnDumpMsg.db)
				direg += " " * (5 - len(direg))
				ret.append(direg)
			else:
				ret.append("--   ")
		return "  ".join(ret)

class CheckAction(QAction):
	def __init__(self, name, toggleCallback=None, parent=None):
		QAction.__init__(self, name, parent)
		self.setCheckable(True)
		if toggleCallback:
			self.toggled.connect(toggleCallback)

class CpuStatsContextMenu(QMenu):
	closed = Signal()

	def __init__(self, parent=None):
		QMenu.__init__(self, parent)

		itemsMenu = QMenu("Online items", self)
		self.__action_NER = CheckAction("Status bit: /FC (/ER)",
						self.__actionToggled, self)
		itemsMenu.addAction(self.__action_NER)
		self.__action_VKE = CheckAction("Status bit: RLO (VKE)",
						self.__actionToggled, self)
		itemsMenu.addAction(self.__action_VKE)
		self.__action_STA = CheckAction("Status bit: STA",
						self.__actionToggled, self)
		itemsMenu.addAction(self.__action_STA)
		self.__action_OR = CheckAction("Status bit: OR",
					       self.__actionToggled, self)
		itemsMenu.addAction(self.__action_OR)
		self.__action_OS = CheckAction("Status bit: OS",
					       self.__actionToggled, self)
		itemsMenu.addAction(self.__action_OS)
		self.__action_OV = CheckAction("Status bit: OV",
					       self.__actionToggled, self)
		itemsMenu.addAction(self.__action_OV)
		self.__action_A0 = CheckAction("Status bit: CC0 (A0)",
					       self.__actionToggled, self)
		itemsMenu.addAction(self.__action_A0)
		self.__action_A1 = CheckAction("Status bit: CC1 (A1)",
					       self.__actionToggled, self)
		itemsMenu.addAction(self.__action_A1)
		self.__action_BIE = CheckAction("Status bit: BR (BIE)",
						self.__actionToggled, self)
		itemsMenu.addAction(self.__action_BIE)
		self.__action_STW = CheckAction("Full status word",
						self.__actionToggled, self)
		itemsMenu.addAction(self.__action_STW)
		self.__action_accu1 = CheckAction("Accu 1",
						  self.__actionToggled, self)
		itemsMenu.addAction(self.__action_accu1)
		self.__action_accu2 = CheckAction("Accu 2",
						  self.__actionToggled, self)
		itemsMenu.addAction(self.__action_accu2)
		self.__action_accu3 = CheckAction("Accu 3",
						  self.__actionToggled, self)
		itemsMenu.addAction(self.__action_accu3)
		self.__action_accu4 = CheckAction("Accu 4",
						  self.__actionToggled, self)
		itemsMenu.addAction(self.__action_accu4)
		self.__action_ar1 = CheckAction("AR 1",
						self.__actionToggled, self)
		itemsMenu.addAction(self.__action_ar1)
		self.__action_ar2 = CheckAction("AR 2",
						self.__actionToggled, self)
		itemsMenu.addAction(self.__action_ar2)
		self.__action_db = CheckAction("DB register",
					       self.__actionToggled, self)
		itemsMenu.addAction(self.__action_db)
		self.__action_di = CheckAction("DI register",
					       self.__actionToggled, self)
		itemsMenu.addAction(self.__action_di)
		self.addMenu(itemsMenu)

	def setShowFlags(self, showFlg):
		self.__action_NER.setChecked(bool(showFlg & CpuStatsEntry.SHOW_NER))
		self.__action_VKE.setChecked(bool(showFlg & CpuStatsEntry.SHOW_VKE))
		self.__action_STA.setChecked(bool(showFlg & CpuStatsEntry.SHOW_STA))
		self.__action_OR.setChecked(bool(showFlg & CpuStatsEntry.SHOW_OR))
		self.__action_OS.setChecked(bool(showFlg & CpuStatsEntry.SHOW_OS))
		self.__action_OV.setChecked(bool(showFlg & CpuStatsEntry.SHOW_OV))
		self.__action_A0.setChecked(bool(showFlg & CpuStatsEntry.SHOW_A0))
		self.__action_A1.setChecked(bool(showFlg & CpuStatsEntry.SHOW_A1))
		self.__action_BIE.setChecked(bool(showFlg & CpuStatsEntry.SHOW_BIE))
		self.__action_STW.setChecked(bool(showFlg & CpuStatsEntry.SHOW_STW))
		self.__action_accu1.setChecked(bool(showFlg & CpuStatsEntry.SHOW_ACCU1))
		self.__action_accu2.setChecked(bool(showFlg & CpuStatsEntry.SHOW_ACCU2))
		self.__action_accu3.setChecked(bool(showFlg & CpuStatsEntry.SHOW_ACCU3))
		self.__action_accu4.setChecked(bool(showFlg & CpuStatsEntry.SHOW_ACCU4))
		self.__action_ar1.setChecked(bool(showFlg & CpuStatsEntry.SHOW_AR1))
		self.__action_ar2.setChecked(bool(showFlg & CpuStatsEntry.SHOW_AR2))
		self.__action_db.setChecked(bool(showFlg & CpuStatsEntry.SHOW_DBREG))
		self.__action_di.setChecked(bool(showFlg & CpuStatsEntry.SHOW_DIREG))

	def getShowFlags(self):
		showFlg = 0
		if self.__action_NER.isChecked():
			showFlg |= CpuStatsEntry.SHOW_NER
		if self.__action_VKE.isChecked():
			showFlg |= CpuStatsEntry.SHOW_VKE
		if self.__action_STA.isChecked():
			showFlg |= CpuStatsEntry.SHOW_STA
		if self.__action_OR.isChecked():
			showFlg |= CpuStatsEntry.SHOW_OR
		if self.__action_OS.isChecked():
			showFlg |= CpuStatsEntry.SHOW_OS
		if self.__action_OV.isChecked():
			showFlg |= CpuStatsEntry.SHOW_OV
		if self.__action_A0.isChecked():
			showFlg |= CpuStatsEntry.SHOW_A0
		if self.__action_A1.isChecked():
			showFlg |= CpuStatsEntry.SHOW_A1
		if self.__action_BIE.isChecked():
			showFlg |= CpuStatsEntry.SHOW_BIE
		if self.__action_STW.isChecked():
			showFlg |= CpuStatsEntry.SHOW_STW
		if self.__action_accu1.isChecked():
			showFlg |= CpuStatsEntry.SHOW_ACCU1
		if self.__action_accu2.isChecked():
			showFlg |= CpuStatsEntry.SHOW_ACCU2
		if self.__action_accu3.isChecked():
			showFlg |= CpuStatsEntry.SHOW_ACCU3
		if self.__action_accu4.isChecked():
			showFlg |= CpuStatsEntry.SHOW_ACCU4
		if self.__action_ar1.isChecked():
			showFlg |= CpuStatsEntry.SHOW_AR1
		if self.__action_ar2.isChecked():
			showFlg |= CpuStatsEntry.SHOW_AR2
		if self.__action_db.isChecked():
			showFlg |= CpuStatsEntry.SHOW_DBREG
		if self.__action_di.isChecked():
			showFlg |= CpuStatsEntry.SHOW_DIREG
		return showFlg

	def __actionToggled(self, newState):
		self.closed.emit()

class EditWidget(SourceCodeEdit):
	"""AWL/STL edit widget."""

	# Signal: Emitted, if the source code changed.
	codeChanged = Signal()
	# Signal: Emitted, if the visible source lines changed (e.g. scrolled)
	visibleRangeChanged = Signal()
	# Signal: editor<->Cpu source code match changed.
	# Parameter 0: This EditWidget
	# Parameter 1: Bool: True -> Editor code does match CPU code.
	cpuCodeMatchChanged = Signal(SourceCodeEdit, bool)
	# Signal: Keyboard focus in/out event.
	focusChanged = Signal(bool)

	# Generate the RUN animation
	__runAniTemplate = ("   x   ",
			    "  -x-  ", " --x-- ", "---x---",
			    "--=x=--", "-==x==-", "===x===",
			    "==*x*==", "=**x**=", "***x***")
	__runAniTemplate = __runAniTemplate + __runAniTemplate[1:-1][::-1]
	__runAni = tuple(c.replace("x", " CPU running ")
			 for c in __runAniTemplate)
	__runAniNoDown = tuple(c.replace("x", " source NOT DOWNLOADED to CPU ")
			       for c in __runAniTemplate)

	def __init__(self, parent=None,
		     readOnly=False,
		     withHeader=True, withCpuStats=True):
		SourceCodeEdit.__init__(self, parent)

		self.setReadOnly(readOnly)

		self.__runAniTimer = QTimer(self)
		self.__runAniTimer.setSingleShot(False)
		self.__runAniTimer.timeout.connect(self.__runAnimation)

		self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.setLineWrapMode(SourceCodeEdit.NoWrap)
		self.setTabStopWidth(self.tabStopWidth() // 2)

		if withHeader:
			self.headerWidget = HeaderSubWidget(self)
		else:
			self.headerWidget = None
		self.lineNumWidget = LineNumSubWidget(self)
		if withCpuStats:
			self.cpuStatsWidget = CpuStatsSubWidget(self)
		else:
			self.cpuStatsWidget = None

		self.__updateFont(getDefaultFixedFont())

		self.__source = AwlSource(name = "Unnamed source")
		self.__needSourceUpdate = True
		self.__sourceMatchesCpuSource = False

		self.__runState = RunState()
		self.__nextHdrUpdate = 0
		self.__hdrAniStat = 0

		if withCpuStats:
			self.__cpuStatsMenu = CpuStatsContextMenu(self)
			self.__cpuStatsMask = 0
		self.enableCpuStats(enabled=False, force=True)
		if withCpuStats:
			self.setCpuStatsMask(CpuStatsEntry.SHOW_VKE |\
					     CpuStatsEntry.SHOW_STA |\
					     CpuStatsEntry.SHOW_ACCU1 |\
					     CpuStatsEntry.SHOW_ACCU2)
		self.resetCpuStats(True)

		self.__textChangeBlocked = Blocker()
		self.textChanged.connect(self.__textChanged)

		self.blockCountChanged.connect(self.__updateMargins)
		self.updateRequest.connect(self.__updateExtraWidgets)
		self.lineNumWidget.needRepaint.connect(self.__repaintLineNumWidget)
		self.lineNumWidget.wasScrolled.connect(self.__forwardWheelEvent)
		if self.headerWidget:
			self.headerWidget.needRepaint.connect(self.__repaintHeaderWidget)
			self.headerWidget.wasScrolled.connect(self.__forwardWheelEvent)
			self.headerWidget.contextMenuReq.connect(self.__cpuStatsContextMenuPopup)
		if self.cpuStatsWidget:
			self.cpuStatsWidget.needRepaint.connect(self.__repaintCpuStatsWidget)
			self.cpuStatsWidget.wasScrolled.connect(self.__forwardWheelEvent)
			self.cpuStatsWidget.contextMenuReq.connect(self.__cpuStatsContextMenuPopup)
			self.__cpuStatsMenu.closed.connect(self.__cpuStatsContextMenuClosed)

	def getSourceId(self):
		return self.__source.identHash

	def shutdown(self):
		pass

	def setSource(self, source):
		with self.__textChangeBlocked:
			self.__source = source.dup()
			self.__source.sourceBytes = b""
			sourceBytes = source.sourceBytes
			try:
				sourceText = sourceBytes.decode(AwlSource.ENCODING,
								errors="strict")
			except UnicodeError:
				MessageBox.error(self, "The AWL/STL code contains "
					"non-%s-characters. These were ignored and stripped "
					"from the code." % AwlSource.ENCODING)
				sourceText = sourceBytes.decode(AwlSource.ENCODING,
								errors="ignore")
			self.setPlainText(sourceText)
			self.resetCpuStats()
		self.__needSourceUpdate = True

	def __updateSource(self):
		sourceText = self.toPlainText()
		# Convert to DOS-style line endings
		sourceText = toDosEol(sourceText)
		# Convert to binary
		try:
			sourceBytes = sourceText.encode(AwlSource.ENCODING,
							errors="strict")
			self.__source.sourceBytes = sourceBytes
		except UnicodeError:
			MessageBox.error(self, "The AWL/STL code contains "
				"non-%s-characters. These were ignored and stripped "
				"from the code." % AwlSource.ENCODING)
			sourceBytes = sourceText.encode(AwlSource.ENCODING,
							errors="ignore")
			self.__source.sourceBytes = sourceBytes
			self.setSource(self.__source)
		self.__needSourceUpdate = False

	def getSource(self):
		if self.__needSourceUpdate:
			self.__updateSource()
		return self.__source

	def setSettings(self, guiSettings):
		self.enableAutoIndent(guiSettings.getEditorAutoIndentEn())
		self.enablePasteIndent(guiSettings.getEditorPasteIndentEn())
		self.enableValidation(guiSettings.getEditorValidationEn())
		font = getDefaultFixedFont()
		fontString = guiSettings.getEditorFont()
		if fontString:
			font.fromString(fontString)
			font.setStyleHint(QFont.Courier)
		self.__updateFont(font)

	def runStateChanged(self, newState):
		self.__runState = newState
		if newState.state == RunState.STATE_LOAD:
			self.resetCpuStats()
			self.__setSourceMatchesCpuSource(True)
		if newState.state == RunState.STATE_RUN:
			self.__setSourceMatchesCpuSource(
				self.__sourceMatchesCpuSource, force = True)
			self.__runAniTimer.start(200)
		else:
			self.__runAniTimer.stop()
		if self.__cpuStatsEnabled:
			self.cpuStatsWidget.update()
		if self.headerWidget:
			self.headerWidget.update()

	def __eachVisibleLine(self):
		block = self.firstVisibleBlock()
		top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
		bottom = top + self.blockBoundingRect(block).height()

		while block.isValid() and\
		      block.isVisible() and\
		      top <= self.viewport().rect().bottom():
			yield (block.blockNumber() + 1, top)
			block = block.next()
			top = bottom
			bottom = top + self.blockBoundingRect(block).height()

	def getVisibleLineRange(self):
		firstVisibleLine = lastVisibleLine = 0
		for lineNr, yOffset in self.__eachVisibleLine():
			if firstVisibleLine == 0 or\
			   lineNr < firstVisibleLine:
				firstVisibleLine = lineNr
			if lineNr > lastVisibleLine:
				lastVisibleLine = lineNr
		return firstVisibleLine, lastVisibleLine

	def __updateFont(self, font):
		# Set the font for new text
		fmt = self.currentCharFormat()
		fmt.setFont(font)
		self.setCurrentCharFormat(fmt)

		# Reformat the existing text
		cursor = self.textCursor()
		cursor.select(QTextCursor.Document)
		fmt = cursor.charFormat()
		fmt.setFont(font)
		cursor.setCharFormat(fmt)

		# Set the font for other window elements
		self.setFont(font)
		self.update()
		if self.headerWidget:
			self.headerWidget.setFont(font)
			self.headerWidget.update()
		self.lineNumWidget.setFont(font)
		self.lineNumWidget.update()
		if self.cpuStatsWidget:
			self.cpuStatsWidget.setFont(font)
			self.cpuStatsWidget.update()

		# Cache metrics
		self.__charHeight = self.fontMetrics().height()
		self.setTabStopWidth(self.fontMetrics().width("X") * 8)

	def enableCpuStats(self, enabled=True, force=False):
		if not self.cpuStatsWidget:
			enabled = False
		if force or enabled != self.__cpuStatsEnabled:
			self.__cpuStatsEnabled = enabled
			self.__updateMargins()
			self.__updateGeo()

	def setCpuStatsMask(self, newMask):
		self.__cpuStatsMask = newMask
		if self.__cpuStatsEnabled:
			self.__updateMargins()
			self.__updateGeo()

	def __cpuStatsContextMenuPopup(self, globalPos):
		if self.__cpuStatsEnabled:
			self.__cpuStatsMenu.setShowFlags(self.__cpuStatsMask)
			self.__cpuStatsMenu.popup(globalPos)

	def __cpuStatsContextMenuClosed(self):
		self.setCpuStatsMask(self.__cpuStatsMenu.getShowFlags())

	def resetCpuStats(self, force=False):
		if not force and not self.__lineCpuStats:
			return
		self.__lineCpuStats = { }
		self.__cpuStatsCount = 0
		self.__cpuStatsUpdate = 1
		self.__cpuStatsStamp = 0
		self.__updateMargins()
		if self.headerWidget:
			self.headerWidget.update()
		if self.cpuStatsWidget:
			self.cpuStatsWidget.update()

	def updateCpuStats_afterInsn(self, insnDumpMsg):
		# insnDumpMsg => AwlSimMessage_INSNDUMP instance
		if not self.__cpuStatsEnabled:
			return
		if insnDumpMsg.sourceId != self.getSourceId():
			# Discard old messages that were still in the queue.
			return
		# Save the instruction dump
		self.__lineCpuStats[insnDumpMsg.lineNr] =\
			CpuStatsEntry(self.__cpuStatsStamp,
				      insnDumpMsg)
		# Update the stats widget
		self.__cpuStatsCount += 1
		if self.__cpuStatsCount >= self.__cpuStatsUpdate:
			self.__cpuStatsCount = 0
			self.__cpuStatsUpdate = 128
			self.cpuStatsWidget.update()

		# First instruction in cycle?
		if insnDumpMsg.serial == 0:
			# Update the 'obsolete'-flag based on the timestamp
			for ent in dictValues(self.__lineCpuStats):
				ent.obsolete = (ent.stamp != self.__cpuStatsStamp)
			# Advance the timestamp
			self.__cpuStatsStamp += 1

	def __pruneInvisibleCpuStats(self):
		if self.__runState.state == RunState.STATE_OFFLINE:
			return
		firstLine, lastLine = self.getVisibleLineRange()
		for line, stats in dictItems(self.__lineCpuStats):
			if line < firstLine or line > lastLine:
				stats.pruned = True
				stats.obsolete = True

	def __runAnimation(self):
		if self.headerWidget:
			self.__hdrAniStat = (self.__hdrAniStat + 1) %\
					    len(self.__runAni)
			self.headerWidget.update()

	def __setSourceMatchesCpuSource(self, sourceIsOnCpu, force=False):
		if sourceIsOnCpu != self.__sourceMatchesCpuSource or force:
			self.__sourceMatchesCpuSource = sourceIsOnCpu
			if self.headerWidget:
				self.headerWidget.update()
			self.cpuCodeMatchChanged.emit(self, sourceIsOnCpu)

	def handleIdentsMsg(self, identsMsg):
		if self.__runState.state == RunState.STATE_RUN:
			cpuHashes = [ s.identHash for s in identsMsg.awlSources ]
			self.__setSourceMatchesCpuSource(
				self.getSource().identHash in cpuHashes)
		else:
			# The CPU is not in RUN state.
			# We don't make a big deal out of code mismatch.
			self.__setSourceMatchesCpuSource(True)

	def __forwardWheelEvent(self, ev):
		self.wheelEvent(ev)

	def lineNumWidgetWidth(self):
		digi, bcnt = 1, self.blockCount()
		while bcnt > 9:
			digi, bcnt = digi + 1, bcnt // 10
		metr = self.lineNumWidget.fontMetrics()
		return 5 + 5 + metr.width("_" * digi)

	def cpuStatsWidgetWidth(self):
		if not self.__cpuStatsEnabled:
			return 0
		metr = self.cpuStatsWidget.fontMetrics()
		return 5 + 5 + metr.width(self.cpuStatsWidget.getBanner(self.__cpuStatsMask).replace(" ", "_"))

	def headerHeight(self):
		if self.headerWidget:
			return 5 + 5 + self.__charHeight
		return 0

	def __updateMargins(self):
		self.setViewportMargins(self.lineNumWidgetWidth(),
					self.headerHeight(),
					self.cpuStatsWidgetWidth(),
					0)

	def sizeHint(self):
		sh = SourceCodeEdit.sizeHint(self)
		sh.setWidth(650 +\
			    self.lineNumWidgetWidth() +\
			    self.cpuStatsWidgetWidth())
		return sh

	def __updateHeaderWidgetGeo(self):
		if self.headerWidget:
			cont = self.contentsRect()
			rect = QRect(cont.left(),
				     cont.top(),
				     cont.width(),
				     self.headerHeight())
			self.headerWidget.setGeometry(rect)

	def __updateLineNumWidgetGeo(self):
		cont = self.contentsRect()
		rect = QRect(cont.left(),
			     cont.top() + self.headerHeight(),
			     self.lineNumWidgetWidth(),
			     cont.height())
		self.lineNumWidget.setGeometry(rect)

	def __updateCpuStatsWidgetGeo(self):
		if not self.cpuStatsWidget:
			return
		if self.__cpuStatsEnabled:
			vp, cont = self.viewport(), self.contentsRect()
			rect = QRect(vp.width() + self.lineNumWidgetWidth(),
				     cont.top() + self.headerHeight(),
				     self.cpuStatsWidgetWidth(),
				     cont.height())
			self.cpuStatsWidget.setGeometry(rect)
			self.cpuStatsWidget.show()
		else:
			self.cpuStatsWidget.hide()

	def __updateGeo(self):
		self.__updateHeaderWidgetGeo()
		self.__updateLineNumWidgetGeo()
		self.__updateCpuStatsWidgetGeo()

	def __updateExtraWidgets(self, rect, dy):
		if dy:
			if self.headerWidget:
				self.headerWidget.scroll(0, dy)
			self.lineNumWidget.scroll(0, dy)
			if self.cpuStatsWidget:
				self.cpuStatsWidget.scroll(0, dy)
			self.__pruneInvisibleCpuStats()
			self.visibleRangeChanged.emit()
			return
		if self.headerWidget:
			self.headerWidget.update(0, rect.y(),
				self.headerWidget.width(),
				rect.height())
		self.lineNumWidget.update(0, rect.y(),
			self.lineNumWidget.width(),
			rect.height())
		if self.cpuStatsWidget:
			self.cpuStatsWidget.update(0, rect.y(),
				self.cpuStatsWidget.width(),
				rect.height())
		if rect.contains(self.viewport().rect()):
			self.__updateMargins()

	def resizeEvent(self, ev):
		SourceCodeEdit.resizeEvent(self, ev)
		self.__updateGeo()

	def focusInEvent(self, ev):
		SourceCodeEdit.focusInEvent(self, ev)
		self.focusChanged.emit(True)

	def focusOutEvent(self, ev):
		SourceCodeEdit.focusOutEvent(self, ev)
		self.focusChanged.emit(False)

	__runStateToText = {
		RunState.STATE_OFFLINE		: "OFFLINE",
		RunState.STATE_ONLINE		: "Online (CPU stopped)",
		RunState.STATE_LOAD		: "DOWNLOADING program. Please wait.",
		RunState.STATE_EXCEPTION	: "ERROR. CPU halted.",
	}

	def __repaintHeaderWidget(self, ev):
		if not self.headerWidget:
			return
		p = self.headerWidget.getPainter()
		if not self.__sourceMatchesCpuSource and\
		   self.__runState.state == RunState.STATE_RUN:
			p.fillRect(ev.rect(), getErrorColor())
		else:
			p.fillRect(ev.rect(), Qt.lightGray)

		if self.__cpuStatsEnabled:
			# Map the CPU-stats start point to header widget
			# coordinates.
			cpuStatsPt = self.cpuStatsWidget.mapToGlobal(QPoint(0, 0))
			cpuStatsPt = self.headerWidget.mapFromGlobal(cpuStatsPt)

			textMaxPixels = cpuStatsPt.x()
		else:
			textMaxPixels = self.headerWidget.width()

		if self.__runState.spawned:
			runText = [ "[SIM]: ", ]
		else:
			runText = [ "[%s:%d%s]: " %(\
				self.__runState.host,
				self.__runState.port,
				" via SSH" if\
				self.__runState.haveTunnel else ""), ]
		if self.__runState.state == RunState.STATE_RUN:
			if self.__sourceMatchesCpuSource:
				runText.append(self.__runAni[self.__hdrAniStat])
			else:
				runText.append(self.__runAniNoDown[self.__hdrAniStat])
		else:
			runText.append(self.__runStateToText[self.__runState.state])

		# Limit the text length to the available space.
		metr = self.headerWidget.fontMetrics()
		maxNrChars = textMaxPixels // metr.width('_')
		runText = "".join(runText)
		if len(runText) > maxNrChars:
			runText = runText[ : max(0, maxNrChars - 3)]
			runText += "..."
			runText = runText[ : maxNrChars]

		p.drawText(5, 5,
			   metr.width(runText.replace(" ", "_")),
			   self.headerWidget.height(),
			   Qt.AlignLeft,
			   runText)

		if self.__cpuStatsEnabled:
			p.drawText(cpuStatsPt.x() + 5, 5,
				   self.headerWidget.width() - cpuStatsPt.x() - 5,
				   self.headerWidget.height(),
				   Qt.AlignLeft,
				   self.cpuStatsWidget.getBanner(self.__cpuStatsMask))

	def __repaintLineNumWidget(self, ev):
		p = self.lineNumWidget.getPainter()
		rect = ev.rect()
		p.fillRect(rect, Qt.lightGray)
		rect.setLeft(rect.left() + rect.width() - 3)
		rect.setWidth(3)
		p.fillRect(rect, Qt.white)
		p.setPen(Qt.black)

		for lineNr, yOffset in self.__eachVisibleLine():
			p.drawText(-5, yOffset,
				   self.lineNumWidget.width(),
				   self.__charHeight,
				   Qt.AlignRight,
				   str(lineNr))

	def __repaintCpuStatsWidget(self, ev):
		if not self.cpuStatsWidget:
			return
		p = self.cpuStatsWidget.getPainter()
		rect = ev.rect()
		p.fillRect(rect, Qt.lightGray)
		rect.setWidth(3)
		p.fillRect(rect, Qt.white)

		for lineNr, yOffset in self.__eachVisibleLine():
			statsEnt = self.__lineCpuStats.get(lineNr)
			if statsEnt:
				if statsEnt.obsolete:
					p.setPen(Qt.darkGray)
				else:
					p.setPen(Qt.black)
				p.drawText(5, yOffset,
					   self.cpuStatsWidget.width(),
					   self.__charHeight,
					   Qt.AlignLeft,
					   statsEnt.getText(self.__cpuStatsMask))

	def __textChanged(self):
		if self.__textChangeBlocked:
			return
		self.__needSourceUpdate = True
		self.codeChanged.emit()
		self.resetCpuStats()
		if self.__runState.state != RunState.STATE_RUN:
			# The CPU is not in RUN state.
			# We don't make a big deal out of code mismatch, even
			# if the code most likely _does_ mismatch after this edit.
			self.__setSourceMatchesCpuSource(True)

	def handleValidationResult(self, exception):
		if exception and exception.getSourceId() == self.getSourceId():
			lineNr = exception.getLineNr()
			if lineNr:
				self.setErraticLine(lineNr - 1, str(exception))
				return
		self.setErraticLine(None)

class EditDialog(QDialog):
	"""AWL/STL edit dialog."""

	def __init__(self, parent=None,
		     readOnly=False,
		     withHeader=True, withCpuStats=True,
		     okButton=False, cancelButton=False):
		QDialog.__init__(self, parent)
		self.setLayout(QGridLayout())

		self.edit = EditWidget(self, readOnly=readOnly,
				       withHeader=withHeader,
				       withCpuStats=withCpuStats)
		self.layout().addWidget(self.edit, 0, 0, 1, 2)

		if okButton:
			self.__okButton = QPushButton("&Ok", self)
			self.layout().addWidget(self.__okButton, 1, 0)
			self.__okButton.released.connect(self.accept)

		if cancelButton:
			self.__cancelButton = QPushButton("&Cancel", self)
			self.layout().addWidget(self.__cancelButton, 1, 1)
			self.__cancelButton.released.connect(self.reject)

		self.resize(1000, 550)

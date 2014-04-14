# -*- coding: utf-8 -*-
#
# AWL simulator - GUI edit widget
#
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
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
from awlsim.core.compat import *

from awlsim.gui.util import *
from awlsim.gui.cpuwidget import *


class EditSubWidget(QWidget):
	needRepaint = Signal(QPaintEvent)
	wasScrolled = Signal(QWheelEvent)

	def __init__(self, editWidget):
		QWidget.__init__(self, editWidget)
		self.editWidget = editWidget

	def paintEvent(self, ev):
		self.needRepaint.emit(ev)

	def wheelEvent(self, ev):
		self.wasScrolled.emit(ev)

	def getPainter(self):
		p = QPainter(self)
		font = p.font()
		font.setFamily("Mono")
		font.setKerning(False)
		font.setFixedPitch(True)
		font.setStyleStrategy(QFont.PreferBitmap)
		p.setFont(font)
		return p

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

	def getBanner(self):
		return "STW          ACCU 1    ACCU 2"

class CpuStatsEntry(object):
	def __init__(self, stamp, statusWord, accu1, accu2):
		self.stamp = stamp
		self.obsolete = False
		self.statusWord = statusWord.getWord()
		self.accu1 = accu1.getDWord()
		self.accu2 = accu2.getDWord()

	@staticmethod
	def getTextWidth():
		return 11 + 2 + 8 + 2 + 8

	def __repr__(self):
		stw = []
		for i in range(S7StatusWord.NR_BITS - 1, -1, -1):
			stw.append('1' if (self.statusWord & (1 << i)) else '0')
			if i % 4 == 0 and i:
				stw.append('_')
		return "%s  %08X  %08X" %\
			("".join(stw), self.accu1, self.accu2)

class EditWidget(QPlainTextEdit):
	codeChanged = Signal()

	__aniChars = ( ' ', '.', 'o', '0', 'O', '0', 'o', '.' )

	def __init__(self, mainWidget):
		QPlainTextEdit.__init__(self, mainWidget)
		self.mainWidget = mainWidget

		self.__updateFonts()

		self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.setLineWrapMode(QPlainTextEdit.NoWrap)
		self.setTabStopWidth(self.tabStopWidth() // 2)

		self.headerWidget = HeaderSubWidget(self)
		self.lineNumWidget = LineNumSubWidget(self)
		self.cpuStatsWidget = CpuStatsSubWidget(self)

		self.__runStateCopy = CpuWidget.STATE_STOP
		self.__nextHdrUpdate = 0
		self.__hdrAniStat = 0
		self.enableCpuStats(False)
		self.resetCpuStats(True)

		self.__textChangeBlocked = 0
		self.textChanged.connect(self.__textChanged)

		self.blockCountChanged.connect(self.__updateMargins)
		self.updateRequest.connect(self.__updateExtraWidgets)
		self.headerWidget.needRepaint.connect(self.__repaintHeaderWidget)
		self.lineNumWidget.needRepaint.connect(self.__repaintLineNumWidget)
		self.cpuStatsWidget.needRepaint.connect(self.__repaintCpuStatsWidget)
		self.headerWidget.wasScrolled.connect(self.__forwardWheelEvent)
		self.lineNumWidget.wasScrolled.connect(self.__forwardWheelEvent)
		self.cpuStatsWidget.wasScrolled.connect(self.__forwardWheelEvent)

	def runStateChanged(self, newState):
		self.__runStateCopy = newState
		if newState == CpuWidget.STATE_PARSE:
			self.resetCpuStats()
		if self.__cpuStatsEnabled:
			self.cpuStatsWidget.update()
		self.headerWidget.update()

	def __updateFonts(self):
		fmt = self.currentCharFormat()
		fmt.setFontFamily("Mono")
		fmt.setFontKerning(False)
		fmt.setFontFixedPitch(True)
		fmt.setFontStyleStrategy(QFont.PreferBitmap)
		self.setCurrentCharFormat(fmt)
		self.__charWidth = self.fontMetrics().width('X')
		self.__charHeight = self.fontMetrics().height()

	def enableCpuStats(self, enabled=True):
		self.__cpuStatsEnabled = enabled
		self.__updateMargins()
		self.__updateGeo()

	def resetCpuStats(self, force=False):
		if not force and not self.__lineCpuStats:
			return
		self.__lineCpuStats = { }
		self.__cpuStatsCount = 0
		self.__cpuStatsUpdate = 1
		self.__cpuStatsStamp = 0
		self.__updateMargins()
		self.headerWidget.update()
		self.cpuStatsWidget.update()

	def updateCpuStats_afterInsn(self, cpu):
		insn = cpu.getCurrentInsn()
		if not self.__cpuStatsEnabled or not insn:
			return
		self.__lineCpuStats[insn.getLineNr() - 1] =\
			CpuStatsEntry(self.__cpuStatsStamp,
				      cpu.getStatusWord(),
				      cpu.getAccu(1),
				      cpu.getAccu(2))
		self.__cpuStatsCount += 1

	def updateCpuStats_afterBlock(self, cpu):
		if cpu.now >= self.__nextHdrUpdate:
			self.__nextHdrUpdate = cpu.now + 0.2
			self.__hdrAniStat = (self.__hdrAniStat + 1) %\
					    len(self.__aniChars)
			self.headerWidget.update()
		if not self.__cpuStatsEnabled:
			return
		# Update the 'obsolete'-flag based on the timestamp
		for ent in self.__lineCpuStats.values():
			ent.obsolete = (ent.stamp != self.__cpuStatsStamp)
		# Update the stats widget
		if self.__cpuStatsCount >= self.__cpuStatsUpdate:
			self.__cpuStatsCount = 0
			self.__cpuStatsUpdate = 128
			self.cpuStatsWidget.update()

	def updateCpuStats_afterCycle(self, cpu):
		if self.__cpuStatsEnabled:
			self.__cpuStatsStamp += 1

	def __forwardWheelEvent(self, ev):
		self.wheelEvent(ev)

	def lineNumWidgetWidth(self):
		digi, bcnt = 1, self.blockCount()
		while bcnt > 9:
			digi, bcnt = digi + 1, bcnt // 10
		digi += 1 # colon
		return 5 + 5 + digi * self.__charWidth

	def cpuStatsWidgetWidth(self):
		if not self.__cpuStatsEnabled:
			return 0
		return 5 + 5 + CpuStatsEntry.getTextWidth() * self.__charWidth

	def headerHeight(self):
		return 5 + 5 + self.__charHeight

	def __updateMargins(self):
		self.setViewportMargins(self.lineNumWidgetWidth(),
					self.headerHeight(),
					self.cpuStatsWidgetWidth(),
					0)

	def sizeHint(self):
		sh = QPlainTextEdit.sizeHint(self)
		sh.setWidth(650 +\
			    self.lineNumWidgetWidth() +\
			    self.cpuStatsWidgetWidth())
		return sh

	def __updateHeaderWidgetGeo(self):
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
			self.headerWidget.scroll(0, dy)
			self.lineNumWidget.scroll(0, dy)
			self.cpuStatsWidget.scroll(0, dy)
			return
		self.headerWidget.update(0, rect.y(),
			self.headerWidget.width(),
			rect.height())
		self.lineNumWidget.update(0, rect.y(),
			self.lineNumWidget.width(),
			rect.height())
		self.cpuStatsWidget.update(0, rect.y(),
			self.cpuStatsWidget.width(),
			rect.height())
		if rect.contains(self.viewport().rect()):
			self.__updateMargins()

	def resizeEvent(self, ev):
		QPlainTextEdit.resizeEvent(self, ev)
		self.__updateGeo()

	def __repaintHeaderWidget(self, ev):
		p = self.headerWidget.getPainter()
		p.fillRect(ev.rect(), Qt.lightGray)

		if self.__runStateCopy == CpuWidget.STATE_RUN:
			runText = self.__aniChars[self.__hdrAniStat]
		else:
			runText = {
				CpuWidget.STATE_STOP:	"-- CPU STOPPED --",
				CpuWidget.STATE_PARSE:	"Parsing code...",
				CpuWidget.STATE_INIT:	"Initializing simulator...",
				CpuWidget.STATE_LOAD:	"Loading code...",
			}[self.__runStateCopy]
		p.drawText(5, 5,
			   self.__charWidth * len(runText) + 1,
			   self.headerWidget.height(),
			   Qt.AlignLeft,
			   runText)

		if self.__cpuStatsEnabled:
			# Map the starting point
			pt = self.cpuStatsWidget.mapToGlobal(QPoint(0, 0))
			pt = self.headerWidget.mapFromGlobal(pt)

			p.drawText(pt.x() + 5, 5,
				   self.headerWidget.width() - pt.x() - 5,
				   self.headerWidget.height(),
				   Qt.AlignLeft,
				   self.cpuStatsWidget.getBanner())

	def __repaintLineNumWidget(self, ev):
		p = self.lineNumWidget.getPainter()
		rect = ev.rect()
		p.fillRect(rect, Qt.lightGray)
		rect.setLeft(rect.left() + rect.width() - 3)
		rect.setWidth(3)
		p.fillRect(rect, Qt.white)
		p.setPen(Qt.black)

		block = self.firstVisibleBlock()
		bn = block.blockNumber()
		top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
		bottom = top + self.blockBoundingRect(block).height()

		while block.isValid() and top <= ev.rect().bottom():
			if block.isVisible() and bottom >= ev.rect().top():
				p.drawText(-5, top,
					   self.lineNumWidget.width(),
					   self.__charHeight,
					   Qt.AlignRight,
					   str(bn + 1) + ':')
			block = block.next()
			top = bottom
			bottom = top + self.blockBoundingRect(block).height()
			bn += 1

	def __repaintCpuStatsWidget(self, ev):
		p = self.cpuStatsWidget.getPainter()
		rect = ev.rect()
		p.fillRect(rect, Qt.lightGray)
		rect.setWidth(3)
		p.fillRect(rect, Qt.white)

		block = self.firstVisibleBlock()
		bn = block.blockNumber()
		top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
		bottom = top + self.blockBoundingRect(block).height()

		while block.isValid() and top <= ev.rect().bottom():
			statsEnt = self.__lineCpuStats.get(bn)
			if statsEnt and block.isVisible() and bottom >= ev.rect().top():
				if statsEnt.obsolete:
					p.setPen(Qt.darkGray)
				else:
					p.setPen(Qt.black)
				p.drawText(5, top,
					   self.cpuStatsWidget.width(),
					   self.__charHeight,
					   Qt.AlignLeft,
					   str(statsEnt))
			block = block.next()
			top = bottom
			bottom = top + self.blockBoundingRect(block).height()
			bn += 1

	def __textChanged(self):
		self.__updateFonts()
		if self.__textChangeBlocked:
			return
		self.codeChanged.emit()
		self.resetCpuStats()

	def loadCode(self, code):
		self.__textChangeBlocked += 1
		self.setPlainText(code)
		self.resetCpuStats()
		self.__textChangeBlocked -= 1

	def getCode(self):
		return self.toPlainText()

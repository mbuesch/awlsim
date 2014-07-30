# -*- coding: utf-8 -*-
#
# AWL simulator - GUI edit widget
#
# Copyright 2012-2014 Michael Buesch <m@bues.ch>
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


def _setFontParams(font):
	font.setFamily("courier")
	font.setPointSize(10)
	font.setKerning(False)
	font.setFixedPitch(True)
	font.setStyleHint(QFont.TypeWriter, QFont.PreferBitmap)

class EditSubWidget(QWidget):
	needRepaint = Signal(QPaintEvent)
	wasScrolled = Signal(QWheelEvent)

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
		font = p.font()
		_setFontParams(font)
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
		return "STW          ACCU 1    ACCU 2  "

class CpuStatsEntry(object):
	def __init__(self, stamp, statusWord, accu1, accu2):
		self.stamp = stamp
		self.obsolete = False
		self.pruned = False
		self.statusWord = statusWord
		self.accu1 = accu1
		self.accu2 = accu2

	def __repr__(self):
		if self.pruned:
			return "[ ... ]"
		stw = []
		for i in range(S7StatusWord.NR_BITS - 1, -1, -1):
			stw.append('1' if (self.statusWord & (1 << i)) else '0')
			if i % 4 == 0 and i:
				stw.append('_')
		return "%s  %08X  %08X" %\
			("".join(stw), self.accu1, self.accu2)

class EditWidget(QPlainTextEdit):
	codeChanged = Signal()
	visibleRangeChanged = Signal()

	__aniChars = ( ' ', '.', 'o', '0', 'O', '0', 'o', '.' )

	def __init__(self, mainWidget):
		QPlainTextEdit.__init__(self, mainWidget)
		self.mainWidget = mainWidget

		self.__aniTimer = QTimer(self)
		self.__aniTimer.setSingleShot(False)
		self.__aniTimer.timeout.connect(self.__animation)

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
		self.enableCpuStats(enabled=False, force=True)
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
		if newState == CpuWidget.STATE_INIT:
			self.resetCpuStats()
		if newState == CpuWidget.STATE_RUN:
			self.__aniTimer.start(200)
		else:
			self.__aniTimer.stop()
		if self.__cpuStatsEnabled:
			self.cpuStatsWidget.update()
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

	def __updateFonts(self):
		fmt = self.currentCharFormat()
		font = fmt.font()
		_setFontParams(font)
		fmt.setFont(font)
		self.setCurrentCharFormat(fmt)
		font = self.font()
		_setFontParams(font)
		self.setFont(font)
		self.__charHeight = self.fontMetrics().height()
		self.setTabStopWidth(self.fontMetrics().width("X") * 8)

	def enableCpuStats(self, enabled=True, force=False):
		if force or enabled != self.__cpuStatsEnabled:
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

	def updateCpuStats_afterInsn(self, insnDumpMsg):
		# insnDumpMsg => AwlSimMessage_INSNDUMP instance
		if not self.__cpuStatsEnabled:
			return
		# Save the instruction dump
		self.__lineCpuStats[insnDumpMsg.lineNr] =\
			CpuStatsEntry(self.__cpuStatsStamp,
				      insnDumpMsg.stw,
				      insnDumpMsg.accu1,
				      insnDumpMsg.accu2)
		# Update the stats widget
		self.__cpuStatsCount += 1
		if self.__cpuStatsCount >= self.__cpuStatsUpdate:
			self.__cpuStatsCount = 0
			self.__cpuStatsUpdate = 128
			self.cpuStatsWidget.update()

		# First instruction in cycle?
		if insnDumpMsg.serial == 0:
			# Update the 'obsolete'-flag based on the timestamp
			for ent in self.__lineCpuStats.values():
				ent.obsolete = (ent.stamp != self.__cpuStatsStamp)
			# Advance the timestamp
			self.__cpuStatsStamp += 1

	def __pruneInvisibleCpuStats(self):
		firstLine, lastLine = self.getVisibleLineRange()
		for line, stats in self.__lineCpuStats.items():
			if line < firstLine or line > lastLine:
				stats.pruned = True
				stats.obsolete = True

	def __animation(self):
		self.__hdrAniStat = (self.__hdrAniStat + 1) %\
				    len(self.__aniChars)
		self.headerWidget.update()

	def __forwardWheelEvent(self, ev):
		self.wheelEvent(ev)

	def lineNumWidgetWidth(self):
		digi, bcnt = 1, self.blockCount()
		while bcnt > 9:
			digi, bcnt = digi + 1, bcnt // 10
		digi += 1 # colon
		metr = self.lineNumWidget.fontMetrics()
		return 5 + 5 + metr.width("_" * digi)

	def cpuStatsWidgetWidth(self):
		if not self.__cpuStatsEnabled:
			return 0
		metr = self.cpuStatsWidget.fontMetrics()
		return 5 + 5 + metr.width(self.cpuStatsWidget.getBanner().replace(" ", "_"))

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
			self.__pruneInvisibleCpuStats()
			self.visibleRangeChanged.emit()
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

	__runStateToText = {
		CpuWidget.STATE_STOP	: "-- CPU STOPPED --",
		CpuWidget.STATE_INIT	: "Initializing simulator...",
		CpuWidget.STATE_LOAD	: "Loading code...",
	}

	def __repaintHeaderWidget(self, ev):
		p = self.headerWidget.getPainter()
		p.fillRect(ev.rect(), Qt.lightGray)

		if self.__runStateCopy == CpuWidget.STATE_RUN:
			runText = self.__aniChars[self.__hdrAniStat]
		else:
			runText = self.__runStateToText[self.__runStateCopy]
		metr = self.headerWidget.fontMetrics()
		p.drawText(5, 5,
			   metr.width(runText.replace(" ", "_")),
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

		for lineNr, yOffset in self.__eachVisibleLine():
			p.drawText(-5, yOffset,
				   self.lineNumWidget.width(),
				   self.__charHeight,
				   Qt.AlignRight,
				   "%d:" % lineNr)

	def __repaintCpuStatsWidget(self, ev):
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
					   str(statsEnt))

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

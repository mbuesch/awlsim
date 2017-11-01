# -*- coding: utf-8 -*-
#
# AWL simulator - Block interface table edit widget
#
# Copyright 2016 Michael Buesch <m@bues.ch>
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

from awlsim.common.blocker import *

from awlsim.gui.interfedit.interftabmodel import *


class AwlInterfaceView(QTableView):
	# Signal: Keyboard focus in/out event.
	focusChanged = Signal(bool)

	def __init__(self, parent=None):
		QTableView.__init__(self, parent)

		if isQt4:
			self.verticalHeader().setMovable(True)
		else:
			self.verticalHeader().setSectionsMovable(True)
		self.verticalHeader().setDefaultSectionSize(20)
		self.verticalHeader().sectionMoved.connect(self.__rowMoved)

		self.pressed.connect(self.__handleMousePress)

		self.setModel(AwlInterfaceModel())

	def isEmpty(self):
		model = self.model()
		return not model or model.isEmpty()

	def __rebuild(self):
		model = self.model()
		yscroll = self.verticalScrollBar().value()
		xscroll = self.horizontalScrollBar().value()
		self.setModel(None)
		self.setModel(model)
		self.verticalScrollBar().setValue(yscroll)
		self.horizontalScrollBar().setValue(xscroll)

	def __rowMoved(self, logicalIndex, oldVisualIndex, newVisualIndex):
		self.model().moveEntry(oldVisualIndex, newVisualIndex)
		self.__rebuild()

	def resizeEvent(self, ev):
		QTableView.resizeEvent(self, ev)

		model = self.model()
		if model:
			hdr = self.horizontalHeader()
			def setMinSize(idx, minSize):
				if hdr.sectionSize(idx) < minSize:
					hdr.resizeSection(idx, minSize)
			setMinSize(0, 150)
			setMinSize(1, 100)
			if model.haveInitValue:
				setMinSize(2, 160)
				setMinSize(3, 250)
			else:
				setMinSize(2, 250)

	def deleteRows(self, rows=None):
		if rows is None:
			rows = set()
			for index in self.selectedIndexes():
				rows.add(index.row())
		self.model().deleteRows(rows)

	def __handleMousePress(self, index):
		btns = QApplication.mouseButtons()
		if btns & Qt.RightButton:
			pass#TODO context menu

	def keyPressEvent(self, ev):
		QTableView.keyPressEvent(self, ev)

		if ev.key() == Qt.Key_Delete:
			self.deleteRows()

	def focusInEvent(self, ev):
		QTableView.focusInEvent(self, ev)
		self.focusChanged.emit(True)

	def focusOutEvent(self, ev):
		QTableView.focusOutEvent(self, ev)
		self.focusChanged.emit(False)

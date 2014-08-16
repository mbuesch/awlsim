# -*- coding: utf-8 -*-
#
# AWL simulator - GUI source tabs
#
# Copyright 2014 Michael Buesch <m@bues.ch>
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

from awlsim.gui.editwidget import *
from awlsim.gui.util import *


class SourceTabCorner(QWidget):
	# Signal: Add new source
	add = Signal()
	# Signal: Delete current source
	delete = Signal()
	# Signal: Edit current source parameters
	params = Signal()

	def __init__(self, itemName, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout())
		self.layout().setContentsMargins(QMargins(3, 0, 0, 0))

		self.itemName = itemName

		self.menu = QMenu(self)
		self.menu.addAction("&Add %s" % itemName, self.__add)
		self.menu.addAction("&Delete %s" % itemName, self.__delete)
		self.menu.addSeparator()
		self.menu.addAction("&Edit %s parameters..." % itemName, self.__params)

		self.menuButton = QPushButton("&Action", self)
		self.menuButton.setMenu(self.menu)
		self.layout().addWidget(self.menuButton, 0, 0)

	def __add(self):
		self.add.emit()

	def __delete(self):
		self.delete.emit()

	def __params(self):
		self.params.emit()

class SourceTabWidget(QTabWidget):
	"Abstract source tab-widget"

	# Signal: Emitted, if the source code changed.
	sourceChanged = Signal()

	def __init__(self, itemName, parent=None):
		QTabWidget.__init__(self, parent)
		self.itemName = itemName

		self.setMovable(True)
		self.actionButton = SourceTabCorner(itemName, self)
		self.actionButton.setEnabled(False)#XXX
		self.setCornerWidget(self.actionButton, Qt.TopRightCorner)

	def allTabWidgets(self):
		for i in range(self.count()):
			yield self.widget(i)

	def clear(self):
		for widget in self.allTabWidgets():
			widget.deleteLater()
		QTabWidget.clear(self)

	def updateRunState(self, newRunState):
		pass

	def getSources(self):
		return []

	def setSources(self, sources):
		raise NotImplementedError

class AwlSourceTabWidget(SourceTabWidget):
	"AWL source tab-widget"

	# Signal: The visible AWL line range changed
	#         Parameters are: source, visibleFromLine, visibleToLine
	visibleLinesChanged = Signal(AwlSource, int, int)

	def __init__(self, parent=None):
		SourceTabWidget.__init__(self, "source", parent)

		self.onlineDiagEnabled = False

		self.addEditWidget("AWL/STL")#XXX

		self.actionButton.add.connect(self.addNewEditWidget)
		self.actionButton.delete.connect(self.deleteCurrent)
		self.actionButton.params.connect(self.editParams)
		self.currentChanged.connect(self.__currentChanged)

	def __emitVisibleLinesSignal(self):
		editWidget = self.currentWidget()
		if editWidget:
			fromLine, toLine = editWidget.getVisibleLineRange()
			source = editWidget.getSource()
			self.visibleLinesChanged.emit(source, fromLine, toLine)
		else:
			self.visibleLinesChanged.emit(None, -1, -1)

	def __currentChanged(self, index):
		if self.onlineDiagEnabled:
			for editWidget in self.allTabWidgets():
				editWidget.enableCpuStats(False)
			if index >= 0:
				editWidget = self.widget(index)
				editWidget.enableCpuStats(True)
		self.__emitVisibleLinesSignal()

	def updateRunState(self, newRunState):
		for editWidget in self.allTabWidgets():
			editWidget.runStateChanged(newRunState)

	def handleOnlineDiagChange(self, enabled):
		self.onlineDiagEnabled = enabled
		editWidget = self.currentWidget()
		if editWidget:
			editWidget.enableCpuStats(enabled)
		self.__emitVisibleLinesSignal()

	def handleInsnDump(self, insnDumpMsg):
		editWidget = self.currentWidget()
		if editWidget:
			editWidget.updateCpuStats_afterInsn(insnDumpMsg)

	def getSources(self):
		"Returns a list of AwlSource()s"
		return [ edit.getSource() for edit in self.allTabWidgets() ]

	def setSources(self, awlSources):
		if not awlSources:
			return
		self.clear()
		for awlSource in awlSources:
			editWidget = self.addEditWidget(awlSource.name)
			editWidget.setSource(awlSource)

	def addNewEditWidget(self):
		return self.addEditWidget("Unnamed source")

	def addEditWidget(self, tabTitleText):
		editWidget = EditWidget(self)
		editWidget.codeChanged.connect(self.sourceChanged)
		editWidget.visibleRangeChanged.connect(self.__emitVisibleLinesSignal)
		self.addTab(editWidget, tabTitleText)
		self.sourceChanged.emit()
		return editWidget

	def deleteCurrent(self):
		index = self.currentIndex()
		if index >= 0 and self.count() > 1:
			self.removeTab(index)
			self.sourceChanged.emit()

	def editParams(self):
		pass#TODO
		self.sourceChanged.emit()

class SymSourceTabWidget(SourceTabWidget):
	"Symbol table source tab-widget"	

	def __init__(self, parent=None):
		SourceTabWidget.__init__(self, "symbol table", parent)

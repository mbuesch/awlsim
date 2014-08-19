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
from awlsim.gui.symtabwidget import *
from awlsim.gui.util import *


class ParamEditDialog(QDialog):
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)

class SourceTabCorner(QWidget):
	# Signal: Add new source
	add = Signal()
	# Signal: Delete current source
	delete = Signal()
	# Signal: Rename current source
	rename = Signal()
	# Signal: Edit current source parameters
	params = Signal()
	# Signal: Integrate source
	integrate = Signal()

	def __init__(self, itemName, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout())
		self.layout().setContentsMargins(QMargins(3, 0, 0, 0))

		self.itemName = itemName

		self.menu = QMenu(self)
		self.menu.addAction("&Add %s" % itemName, self.__add)
		self.menu.addAction("&Delete %s..." % itemName, self.__delete)
		self.menu.addAction("&Rename %s..." % itemName, self.__rename)
		self.menu.addSeparator()
#TODO		self.menu.addAction("&Edit %s parameters..." % itemName, self.__params)
		self.__integrateAction = self.menu.addAction("&Integrate %s into project..." % itemName,
							     self.__integrate)
		self.showIntegrateButton(False)

		self.menuButton = QPushButton("&" + itemName[0].upper() + itemName[1:], self)
		self.menuButton.setMenu(self.menu)
		self.layout().addWidget(self.menuButton, 0, 0)

	def __add(self):
		self.add.emit()

	def __delete(self):
		self.delete.emit()

	def __rename(self):
		self.rename.emit()

	def __params(self):
		self.params.emit()

	def __integrate(self):
		res = QMessageBox.question(self,
			"Integrate current %s" % self.itemName,
			"The current %s is stored in an external file.\n"
			"Do you want to integrate this file info "
			"the awlsim project file (.awlpro)?" %\
			self.itemName,
			QMessageBox.Yes, QMessageBox.No)
		if res == QMessageBox.Yes:
			self.integrate.emit()

	def showIntegrateButton(self, show=True):
		self.__integrateAction.setVisible(show)

class SourceTabWidget(QTabWidget):
	"Abstract source tab-widget"

	# Signal: Emitted, if the source code changed.
	sourceChanged = Signal()

	def __init__(self, itemName, parent=None):
		QTabWidget.__init__(self, parent)
		self.itemName = itemName

		self.setMovable(True)
		self.actionButton = SourceTabCorner(itemName, self)
		self.setCornerWidget(self.actionButton, Qt.TopRightCorner)

		self.actionButton.integrate.connect(self.integrateSource)
		self.currentChanged.connect(self.__currentChanged)
		self.tabBar().tabMoved.connect(self.__tabMoved)

	def __currentChanged(self, index):
		self.updateActionMenu()

	def __tabMoved(self, fromIdx, toIdx):
		self.sourceChanged.emit()

	def updateActionMenu(self):
		curWidget = self.currentWidget()
		showIntegrate = False
		if curWidget:
			showIntegrate = curWidget.getSourceRef().isFileBacked()
		self.actionButton.showIntegrateButton(showIntegrate)

	def updateTabTexts(self):
		for i in range(self.count()):
			self.setTabText(i, self.widget(i).getSourceRef().name)
		self.sourceChanged.emit()

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
		"Returns a list of sources"
		return [ w.getFullSource() for w in self.allTabWidgets() ]

	def setSources(self, sources):
		raise NotImplementedError

	def integrateSource(self):
		curWidget = self.currentWidget()
		if curWidget:
			curWidget.getSourceRef().forceNonFileBacked(self.actionButton.itemName)
			self.updateActionMenu()
			self.updateTabTexts()

class AwlSourceTabWidget(SourceTabWidget):
	"AWL source tab-widget"

	# Signal: The visible AWL line range changed
	#         Parameters are: source, visibleFromLine, visibleToLine
	visibleLinesChanged = Signal(AwlSource, int, int)

	def __init__(self, parent=None):
		SourceTabWidget.__init__(self, "source", parent)

		self.onlineDiagEnabled = False

		self.addEditWidget()

		self.actionButton.add.connect(self.addEditWidget)
		self.actionButton.delete.connect(self.deleteCurrent)
		self.actionButton.rename.connect(self.renameCurrent)
		self.actionButton.params.connect(self.editParams)
		self.currentChanged.connect(self.__currentChanged)

	def __emitVisibleLinesSignal(self):
		editWidget = self.currentWidget()
		if editWidget:
			fromLine, toLine = editWidget.getVisibleLineRange()
			source = editWidget.getSourceRef()
			self.visibleLinesChanged.emit(source, fromLine, toLine)
		else:
			self.visibleLinesChanged.emit(None, -1, -1)

	def __currentChanged(self, index):
		if self.onlineDiagEnabled:
			for editWidget in self.allTabWidgets():
				editWidget.enableCpuStats(False)
				editWidget.resetCpuStats()
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

	def setSources(self, awlSources):
		self.clear()
		if not awlSources:
			self.addEditWidget()
			return
		for awlSource in awlSources:
			index, editWidget = self.addEditWidget()
			self.setTabText(index, awlSource.name)
			editWidget.setSource(awlSource)
		self.updateActionMenu()
		self.setCurrentIndex(0)

	def addEditWidget(self):
		editWidget = EditWidget(self)
		editWidget.codeChanged.connect(self.sourceChanged)
		editWidget.visibleRangeChanged.connect(self.__emitVisibleLinesSignal)
		index = self.addTab(editWidget, editWidget.getSourceRef().name)
		self.setCurrentIndex(index)
		self.updateActionMenu()
		self.sourceChanged.emit()
		return index, editWidget

	def deleteCurrent(self):
		index = self.currentIndex()
		if index >= 0 and self.count() > 1:
			text = self.tabText(index)
			res = QMessageBox.question(self,
				"Delete %s" % text,
				"Delete source '%s'?" % text,
				QMessageBox.Yes, QMessageBox.No)
			if res == QMessageBox.Yes:
				self.removeTab(index)
				self.sourceChanged.emit()

	def renameCurrent(self):
		index = self.currentIndex()
		if index >= 0:
			text = self.tabText(index)
			newText, ok = QInputDialog.getText(self,
					"Rename %s" % text,
					"New name for current source:",
					QLineEdit.Normal,
					text)
			if ok and newText != text:
				editWidget = self.widget(index)
				source = editWidget.getSourceRef()
				source.name = newText
				self.updateTabTexts()

	def editParams(self):
		dlg = ParamEditDialog(self)
		if dlg.exec_() == dlg.Accepted:
			pass#TODO
			self.sourceChanged.emit()

	def pasteText(self, text):
		editWidget = self.currentWidget()
		if editWidget:
			editWidget.insertPlainText(text)

class SymSourceTabWidget(SourceTabWidget):
	"Symbol table source tab-widget"	

	def __init__(self, parent=None):
		SourceTabWidget.__init__(self, "symbol table", parent)

		self.addSymTable()

		self.actionButton.add.connect(self.addSymTable)
		self.actionButton.delete.connect(self.deleteCurrent)
		self.actionButton.rename.connect(self.renameCurrent)
		self.actionButton.params.connect(self.editParams)

	def setSources(self, symTabSources):
		self.clear()
		if not symTabSources:
			self.addSymTable()
			return
		for symTabSource in symTabSources:
			index, symTabView = self.addSymTable()
			self.setTabText(index, symTabSource.name)
			symTabView.model().setSource(symTabSource)
		self.updateActionMenu()
		self.setCurrentIndex(0)

	def addSymTable(self):
		symTabView = SymTabView(self)
		symTabView.setSymTab(SymbolTable())
		symTabView.model().sourceChanged.connect(self.sourceChanged)
		index = self.addTab(symTabView, symTabView.model().getSourceRef().name)
		self.setCurrentIndex(index)
		self.updateActionMenu()
		self.sourceChanged.emit()
		return index, symTabView

	def deleteCurrent(self):
		index = self.currentIndex()
		if index >= 0 and self.count() > 1:
			text = self.tabText(index)
			res = QMessageBox.question(self,
				"Delete %s" % text,
				"Delete symbol table '%s'?" % text,
				QMessageBox.Yes, QMessageBox.No)
			if res == QMessageBox.Yes:
				self.removeTab(index)
				self.sourceChanged.emit()

	def renameCurrent(self):
		index = self.currentIndex()
		if index >= 0:
			text = self.tabText(index)
			newText, ok = QInputDialog.getText(self,
					"Rename %s" % text,
					"New name for current symbol table:",
					QLineEdit.Normal,
					text)
			if ok and newText != text:
				symTabView = self.widget(index)
				source = symTabView.getSourceRef()
				source.name = newText
				self.updateTabTexts()

	def editParams(self):
		pass#TODO

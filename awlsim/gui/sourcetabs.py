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
from awlsim.common.compat import *

from awlsim.gui.editwidget import *
from awlsim.gui.symtabwidget import *
from awlsim.gui.util import *


class SourceTabContextMenu(QMenu):
	# Signal: Add new source
	add = Signal()
	# Signal: Delete current source
	delete = Signal()
	# Signal: Rename current source
	rename = Signal()
	# Signal: Integrate source
	integrate = Signal()
	# Signal: Import source
	import_ = Signal()
	# Signal: Export source
	export = Signal()

	def __init__(self, itemName, parent=None):
		QMenu.__init__(self, parent)

		self.itemName = itemName

		self.addAction("&Add %s" % itemName, self.__add)
		self.addAction("&Delete %s..." % itemName, self.__delete)
		self.addAction("&Rename %s..." % itemName, self.__rename)
		self.addSeparator()
		self.addAction("&Import %s..." % itemName, self.__import)
		self.addAction("&Export %s..." % itemName, self.__export)
		self.__integrateAction = self.addAction("&Integrate %s into project..." % itemName,
							self.__integrate)

		self.showIntegrateButton(False)

	def __add(self):
		self.add.emit()

	def __delete(self):
		self.delete.emit()

	def __rename(self):
		self.rename.emit()

	def __import(self):
		self.import_.emit()

	def __export(self):
		self.export.emit()

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

class SourceTabCorner(QWidget):
	def __init__(self, itemName, contextMenu, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout())
		self.layout().setContentsMargins(QMargins(3, 0, 0, 0))

		self.menuButton = QPushButton("&" + itemName[0].upper() + itemName[1:], self)
		self.menuButton.setMenu(contextMenu)
		self.layout().addWidget(self.menuButton, 0, 0)

class SourceTabWidget(QTabWidget):
	"Abstract source tab-widget"

	# Signal: Emitted, if the source code changed.
	sourceChanged = Signal()

	def __init__(self, itemName, parent=None):
		QTabWidget.__init__(self, parent)
		self.itemName = itemName

		self.contextMenu = SourceTabContextMenu(itemName, self)

		self.setMovable(True)
		self.actionButton = SourceTabCorner(itemName, self.contextMenu, self)
		self.setCornerWidget(self.actionButton, Qt.TopRightCorner)

		self.contextMenu.integrate.connect(self.integrateSource)
		self.currentChanged.connect(self.__currentChanged)
		self.tabBar().tabMoved.connect(self.__tabMoved)

	def reset(self):
		self.clear()

	def __currentChanged(self, index):
		self.updateActionMenu()

	def __tabMoved(self, fromIdx, toIdx):
		self.sourceChanged.emit()

	def updateActionMenu(self):
		curWidget = self.currentWidget()
		showIntegrate = False
		if curWidget:
			showIntegrate = curWidget.getSource().isFileBacked()
		self.contextMenu.showIntegrateButton(showIntegrate)

	def updateTabTexts(self):
		for i in range(self.count()):
			self.setTabText(i, self.widget(i).getSource().name)
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
		return [ w.getSource() for w in self.allTabWidgets() ]

	def setSources(self, sources):
		raise NotImplementedError

	def integrateSource(self):
		curWidget = self.currentWidget()
		if curWidget:
			curWidget.getSource().forceNonFileBacked(self.contextMenu.itemName)
			self.updateActionMenu()
			self.updateTabTexts()

	def contextMenuEvent(self, ev):
		QTabWidget.contextMenuEvent(self, ev)
		tabBar = self.tabBar()
		if tabBar.geometry().contains(tabBar.mapFrom(self, ev.pos())):
			# Tab context menu was requested.
			self.contextMenu.exec_(self.mapToGlobal(ev.pos()))

class AwlSourceTabWidget(SourceTabWidget):
	"AWL source tab-widget"

	# Signal: The visible AWL line range changed
	#         Parameters are: source, visibleFromLine, visibleToLine
	visibleLinesChanged = Signal(AwlSource, int, int)

	def __init__(self, parent=None):
		SourceTabWidget.__init__(self, "source", parent)

		self.reset()

		self.contextMenu.add.connect(self.addEditWidget)
		self.contextMenu.delete.connect(self.deleteCurrent)
		self.contextMenu.rename.connect(self.renameCurrent)
		self.contextMenu.export.connect(self.exportCurrent)
		self.contextMenu.import_.connect(self.importSource)
		self.currentChanged.connect(self.__currentChanged)

	def reset(self):
		SourceTabWidget.reset(self)
		self.onlineDiagEnabled = False
		self.addEditWidget()

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
		index = self.addTab(editWidget, editWidget.getSource().name)
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
				source = editWidget.getSource()
				source.name = newText
				self.updateTabTexts()

	def exportCurrent(self):
		editWidget = self.currentWidget()
		if not editWidget:
			return
		source = editWidget.getSource()
		if not source:
			return
		fn, fil = QFileDialog.getSaveFileName(self,
			"AWL/STL source export", "",
			"AWL/STL source file (*.awl)",
			"*.awl")
		if not fn:
			return
		if not fn.endswith(".awl"):
			fn += ".awl"
		try:
			awlFileWrite(fn, source.sourceBytes, encoding="binary")
		except AwlSimError as e:
			MessageBox.handleAwlSimError(self,
				"Failed to export source", e)

	def importSource(self):
		fn, fil = QFileDialog.getOpenFileName(self,
			"Import AWL/STL source", "",
			"AWL source (*.awl);;"
			"All files (*)")
		if not fn:
			return
		source = AwlSource.fromFile("Imported source",
					    fn)
		index, editWidget = self.addEditWidget()
		editWidget.setSource(source)
		self.updateTabTexts()
		self.setCurrentIndex(index)

	def pasteText(self, text):
		editWidget = self.currentWidget()
		if editWidget:
			editWidget.insertPlainText(text)

class SymSourceTabWidget(SourceTabWidget):
	"Symbol table source tab-widget"	

	def __init__(self, parent=None):
		SourceTabWidget.__init__(self, "symbol table", parent)

		self.reset()

		self.contextMenu.add.connect(self.addSymTable)
		self.contextMenu.delete.connect(self.deleteCurrent)
		self.contextMenu.rename.connect(self.renameCurrent)
		self.contextMenu.export.connect(self.exportCurrent)
		self.contextMenu.import_.connect(self.importSource)

	def reset(self):
		SourceTabWidget.reset(self)
		self.addSymTable()

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
		index = self.addTab(symTabView, symTabView.model().getSource().name)
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
				source = symTabView.getSource()
				source.name = newText
				self.updateTabTexts()

	def exportCurrent(self):
		symTabView = self.currentWidget()
		if not symTabView:
			return
		source = symTabView.getSource()
		if not source:
			return
		fn, fil = QFileDialog.getSaveFileName(self,
			"Symbol table export", "",
			"Symbol table file (*.asc)",
			"*.asc")
		if not fn:
			return
		if not fn.endswith(".asc"):
			fn += ".asc"
		try:
			awlFileWrite(fn, source.sourceBytes, encoding="binary")
		except AwlSimError as e:
			MessageBox.handleAwlSimError(self,
				"Failed to export symbol table", e)

	def importSource(self):
		fn, fil = QFileDialog.getOpenFileName(self,
			"Import symbol table", "",
			"Symbol table file (*.asc);;"
			"All files (*)")
		if not fn:
			return
		source = SymTabSource.fromFile("Imported symbol table",
					       fn)
		index, symTabView = self.addSymTable()
		symTabView.setSource(source)
		self.updateTabTexts()
		self.setCurrentIndex(index)

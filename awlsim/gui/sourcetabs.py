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
from awlsim.gui.finddialog import *
from awlsim.gui.util import *
from awlsim.gui.fup.fupwidget import *


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
	# Signal: Enable/disable source
	enableDisable = Signal()

	def __init__(self, itemName, parent=None):
		QMenu.__init__(self, parent)

		self.itemName = itemName

		self.addAction(getIcon("doc_new"), "&Add %s" % itemName, self.__add)
		self.addAction(getIcon("doc_close"), "&Delete %s..." % itemName, self.__delete)
		self.addAction(getIcon("doc_edit"), "&Rename %s..." % itemName, self.__rename)
		self.addSeparator()
		self.addAction(getIcon("doc_import"), "&Import %s..." % itemName, self.__import)
		self.addAction(getIcon("doc_export"), "&Export %s..." % itemName, self.__export)
		self.__integrateAction = self.addAction("&Integrate %s into project..." % itemName,
							self.__integrate)
		self.addSeparator()
		self.__enableAction = self.addAction("", self.__enableDisable)

		self.showIntegrateButton(False)
		self.showEnable(False)

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

	def __enableDisable(self):
		self.enableDisable.emit()

	def showIntegrateButton(self, show=True):
		self.__integrateAction.setVisible(show)

	def showEnable(self, enable=False):
		if enable:
			self.__enableAction.setText("Enable %s" % self.itemName)
		else:
			self.__enableAction.setText("Disable %s" % self.itemName)

class SourceTabCorner(QWidget):
	def __init__(self, itemName, contextMenu, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout())
		self.layout().setContentsMargins(QMargins(3, 0, 0, 0))

		self.menuButton = QPushButton("+/-", self)
		self.menuButton.setIcon(getIcon("tab_new"))
		self.menuButton.setMenu(contextMenu)
		self.layout().addWidget(self.menuButton, 0, 0)

class DummySourceWidget(QWidget):
	def getSource(self):
		return None

class SourceTabWidget(QTabWidget):
	"Abstract source tab-widget"

	# Signal: Emitted, if the source code changed.
	sourceChanged = Signal()
	# Signal: Keyboard focus in/out event.
	focusChanged = Signal(bool)
	# Signal: UndoAvailable state changed
	undoAvailableChanged = Signal(bool)
	# Signal: RedoAvailable state changed
	redoAvailableChanged = Signal(bool)
	# Signal: CopyAvailable state changed
	copyAvailableChanged = Signal(bool)
	# Signal: Change the font size.
	#         If the parameter is True, increase font size.
	resizeFont = Signal(bool)
	# Signal: Validation request.
	#	  A code validation should take place.
	#	  The parameter is the source editor.
	validateDocument = Signal(SourceCodeEdit)


	def __init__(self, itemName, parent, projectWidget):
		QTabWidget.__init__(self, parent)
		self.itemName = itemName
		self.projectWidget = projectWidget

		self.guiSettings = GuiSettings()

		self.contextMenu = SourceTabContextMenu(itemName, self)

		self.setMovable(True)
		self.actionButton = SourceTabCorner(itemName, self.contextMenu, self)
		self.setCornerWidget(self.actionButton, Qt.TopRightCorner)

		self.contextMenu.integrate.connect(self.integrateSource)
		self.contextMenu.enableDisable.connect(self.__toggleSourceEnable)
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
		showEnable = False
		if curWidget:
			source = curWidget.getSource()
			if source:
				showIntegrate = source.isFileBacked()
				showEnable = not source.enabled
		self.contextMenu.showIntegrateButton(showIntegrate)
		self.contextMenu.showEnable(showEnable)

	def updateTabTexts(self):
		for i in range(self.count()):
			text = ""
			source = self.widget(i).getSource()
			if source:
				text = source.name
				if not source.enabled:
					text += " (DISABLED)"
			self.setTabText(i, text)
		self.sourceChanged.emit()

	def allTabWidgets(self):
		for i in range(self.count()):
			yield self.widget(i)

	def removeDummyWidgets(self):
		for i in range(self.count() - 1, -1, -1):
			fupWidget = self.widget(i)
			if isinstance(fupWidget, DummySourceWidget):
				self.removeTab(i)

	def addDummyWidget(self):
		self.addTab(DummySourceWidget(), "")

	def updateRunState(self, runState):
		pass

	def handleValidationResult(self, exception):
		pass

	def getSources(self):
		"Returns a list of sources"
		return [ s for s in (w.getSource() for w in self.allTabWidgets())
		         if s ]

	def setSources(self, sources):
		raise NotImplementedError

	def getCurrentSource(self):
		"Returns the currently selected source, or None."
		curWidget = self.currentWidget()
		if curWidget:
			return curWidget.getSource()
		return None

	def setSettings(self, guiSettings):
		self.guiSettings = guiSettings

	def integrateSource(self):
		curWidget = self.currentWidget()
		if curWidget:
			source = curWidget.getSource()
			if source:
				source.forceNonFileBacked(self.contextMenu.itemName)
				self.updateActionMenu()
				self.updateTabTexts()

	def __toggleSourceEnable(self):
		curWidget = self.currentWidget()
		if curWidget:
			source = curWidget.getSource()
			if source:
				source.enabled = not source.enabled
				self.updateActionMenu()
				self.updateTabTexts()

	def contextMenuEvent(self, ev):
		QTabWidget.contextMenuEvent(self, ev)
		tabBar = self.tabBar()
		pos = tabBar.mapFrom(self, ev.pos())
		if tabBar.geometry().contains(pos):
			# Tab context menu was requested.
			index = tabBar.tabAt(pos)
			if index >= 0:
				tabBar.setCurrentIndex(index)
				self.contextMenu.exec_(self.mapToGlobal(ev.pos()))

	def undoIsAvailable(self):
		return False

	def undo(self):
		pass

	def redoIsAvailable(self):
		return False

	def redo(self):
		pass

	def copyIsAvailable(self):
		return False

	def clipboardCut(self):
		pass

	def clipboardCopy(self):
		pass

	def clipboardPaste(self):
		pass

	def findText(self):
		pass

	def findReplaceText(self):
		pass

	def handleIdentsMsg(self, identsMsg):
		pass

class AwlSourceTabWidget(SourceTabWidget):
	"AWL source tab-widget"

	# Signal: The visible AWL line range changed
	#         Parameters are: source, visibleFromLine, visibleToLine
	visibleLinesChanged = Signal(object, int, int)

	def __init__(self, parent, projectWidget):
		SourceTabWidget.__init__(self, "source", parent, projectWidget)

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
		index, editWidget = self.addEditWidget()
		source = editWidget.getSource()
		source.name = "Main source"
		self.updateTabTexts()

	def clear(self):
		for editWidget in self.allTabWidgets():
			editWidget.shutdown()
		SourceTabWidget.clear(self)

	def __emitVisibleLinesSignal(self):
		editWidget = self.currentWidget()
		if editWidget:
			fromLine, toLine = editWidget.getVisibleLineRange()
			source = editWidget.getSource()
			self.visibleLinesChanged.emit(source, fromLine, toLine)
		else:
			self.visibleLinesChanged.emit(None, -1, -1)

	# Handle a change in editor-code <-> cpu-code match.
	def __handleCodeMatchChange(self, editWidget, matchesCpu):
		index = self.indexOf(editWidget)
		if matchesCpu:
			self.setTabIcon(index, QIcon())
			self.setTabToolTip(index, "")
		else:
			self.setTabIcon(index, getIcon("warning"))
			self.setTabToolTip(index, "Warning:\n"
				"The code in the editor "
				"widget does not match the code on the CPU.\n"
				"Please re-download the code to the CPU.")

	def __currentChanged(self, index):
		if self.onlineDiagEnabled:
			for editWidget in self.allTabWidgets():
				editWidget.enableCpuStats(False)
				editWidget.resetCpuStats()
			if index >= 0:
				editWidget = self.widget(index)
				editWidget.enableCpuStats(True)
		self.__emitVisibleLinesSignal()
		# Update undo/redo/copy states
		editWidget = self.currentWidget()
		self.undoAvailableChanged.emit(editWidget.undoIsAvailable()
					       if editWidget else False)
		self.redoAvailableChanged.emit(editWidget.redoIsAvailable()
					       if editWidget else False)
		self.copyAvailableChanged.emit(editWidget.copyIsAvailable()
					       if editWidget else False)
		self.validateDocument.emit(editWidget)

	def updateRunState(self, runState):
		for editWidget in self.allTabWidgets():
			editWidget.runStateChanged(runState)

	def handleValidationResult(self, exception):
		for editWidget in self.allTabWidgets():
			editWidget.handleValidationResult(exception)

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
			editWidget.setSource(awlSource)
		self.updateActionMenu()
		self.setCurrentIndex(0)
		self.updateTabTexts()

	def setSettings(self, guiSettings):
		SourceTabWidget.setSettings(self, guiSettings)

		for editWidget in self.allTabWidgets():
			editWidget.setSettings(guiSettings)

	def addEditWidget(self):
		editWidget = EditWidget(self)
		editWidget.setSettings(self.guiSettings)
		editWidget.codeChanged.connect(self.sourceChanged)
		editWidget.focusChanged.connect(self.focusChanged)
		editWidget.visibleRangeChanged.connect(self.__emitVisibleLinesSignal)
		editWidget.cpuCodeMatchChanged.connect(self.__handleCodeMatchChange)
		editWidget.undoAvailable.connect(self.undoAvailableChanged)
		editWidget.redoAvailable.connect(self.redoAvailableChanged)
		editWidget.copyAvailable.connect(self.copyAvailableChanged)
		editWidget.resizeFont.connect(self.resizeFont)
		editWidget.validateDocument.connect(
			lambda editWidget: self.validateDocument.emit(editWidget))
		index = self.addTab(editWidget, editWidget.getSource().name)
		self.setCurrentIndex(index)
		self.updateActionMenu()
		self.sourceChanged.emit()
		return index, editWidget

	def deleteCurrent(self):
		index = self.currentIndex()
		if index >= 0 and self.count() > 1:
			editWidget = self.widget(index)
			source = editWidget.getSource()
			res = QMessageBox.question(self,
				"Delete %s" % source.name,
				"Delete source '%s'?" % source.name,
				QMessageBox.Yes, QMessageBox.No)
			if res == QMessageBox.Yes:
				editWidget.shutdown()
				self.removeTab(index)
				self.sourceChanged.emit()

	def renameCurrent(self):
		index = self.currentIndex()
		if index >= 0:
			editWidget = self.widget(index)
			source = editWidget.getSource()
			newText, ok = QInputDialog.getText(self,
					"Rename %s" % source.name,
					"New name for current source:",
					QLineEdit.Normal,
					source.name)
			if ok and newText != source.name:
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
			safeFileWrite(fn, source.compatSourceBytes)
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
		source = AwlSource.fromFile(name="Imported source",
					    filepath=fn,
					    compatReEncode=True)
		res = QMessageBox.question(self,
			"Integrate source into project?",
			"Do you want to integrate the source\n"
			"%s\n"
			"into the project file (.awlpro)?\n"
			"If you do not integrate the source, it "
			"will stay in the external file.\n\n"
			"It is highly recommended to say 'Yes'." %\
			fn,
			QMessageBox.Yes | QMessageBox.No,
			QMessageBox.Yes)
		if res == QMessageBox.Yes:
			source.forceNonFileBacked(source.name)
		index, editWidget = self.addEditWidget()
		editWidget.setSource(source)
		self.setCurrentIndex(index)
		self.updateTabTexts()
		self.updateActionMenu()

	def pasteText(self, text):
		editWidget = self.currentWidget()
		if editWidget:
			editWidget.pasteText(text)

	def undoIsAvailable(self):
		editWidget = self.currentWidget()
		if editWidget:
			return editWidget.undoIsAvailable()
		return False

	def undo(self):
		editWidget = self.currentWidget()
		if editWidget:
			editWidget.undo()

	def redo(self):
		editWidget = self.currentWidget()
		if editWidget:
			editWidget.redo()

	def redoIsAvailable(self):
		editWidget = self.currentWidget()
		if editWidget:
			return editWidget.redoIsAvailable()
		return False

	def copyIsAvailable(self):
		editWidget = self.currentWidget()
		if editWidget:
			return editWidget.copyIsAvailable()
		return False

	def clipboardCut(self):
		editWidget = self.currentWidget()
		if editWidget:
			editWidget.cut()

	def clipboardCopy(self):
		editWidget = self.currentWidget()
		if editWidget:
			editWidget.copy()

	def clipboardPaste(self):
		editWidget = self.currentWidget()
		if editWidget:
			editWidget.paste()

	def findText(self):
		editWidget = self.currentWidget()
		if editWidget:
			dlg = FindReplaceDialog(editWidget, False, editWidget)
			dlg.exec_()
			dlg.deleteLater()

	def findReplaceText(self):
		editWidget = self.currentWidget()
		if editWidget:
			dlg = FindReplaceDialog(editWidget, True, editWidget)
			dlg.exec_()
			dlg.deleteLater()

	def handleIdentsMsg(self, identsMsg):
		SourceTabWidget.handleIdentsMsg(self, identsMsg)
		for editWidget in self.allTabWidgets():
			editWidget.handleIdentsMsg(identsMsg)

class SymSourceTabWidget(SourceTabWidget):
	"Symbol table source tab-widget"	

	def __init__(self, parent, projectWidget):
		SourceTabWidget.__init__(self, "symbol table", parent, projectWidget)

		self.reset()

		self.contextMenu.add.connect(self.addSymTable)
		self.contextMenu.delete.connect(self.deleteCurrent)
		self.contextMenu.rename.connect(self.renameCurrent)
		self.contextMenu.export.connect(self.exportCurrent)
		self.contextMenu.import_.connect(self.importSource)

	def reset(self):
		SourceTabWidget.reset(self)
		index, symTabView = self.addSymTable()
		source = symTabView.getSource()
		source.name = "Main table"
		self.updateTabTexts()

	def setSources(self, symTabSources):
		self.clear()
		if not symTabSources:
			self.addSymTable()
			return
		for symTabSource in symTabSources:
			index, symTabView = self.addSymTable()
			symTabView.model().setSource(symTabSource)
		self.updateActionMenu()
		self.setCurrentIndex(0)
		self.updateTabTexts()

	def addSymTable(self):
		symTabView = SymTabView(self)
		symTabView.setSymTab(SymbolTable())
		symTabView.model().sourceChanged.connect(self.sourceChanged)
		symTabView.focusChanged.connect(self.focusChanged)
		index = self.addTab(symTabView, symTabView.model().getSource().name)
		self.setCurrentIndex(index)
		self.updateActionMenu()
		self.sourceChanged.emit()
		return index, symTabView

	def deleteCurrent(self):
		index = self.currentIndex()
		if index >= 0 and self.count() > 1:
			symTabView = self.widget(index)
			source = symTabView.getSource()
			res = QMessageBox.question(self,
				"Delete %s" % source.name,
				"Delete symbol table '%s'?" % source.name,
				QMessageBox.Yes, QMessageBox.No)
			if res == QMessageBox.Yes:
				self.removeTab(index)
				self.sourceChanged.emit()

	def renameCurrent(self):
		index = self.currentIndex()
		if index >= 0:
			symTabView = self.widget(index)
			source = symTabView.getSource()
			newText, ok = QInputDialog.getText(self,
					"Rename %s" % source.name,
					"New name for current symbol table:",
					QLineEdit.Normal,
					source.name)
			if ok and newText != source.name:
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
			safeFileWrite(fn, source.compatSourceBytes)
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
		source = SymTabSource.fromFile(name="Imported symbol table",
					       filepath=fn,
					       compatReEncode=True)
		res = QMessageBox.question(self,
			"Integrate symbol table into project?",
			"Do you want to integrate the symbol table\n"
			"%s\n"
			"into the project file (.awlpro)?\n"
			"If you do not integrate the symbol table, it "
			"will stay in the external file.\n\n"
			"It is highly recommended to say 'Yes'." %\
			fn,
			QMessageBox.Yes | QMessageBox.No,
			QMessageBox.Yes)
		if res == QMessageBox.Yes:
			source.forceNonFileBacked(source.name)
		index, symTabView = self.addSymTable()
		symTabView.setSource(source)
		self.setCurrentIndex(index)
		self.updateTabTexts()
		self.updateActionMenu()

	def handleIdentsMsg(self, identsMsg):
		pass#TODO

class FupTabWidget(SourceTabWidget):
	"FUP/FBD tab widget"

	def __init__(self, parent, projectWidget):
		SourceTabWidget.__init__(self, "FUP/FBD diagram", parent, projectWidget)

		self.reset()

		self.contextMenu.add.connect(self.addDiagram)
		self.contextMenu.delete.connect(self.deleteCurrent)
		self.contextMenu.rename.connect(self.renameCurrent)
		self.contextMenu.export.connect(self.exportCurrent)
		self.contextMenu.import_.connect(self.importSource)

	def reset(self):
		SourceTabWidget.reset(self)
		self.addDummyWidget()
		self.updateTabTexts()

	def setSources(self, fupSources):
		self.clear()
		if not fupSources:
			self.addDummyWidget()
			return
		for fupSource in fupSources:
			index, fupWidget = self.addDiagram()
			fupWidget.setSource(fupSource)
		self.updateActionMenu()
		self.setCurrentIndex(0)
		self.updateTabTexts()

	def addDiagram(self):
		fupWidget = FupWidget(self, projectWidget=self.projectWidget)
		fupWidget.diagramChanged.connect(self.sourceChanged)
		self.removeDummyWidgets()
		index = self.addTab(fupWidget, fupWidget.getSource().name)
		self.setCurrentIndex(index)
		self.updateActionMenu()
		self.sourceChanged.emit()
		return index, fupWidget

	def deleteCurrent(self):
		index = self.currentIndex()
		if index >= 0:
			fupWidget = self.widget(index)
			source = fupWidget.getSource()
			res = QMessageBox.question(self,
				"Delete %s" % source.name,
				"Delete FUP/FBD diagram '%s'?" % source.name,
				QMessageBox.Yes, QMessageBox.No)
			if res == QMessageBox.Yes:
				self.removeTab(index)
				self.sourceChanged.emit()
			if self.count() <= 0:
				self.addDummyWidget()

	def renameCurrent(self):
		index = self.currentIndex()
		if index >= 0:
			fupWidget = self.widget(index)
			source = fupWidget.getSource()
			if source:
				newText, ok = QInputDialog.getText(self,
						"Rename %s" % source.name,
						"New name for current FUP/FBD diagram:",
						QLineEdit.Normal,
						source.name)
				if ok and newText != source.name:
					source.name = newText
					self.updateTabTexts()

	def exportCurrent(self):
		fupWidget = self.currentWidget()
		if not fupWidget:
			return
		source = fupWidget.getSource()
		if not source:
			return
		fn, fil = QFileDialog.getSaveFileName(self,
			"FUP/FBD XML source export", "",
			"FUP/FBD XML source file (*.fupxml)",
			"*.fupxml")
		if not fn:
			return
		if not fn.endswith(".fupxml"):
			fn += ".fupxml"
		try:
			safeFileWrite(fn, source.sourceBytes)
		except AwlSimError as e:
			MessageBox.handleAwlSimError(self,
				"Failed to export source", e)

	def importSource(self):
		fn, fil = QFileDialog.getOpenFileName(self,
			"Import FUP/FBD XML source", "",
			"FUP/FBD XML source (*.fupxml);;"
			"All files (*)")
		if not fn:
			return
		source = FupSource.fromFile(name="Imported source",
					    filepath=fn)
		source.forceNonFileBacked(source.name)
		index, fupWidget = self.addDiagram()
		fupWidget.setSource(source)
		self.setCurrentIndex(index)
		self.updateTabTexts()
		self.updateActionMenu()

	def handleIdentsMsg(self, identsMsg):
		pass#TODO

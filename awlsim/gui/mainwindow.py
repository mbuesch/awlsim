# -*- coding: utf-8 -*-
#
# AWL simulator - GUI main window
#
# Copyright 2012-2018 Michael Buesch <m@bues.ch>
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

import sys
import os

from awlsim.gui.util import *
from awlsim.gui.editmdiarea import *
from awlsim.gui.projecttreewidget import *
from awlsim.gui.cpuwidget import *
from awlsim.gui.guiconfig import *
from awlsim.gui.cpuconfig import *
from awlsim.gui.linkconfig import *
from awlsim.gui.hwmodconfig import *
from awlsim.gui.icons import *
from awlsim.gui.templatedialog import *
from awlsim.gui.library import *


class CpuDockWidget(QDockWidget):
	def __init__(self, mainWidget, parent=None):
		QDockWidget.__init__(self, "", parent)
		self.mainWidget = mainWidget

		self.setFeatures(QDockWidget.DockWidgetMovable |
				 QDockWidget.DockWidgetFloatable)
		self.setAllowedAreas(Qt.AllDockWidgetAreas)

		self.setWidget(CpuWidget(mainWidget))

		self.topLevelChanged.connect(self.__handleTopLevelChange)
		self.__handleTopLevelChange(self.isFloating())

	@property
	def cpuWidget(self):
		return self.widget()

	def __handleTopLevelChange(self, floating):
		if floating:
			self.setWindowTitle("%s - CPU view" %\
				self.mainWidget.mainWindow.TITLE)
		else:
			self.setWindowTitle("")

class ProjectTreeDockWidget(QDockWidget):
	def __init__(self, mainWidget, parent=None):
		QDockWidget.__init__(self, "", parent)
		self.mainWidget = mainWidget

		self.setFeatures(QDockWidget.DockWidgetMovable |
				 QDockWidget.DockWidgetFloatable)
		self.setAllowedAreas(Qt.AllDockWidgetAreas)

		self.projectTreeModel = ProjectTreeModel(mainWidget=mainWidget)
		self.projectTreeView = ProjectTreeView(model=self.projectTreeModel,
						       parent=self)
		self.setWidget(self.projectTreeView)

		self.topLevelChanged.connect(self.__handleTopLevelChange)
		self.__handleTopLevelChange(self.isFloating())

	def __handleTopLevelChange(self, floating):
		if floating:
			self.setWindowTitle("%s - Project view" %\
				self.mainWidget.mainWindow.TITLE)
		else:
			self.setWindowTitle("")

class MainWidget(QWidget):
	# Signal: Project loaded
	projectLoaded = Signal(Project)
	# Signal: Dirty-status changed
	dirtyChanged = Signal(bool)
	# Signal: Source text focus changed
	textFocusChanged = Signal(bool)
	# Signal: UndoAvailable state changed
	undoAvailableChanged = Signal(bool)
	# Signal: RedoAvailable state changed
	redoAvailableChanged = Signal(bool)
	# Signal: CopyAvailable state changed
	copyAvailableChanged = Signal(bool)
	# Signal: CutAvailable state changed
	cutAvailableChanged = Signal(bool)
	# Signal: PasteAvailable state changed
	pasteAvailableChanged = Signal(bool)

	def __init__(self, mainWindow, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout(self))
		self.mainWindow = mainWindow

		self.simClient = GuiAwlSimClient()

		self.editMdiArea = EditMdiArea(self)
		self.layout().addWidget(self.editMdiArea, 0, 0)

		self.filename = None
		self.dirty = False

		self.editMdiArea.sourceChanged.connect(self.somethingChanged)
		self.editMdiArea.focusChanged.connect(self.textFocusChanged)
		self.editMdiArea.undoAvailableChanged.connect(self.undoAvailableChanged)
		self.editMdiArea.redoAvailableChanged.connect(self.redoAvailableChanged)
		self.editMdiArea.copyAvailableChanged.connect(self.copyAvailableChanged)
		self.editMdiArea.cutAvailableChanged.connect(self.cutAvailableChanged)
		self.editMdiArea.pasteAvailableChanged.connect(self.pasteAvailableChanged)

	@property
	def projectTreeModel(self):
		return self.mainWindow.projectTreeModel

	def getProject(self):
		return self.projectTreeModel.getProject()

	def isDirty(self):
		return self.dirty

	def setDirty(self, dirty, force=False):
		if dirty != self.dirty or force:
			self.dirty = dirty
			self.dirtyChanged.emit(self.dirty)

	def somethingChanged(self):
		self.setDirty(True)

	def getFilename(self):
		return self.filename

	def getSimClient(self):
		return self.simClient

	def getCpuWidget(self):
		return self.mainWindow.cpuWidget

	def newFile(self, filename=None):
		if isWinStandalone:
			executableName = "awlsim-gui.exe"
		else:
			executableName = sys.executable
		executable = findExecutable(executableName)
		if not executable:
			QMessageBox.critical(self,
				"Failed to find '%s'" % executableName,
				"Could not spawn a new instance.\n"
				"Failed to find '%s'" % executableName)
			return
		if isWinStandalone:
			argv = [ executable, ]
		else:
			argv = [ executable, "-m", "awlsim.gui.startup", ]
		if filename:
			argv.append(filename)
		try:
			PopenWrapper(argv, env=AwlSimEnv.getEnv())
		except OSError as e:
			QMessageBox.critical(self,
				"Failed to execute '%s'" % executableName,
				"Could not spawn a new instance.\n%s"
				"Failed to execute '%s'" % (
				str(e), executableName))
			return

	def loadFile(self, filename, newIfNotExist=False):
		if self.dirty:
			res = QMessageBox.question(self,
				"Unsaved project",
				"The current project is modified and contains unsaved changes.\n "
				"Do you want to:\n"
				"- Save the project, close it and open the new project\n"
				"- Open the new project in a new instance or\n"
				"- Discard the changes and open the new project\n"
				"- Cancel the operation",
				QMessageBox.Save | QMessageBox.Discard |\
				QMessageBox.Open | QMessageBox.Cancel,
				QMessageBox.Open)
			if res == QMessageBox.Save:
				if not self.save():
					return
			elif res == QMessageBox.Discard:
				pass
			elif res == QMessageBox.Open:
				self.newFile(filename)
				return
			elif res == QMessageBox.Cancel:
				return
			else:
				assert(0)
		self.getCpuWidget().goOffline()
		if not fileExists(filename) and newIfNotExist:
			# The file does not exist. We implicitly create it.
			# The actual file will be created when the project is saved.
			isNewProject = True
			self.editMdiArea.resetArea()
			self.projectTreeModel.reset()
		else:
			isNewProject = False
			try:
				self.projectTreeModel.loadProjectFile(filename, self)
			except AwlSimError as e:
				QMessageBox.critical(self,
					"Failed to load project file", str(e))
				return False
		self.filename = filename
		if isNewProject or not self.getProject().getProjectFile():
			self.setDirty(True, force=True)
		else:
			self.setDirty(False, force=True)
		self.projectLoaded.emit(self.getProject())
		return True

	def load(self):
		if isPyQt and isQt4:
			getOpenFileName = QFileDialog.getOpenFileNameAndFilter
		else:
			getOpenFileName = QFileDialog.getOpenFileName
		fn, fil = getOpenFileName(self,
			"Open project", "",
			"Awlsim project or AWL/STL source (*.awlpro *.awl);;"
			"Awlsim project (*.awlpro);;"
			"AWL source (*.awl);;"
			"All files (*)")
		if not fn:
			return
		self.loadFile(fn, newIfNotExist=False)

	def saveFile(self, filename):
		try:
			res = self.projectTreeModel.saveProjectFile(filename, self)
			if res == 0: # Failure
				return False
			elif res < 0: # Force save-as
				return self.save(newFile=True)
		except AwlSimError as e:
			QMessageBox.critical(self,
				"Failed to write project file", str(e))
			return False
		self.filename = filename
		self.setDirty(dirty = False, force = True)
		return True

	def save(self, newFile=False):
		if newFile or not self.filename:
			if isPyQt and isQt4:
				getSaveFileName = QFileDialog.getSaveFileNameAndFilter
			else:
				getSaveFileName = QFileDialog.getSaveFileName
			fn, fil = getSaveFileName(self,
				"Awlsim project save as", "",
				"Awlsim project (*.awlpro)",
				"*.awlpro")
			if not fn:
				return
			if not fn.endswith(".awlpro"):
				fn += ".awlpro"
			return self.saveFile(fn)
		else:
			return self.saveFile(self.filename)

	def guiConfig(self):
		dlg = GuiConfigDialog(self.getProject(), self)
		dlg.settingsChanged.connect(self.somethingChanged)
		if dlg.exec_() == dlg.Accepted:
			self.editMdiArea.setGuiSettings(self.getProject().getGuiSettings())

	def linkConfig(self):
		dlg = LinkConfigDialog(self.getProject(), self)
		dlg.settingsChanged.connect(self.somethingChanged)
		dlg.exec_()

	def cpuConfig(self):
		dlg = CpuConfigDialog(self.getProject(), self)
		dlg.settingsChanged.connect(self.somethingChanged)
		dlg.exec_()

	def hwmodConfig(self):
		dlg = HwmodConfigDialog(self.getProject(), self)
		dlg.settingsChanged.connect(self.somethingChanged)
		dlg.exec_()

	def __pasteAwlText(self, text):
		if not self.editMdiArea.paste(text):
			QMessageBox.information(self,
				"Please select AWL/STL source",
				"Can not paste text.\n\n"
				"Please move the text cursor to the place "
				"in the AWL/STL code where you want to paste to.")
			return False
		return True

	def __pasteSymbol(self, symbolName, address, dataType, comment):
		"""Paste a symbol into one of the available symbol tables.
		symbolName: Symbol name string.
		address: Symbol address string.
		dataType: Symbol type string.
		comment: Symbol comment string.
		Returns True, if the symbol has successfully been added.
		"""

		# Parse the symbol.
		try:
			project = self.getProject()
			p = SymTabParser(project.getCpuConf().getConfiguredMnemonics())
			symbol = p.parseSym(symbolName, address,
					    dataType, comment, 0)
		except AwlSimError as e:
			MessageBox.handleAwlSimError(self,
				"Library symbol error", e)
			return False

		# Try to add the symbol to a symbol table
		return self.projectTreeModel.symbolAdd(symbol, parentWidget=self)

	def __pasteLibSel(self, libSelection):
		"""Paste a library selection into the library selection table.
		libSelection: The AwlLibEntrySelection() instance.
		Returns True, if the selection has successfully been added.
		"""
		assert(isinstance(libSelection, AwlLibEntrySelection))
		return self.projectTreeModel.libSelectionAdd(libSelection,
							     parentWidget=self)

	def insertOB(self):
		dlg = TemplateDialog.make_OB(self)
		if dlg.exec_() == QDialog.Accepted:
			self.__pasteAwlText(Templates.getOB(dlg.getBlockNumber(),
							    dlg.getVerbose()))

	def insertFC(self):
		dlg = TemplateDialog.make_FC(self)
		if dlg.exec_() == QDialog.Accepted:
			self.__pasteAwlText(Templates.getFC(dlg.getBlockNumber(),
							    dlg.getVerbose()))

	def insertFB(self):
		dlg = TemplateDialog.make_FB(self)
		if dlg.exec_() == QDialog.Accepted:
			self.__pasteAwlText(Templates.getFB(dlg.getBlockNumber(),
							    dlg.getVerbose()))

	def insertInstanceDB(self):
		dlg = TemplateDialog.make_instanceDB(self)
		if dlg.exec_() == QDialog.Accepted:
			self.__pasteAwlText(Templates.getInstanceDB(dlg.getBlockNumber(),
								    dlg.getExtraNumber(),
								    dlg.getVerbose()))

	def insertGlobalDB(self):
		dlg = TemplateDialog.make_globalDB(self)
		if dlg.exec_() == QDialog.Accepted:
			self.__pasteAwlText(Templates.getGlobalDB(dlg.getBlockNumber(),
								  dlg.getVerbose()))

	def insertUDT(self):
		dlg = TemplateDialog.make_UDT(self)
		if dlg.exec_() == QDialog.Accepted:
			self.__pasteAwlText(Templates.getUDT(dlg.getBlockNumber(),
							     dlg.getVerbose()))

	def insertFCcall(self):
		dlg = TemplateDialog.make_FCcall(self)
		if dlg.exec_() == QDialog.Accepted:
			self.__pasteAwlText(Templates.getFCcall(dlg.getBlockNumber(),
								dlg.getVerbose()))

	def insertFBcall(self):
		dlg = TemplateDialog.make_FBcall(self)
		if dlg.exec_() == QDialog.Accepted:
			self.__pasteAwlText(Templates.getFBcall(dlg.getBlockNumber(),
								dlg.getExtraNumber(),
								dlg.getVerbose()))

	def openLibrary(self):
		dlg = LibraryDialog(self.getProject(), self)
		if dlg.exec_() == QDialog.Accepted:
			if dlg.pasteText:
				# Paste the code.
				if not self.__pasteAwlText(dlg.pasteText):
					return
			if dlg.pasteSymbol:
				# Add a symbol to a symbol table.
				symbolName, address, dataType, comment = dlg.pasteSymbol
				if not self.__pasteSymbol(symbolName, address,
						          dataType, comment):
					return
			if dlg.pasteLibSel:
				# Add a library selection to the library table.
				if not self.__pasteLibSel(dlg.pasteLibSel):
					return

	def undo(self):
		self.editMdiArea.undo()

	def redo(self):
		self.editMdiArea.redo()

	def cut(self):
		self.editMdiArea.cut()

	def copy(self):
		self.editMdiArea.copy()

	def paste(self):
		self.editMdiArea.paste()

	def findText(self):
		self.editMdiArea.findText()

	def findReplaceText(self):
		self.editMdiArea.findReplaceText()

class MainWindow(QMainWindow):
	TITLE = "AWL/STL soft-PLC v%s" % VERSION_STRING

	@classmethod
	def start(cls,
		  initialAwlSource = None):
		# Set basic qapp-details.
		# This is important for QSettings.
		QApplication.setOrganizationName("awlsim")
		QApplication.setApplicationName("Awlsim GUI")
		QApplication.setApplicationVersion(VERSION_STRING)

		mainwnd = cls(initialAwlSource)
		mainwnd.show()
		return mainwnd

	def __init__(self, awlSource=None, parent=None):
		QMainWindow.__init__(self, parent)
		self.setWindowIcon(getIcon("cpu"))

		self.mainWidget = MainWidget(self, self)
		self.cpuDockWidget = CpuDockWidget(self.mainWidget, self)
		self.treeDockWidget = ProjectTreeDockWidget(self.mainWidget, self)

		self.setCentralWidget(self.mainWidget)
		self.addDockWidget(Qt.LeftDockWidgetArea, self.treeDockWidget)
		self.addDockWidget(Qt.RightDockWidgetArea, self.cpuDockWidget)

		self.tb = QToolBar(self)
		self.tb.addAction(getIcon("new"), "New project",
				  self.mainWidget.newFile)
		self.tb.addAction(getIcon("open"), "Open project",
				  self.mainWidget.load)
		self.tbSaveAct = self.tb.addAction(getIcon("save"), "Save project",
						   self.mainWidget.save)
		self.tb.addSeparator()
		self.tbUndoAct = self.tb.addAction(getIcon("undo"), "Undo last edit",
						   self.mainWidget.undo)
		self.tbRedoAct = self.tb.addAction(getIcon("redo"), "Redo",
						   self.mainWidget.redo)
		self.tb.addSeparator()
		self.tbCutAct = self.tb.addAction(getIcon("cut"), "Cut",
						  self.mainWidget.cut)
		self.tbCopyAct = self.tb.addAction(getIcon("copy"), "Copy",
						   self.mainWidget.copy)
		self.tbPasteAct = self.tb.addAction(getIcon("paste"), "Paste",
						    self.mainWidget.paste)
		self.tb.addSeparator()
		self.tbFindAct = self.tb.addAction(getIcon("find"), "Find...",
						   self.mainWidget.findText)
		self.tbFindReplaceAct = self.tb.addAction(getIcon("findreplace"),
							  "Find and replace...",
							  self.mainWidget.findReplaceText)
		self.tb.addSeparator()
		self.tbLibAct = self.tb.addAction(getIcon("stdlib"), "Standard library",
						  self.mainWidget.openLibrary)
		self.tbLibAct.setToolTip("Standard library.\n"
					 "(Please click into the AWL/STL source code\n"
					 "at the place where to paste the library call)")
		self.addToolBar(Qt.TopToolBarArea, self.tb)

		self.ctrlTb = CpuControlToolBar(self)
		self.addToolBar(Qt.TopToolBarArea, self.ctrlTb)

		self.inspectTb = CpuInspectToolBar(self)
		self.addToolBar(Qt.RightToolBarArea, self.inspectTb)

		self.setMenuBar(QMenuBar(self))

		menu = QMenu("&File", self)
		menu.addAction(getIcon("new"), "&New project",
			       self.mainWidget.newFile)
		menu.addAction(getIcon("open"), "&Open project...",
			       self.mainWidget.load)
		self.saveAct = menu.addAction(getIcon("save"), "&Save project",
					      self.mainWidget.save)
		menu.addAction(getIcon("save"), "&Save project as...",
			       lambda: self.mainWidget.save(True))
		menu.addSeparator()
		menu.addAction(getIcon("exit"), "&Exit...", self.close)
		self.menuBar().addMenu(menu)

		menu = QMenu("&Edit", self)
		self.undoAct = menu.addAction(getIcon("undo"), "&Undo",
					      self.mainWidget.undo)
		self.redoAct = menu.addAction(getIcon("redo"), "&Redo",
					      self.mainWidget.redo)
		menu.addSeparator()
		self.cutAct = menu.addAction(getIcon("cut"), "&Cut",
					     self.mainWidget.cut)
		self.copyAct = menu.addAction(getIcon("copy"), "&Copy",
					      self.mainWidget.copy)
		self.pasteAct = menu.addAction(getIcon("paste"), "&Paste",
					       self.mainWidget.paste)
		menu.addSeparator()
		self.findAct = menu.addAction(getIcon("find"), "&Find...",
					      self.mainWidget.findText)
		self.findReplaceAct = menu.addAction(getIcon("findreplace"),
						     "Find and r&eplace...",
						     self.mainWidget.findReplaceText)
		self.menuBar().addMenu(menu)

		menu = QMenu("&Library", self)
		menu.addAction(getIcon("textsource"), "Insert &OB template...",
			       self.mainWidget.insertOB)
		menu.addAction(getIcon("textsource"), "Insert F&C template...",
			       self.mainWidget.insertFC)
		menu.addAction(getIcon("textsource"), "Insert F&B template...",
			       self.mainWidget.insertFB)
		menu.addAction(getIcon("textsource"), "Insert &instance-DB template...",
			       self.mainWidget.insertInstanceDB)
		menu.addAction(getIcon("textsource"), "Insert &DB template...",
			       self.mainWidget.insertGlobalDB)
		menu.addAction(getIcon("textsource"), "Insert &UDT template...",
			       self.mainWidget.insertUDT)
		menu.addSeparator()
		menu.addAction(getIcon("textsource"), "Insert FC C&ALL template...",
			       self.mainWidget.insertFCcall)
		menu.addAction(getIcon("textsource"), "Insert FB CA&LL template...",
			       self.mainWidget.insertFBcall)
		menu.addSeparator()
		self.libAct = menu.addAction(getIcon("stdlib"), "&Standard library...",
					     self.mainWidget.openLibrary)
		self.menuBar().addMenu(menu)

		menu = QMenu("&Settings", self)
		menu.addAction(getIcon("network"), "&Server connection...",
			       self.mainWidget.linkConfig)
		menu.addAction(getIcon("cpu"), "&CPU config...",
			       self.mainWidget.cpuConfig)
		menu.addAction(getIcon("hwmod"), "&Hardware modules...",
			       self.mainWidget.hwmodConfig)
		menu.addAction(getIcon("prefs"), "&User interface...",
			       self.mainWidget.guiConfig)
		self.menuBar().addMenu(menu)

		menu = QMenu("&CPU", self)
		menu.addAction(self.ctrlTb.onlineAction)
		menu.addAction(self.ctrlTb.resetAction)
		menu.addAction(self.ctrlTb.downloadAction)
		menu.addAction(self.ctrlTb.downloadSingleAction)
		menu.addAction(self.ctrlTb.runAction)
		menu.addAction(self.ctrlTb.diagAction)
		menu.addSeparator()
		menu.addAction(self.inspectTb.blocksAction)
		menu.addAction(self.inspectTb.inputsAction)
		menu.addAction(self.inspectTb.outputsAction)
		menu.addAction(self.inspectTb.flagsAction)
		menu.addAction(self.inspectTb.dbAction)
		menu.addAction(self.inspectTb.timerAction)
		menu.addAction(self.inspectTb.counterAction)
		menu.addAction(self.inspectTb.cpuAction)
		menu.addAction(self.inspectTb.lcdAction)
		self.menuBar().addMenu(menu)

		menu = QMenu("&Help", self)
		menu.addAction(getIcon("browser"), "Awlsim &homepage...", self.awlsimHomepage)
		menu.addSeparator()
		menu.addAction(getIcon("cpu"), "&About...", self.about)
		self.menuBar().addMenu(menu)

		self.__sourceTextHasFocus = False
		self.__dirtyChanged(False)
		self.__textFocusChanged(False)
		self.__undoAvailableChanged(False)
		self.__redoAvailableChanged(False)
		self.__copyAvailableChanged(False)
		self.__cutAvailableChanged(False)
		self.__pasteAvailableChanged(False)

		self.mainWidget.projectLoaded.connect(self.__handleProjectLoaded)
		self.mainWidget.dirtyChanged.connect(self.__dirtyChanged)
		self.mainWidget.textFocusChanged.connect(self.__textFocusChanged)
		self.mainWidget.undoAvailableChanged.connect(self.__undoAvailableChanged)
		self.mainWidget.redoAvailableChanged.connect(self.__redoAvailableChanged)
		self.mainWidget.copyAvailableChanged.connect(self.__copyAvailableChanged)
		self.mainWidget.cutAvailableChanged.connect(self.__cutAvailableChanged)
		self.mainWidget.pasteAvailableChanged.connect(self.__pasteAvailableChanged)
		self.ctrlTb.connectToCpuWidget(self.cpuWidget)
		self.inspectTb.connectToCpuWidget(self.cpuWidget)
		self.mainWidget.dirtyChanged.connect(self.cpuWidget.handleDirtyChange)
		self.editMdiArea.visibleLinesChanged.connect(self.cpuWidget.updateVisibleLineRange)
		self.cpuWidget.onlineDiagChanged.connect(self.editMdiArea.enableOnlineDiag)
		self.cpuWidget.haveInsnDump.connect(self.editMdiArea.handleInsnDump)
		self.cpuWidget.haveIdentsMsg.connect(self.editMdiArea.handleIdentsMsg)
		self.cpuWidget.haveIdentsMsg.connect(self.projectTreeModel.handleIdentsMsg)
		self.cpuWidget.runStateChanged.connect(self.editMdiArea.setCpuRunState)
		self.cpuWidget.runStateChanged.connect(self.projectTreeModel.setCpuRunState)
		self.cpuWidget.configChanged.connect(self.mainWidget.somethingChanged)
		self.projectTreeModel.projectContentChanged.connect(self.mainWidget.somethingChanged)

		if awlSource:
			self.mainWidget.loadFile(awlSource, newIfNotExist=True)

	@property
	def editMdiArea(self):
		return self.mainWidget.editMdiArea

	@property
	def projectTreeModel(self):
		return self.treeDockWidget.projectTreeModel

	@property
	def cpuWidget(self):
		return self.cpuDockWidget.cpuWidget

	def getProject(self):
		return self.projectTreeModel.getProject()

	def getSimClient(self):
		return self.mainWidget.getSimClient()

	def __dirtyChanged(self, isDirty):
		self.saveAct.setEnabled(isDirty)
		self.tbSaveAct.setEnabled(isDirty)

		filename = self.mainWidget.getFilename()
		if filename:
			postfix = " -- " + os.path.basename(filename)
			if isDirty:
				postfix += "*"
		else:
			postfix = ""
		self.setWindowTitle("%s%s" % (self.TITLE, postfix))

	def __handleProjectLoaded(self, project):
		self.__updateLibActions()
		self.__updateFindActions()

	def __updateFindActions(self):
		findAvailable = self.editMdiArea.findTextIsAvailable()
		self.tbFindAct.setEnabled(findAvailable)
		self.findAct.setEnabled(findAvailable)

		replaceAvailable = self.editMdiArea.findReplaceTextIsAvailable()
		self.tbFindReplaceAct.setEnabled(replaceAvailable)
		self.findReplaceAct.setEnabled(replaceAvailable)

	def __updateLibActions(self):
		# Enable/disable the library toolbar button.
		# The menu library button is always available on purpose.
		self.tbLibAct.setEnabled(self.editMdiArea.pasteIsAvailable())

	def __textFocusChanged(self, textHasFocus):
		self.__sourceTextHasFocus = textHasFocus
		self.__updateLibActions()
		self.__updateFindActions()

	def __undoAvailableChanged(self, undoAvailable):
		self.undoAct.setEnabled(undoAvailable)
		self.tbUndoAct.setEnabled(undoAvailable)

	def __redoAvailableChanged(self, redoAvailable):
		self.redoAct.setEnabled(redoAvailable)
		self.tbRedoAct.setEnabled(redoAvailable)

	def __copyAvailableChanged(self, copyAvailable):
		self.copyAct.setEnabled(copyAvailable)
		self.tbCopyAct.setEnabled(copyAvailable)

	def __cutAvailableChanged(self, cutAvailable):
		self.cutAct.setEnabled(cutAvailable)
		self.tbCutAct.setEnabled(cutAvailable)

	def __pasteAvailableChanged(self, pasteAvailable):
		self.pasteAct.setEnabled(pasteAvailable)
		self.tbPasteAct.setEnabled(pasteAvailable)
		self.__updateLibActions()

	def closeEvent(self, ev):
		if self.mainWidget.isDirty():
			res = QMessageBox.question(self,
				"Unsaved AWL/STL code",
				"The editor contains unsaved AWL/STL code.\n"
				"AWL/STL code will be lost by exiting without saving.",
				QMessageBox.Discard | QMessageBox.Save | QMessageBox.Cancel,
				QMessageBox.Cancel)
			if res == QMessageBox.Save:
				if not self.mainWidget.save():
					ev.ignore()
					return
			elif res == QMessageBox.Cancel:
				ev.ignore()
				return
		self.getSimClient().shutdown()
		ev.accept()
		QMainWindow.closeEvent(self, ev)

	def awlsimHomepage(self):
		QDesktopServices.openUrl(QUrl(AWLSIM_HOME_URL, QUrl.StrictMode))

	def about(self):
		QMessageBox.about(self, "About AWL/STL soft-PLC",
			"Awlsim soft-PLC version %s\n"
			"\n"
			"Copyright 2012-2018 Michael Büsch <m@bues.ch>\n"
			"\n"
			"Project home:  %s\n"
			"\n"
			"\n"
			"This program is free software; you can redistribute it and/or modify "
			"it under the terms of the GNU General Public License as published by "
			"the Free Software Foundation; either version 2 of the License, or "
			"(at your option) any later version.\n"
			"\n"
			"This program is distributed in the hope that it will be useful, "
			"but WITHOUT ANY WARRANTY; without even the implied warranty of "
			"MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the "
			"GNU General Public License for more details.\n"
			"\n"
			"You should have received a copy of the GNU General Public License along "
			"with this program; if not, write to the Free Software Foundation, Inc., "
			"51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA." %\
			(VERSION_STRING, AWLSIM_HOME_URL))

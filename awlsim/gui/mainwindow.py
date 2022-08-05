# -*- coding: utf-8 -*-
#
# AWL simulator - GUI main window
#
# Copyright 2012-2022 Michael Buesch <m@bues.ch>
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
from awlsim.gui.runstate import *
from awlsim.gui.toolbars import *
from awlsim.gui.validatorsched import *


class LoadProgressDialog(QDialog):
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		self.setLayout(QGridLayout())
		self.setContentsMargins(30, 30, 30, 30)
		self.setWindowModality(Qt.ApplicationModal)
		self.__isShown = False
		self.__icon = QLabel(self)
		self.layout().addWidget(self.__icon, 0, 0)
		self.layout().setColumnMinimumWidth(1, 60)
		self.__text = QLabel(self)
		self.layout().addWidget(self.__text, 0, 2)

	def closeEvent(self, ev):
		if self.__isShown:
			ev.ignore()
			return
		QDialog.closeEvent(self, ev)

	def showProgress(self):
		self.__isShown = True
		self.show()
		QApplication.processEvents(QEventLoop.ExcludeUserInputEvents, 50)

	def hideProgress(self):
		self.__isShown = False
		self.hide()
		QApplication.processEvents(QEventLoop.ExcludeUserInputEvents, 50)

	def setGuiRunState(self, guiRunState):
		if guiRunState.state == GuiRunState.STATE_LOAD:
			self.setWindowTitle("Awlsim - Downloading...")
			self.__icon.setPixmap(getIcon("download").pixmap(64, 64))
			self.__text.setText("Downloading project to CPU.\n\n"
					    "Please be patient.\n"
					    "This might take a few seconds.")
			self.showProgress()
		else:
			self.hideProgress()

class CpuDockWidget(QDockWidget):
	def __init__(self, mainWidget, parent=None):
		QDockWidget.__init__(self, "", parent)
		self.mainWidget = mainWidget
		self.setObjectName("CpuDockWidget")
		self.toggleViewAction().setIcon(getIcon("cpu"))

		self.setFeatures(QDockWidget.DockWidgetMovable |
				 QDockWidget.DockWidgetFloatable |
				 QDockWidget.DockWidgetClosable)
		self.setAllowedAreas(Qt.AllDockWidgetAreas)

		self.setWidget(CpuWidget(mainWidget))

		self.topLevelChanged.connect(self.__handleTopLevelChange)
		self.__handleTopLevelChange(self.isFloating())

	@property
	def cpuWidget(self):
		return self.widget()

	def __handleTopLevelChange(self, floating):
		prefix = ""
		if floating:
			prefix = "%s - " % self.mainWidget.mainWindow.TITLE
		self.setWindowTitle("%sCPU view" % prefix)

class ProjectTreeDockWidget(QDockWidget):
	def __init__(self, mainWidget, parent=None):
		QDockWidget.__init__(self, "", parent)
		self.mainWidget = mainWidget
		self.setObjectName("ProjectTreeDockWidget")
		self.toggleViewAction().setIcon(getIcon("doc_edit"))

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
		prefix = ""
		if floating:
			prefix = "%s - " % self.mainWidget.mainWindow.TITLE
		self.setWindowTitle("%sProject" % prefix)

class MainWidget(QWidget):
	# Signal: Project loaded
	projectLoaded = Signal(Project)
	# Signal: Dirty-status changed
	dirtyChanged = Signal(int)
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

	# Document dirty levels
	EnumGen.start
	DIRTY_NO	= EnumGen.item
	DIRTY_SLIGHT	= EnumGen.item
	DIRTY_FULL	= EnumGen.item
	EnumGen.end

	def __init__(self, mainWindow, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout(self))
		self.mainWindow = mainWindow

		self.simClient = GuiAwlSimClient(mainWindow)

		self.editMdiArea = EditMdiArea(self)
		self.layout().addWidget(self.editMdiArea, 0, 0)

		self.filename = None
		self.__dirtyLevel = self.DIRTY_NO
		self.__guiRunState = GuiRunState()
		self.__insnPerSecond = 0.0
		self.__avgCycleTime = 0.0
		self.__minCycleTime = 0.0
		self.__maxCycleTime = 0.0
		self.__padCycleTime = 0.0

		self.__updateStatusBar()

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
		return self.__dirtyLevel == self.DIRTY_FULL

	def setDirty(self, dirtyLevel=DIRTY_FULL, force=False):
		if dirtyLevel != self.__dirtyLevel or force:
			if (not force and
			    self.__dirtyLevel == self.DIRTY_FULL and
			    dirtyLevel == self.DIRTY_SLIGHT):
				# Cannot go from full to slight.
				return
			self.__dirtyLevel = dirtyLevel
			self.dirtyChanged.emit(self.__dirtyLevel)

	def somethingChanged(self):
		self.setDirty(self.DIRTY_FULL)

	def getFilename(self):
		return self.filename

	def getSimClient(self):
		return self.simClient

	def getCpuWidget(self):
		return self.mainWindow.cpuWidget

	def __updateCpuViewConfig(self):
		"""Update the GuiCpuStateViewSettings objects in the project.
		"""
		settingsList = []

		stateMdiArea = self.getCpuWidget().stateMdi
		settingsList.append(stateMdiArea.getSettings())

		self.getProject().getGuiSettings().setCpuStateViewSettingsList(settingsList)

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
		if self.isDirty():
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
		self.getSimClient().action_goOffline()
		self.getCpuWidget().stateMdi.reset()
		if not os.path.exists(filename) and newIfNotExist:
			# The file does not exist. We implicitly create it.
			# The actual file will be created when the project is saved.
			isNewProject = True
			self.editMdiArea.resetArea()
			self.projectTreeModel.reset()
		else:
			isNewProject = False
			try:
				self.projectTreeModel.loadProjectFile(filename, self)
				guiSettings = self.getProject().getGuiSettings()
				for viewSettings in guiSettings.getCpuStateViewSettingsList():
					# We currently only have one CPU state view.
					# If the project has multiple viewSettings, all but the
					# last one will be lost.
					self.getCpuWidget().stateMdi.loadFromCpuStateViewSettings(viewSettings)
			except AwlSimError as e:
				QMessageBox.critical(self,
					"Failed to load project file", str(e))
				return False
		self.filename = filename
		if isNewProject or not self.getProject().getProjectFile():
			self.setDirty(self.DIRTY_FULL, force=True)
		else:
			self.setDirty(self.DIRTY_NO, force=True)
		self.projectLoaded.emit(self.getProject())
		return True

	def load(self):
		fn, fil = QFileDialog.getOpenFileName(self,
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
			self.__updateCpuViewConfig()
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
		self.setDirty(self.DIRTY_NO, force=True)
		return True

	def save(self, newFile=False):
		if newFile or not self.filename:
			fn, fil = QFileDialog.getSaveFileName(self,
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
		return self.projectTreeModel.libSelectionAdd(libSelection,
							     parentWidget=self)

	def insertOB(self):
		dlg = TemplateDialog.make_OB(self)
		def dialogFinished(result):
			if result != QDialog.Accepted:
				return
			self.__pasteAwlText(Templates.getOB(dlg.getBlockNumber(),
							    dlg.getVerbose()))
		dlg.finished.connect(dialogFinished)
		dlg.show()

	def insertFC(self):
		dlg = TemplateDialog.make_FC(self)
		def dialogFinished(result):
			if result != QDialog.Accepted:
				return
			self.__pasteAwlText(Templates.getFC(dlg.getBlockNumber(),
							    dlg.getVerbose()))
		dlg.finished.connect(dialogFinished)
		dlg.show()

	def insertFB(self):
		dlg = TemplateDialog.make_FB(self)
		def dialogFinished(result):
			if result != QDialog.Accepted:
				return
			self.__pasteAwlText(Templates.getFB(dlg.getBlockNumber(),
							    dlg.getVerbose()))
		dlg.finished.connect(dialogFinished)
		dlg.show()

	def insertInstanceDB(self):
		dlg = TemplateDialog.make_instanceDB(self)
		def dialogFinished(result):
			if result != QDialog.Accepted:
				return
			self.__pasteAwlText(Templates.getInstanceDB(dlg.getBlockNumber(),
								    dlg.getExtraNumber(),
								    dlg.getVerbose()))
		dlg.finished.connect(dialogFinished)
		dlg.show()

	def insertGlobalDB(self):
		dlg = TemplateDialog.make_globalDB(self)
		def dialogFinished(result):
			if result != QDialog.Accepted:
				return
			self.__pasteAwlText(Templates.getGlobalDB(dlg.getBlockNumber(),
								  dlg.getVerbose()))
		dlg.finished.connect(dialogFinished)
		dlg.show()

	def insertUDT(self):
		dlg = TemplateDialog.make_UDT(self)
		def dialogFinished(result):
			if result != QDialog.Accepted:
				return
			self.__pasteAwlText(Templates.getUDT(dlg.getBlockNumber(),
							     dlg.getVerbose()))
		dlg.finished.connect(dialogFinished)
		dlg.show()

	def insertFCcall(self):
		dlg = TemplateDialog.make_FCcall(self)
		def dialogFinished(result):
			if result != QDialog.Accepted:
				return
			self.__pasteAwlText(Templates.getFCcall(dlg.getBlockNumber(),
								dlg.getVerbose()))
		dlg.finished.connect(dialogFinished)
		dlg.show()

	def insertFBcall(self):
		dlg = TemplateDialog.make_FBcall(self)
		def dialogFinished(result):
			if result != QDialog.Accepted:
				return
			self.__pasteAwlText(Templates.getFBcall(dlg.getBlockNumber(),
								dlg.getExtraNumber(),
								dlg.getVerbose()))
		dlg.finished.connect(dialogFinished)
		dlg.show()

	def openLibrary(self):
		dlg = LibraryDialog(self.getProject(), self)
		def dialogFinished(result):
			if result != QDialog.Accepted:
				return
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
		dlg.finished.connect(dialogFinished)
		dlg.show()

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

	def openByIdentHash(self, identHash):
		projectTreeModel = self.projectTreeModel
		index = projectTreeModel.identHashToIndex(identHash)
		if index.isValid():
			return projectTreeModel.entryActivate(index, parentWidget=self)
		return False

	def handleGuiRunStateChange(self, guiRunState):
		"""CPU RunState changed.
		"""
		self.__guiRunState = guiRunState
		self.__updateStatusBar()
		self.mainWindow.loadProgressDialog.setGuiRunState(guiRunState)

	def handleCpuStats(self, statsMsg):
		"""Received new AwlSimMessage_CPUSTATS.
		"""
		self.__insnPerSecond = statsMsg.insnPerSecond
		self.__avgCycleTime = statsMsg.avgCycleTime
		self.__minCycleTime = statsMsg.minCycleTime
		self.__maxCycleTime = statsMsg.maxCycleTime
		self.__padCycleTime = statsMsg.padCycleTime
		self.__updateStatusBar()

	def __updateStatusBar(self):
		"""Update the main window status bar.
		"""
		status = []

		if self.__guiRunState == GuiRunState.STATE_OFFLINE:
			status.append("CPU: offline")
		elif self.__guiRunState == GuiRunState.STATE_ONLINE:
			status.append("CPU: online / STOP")
		elif self.__guiRunState == GuiRunState.STATE_LOAD:
			status.append("CPU: loading")
		elif self.__guiRunState == GuiRunState.STATE_RUN:
			status.append("CPU: RUN")
		elif self.__guiRunState == GuiRunState.STATE_EXCEPTION:
			status.append("CPU: EXCEPTION")

		if self.__guiRunState == GuiRunState.STATE_RUN:
			if self.__insnPerSecond > 0.0:
				usPerInsnStr = "%.02f" % ((1.0 / self.__insnPerSecond) * 1000000.0)
				status.append("%s stmt/s (%s µs/stmt)" % (
					      floatToHumanReadable(self.__insnPerSecond),
					      usPerInsnStr))

			if (self.__avgCycleTime > 0.0 and
			    self.__minCycleTime > 0.0 and
			    self.__maxCycleTime > 0.0):
				avgCycleTimeStr = "%.01f" % (self.__avgCycleTime * 1000.0)
				minCycleTimeStr = "%.01f" % (self.__minCycleTime * 1000.0)
				maxCycleTimeStr = "%.01f" % (self.__maxCycleTime * 1000.0)
				padCycleTimeStr = "%.01f" % (self.__padCycleTime * 1000.0)
				status.append("OB1: avg: %s ms  min: %s ms  max: %s ms  padding: %s ms" % (
					      avgCycleTimeStr,
					      minCycleTimeStr,
					      maxCycleTimeStr,
					      padCycleTimeStr))

		statusBar = self.mainWindow.statusBar()
		statusBar.showMessage("  --  ".join(status))

class MainWindow(QMainWindow):
	TITLE = "Awlsim PLC v%s" % VERSION_STRING

	@classmethod
	def start(cls,
		  initialAwlSource = None):
		# Set basic qapp-details.
		# This is important for QSettings.
		QApplication.setOrganizationName("awlsim")
		QApplication.setOrganizationDomain(AWLSIM_HOME_DOMAIN)
		QApplication.setApplicationName("awlsim-gui")
		QApplication.setApplicationVersion(VERSION_STRING)

		mainwnd = cls(initialAwlSource)
		mainwnd.show()

		if initialAwlSource and not mainwnd.mainWidget.isDirty():
			# Revert back from DIRTY_SLIGHT to DIRTY_NO.
			mainwnd.mainWidget.setDirty(mainwnd.mainWidget.DIRTY_NO,
						    force=True)

		return mainwnd

	def __init__(self, awlSource=None, parent=None):
		QMainWindow.__init__(self, parent)
		self.setWindowIcon(getIcon("cpu"))

		self.__profiler = None

		self.setStatusBar(QStatusBar(self))

		self.mainWidget = MainWidget(self, self)
		self.cpuDockWidget = CpuDockWidget(self.mainWidget, self)
		self.treeDockWidget = ProjectTreeDockWidget(self.mainWidget, self)

		self.setCentralWidget(self.mainWidget)

		self.setDockOptions(self.dockOptions() | QMainWindow.AllowTabbedDocks)
		self.addDockWidget(Qt.LeftDockWidgetArea, self.treeDockWidget)
		self.addDockWidget(Qt.BottomDockWidgetArea, self.cpuDockWidget)

		self.tb = QToolBar(self)
		self.tb.setObjectName("Main QToolBar")
		self.tb.setWindowTitle("Main tool bar")
		self.tb.toggleViewAction().setIcon(getIcon("prefs"))
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
		self.ctrlTb.toggleViewAction().setIcon(getIcon("prefs"))
		self.addToolBar(Qt.LeftToolBarArea, self.ctrlTb)

		self.inspectTb = CpuInspectToolBar(self)
		self.inspectTb.toggleViewAction().setIcon(getIcon("prefs"))
		self.addToolBar(Qt.LeftToolBarArea, self.inspectTb)

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

		self.__windowMenu = QMenu("&Window", self)
		self.menuBar().addMenu(self.__windowMenu)
		self.__windowMenu.aboutToShow.connect(self.__buildWindowMenu)

		menu = QMenu("&Help", self)
		menu.addAction(getIcon("browser"), "Awlsim &homepage...", self.awlsimHomepage)
		menu.addSeparator()
		menu.addAction(getIcon("cpu"), "&About...", self.about)
		menu.addSeparator()
		self.__actProfileStart = menu.addAction(getIcon("enable"),
							"Start profiling",
							self.profileStart)
		self.__actProfileStop = menu.addAction(getIcon("disable"),
						       "Stop profiling",
						       self.profileStop)
		profEnabled = (AwlSimEnv.getProfileLevel() > 0)
		self.__actProfileStart.setVisible(profEnabled)
		self.__actProfileStop.setVisible(False)
		self.menuBar().addMenu(menu)

		self.__loadProgressDialog = LoadProgressDialog(self)

		self.__sourceTextHasFocus = False
		self.__dirtyChanged(MainWidget.DIRTY_NO)
		self.__textFocusChanged(False)
		self.__undoAvailableChanged(False)
		self.__redoAvailableChanged(False)
		self.__copyAvailableChanged(False)
		self.__cutAvailableChanged(False)
		self.__pasteAvailableChanged(False)

		client = self.getSimClient()

		self.mainWidget.projectLoaded.connect(self.__handleProjectLoaded)
		self.mainWidget.dirtyChanged.connect(self.__dirtyChanged)
		self.mainWidget.textFocusChanged.connect(self.__textFocusChanged)
		self.mainWidget.undoAvailableChanged.connect(self.__undoAvailableChanged)
		self.mainWidget.redoAvailableChanged.connect(self.__redoAvailableChanged)
		self.mainWidget.copyAvailableChanged.connect(self.__copyAvailableChanged)
		self.mainWidget.cutAvailableChanged.connect(self.__cutAvailableChanged)
		self.mainWidget.pasteAvailableChanged.connect(self.__pasteAvailableChanged)
		self.cpuDockWidget.toggleViewAction().toggled.connect(self.__cpuDockToggled)
		self.inspectTb.connectToCpuWidget(self.cpuWidget)
		GuiValidatorSched.get().haveValidationResult.connect(self.projectTreeModel.handleAwlSimError)
		self.projectTreeModel.projectContentChanged.connect(self.mainWidget.somethingChanged)
		client.haveCpuStats.connect(self.mainWidget.handleCpuStats)
		client.haveIdentsMsg.connect(self.projectTreeModel.handleIdentsMsg)
		client.haveException.connect(self.projectTreeModel.handleAwlSimError)
		client.haveIdentsMsg.connect(self.editMdiArea.handleIdentsMsg)
		client.haveInsnDump.connect(self.editMdiArea.handleInsnDump)
		client.guiRunState.stateChanged.connect(self.editMdiArea.setGuiRunState)
		client.guiRunState.stateChanged.connect(self.projectTreeModel.setGuiRunState)
		client.guiRunState.stateChanged.connect(self.mainWidget.handleGuiRunStateChange)

		if awlSource:
			self.mainWidget.loadFile(awlSource, newIfNotExist=True)

		self.__restoreState()

	@property
	def loadProgressDialog(self):
		return self.__loadProgressDialog

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

	def __cpuDockToggled(self, cpuDockEnabled):
		action = self.inspectTb.toggleViewAction()
		if action.isChecked() != cpuDockEnabled:
			action.trigger()
		action.setEnabled(cpuDockEnabled)

	def __buildWindowMenu(self):
		"""Rebuild the window menu.
		"""
		menu = self.__windowMenu
		menu.clear()
		mdiSubWins = self.editMdiArea.subWindowList()
		if mdiSubWins:
			activeMdiSubWin = self.editMdiArea.activeOpenSubWindow
			for mdiSubWin in mdiSubWins:
				def activateWin(mdiSubWin=mdiSubWin):
					self.editMdiArea.setActiveSubWindow(mdiSubWin)
				action = menu.addAction(mdiSubWin.windowIcon(),
							mdiSubWin.windowTitle(),
							activateWin)
				if mdiSubWin is activeMdiSubWin:
					font = action.font()
					font.setBold(True)
					action.setFont(font)
		menu.addSeparator()
		def closeActive():
			w = self.editMdiArea.activeOpenSubWindow
			if w:
				w.close()
		def closeAllExceptActive():
			active = self.editMdiArea.activeOpenSubWindow
			for w in self.editMdiArea.subWindowList():
				if w is not active:
					w.close()
		def closeAll():
			self.editMdiArea.closeAllSubWindows()
		action = menu.addAction(getIcon("doc_close"),
					"&Close active window",
					closeActive)
		action.setEnabled(bool(mdiSubWins))
		action = menu.addAction(getIcon("doc_close"),
					"Close &all except active",
					closeAllExceptActive)
		action.setEnabled(bool(mdiSubWins))
		action = menu.addAction(getIcon("doc_close"),
					"Close a&ll",
					closeAll)
		action.setEnabled(bool(mdiSubWins))
		menu.addSeparator()
		menu.addAction(self.cpuDockWidget.toggleViewAction())
		menu.addSeparator()
		for tb in (self.tb, self.ctrlTb, self.inspectTb):
			menu.addAction(tb.toggleViewAction())

	def __saveState(self):
		settings = QSettings()

		# Save the main window state
		settings.setValue("gui_main_window_state",
				  self.saveState(VERSION_ID))

		# Save the main window geometry
		settings.setValue("gui_main_window_geo",
				  self.saveGeometry())

	def __restoreState(self):
		settings = QSettings()

		# Restore the main window geometry
		geo = settings.value("gui_main_window_geo")
		if geo:
			self.restoreGeometry(geo)

		# Restore the main window state
		state = settings.value("gui_main_window_state")
		if state:
			self.restoreState(state, VERSION_ID)

		# Only allow inspect tool bar switching, if the CPU dock is available.
		cpuDockEn = self.cpuDockWidget.toggleViewAction().isChecked()
		self.inspectTb.toggleViewAction().setEnabled(cpuDockEn)

	def __dirtyChanged(self, dirtyLevel):
		self.saveAct.setEnabled(dirtyLevel != MainWidget.DIRTY_NO)
		self.tbSaveAct.setEnabled(dirtyLevel != MainWidget.DIRTY_NO)

		filename = self.mainWidget.getFilename()
		if filename:
			postfix = " -- " + os.path.basename(filename)
			if dirtyLevel == MainWidget.DIRTY_FULL:
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
		self.__saveState()
		self.getSimClient().shutdown()
		ev.accept()
		QMainWindow.closeEvent(self, ev)
		self.profileStop()

	def keyPressEvent(self, ev):
		if ev.matches(QKeySequence.Save):
			self.mainWidget.save(False)
			ev.accept()
			return
		elif ev.matches(QKeySequence.SaveAs):
			self.mainWidget.save(True)
			ev.accept()
			return

		QMainWindow.keyPressEvent(self, ev)

	def awlsimHomepage(self):
		QDesktopServices.openUrl(QUrl(AWLSIM_HOME_URL, QUrl.StrictMode))

	def about(self):
		QMessageBox.about(self, "About Awlsim PLC",
			"Awlsim PLC version %s\n"
			"\n"
			"Copyright 2012-2022 Michael Büsch <m@bues.ch>\n"
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

	def profileStart(self):
		if not self.__profiler:
			try:
				self.__profiler = Profiler()
				self.__profiler.start()
			except AwlSimError as e:
				MessageBox.handleAwlSimError(self,
					"Failed to start profiler.", e)
				self.__profiler = None
				return

			self.__actProfileStart.setVisible(False)
			self.__actProfileStop.setVisible(True)

	def profileStop(self):
		if self.__profiler:
			self.__profiler.stop()
			printInfo("GUI profiler dump:\n" + self.__profiler.getResult())
			self.__profiler = None

			self.__actProfileStart.setVisible(True)
			self.__actProfileStop.setVisible(False)

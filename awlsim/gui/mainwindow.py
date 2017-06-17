# -*- coding: utf-8 -*-
#
# AWL simulator - GUI main window
#
# Copyright 2012-2017 Michael Buesch <m@bues.ch>
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
from awlsim.gui.editwidget import *
from awlsim.gui.projectwidget import *
from awlsim.gui.cpuwidget import *
from awlsim.gui.guiconfig import *
from awlsim.gui.cpuconfig import *
from awlsim.gui.linkconfig import *
from awlsim.gui.hwmodconfig import *
from awlsim.gui.icons import *


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

class MainWidget(QWidget):
	# Signal: Project loaded
	projectLoaded = Signal(Project)
	# Signal: Dirty-status changed
	dirtyChanged = Signal(bool)
	# Signal: CPU run state changed
	runStateChanged = Signal(RunState)
	# Signal: Source text focus changed
	textFocusChanged = Signal(bool)
	# Signal: Selected project resource changed
	selResourceChanged = Signal(int)
	# Signal: UndoAvailable state changed
	undoAvailableChanged = Signal(bool)
	# Signal: RedoAvailable state changed
	redoAvailableChanged = Signal(bool)
	# Signal: CopyAvailable state changed
	copyAvailableChanged = Signal(bool)

	def __init__(self, mainWindow, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout(self))
		self.mainWindow = mainWindow

		self.simClient = GuiAwlSimClient()

		self.projectWidget = ProjectWidget(self)
		self.layout().addWidget(self.projectWidget, 0, 0)

		self.filename = None
		self.dirty = False

		self.projectWidget.codeChanged.connect(self.somethingChanged)
		self.projectWidget.fupChanged.connect(self.somethingChanged)
		self.projectWidget.kopChanged.connect(self.somethingChanged)
		self.projectWidget.symTabChanged.connect(self.somethingChanged)
		self.projectWidget.libTableChanged.connect(self.somethingChanged)
		self.projectWidget.textFocusChanged.connect(self.textFocusChanged)
		self.projectWidget.selResourceChanged.connect(self.selResourceChanged)
		self.projectWidget.undoAvailableChanged.connect(self.undoAvailableChanged)
		self.projectWidget.redoAvailableChanged.connect(self.redoAvailableChanged)
		self.projectWidget.copyAvailableChanged.connect(self.copyAvailableChanged)
		self.runStateChanged.connect(self.projectWidget.updateRunState)

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

	def getProject(self):
		return self.projectWidget.getProject()

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
			self.projectWidget.reset()
		else:
			isNewProject = False
			try:
				self.projectWidget.loadProjectFile(filename)
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
			res = self.projectWidget.saveProjectFile(filename)
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
			self.projectWidget.setSettings(self.getProject().getGuiSettings())
		dlg.deleteLater()

	def linkConfig(self):
		dlg = LinkConfigDialog(self.getProject(), self)
		dlg.settingsChanged.connect(self.somethingChanged)
		dlg.exec_()
		dlg.deleteLater()

	def cpuConfig(self):
		dlg = CpuConfigDialog(self.getProject(), self)
		dlg.settingsChanged.connect(self.somethingChanged)
		dlg.exec_()
		dlg.deleteLater()

	def hwmodConfig(self):
		dlg = HwmodConfigDialog(self.getProject(), self)
		dlg.settingsChanged.connect(self.somethingChanged)
		dlg.exec_()
		dlg.deleteLater()

	def insertOB(self):
		self.projectWidget.insertOB()

	def insertFC(self):
		self.projectWidget.insertFC()

	def insertFB(self):
		self.projectWidget.insertFB()

	def insertInstanceDB(self):
		self.projectWidget.insertInstanceDB()

	def insertGlobalDB(self):
		self.projectWidget.insertGlobalDB()

	def insertUDT(self):
		self.projectWidget.insertUDT()

	def insertFCcall(self):
		self.projectWidget.insertFCcall()

	def insertFBcall(self):
		self.projectWidget.insertFBcall()

	def openLibrary(self):
		self.projectWidget.openLibrary()

	def undo(self):
		self.projectWidget.undo()

	def redo(self):
		self.projectWidget.redo()

	def cut(self):
		self.projectWidget.clipboardCut()

	def copy(self):
		self.projectWidget.clipboardCopy()

	def paste(self):
		self.projectWidget.clipboardPaste()

	def findText(self):
		self.projectWidget.findText()

	def findReplaceText(self):
		self.projectWidget.findReplaceText()

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

		self.setCentralWidget(self.mainWidget)
		self.addDockWidget(Qt.RightDockWidgetArea, self.cpuDockWidget)

		self.tb = QToolBar(self)
		self.tb.addAction(getIcon("new"), "New project", self.new)
		self.tb.addAction(getIcon("open"), "Open project", self.load)
		self.tbSaveAct = self.tb.addAction(getIcon("save"), "Save project", self.save)
		self.tb.addSeparator()
		self.tbUndoAct = self.tb.addAction(getIcon("undo"), "Undo last edit", self.undo)
		self.tbRedoAct = self.tb.addAction(getIcon("redo"), "Redo", self.redo)
		self.tb.addSeparator()
		self.tbCutAct = self.tb.addAction(getIcon("cut"), "Cut", self.cut)
		self.tbCopyAct = self.tb.addAction(getIcon("copy"), "Copy", self.copy)
		self.tbPasteAct = self.tb.addAction(getIcon("paste"), "Paste", self.paste)
		self.tb.addSeparator()
		self.tbFindAct = self.tb.addAction(getIcon("find"), "Find...", self.findText)
		self.tbFindReplaceAct = self.tb.addAction(getIcon("findreplace"),
							  "Find and replace...", self.findReplaceText)
		self.tb.addSeparator()
		self.tbLibAct = self.tb.addAction(getIcon("stdlib"), "Standard library", self.openLibrary)
		self.addToolBar(Qt.TopToolBarArea, self.tb)

		self.ctrlTb = CpuControlToolBar(self)
		self.addToolBar(Qt.TopToolBarArea, self.ctrlTb)

		self.inspectTb = CpuInspectToolBar(self)
		self.addToolBar(Qt.RightToolBarArea, self.inspectTb)

		self.setMenuBar(QMenuBar(self))

		menu = QMenu("&File", self)
		menu.addAction(getIcon("new"), "&New project", self.new)
		menu.addAction(getIcon("open"), "&Open project...", self.load)
		self.saveAct = menu.addAction(getIcon("save"), "&Save project", self.save)
		menu.addAction(getIcon("save"), "&Save project as...", self.saveAs)
		menu.addSeparator()
		menu.addAction(getIcon("exit"), "&Exit...", self.close)
		self.menuBar().addMenu(menu)

		menu = QMenu("&Edit", self)
		self.undoAct = menu.addAction(getIcon("undo"), "&Undo", self.undo)
		self.redoAct = menu.addAction(getIcon("redo"), "&Redo", self.redo)
		menu.addSeparator()
		self.cutAct = menu.addAction(getIcon("cut"), "&Cut", self.cut)
		self.copyAct = menu.addAction(getIcon("copy"), "&Copy", self.copy)
		self.pasteAct = menu.addAction(getIcon("paste"), "&Paste", self.paste)
		menu.addSeparator()
		self.findAct = menu.addAction(getIcon("find"), "&Find...", self.findText)
		self.findReplaceAct = menu.addAction(getIcon("findreplace"),
						     "Find and r&eplace...", self.findReplaceText)
		self.menuBar().addMenu(menu)

		menu = QMenu("&Library", self)
		menu.addAction(getIcon("textsource"), "Insert &OB template...", self.insertOB)
		menu.addAction(getIcon("textsource"), "Insert F&C template...", self.insertFC)
		menu.addAction(getIcon("textsource"), "Insert F&B template...", self.insertFB)
		menu.addAction(getIcon("textsource"), "Insert &instance-DB template...", self.insertInstanceDB)
		menu.addAction(getIcon("textsource"), "Insert &DB template...", self.insertGlobalDB)
		menu.addAction(getIcon("textsource"), "Insert &UDT template...", self.insertUDT)
		menu.addSeparator()
		menu.addAction(getIcon("textsource"), "Insert FC C&ALL template...", self.insertFCcall)
		menu.addAction(getIcon("textsource"), "Insert FB CA&LL template...", self.insertFBcall)
		menu.addSeparator()
		self.libAct = menu.addAction(getIcon("stdlib"), "&Standard library...", self.openLibrary)
		self.menuBar().addMenu(menu)

		menu = QMenu("&Settings", self)
		menu.addAction(getIcon("network"), "&Server connection...", self.linkConfig)
		menu.addAction(getIcon("cpu"), "&CPU config...", self.cpuConfig)
		menu.addAction(getIcon("hwmod"), "&Hardware modules...", self.hwmodConfig)
		menu.addAction(getIcon("prefs"), "&User interface...", self.guiConfig)
		self.menuBar().addMenu(menu)

		menu = QMenu("&CPU", self)
		menu.addAction(self.ctrlTb.onlineAction)
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
		self.__selResourceChanged(ProjectWidget.RES_SOURCES)
		self.__textFocusChanged(False)
		self.__undoAvailableChanged(False)
		self.__redoAvailableChanged(False)
		self.__copyAvailableChanged(False)

		self.mainWidget.projectLoaded.connect(self.__handleProjectLoaded)
		self.mainWidget.dirtyChanged.connect(self.__dirtyChanged)
		self.mainWidget.textFocusChanged.connect(self.__textFocusChanged)
		self.mainWidget.selResourceChanged.connect(self.__selResourceChanged)
		self.mainWidget.undoAvailableChanged.connect(self.__undoAvailableChanged)
		self.mainWidget.redoAvailableChanged.connect(self.__redoAvailableChanged)
		self.mainWidget.copyAvailableChanged.connect(self.__copyAvailableChanged)
		self.ctrlTb.connectToCpuWidget(self.cpuWidget)
		self.inspectTb.connectToCpuWidget(self.cpuWidget)
		self.mainWidget.dirtyChanged.connect(self.cpuWidget.handleDirtyChange)
		self.mainWidget.projectWidget.visibleLinesChanged.connect(self.cpuWidget.updateVisibleLineRange)
		self.cpuWidget.runStateChanged.connect(self.mainWidget.runStateChanged)
		self.cpuWidget.onlineDiagChanged.connect(self.mainWidget.projectWidget.handleOnlineDiagChange)
		self.cpuWidget.haveInsnDump.connect(self.mainWidget.projectWidget.handleInsnDump)
		self.cpuWidget.haveIdentsMsg.connect(self.mainWidget.projectWidget.handleIdentsMsg)
		self.cpuWidget.configChanged.connect(self.mainWidget.somethingChanged)

		if awlSource:
			self.mainWidget.loadFile(awlSource, newIfNotExist=True)

	@property
	def cpuWidget(self):
		return self.cpuDockWidget.cpuWidget

	def insertOB(self):
		self.mainWidget.insertOB()

	def insertFC(self):
		self.mainWidget.insertFC()

	def insertFB(self):
		self.mainWidget.insertFB()

	def insertInstanceDB(self):
		self.mainWidget.insertInstanceDB()

	def insertGlobalDB(self):
		self.mainWidget.insertGlobalDB()

	def insertUDT(self):
		self.mainWidget.insertUDT()

	def insertFCcall(self):
		self.mainWidget.insertFCcall()

	def insertFBcall(self):
		self.mainWidget.insertFBcall()

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
		if self.__selProjectResource == ProjectWidget.RES_SOURCES:
			self.tbFindAct.setEnabled(True)
			self.tbFindReplaceAct.setEnabled(True)
			self.findAct.setEnabled(True)
			self.findReplaceAct.setEnabled(True)
		else:
			self.tbFindAct.setEnabled(False)
			self.tbFindReplaceAct.setEnabled(False)
			self.findAct.setEnabled(False)
			self.findReplaceAct.setEnabled(False)

	def __updateLibActions(self):
		# Enable/disable the library toolbar button.
		# The menu library button is always available on purpose.
		if self.tbLibAct.isEnabled():
			if self.__selProjectResource != ProjectWidget.RES_SOURCES:
				self.tbLibAct.setEnabled(False)
				self.tbLibAct.setToolTip("Standard library.\n"
					"Please click in the AWL/STL source "
					"code at the place where to paste the "
					"library call.")
		else:
			if self.__selProjectResource == ProjectWidget.RES_SOURCES and\
			   self.__sourceTextHasFocus:
				self.tbLibAct.setEnabled(True)
				self.tbLibAct.setToolTip("Standard library")

	def __textFocusChanged(self, textHasFocus):
		self.__sourceTextHasFocus = textHasFocus
		self.__updateLibActions()
		self.__updateFindActions()

	def __selResourceChanged(self, resourceNumber):
		self.__selProjectResource = resourceNumber
		self.__updateLibActions()
		self.__updateFindActions()

	def __updateUndoActions(self):
		self.undoAct.setEnabled(
			self.__undoAvailable and
			self.__selProjectResource == ProjectWidget.RES_SOURCES
		)
		self.tbUndoAct.setEnabled(self.undoAct.isEnabled())

	def __undoAvailableChanged(self, undoAvailable):
		self.__undoAvailable = undoAvailable
		self.__updateUndoActions()

	def __updateRedoActions(self):
		self.redoAct.setEnabled(
			self.__redoAvailable and
			self.__selProjectResource == ProjectWidget.RES_SOURCES
		)
		self.tbRedoAct.setEnabled(self.redoAct.isEnabled())

	def __redoAvailableChanged(self, redoAvailable):
		self.__redoAvailable = redoAvailable
		self.__updateRedoActions()

	def __updateClipboardActions(self):
		self.cutAct.setEnabled(
			self.__copyAvailable and
			self.__selProjectResource == ProjectWidget.RES_SOURCES
		)
		self.tbCutAct.setEnabled(self.cutAct.isEnabled())
		self.copyAct.setEnabled(self.cutAct.isEnabled())
		self.tbCopyAct.setEnabled(self.copyAct.isEnabled())

	def __copyAvailableChanged(self, copyAvailable):
		self.__copyAvailable = copyAvailable
		self.__updateClipboardActions()

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
		self.mainWidget.getSimClient().shutdown()
		ev.accept()
		QMainWindow.closeEvent(self, ev)

	def awlsimHomepage(self):
		QDesktopServices.openUrl(QUrl(AWLSIM_HOME_URL, QUrl.StrictMode))

	def about(self):
		QMessageBox.about(self, "About AWL/STL soft-PLC",
			"Awlsim soft-PLC version %s\n"
			"\n"
			"Copyright 2012-2017 Michael Büsch <m@bues.ch>\n"
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

	def new(self):
		self.mainWidget.newFile()

	def load(self):
		self.mainWidget.load()

	def save(self):
		self.mainWidget.save()

	def saveAs(self):
		self.mainWidget.save(True)

	def guiConfig(self):
		self.mainWidget.guiConfig()

	def hwmodConfig(self):
		self.mainWidget.hwmodConfig()

	def linkConfig(self):
		self.mainWidget.linkConfig()

	def cpuConfig(self):
		self.mainWidget.cpuConfig()

	def openLibrary(self):
		self.mainWidget.openLibrary()

	def undo(self):
		self.mainWidget.undo()

	def redo(self):
		self.mainWidget.redo()

	def cut(self):
		self.mainWidget.cut()

	def copy(self):
		self.mainWidget.copy()

	def paste(self):
		self.mainWidget.paste()

	def findText(self):
		self.mainWidget.findText()

	def findReplaceText(self):
		self.mainWidget.findReplaceText()

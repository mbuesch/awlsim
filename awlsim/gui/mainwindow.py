# -*- coding: utf-8 -*-
#
# AWL simulator - GUI main window
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
from awlsim.gui.editwidget import *
from awlsim.gui.projectwidget import *
from awlsim.gui.cpuconfig import *
from awlsim.gui.coreconfig import *

from awlsim.coreserver.client import *


class MainWidget(QWidget):
	dirtyChanged = Signal(bool)
	runStateChanged = Signal(int)

	def __init__(self, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout(self))

		self.simClient = GuiAwlSimClient()

		self.coreConfigDialog = CoreConfigDialog(self, self.simClient)

		self.splitter = QSplitter(Qt.Horizontal)
		self.layout().addWidget(self.splitter, 0, 0)

		self.projectWidget = ProjectWidget(self)
		self.splitter.addWidget(self.projectWidget)

		self.cpuWidget = CpuWidget(self, self)
		self.splitter.addWidget(self.cpuWidget)

		self.filename = None
		self.dirty = False

		self.projectWidget.codeChanged.connect(self.__somethingChanged)
		self.projectWidget.symTabChanged.connect(self.__somethingChanged)
		self.projectWidget.visibleLinesChanged.connect(self.cpuWidget.updateVisibleLineRange)
		self.cpuWidget.runStateChanged.connect(self.__runStateChanged)
		self.cpuWidget.onlineDiagChanged.connect(self.projectWidget.handleOnlineDiagChange)
		self.cpuWidget.haveInsnDump.connect(self.projectWidget.handleInsnDump)
		self.runStateChanged.connect(self.projectWidget.updateRunState)

	def isDirty(self):
		return self.dirty

	def __runStateChanged(self, newState):
		self.runStateChanged.emit(newState)

	def getSimClient(self):
		return self.simClient

	def getCpuWidget(self):
		return self.cpuWidget

	def getProject(self):
		return self.projectWidget.getProject()

	def __somethingChanged(self):
		self.cpuWidget.stop()
		self.dirty = True
		self.dirtyChanged.emit(self.dirty)

	def loadFile(self, filename):
		try:
			res = self.projectWidget.loadProjectFile(filename)
			if not res:
				return False
		except AwlSimError as e:
			QMessageBox.critical(self,
				"Failed to load project file", str(e))
			return False
		self.filename = filename
		self.dirty = not bool(self.getProject().getProjectFile())
		self.dirtyChanged.emit(self.dirty)
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
		self.loadFile(fn)

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
		self.dirty = False
		self.dirtyChanged.emit(self.dirty)
		self.filename = filename
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

	def cpuConfig(self):
		project = self.getProject()
		dlg = CpuConfigDialog(self, self.simClient)
		dlg.loadFromProject(project)
		if dlg.exec_() == dlg.Accepted:
			dlg.saveToProject(project)
			self.__somethingChanged()

	def coreConfig(self):
		self.coreConfigDialog.exec_()

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

	def insertFCcall(self):
		self.projectWidget.insertFCcall()

	def insertFBcall(self):
		self.projectWidget.insertFBcall()

class MainWindow(QMainWindow):
	@classmethod
	def start(cls,
		  qApplication = None,
		  initialAwlSource = None):
		if not qApplication:
			qApplication = QApplication(sys.argv)
		mainwnd = cls(qApplication,
			      initialAwlSource)
		mainwnd.show()
		return mainwnd

	def __init__(self, qApplication, awlSource=None):
		QMainWindow.__init__(self)
		self.qApplication = qApplication

		self.setWindowTitle("Awlsim - AWL/STL Soft-PLC v%d.%d" %\
				    (VERSION_MAJOR, VERSION_MINOR))
		self.setCentralWidget(MainWidget(self))

		self.setMenuBar(QMenuBar(self))

		menu = QMenu("&File", self)
		menu.addAction("&Open...", self.load)
		self.saveAct = menu.addAction("&Save", self.save)
		menu.addAction("&Save as...", self.saveAs)
		menu.addSeparator()
		menu.addAction("&Exit...", self.close)
		self.menuBar().addMenu(menu)

		menu = QMenu("&Templates", self)
		menu.addAction("Insert &OB", self.insertOB)
		menu.addAction("Insert F&C", self.insertFC)
		menu.addAction("Insert F&B", self.insertFB)
		menu.addAction("Insert &instance-DB", self.insertInstanceDB)
		menu.addAction("Insert &DB", self.insertGlobalDB)
		menu.addSeparator()
		menu.addAction("Insert FC C&ALL", self.insertFCcall)
		menu.addAction("Insert FB CA&LL", self.insertFBcall)
		self.menuBar().addMenu(menu)

		menu = QMenu("&Simulator", self)
		menu.addAction("&Awlsim core settings...", self.coreConfig)
		menu.addAction("&CPU config...", self.cpuConfig)
		self.menuBar().addMenu(menu)

		menu = QMenu("Help", self)
		menu.addAction("&About...", self.about)
		self.menuBar().addMenu(menu)

		self.tb = QToolBar(self)
		self.tb.addAction("Open", self.load)
		self.tbSaveAct = self.tb.addAction("Save", self.save)
		self.addToolBar(self.tb)

		self.__dirtyChanged(False)

		self.centralWidget().dirtyChanged.connect(self.__dirtyChanged)
		self.centralWidget().runStateChanged.connect(self.__runStateChanged)

		if awlSource:
			self.centralWidget().loadFile(awlSource)

	def insertOB(self):
		self.centralWidget().insertOB()

	def insertFC(self):
		self.centralWidget().insertFC()

	def insertFB(self):
		self.centralWidget().insertFB()

	def insertInstanceDB(self):
		self.centralWidget().insertInstanceDB()

	def insertGlobalDB(self):
		self.centralWidget().insertGlobalDB()

	def insertFCcall(self):
		self.centralWidget().insertFCcall()

	def insertFBcall(self):
		self.centralWidget().insertFBcall()

	def runEventLoop(self):
		return self.qApplication.exec_()

	def getSimClient(self):
		return self.centralWidget().getSimClient()

	def cpuRun(self):
		self.centralWidget().getCpuWidget().run()

	def cpuStop(self):
		self.centralWidget().getCpuWidget().stop()

	def __runStateChanged(self, newState):
		self.menuBar().setEnabled(newState == CpuWidget.STATE_STOP)
		self.tb.setEnabled(newState == CpuWidget.STATE_STOP)

	def __dirtyChanged(self, isDirty):
		self.saveAct.setEnabled(isDirty)
		self.tbSaveAct.setEnabled(isDirty)

	def closeEvent(self, ev):
		cpuWidget = self.centralWidget().getCpuWidget()
		if cpuWidget.getState() != CpuWidget.STATE_STOP:
			res = QMessageBox.question(self,
				"CPU is in RUN state",
				"CPU is in RUN state.\n"
				"STOP CPU and quit application?",
				QMessageBox.Yes | QMessageBox.No,
				QMessageBox.Yes)
			if res != QMessageBox.Yes:
				ev.ignore()
				return
		self.centralWidget().getCpuWidget().stop()
		if self.centralWidget().isDirty():
			res = QMessageBox.question(self,
				"Unsaved AWL/STL code",
				"The editor contains unsaved AWL/STL code.\n"
				"AWL/STL code will be lost by exiting without saving.",
				QMessageBox.Discard | QMessageBox.Save | QMessageBox.Cancel,
				QMessageBox.Cancel)
			if res == QMessageBox.Save:
				if not self.centralWidget().save():
					ev.ignore()
					return
			elif res == QMessageBox.Cancel:
				ev.ignore()
				return
		ev.accept()
		QMainWindow.closeEvent(self, ev)

	def about(self):
		QMessageBox.information(self, "About AWL/STL Soft-PLC",
			"awlsim version %d.%d\n\n"
			"Copyright 2012-2014 Michael Büsch <m@bues.ch>\n"
			"Licensed under the terms of the "
			"GNU GPL version 2 or (at your option) "
			"any later version." %\
			(VERSION_MAJOR, VERSION_MINOR))

	def load(self):
		self.centralWidget().load()

	def save(self):
		self.centralWidget().save()

	def saveAs(self):
		self.centralWidget().save(True)

	def cpuConfig(self):
		self.centralWidget().cpuConfig()

	def coreConfig(self):
		self.centralWidget().coreConfig()

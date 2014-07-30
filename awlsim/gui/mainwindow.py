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

		self.cpuConfigDialog = CpuConfigDialog(self, self.simClient)
		self.coreConfigDialog = CoreConfigDialog(self, self.simClient)

		self.splitter = QSplitter(Qt.Horizontal)
		self.layout().addWidget(self.splitter, 0, 0)

		self.codeEdit = EditWidget(self)
		self.splitter.addWidget(self.codeEdit)

		self.cpuWidget = CpuWidget(self, self)
		self.splitter.addWidget(self.cpuWidget)

		self.filename = None
		self.dirty = False

		self.codeEdit.codeChanged.connect(self.__codeChanged)
		self.codeEdit.codeChanged.connect(self.cpuWidget.stop)
		self.cpuWidget.runStateChanged.connect(self.__runStateChanged)
		self.runStateChanged.connect(self.codeEdit.runStateChanged)

	def isDirty(self):
		return self.dirty

	def __runStateChanged(self, newState):
		self.runStateChanged.emit(newState)

	def getSimClient(self):
		return self.simClient

	def getCodeEditWidget(self):
		return self.codeEdit

	def getCpuWidget(self):
		return self.cpuWidget

	def __codeChanged(self):
		self.dirty = True
		self.dirtyChanged.emit(self.dirty)

	def loadFile(self, filename):
		try:
			data = awlFileRead(filename)
		except AwlParserError as e:
			QMessageBox.critical(self,
				"File read failed", str(e))
			return False
		self.codeEdit.loadCode(data)
		self.filename = filename
		return True

	def load(self):
		fn, fil = QFileDialog.getOpenFileName(self,
			"Open AWL/STL source", "",
			"AWL source (*.awl);;"
			"All files (*)")
		if not fn:
			return
		self.loadFile(fn)

	def saveFile(self, filename):
		code = self.codeEdit.getCode()
		try:
			awlFileWrite(filename, code)
		except AwlParserError as e:
			QMessageBox.critical(self,
				"Failed to write file", str(e))
			return False
		self.dirty = False
		self.dirtyChanged.emit(self.dirty)
		self.filename = filename
		return True

	def save(self, newFile=False):
		if newFile or not self.filename:
			fn, fil = QFileDialog.getSaveFileName(self,
				"AWL/STL source save as", "",
				"AWL source (*.awl)",
				"*.awl")
			if not fn:
				return
			if not fn.endswith(".awl"):
				fn += ".awl"
			return self.saveFile(fn)
		else:
			return self.saveFile(self.filename)

	def cpuConfig(self):
		self.cpuConfigDialog.exec_()

	def coreConfig(self):
		self.coreConfigDialog.exec_()

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

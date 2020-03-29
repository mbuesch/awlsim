# -*- coding: utf-8 -*-
#
# AWL simulator - GUI CPU widget
#
# Copyright 2012-2020 Michael Buesch <m@bues.ch>
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

from awlsim.gui.icons import *
from awlsim.gui.runstate import *
from awlsim.gui.util import *


__all__ = [
	"CpuInspectToolBar",
	"CpuControlToolBar",
]


class OnlineSelectAction(QAction):
	def __init__(self, parent):
		QAction.__init__(self, getIcon("network"), "", parent)

		self.setCheckable(True)
		self.__handleToggle(self.isChecked())

		self.toggled.connect(self.__handleToggle)

	def __handleToggle(self, checked):
		if checked:
			self.setText("Go offline")
		else:
			self.setText("Go online (Connect to a CPU)")

class RunSelectAction(QAction):
	def __init__(self, parent):
		QAction.__init__(self, getIcon("run"), "", parent)

		self.setCheckable(True)
		self.__handleToggle(self.isChecked())

		self.toggled.connect(self.__handleToggle)

	def __handleToggle(self, checked):
		if checked:
			self.setText("Stop CPU (STOP mode)")
			self.setIcon(getIcon("stop"))
		else:
			self.setText("Start CPU (RUN mode)")
			self.setIcon(getIcon("run"))

class DiagSelectAction(QAction):
	def __init__(self, parent):
		QAction.__init__(self, getIcon("glasses"), "", parent)

		self.setCheckable(True)
		self.__handleToggle(self.isChecked())

		self.toggled.connect(self.__handleToggle)

	def __handleToggle(self, checked):
		if checked:
			self.setText("Disable online diagnosis")
		else:
			self.setText("Enable online diagnosis")

class CpuInspectToolBar(QToolBar):
	def __init__(self, mainWindow):
		QToolBar.__init__(self, mainWindow)
		self.setObjectName("CpuInspectToolBar")
		self.setWindowTitle("CPU inspection tool bar")

		self.mainWindow = mainWindow

		self.blocksAction = QAction(getIcon("plugin"),
					    "Add inspection: Online blocks",
					    self)
		self.addAction(self.blocksAction)
		self.inputsAction = QAction(getIcon("inputs"),
					    "Add inspection: Input memory (I / E)",
					    self)
		self.addAction(self.inputsAction)
		self.outputsAction = QAction(getIcon("outputs"),
					     "Add inspection: Output memory (Q / A)",
					     self)
		self.addAction(self.outputsAction)
		self.flagsAction = QAction(getIcon("flags"),
					   "Add inspection: Flag memory (M)",
					   self)
		self.addAction(self.flagsAction)
		self.dbAction = QAction(getIcon("datablock"),
					"Add inspection: Data block (DB)",
					self)
		self.addAction(self.dbAction)
		self.timerAction = QAction(getIcon("timer"),
					   "Add inspection: Timer (T)",
					   self)
		self.addAction(self.timerAction)
		self.counterAction = QAction(getIcon("counter"),
					     "Add inspection: Counter (C / Z)",
					     self)
		self.addAction(self.counterAction)
		self.cpuAction = QAction(getIcon("cpu"),
					 "Add inspection: CPU overview",
					 self)
		self.addAction(self.cpuAction)
		self.lcdAction = QAction(getIcon("lcd"),
					 "Add inspection: LCD",
					 self)
		self.addAction(self.lcdAction)

	def connectToCpuWidget(self, cpuWidget):
		self.blocksAction.triggered.connect(cpuWidget.newWin_Blocks)
		self.inputsAction.triggered.connect(cpuWidget.newWin_E)
		self.outputsAction.triggered.connect(cpuWidget.newWin_A)
		self.flagsAction.triggered.connect(cpuWidget.newWin_M)
		self.dbAction.triggered.connect(cpuWidget.newWin_DB)
		self.timerAction.triggered.connect(cpuWidget.newWin_T)
		self.counterAction.triggered.connect(cpuWidget.newWin_Z)
		self.cpuAction.triggered.connect(cpuWidget.newWin_CPU)
		self.lcdAction.triggered.connect(cpuWidget.newWin_LCD)

class CpuControlToolBar(QToolBar):
	def __init__(self, mainWindow):
		QToolBar.__init__(self, mainWindow)
		self.setObjectName("CpuControlToolBar")
		self.setWindowTitle("CPU control tool bar")

		self.mainWindow = mainWindow
		self.__runButtonsBlocked = Blocker()

		self.__onlineDiagIdentHash = None
		self.__onlineDiagFromLine = None
		self.__onlineDiagToLine = None

		self.onlineAction = OnlineSelectAction(self)
		self.addAction(self.onlineAction)
		self.resetAction = QAction(getIcon("doc_delete"),
					   "Reset the CPU",
					   self)
		self.addAction(self.resetAction)
		self.downloadAction = QAction(getIcon("download"),
					      "Download all sources to CPU",
					      self)
		self.addAction(self.downloadAction)
		self.downloadSingleAction = QAction(getIcon("download_one"),
						    "Download single source to CPU",
						    self)
		self.addAction(self.downloadSingleAction)
		self.runAction = RunSelectAction(self)
		self.addAction(self.runAction)
		self.diagAction = DiagSelectAction(self)
		self.addAction(self.diagAction)

		client = self.mainWindow.getSimClient()
		client.guiRunState.stateChanged.connect(self.__handleGuiRunStateChange)

		self.mainWindow.mainWidget.dirtyChanged.connect(self.__handleDirtyChange)
		self.mainWindow.editMdiArea.visibleLinesChanged.connect(self.__updateVisibleLineRange)

		self.onlineAction.toggled.connect(self.__handleOnlineToggle)
		self.resetAction.triggered.connect(self.__handleResetTrigger)
		self.downloadAction.triggered.connect(self.__handleDownloadTrigger)
		self.downloadSingleAction.triggered.connect(self.__handleDownloadSingleTrigger)
		self.runAction.toggled.connect(self.__handleRunToggle)
		self.diagAction.toggled.connect(self.__handleDiagToggle)

	def __handleOnlineToggle(self, pressed):
		if not self.__runButtonsBlocked:
			client = self.mainWindow.getSimClient()
			if pressed:
				client.action_goOnline()
			else:
				client.action_goOffline()

	def __handleResetTrigger(self):
		if not self.__runButtonsBlocked:
			client = self.mainWindow.getSimClient()
			client.action_resetCpu()

	def __handleDownloadTrigger(self):
		if not self.__runButtonsBlocked:
			client = self.mainWindow.getSimClient()
			client.action_download()

	def __handleDownloadSingleTrigger(self):
		if not self.__runButtonsBlocked:
			client = self.mainWindow.getSimClient()
			client.action_downloadSingle()

	def __handleRunToggle(self, pressed):
		if not self.__runButtonsBlocked:
			client = self.mainWindow.getSimClient()
			if pressed:
				client.action_goRun()
			else:
				client.action_goStop()

	def __handleDiagToggle(self, pressed):
		self.mainWindow.editMdiArea.enableOnlineDiag(pressed)

	def __handleGuiRunStateChange(self, newState):
		"""The GuiRunState changed. Update the buttons.
		"""
		# Update diag state.
		if newState == GuiRunState.STATE_RUN:
			self.mainWindow.editMdiArea.enableOnlineDiag(self.diagAction.isChecked())

		# Update the buttons to reflect the actual state.
		with self.__runButtonsBlocked:
			if newState == GuiRunState.STATE_OFFLINE:
				self.onlineAction.setChecked(False)
				self.runAction.setChecked(False)
			elif newState == GuiRunState.STATE_ONLINE:
				self.onlineAction.setChecked(True)
				self.runAction.setChecked(False)
			elif newState == GuiRunState.STATE_LOAD:
				self.onlineAction.setChecked(True)
				self.runAction.setChecked(False)
			elif newState == GuiRunState.STATE_RUN:
				self.onlineAction.setChecked(True)
				self.runAction.setChecked(True)
			elif newState == GuiRunState.STATE_EXCEPTION:
				self.runAction.setChecked(False)
			else:
				assert(0)

	def __handleDirtyChange(self, dirtyLevel):
		"""The document dirty-state changed.
		"""
		# Disable diag, if dirty.
		if dirtyLevel == self.mainWindow.mainWidget.DIRTY_FULL:
			if self.diagAction.isChecked():
				self.diagAction.trigger()

	def __updateVisibleLineRange(self, source, fromLine, toLine):
		"""The diag visible line range changed.
		"""
		client = self.mainWindow.getSimClient()
		try:
			if self.diagAction.isChecked() and source:
				identHash = source.identHash
				if (self.__onlineDiagIdentHash != identHash or
				    self.__onlineDiagFromLine != fromLine or
				    self.__onlineDiagToLine != toLine):
					client.setInsnStateDump(enable=True,
								sourceId=identHash,
								fromLine=fromLine, toLine=toLine,
								userData=42,
								ob1Div=1,
								sync=False)
					self.__onlineDiagIdentHash = identHash
					self.__onlineDiagFromLine = fromLine
					self.__onlineDiagToLine = toLine
			else:
				if self.__onlineDiagIdentHash:
					client.setInsnStateDump(enable=False, sync=False)
					self.__onlineDiagIdentHash = None
					self.__onlineDiagFromLine = None
					self.__onlineDiagToLine = None
		except AwlSimError as e:
			MessageBox.handleAwlSimError(self.mainWindow,
				"Failed to setup instruction dumping", e)
			return
		except MaintenanceRequest as e:
			client.handleMaintenance(e)
			return

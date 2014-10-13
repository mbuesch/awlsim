# -*- coding: utf-8 -*-
#
# AWL simulator - GUI CPU widget
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
from awlsim.common.compat import *

from awlsim.gui.util import *
from awlsim.gui.cpustate import *
from awlsim.gui.awlsimclient import *
from awlsim.gui.icons import *


class ToolButton(QPushButton):
	ICONSIZE	= (32, 32)
	BTNFACT		= 1.3

	def __init__(self, iconName, description, parent=None):
		QPushButton.__init__(self, parent)

		iconSize = QSize(self.ICONSIZE[0], self.ICONSIZE[1])
		btnSize = QSize(int(round(iconSize.width() * self.BTNFACT)),
				int(round(iconSize.height() * self.BTNFACT)))

		self.setMinimumSize(btnSize)
		self.setMaximumSize(btnSize)
		self.setIcon(getIcon(iconName))
		self.setIconSize(iconSize)

		self.setToolTip(description)

class RunButton(ToolButton):
	def __init__(self, parent=None):
		ToolButton.__init__(self, "run", "", parent)

		self.setCheckable(True)
		self.setChecked(False)
		self.__handleToggle(False)
		self.toggled.connect(self.__handleToggle)

	def __handleToggle(self, checked):
		if checked:
			self.setIcon(getIcon("stop"))
			self.setToolTip("Click to stop CPU")
		else:
			self.setIcon(getIcon("run"))
			self.setToolTip("Click to start CPU")

class CpuWidget(QWidget):
	# Signal: The CPU run-state changed
	runStateChanged = Signal(int)
	# Signal: The online-diag state changed
	onlineDiagChanged = Signal(bool)
	# Signal: Have a new instruction dump
	haveInsnDump = Signal(AwlSimMessage_INSNSTATE)

	EnumGen.start
	STATE_STOP	= EnumGen.item
	STATE_INIT	= EnumGen.item
	STATE_LOAD	= EnumGen.item
	STATE_RUN	= EnumGen.item
	EnumGen.end

	def __init__(self, mainWidget, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout(self))
		self.layout().setContentsMargins(QMargins(7, 0, 0, 0))

		self.mainWidget = mainWidget
		self.state = self.STATE_STOP

		client = self.mainWidget.getSimClient()
		client.haveCpuDump.connect(self.__handleCpuDump)
		client.haveInsnDump.connect(self.haveInsnDump)
		client.haveMemoryUpdate.connect(self.__handleMemoryUpdate)

		toolsLayout = QHBoxLayout()

		group = QGroupBox("CPU", self)
		group.setLayout(QGridLayout(group))
		self.runButton = RunButton(group)
		group.layout().addWidget(self.runButton, 0, 0)
		self.onlineDiagButton = ToolButton("glasses", "Online diagnosis", group)
		self.onlineDiagButton.setCheckable(True)
		group.layout().addWidget(self.onlineDiagButton, 0, 1)
		toolsLayout.addWidget(group)

		group = QGroupBox("Inspection", self)
		group.setLayout(QGridLayout(group))
		self.newEButton = ToolButton("inputs", "Input memory (I / E)", group)
		group.layout().addWidget(self.newEButton, 0, 0)
		self.newAButton = ToolButton("outputs", "Output memory (Q / A)", group)
		group.layout().addWidget(self.newAButton, 0, 1)
		self.newMButton = ToolButton("flags", "Flag memory (M)", group)
		group.layout().addWidget(self.newMButton, 0, 2)
		self.newDBButton = ToolButton("datablock", "Data block (DB)", group)
		group.layout().addWidget(self.newDBButton, 0, 3)
		self.newTButton = ToolButton("timer", "Timer (T)", group)
		group.layout().addWidget(self.newTButton, 0, 4)
		self.newZButton = ToolButton("counter", "Counter (C / Z)", group)
		group.layout().addWidget(self.newZButton, 0, 5)
		self.newCpuStateButton = ToolButton("cpu", "CPU status", group)
		group.layout().addWidget(self.newCpuStateButton, 0, 6)
		self.newLCDButton = ToolButton("lcd", "LCD", group)
		group.layout().addWidget(self.newLCDButton, 0, 7)
		toolsLayout.addWidget(group)

		toolsLayout.addStretch()
		self.layout().addLayout(toolsLayout, 0, 0)

		self.stateWs = StateWorkspace(self)
		self.stateWs.setScrollBarsEnabled(True)
		self.layout().addWidget(self.stateWs, 1, 0)

		self.runButton.toggled.connect(self.__runStateToggled)
		self.onlineDiagButton.toggled.connect(self.__updateOnlineViewState)
		self.newCpuStateButton.released.connect(self.__newWin_CPU)
		self.newDBButton.released.connect(self.__newWin_DB)
		self.newEButton.released.connect(self.__newWin_E)
		self.newAButton.released.connect(self.__newWin_A)
		self.newMButton.released.connect(self.__newWin_M)
		self.newTButton.released.connect(self.__newWin_T)
		self.newZButton.released.connect(self.__newWin_Z)
		self.newLCDButton.released.connect(self.__newWin_LCD)

		self.__newWin_CPU()
		self.update()

	def __addWindow(self, win):
		self.stateWs.addWindow(win, Qt.Window)
		win.configChanged.connect(self.__stateWinConfigChanged)
		win.show()
		self.update()
		self.__uploadMemReadAreas()

	def __newWin_CPU(self):
		self.__addWindow(State_CPU(self.mainWidget.getSimClient(), self))

	def __newWin_DB(self):
		self.__addWindow(State_Mem(self.mainWidget.getSimClient(),
					   AbstractDisplayWidget.ADDRSPACE_DB,
					   self))

	def __newWin_E(self):
		self.__addWindow(State_Mem(self.mainWidget.getSimClient(),
					   AbstractDisplayWidget.ADDRSPACE_E,
					   self))

	def __newWin_A(self):
		self.__addWindow(State_Mem(self.mainWidget.getSimClient(),
					   AbstractDisplayWidget.ADDRSPACE_A,
					   self))

	def __newWin_M(self):
		self.__addWindow(State_Mem(self.mainWidget.getSimClient(),
					   AbstractDisplayWidget.ADDRSPACE_M,
					   self))

	def __newWin_T(self):
		self.__addWindow(State_Timer(self.mainWidget.getSimClient(),
					     self))

	def __newWin_Z(self):
		self.__addWindow(State_Counter(self.mainWidget.getSimClient(),
					       self))

	def __newWin_LCD(self):
		self.__addWindow(State_LCD(self.mainWidget.getSimClient(), self))

	def __stateWinConfigChanged(self, stateWin):
		self.__uploadMemReadAreas()

	def update(self):
		for win in self.stateWs.windowList():
			win.update()

	# Upload the used memory area descriptors to the core.
	def __uploadMemReadAreas(self):
		client = self.mainWidget.getSimClient()
		wantDump = False
		memAreas = []
		for win in self.stateWs.windowList():
			memAreas.extend(win.getMemoryAreas())
			if isinstance(win, State_CPU):
				wantDump = True
		try:
			client.setMemoryReadRequests(memAreas,
						     repetitionFactor = 10,
						     sync = True)
			client.setPeriodicDumpInterval(300 if wantDump else 0)
		except AwlSimError as e:
			MessageBox.handleAwlSimError(self,
				"Communication error with the simulator core",
				e)

	def __handleCpuDump(self, dumpText):
		for win in self.stateWs.windowList():
			if isinstance(win, State_CPU):
				win.setDumpText(dumpText)

	def __handleMemoryUpdate(self, memAreas):
		for win in self.stateWs.windowList():
			win.setMemories(memAreas)

	def __run(self):
		client = self.mainWidget.getSimClient()

		self.__setState(self.STATE_INIT)
		self.runButton.setChecked(True)
		self.runButton.setEnabled(False) # Redraws the radio button
		self.runButton.setEnabled(True)

		project = self.mainWidget.getProject()
		awlSources = self.mainWidget.projectWidget.getAwlSources()
		symTabSources = self.mainWidget.projectWidget.getSymTabSources()
		if not all(awlSources) or not all(symTabSources):
			self.stop()
			return

		try:
			if self.mainWidget.coreConfigDialog.shouldSpawnServer():
				firstPort, lastPort = self.mainWidget.coreConfigDialog.getSpawnPortRange()
				interp = self.mainWidget.coreConfigDialog.getInterpreterList()
				host = AwlSimServer.DEFAULT_HOST
				for port in range(firstPort, lastPort + 1):
					if not AwlSimServer.portIsUnused(host, port):
						continue
					# XXX: There is a race-window here. Another process might
					#      allocate the port that we just checked
					#      before our server is able to allocate it.
					if isWinStandalone:
						# Run the py2exe standalone server process
						client.spawnServer(serverExecutable = "awlsim-server-module.exe",
								   listenHost = host,
								   listenPort = port)
					else:
						client.spawnServer(interpreter = interp,
								   listenHost = host,
								   listenPort = port)
					break
				else:
					raise AwlSimError("Did not find a free port to run the "
						"awlsim core server on.\nTried port %d to %d on '%s'." %\
						(firstPort, lastPort, host))
			else:
				host = self.mainWidget.coreConfigDialog.getConnectHost()
				port = self.mainWidget.coreConfigDialog.getConnectPort()
			client.connectToServer(host = host,
					       port = port)
			client.setRunState(False)
			client.reset()

			client.setCpuSpecs(project.getCpuSpecs())
			client.enableOBTempPresets(project.getObTempPresetsEn())
			client.enableExtendedInsns(project.getExtInsnsEn())

			self.__uploadMemReadAreas()
			self.__updateOnlineViewState()

			self.__setState(self.STATE_LOAD)
			client.loadHardwareModule("dummy")
			for symTabSource in symTabSources:
				client.loadSymbolTable(symTabSource)
			for awlSource in awlSources:
				client.loadCode(awlSource)
			client.setRunState(True)
		except AwlParserError as e:
			MessageBox.handleAwlParserError(self, e)
			self.stop()
			client.shutdown()
			return
		except AwlSimError as e:
			MessageBox.handleAwlSimError(self,
				"Error while loading code", e)
			self.stop()
			client.shutdown()
			return
		except Exception:
			try:
				client.setRunState(False)
			except: pass
			client.shutdown()
			handleFatalException(self)
		self.__setState(self.STATE_RUN)
		try:
			# The main loop
			while self.state == self.STATE_RUN:
				# Receive messages, until we hit a timeout
				while client.processMessages(0.1):
					pass
				# Process GUI events
				QApplication.processEvents(QEventLoop.AllEvents)
		except AwlSimError as e:
			MessageBox.handleAwlSimError(self,
				"Error while executing code", e)
			self.stop()
		except MaintenanceRequest as e:
			if e.requestType == MaintenanceRequest.TYPE_SHUTDOWN:
				print("Shutting down, as requested...")
				client.shutdown()
				QApplication.exit(0)
				return
			elif e.requestType == MaintenanceRequest.TYPE_STOP or\
			     e.requestType == MaintenanceRequest.TYPE_RTTIMEOUT:
				self.stop()
			else:
				print("Unknown maintenance request %d" % e.requestType)
				self.stop()
		except Exception:
			try:
				client.setRunState(False)
			except: pass
			client.shutdown()
			handleFatalException(self)
		try:
			client.setRunState(False)
		except: pass
		client.shutdown()

	def stop(self):
		if self.state == self.STATE_STOP:
			return
		self.runButton.setChecked(False)
		self.__setState(self.STATE_STOP)

	def run(self):
		if self.state != self.STATE_STOP:
			return
		self.runButton.setChecked(True)

	def getState(self):
		return self.state

	def __setState(self, newState):
		if newState != self.state:
			self.state = newState
			self.runStateChanged.emit(self.state)
			QApplication.processEvents(QEventLoop.AllEvents, 1000)

	def __runStateToggled(self):
		if self.runButton.isChecked():
			if self.state == self.STATE_STOP:
				self.__run()
		else:
			if self.state != self.STATE_STOP:
				self.stop()

	def __updateOnlineViewState(self):
		onlineDiagEn = self.onlineDiagButton.isChecked()
		self.onlineDiagChanged.emit(onlineDiagEn)

	def updateVisibleLineRange(self, source, fromLine, toLine):
		onlineDiagEn = self.onlineDiagButton.isChecked()
		try:
			client = self.mainWidget.getSimClient()
			if onlineDiagEn and source:
				client.setInsnStateDump(enable=True,
							sourceId=source.identHash,
							fromLine=fromLine, toLine=toLine,
							sync=False)
			else:
				client.setInsnStateDump(enable=False, sync=False)
		except AwlSimError as e:
			MessageBox.handleAwlSimError(self,
				"Failed to setup instruction dumping", e)
			return

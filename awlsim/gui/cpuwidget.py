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
from awlsim.core.compat import *

from awlsim.gui.util import *
from awlsim.gui.cpustate import *
from awlsim.gui.awlsimclient import *


class CpuWidget(QWidget):
	runStateChanged = Signal(int)

	EnumGen.start
	STATE_STOP	= EnumGen.item
	STATE_INIT	= EnumGen.item
	STATE_LOAD	= EnumGen.item
	STATE_RUN	= EnumGen.item
	EnumGen.end

	def __init__(self, mainWidget, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout(self))

		self.mainWidget = mainWidget
		self.state = self.STATE_STOP

		client = self.mainWidget.getSimClient()
		client.haveCpuDump.connect(self.__handleCpuDump)
		client.haveInsnDump.connect(self.mainWidget.codeEdit.updateCpuStats_afterInsn)
		client.haveMemoryUpdate.connect(self.__handleMemoryUpdate)

		self.mainWidget.codeEdit.visibleRangeChanged.connect(self.__updateOnlineViewState)

		group = QGroupBox("CPU status", self)
		group.setLayout(QGridLayout(group))
		self.runButton = QRadioButton("RUN", group)
		group.layout().addWidget(self.runButton, 0, 0)
		self.stopButton = QRadioButton("STOP", group)
		group.layout().addWidget(self.stopButton, 1, 0)
		self.onlineViewCheckBox = QCheckBox("Online diag.", group)
		group.layout().addWidget(self.onlineViewCheckBox, 2, 0)
		self.layout().addWidget(group, 0, 0)

		group = QGroupBox("Add window", self)
		group.setLayout(QGridLayout(group))
		self.newCpuStateButton = QPushButton("CPU", group)
		group.layout().addWidget(self.newCpuStateButton, 0, 0)
		self.newLCDButton = QPushButton("LCD", group)
		group.layout().addWidget(self.newLCDButton, 0, 1)
		self.newDBButton = QPushButton("DB", group)
		group.layout().addWidget(self.newDBButton, 0, 2)
		self.newEButton = QPushButton("E (I)", group)
		group.layout().addWidget(self.newEButton, 1, 0)
		self.newAButton = QPushButton("A (Q)", group)
		group.layout().addWidget(self.newAButton, 1, 1)
		self.newMButton = QPushButton("M", group)
		group.layout().addWidget(self.newMButton, 1, 2)
		self.layout().addWidget(group, 0, 1)

		self.stateWs = StateWorkspace(self)
		self.stateWs.setScrollBarsEnabled(True)
		self.layout().addWidget(self.stateWs, 1, 0, 1, 2)

		self.stopButton.setChecked(Qt.Checked)

		self.runButton.toggled.connect(self.__runStateToggled)
		self.stopButton.toggled.connect(self.__runStateToggled)
		self.onlineViewCheckBox.stateChanged.connect(self.__updateOnlineViewState)
		self.newCpuStateButton.released.connect(self.__newWin_CPU)
		self.newDBButton.released.connect(self.__newWin_DB)
		self.newEButton.released.connect(self.__newWin_E)
		self.newAButton.released.connect(self.__newWin_A)
		self.newMButton.released.connect(self.__newWin_M)
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

		awlCode = self.mainWidget.getCodeEditWidget().getCode()
		if not awlCode.strip():
			MessageBox.error(self, "No AWL/STL code available. Cannot run.")
			self.stop()
			return
		try:
			awlCode = awlCode.encode("latin_1")
		except UnicodeError:
			MessageBox.error(self, "AWL/STL code contains invalid characters.")
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
						client.spawnServer(serverExecutable = "server.exe",
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

			self.mainWidget.cpuConfigDialog.uploadToCPU()
			self.__uploadMemReadAreas()
			self.__updateOnlineViewState()

			self.__setState(self.STATE_LOAD)
			client.loadHardwareModule("dummy")
			client.loadCode(AwlSource("gui", None, awlCode))
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
			else:
				assert(0)
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
		self.stopButton.setChecked(True)
		self.runButton.setEnabled(True)
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
		if self.stopButton.isChecked():
			if self.state != self.STATE_STOP:
				self.stop()

	def __updateOnlineViewState(self):
		en = self.onlineViewCheckBox.checkState() == Qt.Checked
		self.mainWidget.codeEdit.enableCpuStats(en)
		try:
			client = self.mainWidget.getSimClient()
			if en:
				fromLine, toLine = self.mainWidget.codeEdit.getVisibleLineRange()
				client.setInsnStateDump(fromLine, toLine, sync=False)
			else:
				client.setInsnStateDump(0, 0, sync=False)
		except AwlSimError as e:
			MessageBox.handleAwlSimError(self,
				"Failed to setup instruction dumping", e)
			return

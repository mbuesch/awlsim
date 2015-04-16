# -*- coding: utf-8 -*-
#
# AWL simulator - GUI CPU widget
#
# Copyright 2012-2015 Michael Buesch <m@bues.ch>
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
from awlsim.gui.linkconfig import *


class RunState(QObject):
	# Signal: Emitted, if the state changed.
	# The parameter is 'self'.
	stateChanged = Signal(QObject)

	EnumGen.start
	STATE_OFFLINE	= EnumGen.item
	STATE_ONLINE	= EnumGen.item
	STATE_LOAD	= EnumGen.item
	STATE_RUN	= EnumGen.item
	STATE_EXCEPTION	= EnumGen.item
	EnumGen.end

	def __init__(self):
		QObject.__init__(self)
		self.state = self.STATE_OFFLINE
		self.setCoreDetails()

	def __emitStateChanged(self):
		self.stateChanged.emit(self)
		QApplication.processEvents(QEventLoop.ExcludeUserInputEvents,
					   50)

	def setState(self, newState):
		if self.state != newState:
			self.state = newState
			self.__emitStateChanged()

	def setCoreDetails(self, spawned=True,
			   host=None, port=None):
		self.spawned = spawned
		self.host = host
		self.port = port
		self.__emitStateChanged()

class ToolButton(QPushButton):
	ICONSIZE	= (32, 32)
	BTNFACT		= 1.2

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

class CheckableToolButton(ToolButton):
	def __init__(self,
		     checkedIconName, uncheckedIconName="",
		     checkedToolTip="", uncheckedToolTip="",
		     parent=None):
		ToolButton.__init__(self, uncheckedIconName, "", parent)

		self.__checkedIconName = checkedIconName
		self.__uncheckedIconName = uncheckedIconName
		if not self.__uncheckedIconName:
			self.__uncheckedIconName = self.__checkedIconName
		self.__checkedToolTip = checkedToolTip
		self.__uncheckedToolTip = uncheckedToolTip
		if not self.__uncheckedToolTip:
			self.__uncheckedToolTip = self.__checkedToolTip

		self.setCheckable(True)
		self.setChecked(False)
		self.__handleToggle(False)
		self.toggled.connect(self.__handleToggle)

	def __handleToggle(self, checked):
		self.setToolTip(self.__checkedToolTip if checked else\
				self.__uncheckedToolTip)
		self.setIcon(getIcon(self.__checkedIconName if checked else\
				     self.__uncheckedIconName))

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
	def __init__(self, parent=None):
		QToolBar.__init__(self, parent)

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
		self.inputsAction.triggered.connect(cpuWidget.newWin_E)
		self.outputsAction.triggered.connect(cpuWidget.newWin_A)
		self.flagsAction.triggered.connect(cpuWidget.newWin_M)
		self.dbAction.triggered.connect(cpuWidget.newWin_DB)
		self.timerAction.triggered.connect(cpuWidget.newWin_T)
		self.counterAction.triggered.connect(cpuWidget.newWin_Z)
		self.cpuAction.triggered.connect(cpuWidget.newWin_CPU)
		self.lcdAction.triggered.connect(cpuWidget.newWin_LCD)

class CpuControlToolBar(QToolBar):
	def __init__(self, parent=None):
		QToolBar.__init__(self, parent)

		self.onlineAction = OnlineSelectAction(self)
		self.addAction(self.onlineAction)
		self.downloadAction = QAction(getIcon("download"),
					      "Download all AWL/STL code to CPU",
					      self)
		self.addAction(self.downloadAction)
		self.runAction = RunSelectAction(self)
		self.addAction(self.runAction)
		self.diagAction = DiagSelectAction(self)
		self.addAction(self.diagAction)

	def connectToCpuWidget(self, cpuWidget):
		self.onlineAction.toggled.connect(cpuWidget._onlineToggled)
		self.downloadAction.triggered.connect(cpuWidget.download)
		self.runAction.toggled.connect(cpuWidget._runStateToggled)
		self.diagAction.toggled.connect(cpuWidget._onlineDiagToggled)

		cpuWidget.reqRunButtonState.connect(self.__setRun)
		cpuWidget.reqOnlineButtonState.connect(self.__setOnline)
		cpuWidget.reqOnlineDiagButtonState.connect(self.__setOnlineDiag)

	def __setRun(self, en):
		if en != self.runAction.isChecked():
			self.runAction.trigger()

	def __setOnline(self, en):
		if en != self.onlineAction.isChecked():
			self.onlineAction.trigger()

	def __setOnlineDiag(self, en):
		if en != self.diagAction.isChecked():
			self.diagAction.trigger()

class CpuWidget(QWidget):
	# Signal: The CPU run-state changed
	runStateChanged = Signal(RunState)
	# Signal: The online-diag state changed
	onlineDiagChanged = Signal(bool)
	# Signal: Some configuration value changed
	configChanged = Signal()
	# Signal: Have a new instruction dump
	haveInsnDump = Signal(AwlSimMessage_INSNSTATE)
	# Signal: Have a new ident hashes message
	haveIdentsMsg = Signal(AwlSimMessage_IDENTS)

	# Signal: Request a new run button state.
	reqRunButtonState = Signal(bool)
	# Signal: Request a new online button state.
	reqOnlineButtonState = Signal(bool)
	# Signal: request a new online diagnosis button state.
	reqOnlineDiagButtonState = Signal(bool)

	def __init__(self, mainWidget, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout(self))
		self.layout().setContentsMargins(QMargins(7, 0, 0, 0))

		self.mainWidget = mainWidget
		self.state = RunState()
		self.__runStateChangeBlocked = Blocker()

		self.__onlineBtnPressed = False
		self.__runBtnPressed = False
		self.__onlineDiagBtnPressed = False

		self.__coreMsgTimer = QTimer(self)
		self.__coreMsgTimer.setSingleShot(False)
		self.__coreMsgTimer.timeout.connect(self.__processCoreMessages)

		self.__corePeriodicTimer = QTimer(self)
		self.__corePeriodicTimer.setSingleShot(False)
		self.__corePeriodicTimer.timeout.connect(self.__periodicCoreWork)

		client = self.mainWidget.getSimClient()
		client.haveCpuDump.connect(self.__handleCpuDump)
		client.haveInsnDump.connect(self.haveInsnDump)
		client.haveMemoryUpdate.connect(self.__handleMemoryUpdate)
		client.haveIdentsMsg.connect(self.__handleIdentsMsg)

		self.stateMdi = StateMdiArea(self)
		self.stateMdi.setViewMode(QMdiArea.SubWindowView)
		self.stateMdi.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.stateMdi.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.layout().addWidget(self.stateMdi, 0, 0)

		self.state.stateChanged.connect(self.runStateChanged)

		self.newWin_CPU()
		self.update()

	def __stateMdiWindowClosed(self, mdiWin):
		QTimer.singleShot(0, self.__uploadMemReadAreas)

	def __addWindow(self, win):
		mdiWin = StateMdiSubWindow(win)
		mdiWin.closed.connect(self.__stateMdiWindowClosed)
		self.stateMdi.addSubWindow(mdiWin, Qt.Window)
		win.configChanged.connect(self.__stateWinConfigChanged)
		win.show()
		self.update()
		self.__uploadMemReadAreas()

	def newWin_CPU(self):
		self.__addWindow(State_CPU(self.mainWidget.getSimClient(), self))

	def newWin_DB(self):
		self.__addWindow(State_Mem(self.mainWidget.getSimClient(),
					   AbstractDisplayWidget.ADDRSPACE_DB,
					   self))

	def newWin_E(self):
		self.__addWindow(State_Mem(self.mainWidget.getSimClient(),
					   AbstractDisplayWidget.ADDRSPACE_E,
					   self))

	def newWin_A(self):
		self.__addWindow(State_Mem(self.mainWidget.getSimClient(),
					   AbstractDisplayWidget.ADDRSPACE_A,
					   self))

	def newWin_M(self):
		self.__addWindow(State_Mem(self.mainWidget.getSimClient(),
					   AbstractDisplayWidget.ADDRSPACE_M,
					   self))

	def newWin_T(self):
		self.__addWindow(State_Timer(self.mainWidget.getSimClient(),
					     self))

	def newWin_Z(self):
		self.__addWindow(State_Counter(self.mainWidget.getSimClient(),
					       self))

	def newWin_LCD(self):
		self.__addWindow(State_LCD(self.mainWidget.getSimClient(), self))

	def __stateWinConfigChanged(self, stateWin):
		self.__uploadMemReadAreas()

	def update(self):
		for mdiWin in self.stateMdi.subWindowList():
			win = mdiWin.widget()
			win.update()

	# Upload the used memory area descriptors to the core.
	def __uploadMemReadAreas(self):
		client = self.mainWidget.getSimClient()
		wantDump = False
		memAreas = []
		for mdiWin in self.stateMdi.subWindowList():
			win = mdiWin.widget()
			memAreas.extend(win.getMemoryAreas())
			if isinstance(win, State_CPU):
				wantDump = True
		try:
			client.setMemoryReadRequests(memAreas,
						     repetitionFactor = 10,
						     sync = True)
			client.setPeriodicDumpInterval(300 if wantDump else 0)
		except AwlSimError as e:
			self.state.setState(RunState.STATE_EXCEPTION)
			MessageBox.handleAwlSimError(self,
				"Error in awlsim core", e)
			return False
		except MaintenanceRequest as e:
			self.__handleMaintenance(e)
			return False
		return True

	def __handleCpuDump(self, dumpText):
		for mdiWin in self.stateMdi.subWindowList():
			win = mdiWin.widget()
			if isinstance(win, State_CPU):
				win.setDumpText(dumpText)

	def __handleMemoryUpdate(self, memAreas):
		for mdiWin in self.stateMdi.subWindowList():
			win = mdiWin.widget()
			win.setMemories(memAreas)

	def __handleMaintenance(self, maintRequest):
		client = self.mainWidget.getSimClient()

		if maintRequest.requestType == MaintenanceRequest.TYPE_SHUTDOWN:
			res = QMessageBox.question(self,
				"Shut down application?",
				"The core server requested an "
				"application shutdown.\n"
				"Do you want to close Awlsim GUI?",
				QMessageBox.Yes | QMessageBox.No,
				QMessageBox.No)
			if res == QMessageBox.Yes:
				print("Shutting down, as requested by server...")
				client.shutdown()
				QApplication.exit(0)
			else:
				self.stop()
				self.goOffline()
		elif maintRequest.requestType == MaintenanceRequest.TYPE_STOP or\
		     maintRequest.requestType == MaintenanceRequest.TYPE_RTTIMEOUT:
			self.stop()
		else:
			print("Unknown maintenance request %d" %\
			      maintRequest.requestType)
			self.stop()

	def __run(self, goOnlineFirst=True, downloadFirstIfSimulator=True):
		client = self.mainWidget.getSimClient()

		# Make sure the button is pressed.
		with self.__runStateChangeBlocked:
			self.run()

		# If requested, go online first.
		if goOnlineFirst:
			self.goOnline()
			if not self.isOnline():
				self.stop()
				return
		assert(self.isOnline())

		# If requested and if in sim (FORK) mode,
		# download the program first.
		if downloadFirstIfSimulator and\
		   client.getMode() == client.MODE_FORK:
			if not self.download(noRun=True):
				self.stop()
				return

		# Put the CPU and the GUI into RUN state.
		try:
			# Put CPU into RUN mode, if it's not already there.
			client.setRunState(True)

			# Upload the GUI requests.
			if not self.__uploadMemReadAreas():
				self.stop()
				return
			self.updateOnlineViewState()

			# Put the GUI into RUN mode.
			self.state.setState(RunState.STATE_RUN)
			self.__identsPending = False
			self.__periodicCoreWork()
			self.__coreMsgTimer.start(0)
			self.__corePeriodicTimer.start(1000)
		except AwlSimError as e:
			self.state.setState(RunState.STATE_EXCEPTION)
			MessageBox.handleAwlSimError(self,
				"Could not start CPU", e)
			self.stop()
		except MaintenanceRequest as e:
			self.__handleMaintenance(e)

	# Periodic timer for core message handling.
	def __processCoreMessages(self):
		client = self.mainWidget.getSimClient()
		try:
			# Receive messages, until we hit a timeout
			while client.processMessages(0.1):
				pass
		except AwlSimError as e:
			self.state.setState(RunState.STATE_EXCEPTION)
			MessageBox.handleAwlSimError(self,
				"Core server error", e)
			self.stop()
		except MaintenanceRequest as e:
			self.__handleMaintenance(e)
		except Exception:
			CALL_NOEX(client.setRunState, False)
			client.shutdown()
			handleFatalException(self)

	# Periodic timer for core status work.
	def __periodicCoreWork(self):
		client = self.mainWidget.getSimClient()

		if not self.__identsPending:
			self.__identsPending = True
			client.requestIdents(reqAwlSources = True,
					     reqSymTabSources = True)

	def __handleIdentsMsg(self, identsMsg):
		if self.__identsPending:
			self.__identsPending = False
			self.haveIdentsMsg.emit(identsMsg)

	def __stop(self):
		# Make sure the button is released.
		with self.__runStateChangeBlocked:
			self.stop()

		self.__coreMsgTimer.stop()
		self.__corePeriodicTimer.stop()
		if self.isOnline():
			client = self.mainWidget.getSimClient()
			try:
				client.setRunState(False)
			except AwlSimError as e:
				MessageBox.handleAwlSimError(self,
					"Could not stop CPU", e)
		self.state.setState(RunState.STATE_ONLINE)

	def stop(self):
		self.reqRunButtonState.emit(False)

	def run(self):
		self.reqRunButtonState.emit(True)

	def __goOnline(self):
		project = self.mainWidget.getProject()

		if LinkConfigWidget.askWhenConnecting():
			dlg = LinkConfigDialog(project, self)
			dlg.settingsChanged.connect(self.configChanged)
			if dlg.exec_() != LinkConfigDialog.Accepted:
				self.goOffline()
				return

		linkConfig = project.getCoreLinkSettings()
		client = self.mainWidget.getSimClient()
		try:
			if linkConfig.getSpawnLocalEn():
				portRange = linkConfig.getSpawnLocalPortRange()
				interp = linkConfig.getSpawnLocalInterpreterList()
				if isWinStandalone:
					# Run the frozen standalone server process
					client.setMode_FORK(portRange = portRange,
						serverExecutable = "awlsim-server-module.exe")
				else:
					client.setMode_FORK(portRange = portRange,
						interpreterList = interp)
				host = port = None
			else:
				host = linkConfig.getConnectHost()
				port = linkConfig.getConnectPort()
				timeout = linkConfig.getConnectTimeoutMs() / 1000.0
				client.setMode_ONLINE(host = host,
						      port = port,
						      timeout = timeout)

			self.state.setCoreDetails(spawned = linkConfig.getSpawnLocalEn(),
						  host = host,
						  port = port)
			self.state.setState(RunState.STATE_ONLINE)

			if client.getRunState():
				# The core is already running.
				# Set the GUI to run state, too.
				self.__run(goOnlineFirst = False,
					   downloadFirstIfSimulator = False)
		except AwlSimError as e:
			CALL_NOEX(client.setMode_OFFLINE)
			MessageBox.handleAwlSimError(self,
				"Error while trying to connect to CPU", e)
			self.goOffline()
			return
		except MaintenanceRequest as e:
			self.__handleMaintenance(e)

	def __goOffline(self):
		client = self.mainWidget.getSimClient()
		try:
			client.setMode_OFFLINE()
		except AwlSimError as e:
			MessageBox.handleAwlSimError(self,
				"Error while trying to disconnect from CPU", e)
		# Release the stop-button.
		# This will _not_ stop the CPU, as we're offline already.
		self.stop()
		self.state.setState(RunState.STATE_OFFLINE)

	def _onlineToggled(self, onlineBtnPressed):
		self.__onlineBtnPressed = onlineBtnPressed
		if self.__onlineBtnPressed:
			self.__goOnline()
		else:
			self.__goOffline()

	def isOnline(self):
		return self.__onlineBtnPressed

	def goOnline(self):
		self.reqOnlineButtonState.emit(True)

	def goOffline(self):
		self.reqOnlineButtonState.emit(False)

	def download(self, noRun=False):
		# Make sure we are online.
		self.goOnline()
		if not self.isOnline():
			return False

		client = self.mainWidget.getSimClient()
		project = self.mainWidget.getProject()
		awlSources = self.mainWidget.projectWidget.getAwlSources()
		symTabSources = self.mainWidget.projectWidget.getSymTabSources()
		libSelections = self.mainWidget.projectWidget.getLibSelections()
		if not all(awlSources) or not all(symTabSources):
			return False

		try:
			self.state.setState(RunState.STATE_LOAD)

			client.setRunState(False)
			client.reset()

			client.setCpuSpecs(project.getCpuSpecs())
			client.enableOBTempPresets(project.getObTempPresetsEn())
			client.enableExtendedInsns(project.getExtInsnsEn())

			for modDesc in project.getHwmodSettings().getLoadedModules():
				client.loadHardwareModule(modDesc.getModuleName(),
							  modDesc.getParameters())
			for symTabSource in symTabSources:
				client.loadSymbolTable(symTabSource)
			for libSel in libSelections:
				client.loadLibraryBlock(libSel)
			for awlSource in awlSources:
				client.loadCode(awlSource)

			self.state.setState(RunState.STATE_ONLINE)
		except AwlParserError as e:
			self.state.setState(RunState.STATE_ONLINE)
			self.stop()
			MessageBox.handleAwlParserError(self, e)
			return False
		except AwlSimError as e:
			self.state.setState(RunState.STATE_ONLINE)
			self.stop()
			MessageBox.handleAwlSimError(self,
				"Error while loading code", e)
			return False
		except MaintenanceRequest as e:
			self.__handleMaintenance(e)
			return False
		except Exception:
			client.shutdown()
			handleFatalException(self)

		# If we were RUNning before download, put
		# the CPU into RUN state again.
		if self.__runBtnPressed and not noRun:
			self.__run(goOnlineFirst = False,
				   downloadFirstIfSimulator = False)

		return True

	def _runStateToggled(self, runBtnPressed):
		self.__runBtnPressed = runBtnPressed
		if not self.__runStateChangeBlocked:
			if self.__runBtnPressed:
				self.__run()
			else:
				self.__stop()

	def handleDirtyChange(self, dirty):
		if dirty:
			self.reqOnlineDiagButtonState.emit(False)

	def _onlineDiagToggled(self, onlineDiagBtnPressed):
		self.__onlineDiagBtnPressed = onlineDiagBtnPressed
		self.updateOnlineViewState()

	def updateOnlineViewState(self):
		self.onlineDiagChanged.emit(self.__onlineDiagBtnPressed)

	def updateVisibleLineRange(self, source, fromLine, toLine):
		try:
			client = self.mainWidget.getSimClient()
			if self.__onlineDiagBtnPressed and source:
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
		except MaintenanceRequest as e:
			self.__handleMaintenance(e)
			return

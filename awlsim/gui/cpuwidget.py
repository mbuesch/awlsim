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
			   host=None, port=None,
			   haveTunnel=False):
		self.spawned = spawned
		self.host = host
		self.port = port
		self.haveTunnel = haveTunnel
		self.__emitStateChanged()

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
	def __init__(self, parent=None):
		QToolBar.__init__(self, parent)

		self.onlineAction = OnlineSelectAction(self)
		self.addAction(self.onlineAction)
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

	def connectToCpuWidget(self, cpuWidget):
		self.onlineAction.toggled.connect(cpuWidget._onlineToggled)
		self.downloadAction.triggered.connect(cpuWidget.download)
		self.downloadSingleAction.triggered.connect(cpuWidget.downloadSingle)
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
		client.haveException.connect(self.__handleCpuException)
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

		self.newWin_Blocks()
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

	def newWin_Blocks(self):
		self.__addWindow(State_Blocks(self.mainWidget.getSimClient(),
					      self))

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
						     repetitionPeriod = 0.1,
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

	def __handleCpuException(self, exception):
		# The CPU is in an exception state.
		# Set our state to exception/stopped.
		# This will stop the CPU, if it wasn't already stopped.
		# Subsequent exception handlers might do additional steps.
		self.state.setState(RunState.STATE_EXCEPTION)
		self.stop()

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

	def __run(self, goOnlineFirst=True):
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

		# Put the CPU and the GUI into RUN state.
		try:
			# Put CPU into RUN mode, if it's not already there.
			client.setRunState(True)

			# Upload the GUI requests.
			if not self.__uploadMemReadAreas():
				self.stop()
				return
			self.updateOnlineViewState()

			# Start the message handler (fast mode).
			self.__startCoreMessageHandler(inRunMode=True)

			# Put the GUI into RUN mode.
			self.state.setState(RunState.STATE_RUN)
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
			while client.processMessages(0.02):
				pass
		except AwlSimError as e:
			self.state.setState(RunState.STATE_EXCEPTION)
			MessageBox.handleAwlSimError(self,
				"Core server error", e)
			self.stop()
			self.__stopCoreMessageHandler()
		except MaintenanceRequest as e:
			self.__handleMaintenance(e)
		except Exception:
			with suppressAllExc:
				client.setRunState(False)
			client.shutdown()
			handleFatalException(self)

	def __startCoreMessageHandler(self, inRunMode=False):
		self.__stopCoreMessageHandler()

		# Start the main message fetcher.
		self.__coreMsgTimer.start(0 if inRunMode else 300)

		# Start the periodic core work handler.
		self.__periodicCoreWork()
		self.__corePeriodicTimer.start(1000 if inRunMode else 300)

	def __stopCoreMessageHandler(self):
		# Stop the periodic core work handler.
		self.__corePeriodicTimer.stop()

		# Stop the main message fetcher.
		self.__coreMsgTimer.stop()

	# Periodic timer for core status work.
	def __periodicCoreWork(self):
		client = self.mainWidget.getSimClient()
		hasBlockTree = client.blockTreeModelActive()
		try:
			client.requestIdents(reqAwlSources = True,
					     reqSymTabSources = True,
					     reqHwModules = hasBlockTree,
					     reqLibSelections = hasBlockTree)
			if hasBlockTree:
				client.requestBlockInfo(reqOBInfo = True,
							reqFCInfo = True,
							reqFBInfo = True,
							reqDBInfo = True)
		except AwlSimError as e:
			self.state.setState(RunState.STATE_EXCEPTION)
			MessageBox.handleAwlSimError(self,
				"Core server error", e)
			self.stop()
			self.__stopCoreMessageHandler()
		except MaintenanceRequest as e:
			self.__handleMaintenance(e)
		except Exception:
			with suppressAllExc:
				client.setRunState(False)
			client.shutdown()
			handleFatalException(self)

	def __handleIdentsMsg(self, identsMsg):
		self.haveIdentsMsg.emit(identsMsg)

	def __stop(self):
		# Make sure the button is released.
		with self.__runStateChangeBlocked:
			self.stop()

		if self.isOnline():
			client = self.mainWidget.getSimClient()
			try:
				client.setRunState(False)
			except AwlSimError as e:
				MessageBox.handleAwlSimError(self,
					"Could not stop CPU", e)

		# Start the message handler (slow mode).
		self.__startCoreMessageHandler()

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
				dlg.deleteLater()
				self.goOffline()
				return
			dlg.deleteLater()

		linkConfig = project.getCoreLinkSettings()
		client = self.mainWidget.getSimClient()
		try:
			if linkConfig.getSpawnLocalEn():
				portRange = linkConfig.getSpawnLocalPortRange()
				interp = linkConfig.getSpawnLocalInterpreterList()
				client.setMode_FORK(portRange = portRange,
						    interpreterList = interp)
				host = port = None
			else:
				client.setMode_ONLINE(self, linkConfig)

			self.state.setCoreDetails(
				spawned = linkConfig.getSpawnLocalEn(),
				host = linkConfig.getConnectHost(),
				port = linkConfig.getConnectPort(),
				haveTunnel = (linkConfig.getTunnel() == linkConfig.TUNNEL_SSH))
			self.state.setState(RunState.STATE_ONLINE)

			if client.getRunState():
				# The core is already running.
				# Set the GUI to run state, too.
				self.__run(goOnlineFirst = False)

			# Start the message handler (slow mode).
			self.__startCoreMessageHandler()

		except AwlSimError as e:
			with suppressAllExc:
				self.__stopCoreMessageHandler()
			with suppressAllExc:
				client.setMode_OFFLINE()
			MessageBox.handleAwlSimError(self,
				"Error while trying to connect to CPU", e)
			self.goOffline()
			return
		except MaintenanceRequest as e:
			self.__handleMaintenance(e)

	def __goOffline(self):
		self.__stopCoreMessageHandler()
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

	# Reset/clear the CPU and upload all sources.
	def download(self):
		# Make sure we are online.
		self.goOnline()
		if not self.isOnline():
			return False

		client = self.mainWidget.getSimClient()
		project = self.mainWidget.getProject()
		awlSources = self.mainWidget.projectWidget.getAwlSources()
		fupSources = self.mainWidget.projectWidget.getFupSources()
		kopSources = self.mainWidget.projectWidget.getKopSources()
		symTabSources = self.mainWidget.projectWidget.getSymTabSources()
		libSelections = self.mainWidget.projectWidget.getLibSelections()
		if not all(awlSources) or not all(symTabSources):
			return False

		try:
			self.state.setState(RunState.STATE_LOAD)

			client.setRunState(False)
			client.reset()

			client.loadProject(project, loadSymTabs=False,
					   loadLibSelections=False,
					   loadSources=False,
					   loadFup=False,
					   loadKop=False)
			client.loadSymTabSources(symTabSources)
			client.loadLibraryBlocks(libSelections)
			client.loadAwlSources(awlSources)
			client.loadFupSources(fupSources)
			client.loadKopSources(kopSources)

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
		if self.__runBtnPressed:
			self.__run(goOnlineFirst = False)

		return True

	# Download the current source.
	def downloadSingle(self):
		# Make sure we are online.
		self.goOnline()
		if not self.isOnline():
			return False

		client = self.mainWidget.getSimClient()
		project = self.mainWidget.getProject()
		projectWidget = self.mainWidget.projectWidget
		selectedResource = projectWidget.getSelectedResource()

		try:
			self.state.setState(RunState.STATE_LOAD)

			if selectedResource == projectWidget.RES_SOURCES:
				awlSource = projectWidget.getCurrentAwlSource()
				if awlSource:
					printVerbose("Single AWL download: %s/%s" %\
						(awlSource.name,
						 awlSource.identHashStr))
					client.loadAwlSource(awlSource)
			elif selectedResource == projectWidget.RES_FUP:
				fupSource = projectWidget.getCurrentFupSource()
				if fupSource:
					printVerbose("Single FUP download: %s/%s" %\
						(fupSource.name,
						 fupSource.identHashStr))
					client.loadFupSource(fupSource)
			elif selectedResource == projectWidget.RES_KOP:
				kopSource = projectWidget.getCurrentKopSource()
				if kopSource:
					printVerbose("Single KOP download: %s/%s" %\
						(kopSource.name,
						 kopSource.identHashStr))
					client.loadKopSource(kopSource)
			elif selectedResource == projectWidget.RES_SYMTABS:
				symTabSource = projectWidget.getCurrentSymTabSource()
				if symTabSource:
					printVerbose("Single sym download: %s/%s" %\
						(symTabSource.name,
						 symTabSource.identHashStr))
					client.loadSymTabSource(symTabSource)
			elif selectedResource == projectWidget.RES_LIBSELS:
				libSelections = projectWidget.getLibSelections()
				printVerbose("Single libSelections download.")
				client.loadLibraryBlocks(libSelections)
			else:
				assert(0)

			if self.__runBtnPressed:
				self.state.setState(RunState.STATE_RUN)
			else:
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
				"Error while loading code (single source)", e)
			return False
		except MaintenanceRequest as e:
			self.__handleMaintenance(e)
			return False
		except Exception:
			client.shutdown()
			handleFatalException(self)
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

	def sizeHint(self):
		return QSize(550, 400)

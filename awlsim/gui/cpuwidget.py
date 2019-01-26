# -*- coding: utf-8 -*-
#
# AWL simulator - GUI CPU widget
#
# Copyright 2012-2019 Michael Buesch <m@bues.ch>
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

from awlsim.gui.util import *
from awlsim.gui.cpustate import *
from awlsim.gui.awlsimclient import *
from awlsim.gui.icons import *
from awlsim.gui.linkconfig import *
from awlsim.gui.runstate import *


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
	# CPU-stats signal.
	# Parameter: AwlSimMessage_CPUSTATE instance.
	haveCpuStats = Signal(AwlSimMessage_CPUSTATS)

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
		self.__onlineDiagIdentHash = None
		self.__onlineDiagFromLine = None
		self.__onlineDiagToLine = None

		self.__coreMsgTimer = QTimer(self)
		self.__coreMsgTimer.setSingleShot(False)
		self.__coreMsgTimer.timeout.connect(self.__processCoreMessages)

		self.__corePeriodicTimer = QTimer(self)
		self.__corePeriodicTimer.setSingleShot(False)
		self.__corePeriodicTimer.timeout.connect(self.__periodicCoreWork)

		client = self.getSimClient()
		client.haveException.connect(self.__handleCpuException)
		client.haveCpuDump.connect(self.__handleCpuDump)
		client.haveCpuStats.connect(self.haveCpuStats)
		client.haveInsnDump.connect(self.haveInsnDump)
		client.haveMemoryUpdate.connect(self.__handleMemoryUpdate)
		client.haveIdentsMsg.connect(self.__handleIdentsMsg)

		self.stateMdi = StateMdiArea(client=client, parent=self)
		self.stateMdi.setViewMode(QMdiArea.SubWindowView)
		self.stateMdi.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.stateMdi.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.layout().addWidget(self.stateMdi, 0, 0)

		self.stateMdi.subWinAdded.connect(lambda w: self.__uploadMemReadAreas())
		self.stateMdi.subWinClosed.connect(lambda w: self.__stateMdiWindowClosed(w))
		self.stateMdi.settingsChanged.connect(lambda: self.__uploadMemReadAreas())
		self.stateMdi.contentChanged.connect(
			lambda: self.mainWidget.setDirty(self.mainWidget.DIRTY_SLIGHT))
		self.stateMdi.openByIdentHash.connect(
			lambda mdiWin, identHash: self.mainWidget.openByIdentHash(identHash))

		self.state.stateChanged.connect(self.runStateChanged)

	def getProject(self):
		return self.mainWidget.getProject()

	def getSimClient(self):
		return self.mainWidget.getSimClient()

	def __stateMdiWindowClosed(self, mdiWin):
		QTimer.singleShot(0, self.__uploadMemReadAreas)

	def newWin_CPU(self):
		win = State_CPU(self.getSimClient())
		self.stateMdi.addCpuStateWindow(win)

	def newWin_DB(self):
		win = State_Mem(self.getSimClient(),
				AbstractDisplayWidget.ADDRSPACE_DB)
		self.stateMdi.addCpuStateWindow(win)

	def newWin_E(self):
		win = State_Mem(self.getSimClient(),
				AbstractDisplayWidget.ADDRSPACE_E)
		self.stateMdi.addCpuStateWindow(win)

	def newWin_A(self):
		win = State_Mem(self.getSimClient(),
				AbstractDisplayWidget.ADDRSPACE_A)
		self.stateMdi.addCpuStateWindow(win)

	def newWin_M(self):
		win = State_Mem(self.getSimClient(),
				AbstractDisplayWidget.ADDRSPACE_M)
		self.stateMdi.addCpuStateWindow(win)

	def newWin_T(self):
		win = State_Timer(self.getSimClient())
		self.stateMdi.addCpuStateWindow(win)

	def newWin_Z(self):
		win = State_Counter(self.getSimClient())
		self.stateMdi.addCpuStateWindow(win)

	def newWin_LCD(self):
		win = State_LCD(self.getSimClient())
		self.stateMdi.addCpuStateWindow(win)

	def newWin_Blocks(self):
		win = State_Blocks(self.getSimClient())
		self.stateMdi.addCpuStateWindow(win)

	# Upload the used memory area descriptors to the core.
	def __uploadMemReadAreas(self):
		client = self.getSimClient()
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
		client = self.getSimClient()

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
		client = self.getSimClient()

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

			# Re-Start the message handler.
			self.__startCoreMessageHandler()

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
		client = self.getSimClient()
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

	def __startCoreMessageHandler(self):
		self.__stopCoreMessageHandler()

		# Check if the CPU is in RUN mode.
		client = self.getSimClient()
		inRunMode = False
		with suppressAllExc:
			inRunMode = client.getRunState()

		# Start the main message fetcher.
		self.__coreMsgTimer.start(0 if inRunMode else 50)

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
		client = self.getSimClient()
		hasBlockTree = client.blockTreeModelActive()
		try:
			client.requestIdents(reqAwlSources=True,
					     reqFupSources=True,
					     reqKopSources=True,
					     reqSymTabSources=True,
					     reqHwModules=hasBlockTree,
					     reqLibSelections=hasBlockTree)
			if hasBlockTree:
				client.requestBlockInfo(reqOBInfo=True,
							reqFCInfo=True,
							reqFBInfo=True,
							reqDBInfo=True,
							reqUDTInfo=True)
			client.getCpuStats()
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
			client = self.getSimClient()
			try:
				client.setRunState(False)
			except AwlSimError as e:
				MessageBox.handleAwlSimError(self,
					"Could not stop CPU", e)

		# Re-Start the message handler.
		self.__startCoreMessageHandler()

		self.state.setState(RunState.STATE_ONLINE)

	def stop(self):
		self.reqRunButtonState.emit(False)

	def run(self):
		self.reqRunButtonState.emit(True)

	def __goOnline(self):
		project = self.getProject()

		if LinkConfigWidget.askWhenConnecting():
			dlg = LinkConfigDialog(project, self)
			dlg.settingsChanged.connect(self.configChanged)
			if dlg.exec_() != LinkConfigDialog.Accepted:
				dlg.deleteLater()
				self.goOffline()
				return
			dlg.deleteLater()

		linkConfig = project.getCoreLinkSettings()
		client = self.getSimClient()
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

			# Re-Start the message handler.
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
		client = self.getSimClient()
		try:
			client.setMode_OFFLINE()
		except AwlSimError as e:
			MessageBox.handleAwlSimError(self,
				"Error while trying to disconnect from CPU", e)
		# Release the stop-button.
		# This will _not_ stop the CPU, as we're offline already.
		self.stop()
		self.state.setState(RunState.STATE_OFFLINE)
		self.__stopCoreMessageHandler()

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

		client = self.getSimClient()
		project = self.getProject()
		try:
			self.state.setState(RunState.STATE_LOAD)

			client.setRunState(False)
			client.reset()

			client.loadProject(project)
			client.build()

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
		editMdiArea = self.mainWidget.editMdiArea
		mdiSubWin = editMdiArea.activeOpenSubWindow
		source = libSelections = None
		if mdiSubWin:
			if mdiSubWin.TYPE in {mdiSubWin.TYPE_AWL,
					      mdiSubWin.TYPE_FUP,
					      mdiSubWin.TYPE_KOP,
					      mdiSubWin.TYPE_SYMTAB,}:
				source = mdiSubWin.getSource()
			elif mdiSubWin.TYPE == mdiSubWin.TYPE_LIBSEL:
				libSelections = mdiSubWin.getLibSelections()
			else:
				assert(0)
		if not mdiSubWin or (not source and not libSelections):
			QMessageBox.critical(self,
				"No source selected.",
				"Cannot download a single source.\n"
				"No source has been opened in the edit area.",
				QMessageBox.Ok)
			return False

		# Make sure we are online.
		self.goOnline()
		if not self.isOnline():
			return False

		client = self.getSimClient()
		project = self.getProject()
		try:
			self.state.setState(RunState.STATE_LOAD)

			if mdiSubWin.TYPE == mdiSubWin.TYPE_AWL:
				printVerbose("Single AWL download: %s/%s" %\
					(source.name,
					 source.identHashStr))
				client.loadAwlSource(source)
			elif mdiSubWin.TYPE == mdiSubWin.TYPE_FUP:
				printVerbose("Single FUP download: %s/%s" %\
					(source.name,
					 source.identHashStr))
				client.loadFupSource(source)
			elif mdiSubWin.TYPE == mdiSubWin.TYPE_KOP:
				printVerbose("Single KOP download: %s/%s" %\
					(source.name,
					 source.identHashStr))
				client.loadKopSource(source)
			elif mdiSubWin.TYPE == mdiSubWin.TYPE_SYMTAB:
				printVerbose("Single sym download: %s/%s" %\
					(source.name,
					 source.identHashStr))
				client.loadSymTabSource(source)
			elif mdiSubWin.TYPE == mdiSubWin.TYPE_LIBSEL:
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

	def resetCpu(self):
		"""Reset the CPU.
		"""

		# Make sure we are online.
		self.goOnline()
		if not self.isOnline():
			return False

		client = self.getSimClient()
		try:
			client.setRunState(False)
			client.reset()
		except AwlParserError as e:
			MessageBox.handleAwlParserError(self, e)
			return False
		except AwlSimError as e:
			MessageBox.handleAwlSimError(self,
				"Error while reseting CPU", e)
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

	def handleDirtyChange(self, dirtyLevel):
		if dirtyLevel == self.mainWidget.DIRTY_FULL:
			self.reqOnlineDiagButtonState.emit(False)

	def _onlineDiagToggled(self, onlineDiagBtnPressed):
		self.__onlineDiagBtnPressed = onlineDiagBtnPressed
		self.updateOnlineViewState()

	def updateOnlineViewState(self):
		self.onlineDiagChanged.emit(self.__onlineDiagBtnPressed)

	def updateVisibleLineRange(self, source, fromLine, toLine):
		try:
			client = self.getSimClient()
			if self.__onlineDiagBtnPressed and source:
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
			MessageBox.handleAwlSimError(self,
				"Failed to setup instruction dumping", e)
			return
		except MaintenanceRequest as e:
			self.__handleMaintenance(e)
			return

	def sizeHint(self):
		return QSize(550, 200)

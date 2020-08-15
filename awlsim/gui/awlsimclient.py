# -*- coding: utf-8 -*-
#
# AWL simulator - GUI simulator client access
#
# Copyright 2014-2020 Michael Buesch <m@bues.ch>
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

from awlsim.gui.util import *
from awlsim.gui.blocktreewidget import *
from awlsim.gui.runstate import *
from awlsim.gui.linkconfig import *
from awlsim.gui.validatorsched import *

from awlsim.coreclient.client import *
from awlsim.coreclient.sshtunnel import *


class GuiSSHTunnel(SSHTunnel, QDialog):
	"""SSH tunnel helper with GUI.
	"""

	def __init__(self, parent, *args, **kwargs):
		self.__cancelRequest = False

		QDialog.__init__(self, parent)
		SSHTunnel.__init__(self, *args, **kwargs)

		self.setLayout(QGridLayout())
		self.setWindowTitle("Establishing SSH tunnel...")

		self.log = QPlainTextEdit(self)
		self.log.setFont(getDefaultFixedFont())
		self.log.setReadOnly(True)
		self.layout().addWidget(self.log, 0, 0)

		self.resize(750, 180)

	def closeEvent(self, ev):
		self.__cancelRequest = True
		QDialog.closeEvent(self, ev)

	def sleep(self, seconds):
		sleepWithEventLoop(seconds, excludeInput=False)
		return not self.__cancelRequest

	def connect(self):
		self.__cancelRequest = False
		self.hide()
		self.setWindowModality(Qt.ApplicationModal)
		self.show()
		try:
			result = SSHTunnel.connect(self, timeout=None)
		except AwlSimError as e:
			QMessageBox.critical(self,
				"Failed to establish SSH tunnel",
				"Failed to establish SSH tunnel:\n\n%s" % str(e))
			e.setSeenByUser()
			raise e
		finally:
			self.hide()
		return result

	def sshMessage(self, message, isDebug):
		"""Print a SSH log message.
		"""
		if not isDebug:
			self.log.setPlainText(self.log.toPlainText() + "\n" + message)
			sb = self.log.verticalScrollBar()
			sb.setSliderPosition(sb.maximum())

	def getPassphrase(self, prompt):
		"""Get a password from the user.
		"""
		pw, ok = QInputDialog.getText(self,
			"Please enter SSH password",
			"Please enter SSH password for '%s@%s':" %(
				self.sshUser, self.remoteHost),
			QLineEdit.Password)
		if not ok:
			return None
		try:
			return pw.encode("UTF-8", "ignore")
		except UnicodeError:
			return None

	def hostAuth(self, prompt):
		"""Get the user answer to the host authentication question.
		This function returns a boolean.
		"""
		res = QMessageBox.question(self,
			"Confirm host authenticity?",
			prompt,
			QMessageBox.Yes | QMessageBox.No,
			QMessageBox.No)
		return res == QMessageBox.Yes

class OnlineData(QObject):
	"""Container for data retrieved from the server.
	"""

	# Symbol table signal.
	# Contains only SymTabSources that can be parsed without errors.
	# Parameter: a list of tuples such as:
	#		[ (SymTabSource, SymbolTable), ... ]
	symTabsUpdate = Signal(list)

	def __init__(self, client):
		QObject.__init__(self)
		self.__client = client

		self.reset()

	def reset(self):
		self.__symTabCache = {}

	def __getSymTabByIdent(self, identHash):
		try:
			symTabSrc = self.__client.getSymTabSource(identHash)
			if symTabSrc:
				return SymTabParser.parseSource(symTabSrc)
		except AwlSimError as e:
			return None
		return None

	def handle_IDENTS(self, msg):
		# Parse the symbol table sources
		newSymTabCache = {}
		symTabList = []
		for symTabSrc in msg.symTabSources:
			identHash = symTabSrc.identHash
			symTab = self.__symTabCache.get(identHash, None)
			if symTab is None:
				symTab = self.__getSymTabByIdent(identHash)
			newSymTabCache[identHash] = symTab
			self.__symTabCache[identHash] = symTab
			if symTab is not None:
				symTabList.append((symTabSrc, symTab))
		self.__symTabCache = newSymTabCache
		self.symTabsUpdate.emit(symTabList)

class GuiAwlSimClient_LowLevel(AwlSimClient, QObject):
	"""AwlSimClient for GUI.
	Low level part.
	"""

	# CPU exception signal.
	haveException = Signal(AwlSimError)

	# CPU-dump signal.
	# Parameter: The dump text.
	haveCpuDump = Signal(str)

	# CPU-stats signal.
	# Parameter: AwlSimMessage_CPUSTATE instance.
	haveCpuStats = Signal(AwlSimMessage_CPUSTATS)

	# Instruction dump signal.
	# Parameter: AwlSimMessage_INSNSTATE instance.
	haveInsnDump = Signal(AwlSimMessage_INSNSTATE)

	# Memory update signal.
	# Parameter: A list of MemoryArea instances.
	haveMemoryUpdate = Signal(list)

	# Ident hashes signal.
	# Parameter: AwlSimMessage_IDENTS instance.
	haveIdentsMsg = Signal(AwlSimMessage_IDENTS)

	# Block info signal.
	# Parameter: AwlSimMessage_BLOCKINFO instance.
	haveBlockInfoMsg = Signal(AwlSimMessage_BLOCKINFO)

	# The client mode
	EnumGen.start
	MODE_OFFLINE	= EnumGen.item # Not connected
	MODE_ONLINE	= EnumGen.item # Connected to an existing core
	MODE_FORK	= EnumGen.item # Online to a newly forked core
	EnumGen.end

	def __init__(self):
		QObject.__init__(self)
		AwlSimClient.__init__(self)

		self.__onlineData = OnlineData(self)

		self.__setMode(self.MODE_OFFLINE)

		self.__blockTreeModelManager = None
		self.__blockTreeModel = None

	# Override sleep handler
	def sleep(self, seconds):
		sleepWithEventLoop(seconds, excludeInput=True)

	# Override exception handler
	def handle_EXCEPTION(self, exception):
		# Emit the exception signal.
		self.haveException.emit(exception)
		# Call the default exception handler.
		AwlSimClient.handle_EXCEPTION(self, exception)

	# Override cpudump handler
	def handle_CPUDUMP(self, dumpText):
		self.haveCpuDump.emit(dumpText)

	# Override cpustate handler
	def handle_CPUSTATS(self, msg):
		self.haveCpuStats.emit(msg)

	# Override memory update handler
	def handle_MEMORY(self, memAreas):
		self.haveMemoryUpdate.emit(memAreas)

	# Override instruction state handler
	def handle_INSNSTATE(self, msg):
		self.haveInsnDump.emit(msg)

	# Override ident hashes handler
	def handle_IDENTS(self, msg):
		self.__onlineData.handle_IDENTS(msg)
		self.haveIdentsMsg.emit(msg)

	# Override block info handler
	def handle_BLOCKINFO(self, msg):
		self.haveBlockInfoMsg.emit(msg)

	def getMode(self):
		return self.__mode

	def __setMode(self, mode, host = None, port = None, tunnel = None):
		self.__mode = mode
		self.__host = host
		self.__port = port
		self.__tunnel = tunnel
		self.__onlineData.reset()

	def shutdown(self):
		# Shutdown the client.
		# If we are in FORK mode, this will also terminate
		# the forked core.
		# If we are in ONLINE mode, this will only
		# close the connection and possibly the tunnel.
		if self.__tunnel:
			self.__tunnel.shutdown()
			self.__tunnel = None
		AwlSimClient.shutdown(self)
		self.__setMode(self.MODE_OFFLINE)

	def setMode_OFFLINE(self):
		if self.__mode == self.MODE_OFFLINE:
			return
		if self.serverProcess:
			# Put the spawned core into STOP state.
			try:
				if not self.setRunState(False):
					raise RuntimeError
			except (AwlSimError, RuntimeError) as e:
				with suppressAllExc:
					self.killSpawnedServer()
		self.shutdownTransceiver()
		self.__setMode(self.MODE_OFFLINE)

	def setMode_ONLINE(self, parentWidget, linkSettings):
		host = linkSettings.getConnectHost()
		port = linkSettings.getConnectPort()
		timeout = linkSettings.getConnectTimeoutMs() / 1000.0
		wantTunnel = (linkSettings.getTunnel() == linkSettings.TUNNEL_SSH)
		sshUser = linkSettings.getSSHUser()
		sshPort = linkSettings.getSSHPort()
		sshExecutable = linkSettings.getSSHExecutable()

		if self.__mode == self.MODE_ONLINE:
			if wantTunnel and self.__tunnel:
				if host == self.__tunnel.remoteHost and\
				   port == self.__tunnel.remotePort and\
				   sshUser == self.__tunnel.sshUser and\
				   sshPort == self.__tunnel.sshPort and\
				   sshExecutable == self.__tunnel.sshExecutable:
					# We are already up and running.
					return
			elif not wantTunnel and not self.__tunnel:
				if self.__host == host and\
				   self.__port == port:
					# We are already up and running.
					return

		self.__interpreterList = None
		self.shutdown()

		tunnel = None
		try:
			if wantTunnel:
				localPort = linkSettings.getTunnelLocalPort()
				if localPort == linkSettings.TUNNEL_LOCPORT_AUTO:
					localPort = None
				tunnel = GuiSSHTunnel(parentWidget,
					remoteHost = host,
					remotePort = port,
					localPort = localPort,
					sshUser = sshUser,
					sshPort = sshPort,
					sshExecutable = sshExecutable
				)
				host, port = tunnel.connect()
				self.__tunnel = tunnel
			self.connectToServer(host = host,
					     port = port,
					     timeout = timeout)
		except AwlSimError as e:
			with suppressAllExc:
				self.shutdown()
			raise e
		self.__setMode(self.MODE_ONLINE, host = host,
			       port = port, tunnel = tunnel)

	def setMode_FORK(self, portRange,
			 interpreterList=None):
		host = "localhost"
		if self.__mode == self.MODE_FORK:
			if self.__port in portRange and\
			   self.__interpreterList == interpreterList:
				assert(self.__host == host)
				# We are already up and running.
				return
		try:
			if self.serverProcess:
				if self.serverProcessPort not in portRange or\
				   self.__interpreterList != interpreterList:
					self.killSpawnedServer()
			if not self.serverProcess:
				self.spawnServer(interpreter = interpreterList,
						 listenHost = host,
						 listenPort = portRange)
			self.shutdownTransceiver()
			self.connectToServer(host=host,
					     port=self.serverProcessPort,
					     timeout=10.0)
		except AwlSimError as e:
			with suppressAllExc:
				self.shutdown()
			raise e
		self.__setMode(self.MODE_FORK,
			       host=host,
			       port=self.serverProcessPort)
		self.__interpreterList = interpreterList

	def getBlockTreeModelRef(self):
		"""Get an ObjRef to the BlockTreeModel object."""

		if not self.__blockTreeModelManager:
			# Create a new block tree model
			self.__blockTreeModelManager = ObjRefManager("BlockTreeModel",
				allDestroyedCallback = self.__allBlockTreeModelRefsDestroyed)
			self.__blockTreeModel = BlockTreeModel(self)
			# Connect block tree message handlers
			self.haveIdentsMsg.connect(self.__blockTreeModel.handle_IDENTS)
			self.haveBlockInfoMsg.connect(self.__blockTreeModel.handle_BLOCKINFO)
			self.__onlineData.symTabsUpdate.connect(self.__blockTreeModel.handle_symTabInfo)

		return ObjRef.make(name="BlockTreeModel",
				   manager=self.__blockTreeModelManager,
				   obj=self.__blockTreeModel)

	def blockTreeModelActive(self):
		"""Returns True, if there is at least one active ref to
		the BlockTreeModel."""

		if self.__blockTreeModelManager:
			return self.__blockTreeModelManager.hasReferences
		return False

	def __allBlockTreeModelRefsDestroyed(self):
		# The last block tree model reference died. Destroy it.
		self.__blockTreeModelManager = None
		self.__blockTreeModel = None

class GuiAwlSimClient(GuiAwlSimClient_LowLevel):
	"""AwlSimClient for GUI.
	High level part.
	"""

	def __init__(self, mainWidget):
		self.__mainWindow = mainWidget
		GuiAwlSimClient_LowLevel.__init__(self)

		self.__actionGoOnlineBlocked = Blocker()
		self.__actionGoOfflineBlocked = Blocker()
		self.__actionDownloadBlocked = Blocker()
		self.__actionDownloadSingleBlocked = Blocker()
		self.__actionResetCpuBlocked = Blocker()
		self.__actionGoRunBlocked = Blocker()
		self.__actionGoStopBlocked = Blocker()

		self.__guiRunState = GuiRunState()

		self.__coreMsgTimer = QTimer(self)
		self.__coreMsgTimer.setSingleShot(False)
		self.__coreMsgTimer.timeout.connect(self.__processCoreMessages)

		self.__corePeriodicTimer = QTimer(self)
		self.__corePeriodicTimer.setSingleShot(False)
		self.__corePeriodicTimer.timeout.connect(self.__periodicCoreWork)

		self.haveException.connect(self.__handleCpuException)

	@property
	def guiRunState(self):
		"""Get the central GuiRunState().
		"""
		return self.__guiRunState

	def getProject(self):
		"""Get the active Project().
		"""
		return self.__mainWindow.getProject()

	def getEditMdiArea(self):
		return self.__mainWindow.mainWidget.editMdiArea

	# Periodic timer for core message handling.
	def __processCoreMessages(self):
		try:
			# Receive messages, until we hit a timeout
			while self.processMessages(0.02):
				pass
		except AwlSimError as e:
			with MessageBox.awlSimErrorBlocked:
				self.guiRunState.setState(GuiRunState.STATE_EXCEPTION)
			MessageBox.handleAwlSimError(self.__mainWindow,
				"Core server error", e)
			with MessageBox.awlSimErrorBlocked:
				self.action_goStop()
				self.__stopCoreMessageHandler()
		except MaintenanceRequest as e:
			self.handleMaintenance(e)
		except Exception:
			with suppressAllExc:
				self.setRunState(False)
			with suppressAllExc:
				self.shutdown()
			handleFatalException(self.__mainWindow)

	def __startCoreMessageHandler(self):
		self.__stopCoreMessageHandler()

		# Check if the CPU is in RUN mode.
		inRunMode = False
		with suppressAllExc:
			inRunMode = self.getRunState()

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

	def __periodicCoreWork(self):
		"""Periodic timer for core status work.
		"""
		hasBlockTree = self.blockTreeModelActive()
		try:
			self.requestIdents(reqAwlSources=True,
					   reqFupSources=True,
					   reqKopSources=True,
					   reqSymTabSources=True,
					   reqHwModules=hasBlockTree,
					   reqLibSelections=hasBlockTree)
			if hasBlockTree:
				self.requestBlockInfo(reqOBInfo=True,
						      reqFCInfo=True,
						      reqFBInfo=True,
						      reqDBInfo=True,
						      reqUDTInfo=True)
			self.getCpuStats()
		except AwlSimError as e:
			with MessageBox.awlSimErrorBlocked:
				self.guiRunState.setState(GuiRunState.STATE_EXCEPTION)
			MessageBox.handleAwlSimError(self.__mainWindow,
				"Core server error", e)
			with MessageBox.awlSimErrorBlocked:
				self.action_goStop()
				self.__stopCoreMessageHandler()
		except MaintenanceRequest as e:
			self.handleMaintenance(e)
		except Exception:
			with suppressAllExc:
				self.setRunState(False)
			with suppressAllExc:
				self.shutdown()
			handleFatalException(self.__mainWindow)

	def handleMaintenance(self, maintRequest):
		"""Handle a maintenance request exception.
		"""
		if maintRequest.requestType == MaintenanceRequest.TYPE_SHUTDOWN:
			res = QMessageBox.question(self.__mainWindow,
				"Shut down application?",
				"The core server requested an "
				"application shutdown.\n"
				"Do you want to close Awlsim GUI?",
				QMessageBox.Yes | QMessageBox.No,
				QMessageBox.No)
			if res == QMessageBox.Yes:
				print("Shutting down, as requested by server...")
				self.shutdown()
				QApplication.exit(0)
			else:
				self.action_goStop()
				self.action_goOffline()
		elif (maintRequest.requestType == MaintenanceRequest.TYPE_STOP or
		      maintRequest.requestType == MaintenanceRequest.TYPE_RTTIMEOUT):
			self.action_goStop()
		else:
			print("Unknown maintenance request %d" % (
			      maintRequest.requestType))
			self.action_goStop()

	def __validatePreDownload(self, project):
		guiSettings = project.getGuiSettings()
		if not guiSettings.getPreDownloadValidationEn():
			return True

		printInfo("Validating project before downloading...")
		valSched = GuiValidatorSched.get()
		exception = valSched.syncValidation(project)
		if exception is valSched.TIMEOUT:
			printError("Project validation timeout. Loading anyway...")
		elif exception is not None:
			res = MessageBox.handleAwlSimError(self.__mainWindow,
				"\nPre-download validation of the project failed.\n"
				"Continuing the download may bring the CPU to STOP.\n\n"
				"Do you want to continue or cancel "
				"downloading the project to the CPU?",
				exception,
				okButton=False,
				continueButton=True,
				cancelButton=True)
			if res != MessageBox.Accepted:
				return False
		return True

	def action_goOnline(self):
		"""Connect to a core server.
		"""
		if self.__actionGoOnlineBlocked:
			return True
		with self.__actionGoOnlineBlocked:

			if self.guiRunState != GuiRunState.STATE_OFFLINE:
				return True

			project = self.getProject()

			if LinkConfigWidget.askWhenConnecting():
				dlg = LinkConfigDialog(project, self.__mainWindow)
				dlg.settingsChanged.connect(self.__mainWindow.mainWidget.somethingChanged)
				if dlg.exec_() != LinkConfigDialog.Accepted:
					dlg.deleteLater()
					self.action_goOffline()
					return False
				dlg.deleteLater()

			linkConfig = project.getCoreLinkSettings()
			try:
				if linkConfig.getSpawnLocalEn():
					portRange = linkConfig.getSpawnLocalPortRange()
					interp = linkConfig.getSpawnLocalInterpreterList()
					self.setMode_FORK(portRange=portRange,
							  interpreterList=interp)
					host = port = None
				else:
					self.setMode_ONLINE(self.__mainWindow, linkConfig)

				self.guiRunState.setCoreDetails(
					spawned=linkConfig.getSpawnLocalEn(),
					host=linkConfig.getConnectHost(),
					port=linkConfig.getConnectPort(),
					haveTunnel=(linkConfig.getTunnel() == linkConfig.TUNNEL_SSH))
				self.guiRunState.setState(GuiRunState.STATE_ONLINE)

				if self.getRunState():
					# The core is already running.
					# Set the GUI to run state, too.
					self.guiRunState.setState(GuiRunState.STATE_RUN)

				# Re-Start the message handler.
				self.__startCoreMessageHandler()

			except AwlSimError as e:
				with suppressAllExc:
					self.__stopCoreMessageHandler()
				with suppressAllExc:
					self.setMode_OFFLINE()
				MessageBox.handleAwlSimError(self.__mainWindow,
					"Error while trying to connect to CPU", e)
				with MessageBox.awlSimErrorBlocked:
					self.action_goOffline()
				return False
			except MaintenanceRequest as e:
				self.handleMaintenance(e)

			return True

	def action_goOffline(self):
		"""Disconnect from the core server.
		"""
		if self.__actionGoOfflineBlocked:
			return True
		with self.__actionGoOfflineBlocked:

			if self.guiRunState == GuiRunState.STATE_OFFLINE:
				return True

			try:
				self.setMode_OFFLINE()
			except AwlSimError as e:
				MessageBox.handleAwlSimError(self.__mainWindow,
					"Error while trying to disconnect from CPU", e)

			self.guiRunState.setState(GuiRunState.STATE_OFFLINE)
			self.__stopCoreMessageHandler()

			return True

	# Reset/clear the CPU and upload all sources.
	def action_download(self):
		if self.__actionDownloadBlocked:
			return True
		with self.__actionDownloadBlocked:

			prevGuiRunState = self.guiRunState.state

			# Make sure we are online.
			self.action_goOnline()
			if self.guiRunState < GuiRunState.STATE_ONLINE:
				return False

			project = self.getProject()
			try:
				self.guiRunState.setState(GuiRunState.STATE_LOAD)

				if not self.__validatePreDownload(project):
					self.guiRunState.setState(prevGuiRunState)
					return False

				self.setRunState(False)
				self.reset()

				self.loadProject(project)
				self.build()

				self.guiRunState.setState(GuiRunState.STATE_ONLINE)
			except AwlParserError as e:
				with MessageBox.awlSimErrorBlocked:
					self.guiRunState.setState(GuiRunState.STATE_ONLINE)
					self.action_goStop()
				MessageBox.handleAwlParserError(self, e)
				return False
			except AwlSimError as e:
				with MessageBox.awlSimErrorBlocked:
					self.guiRunState.setState(GuiRunState.STATE_ONLINE)
					self.action_goStop()
				MessageBox.handleAwlSimError(self.__mainWindow,
					"Error while loading code", e)
				return False
			except MaintenanceRequest as e:
				self.handleMaintenance(e)
				return False
			except Exception:
				with suppressAllExc:
					self.shutdown()
				handleFatalException(self.__mainWindow)

			# If we were RUNning before download, put
			# the CPU into RUN state again.
			if prevGuiRunState >= GuiRunState.STATE_RUN:
				self.action_goRun()

			return True

	# Download the current source.
	def action_downloadSingle(self):
		if self.__actionDownloadSingleBlocked:
			return True
		with self.__actionDownloadSingleBlocked:

			prevGuiRunState = self.guiRunState.state

			mdiSubWin = self.getEditMdiArea().activeOpenSubWindow
			source = libSelections = None
			if mdiSubWin:
				if mdiSubWin.TYPE in (mdiSubWin.TYPE_AWL,
						      mdiSubWin.TYPE_FUP,
						      mdiSubWin.TYPE_KOP,
						      mdiSubWin.TYPE_SYMTAB,):
					source = mdiSubWin.getSource()
				elif mdiSubWin.TYPE == mdiSubWin.TYPE_LIBSEL:
					libSelections = mdiSubWin.getLibSelections()
				else:
					assert(0)
			if not mdiSubWin or (not source and not libSelections):
				QMessageBox.critical(self.__mainWindow,
					"No source selected.",
					"Cannot download a single source.\n"
					"No source has been opened in the edit area.",
					QMessageBox.Ok)
				return False

			# Make sure we are online.
			self.action_goOnline()
			if self.guiRunState < GuiRunState.STATE_ONLINE:
				return False

			project = self.getProject()
			try:
				self.guiRunState.setState(GuiRunState.STATE_LOAD)

				if not self.__validatePreDownload(project):
					self.guiRunState.setState(prevGuiRunState)
					return False

				if mdiSubWin.TYPE == mdiSubWin.TYPE_AWL:
					printVerbose("Single AWL download: %s/%s" %\
						(source.name,
						 source.identHashStr))
					self.loadAwlSource(source)
				elif mdiSubWin.TYPE == mdiSubWin.TYPE_FUP:
					printVerbose("Single FUP download: %s/%s" %\
						(source.name,
						 source.identHashStr))
					self.loadFupSource(source)
				elif mdiSubWin.TYPE == mdiSubWin.TYPE_KOP:
					printVerbose("Single KOP download: %s/%s" %\
						(source.name,
						 source.identHashStr))
					self.loadKopSource(source)
				elif mdiSubWin.TYPE == mdiSubWin.TYPE_SYMTAB:
					printVerbose("Single sym download: %s/%s" %\
						(source.name,
						 source.identHashStr))
					self.loadSymTabSource(source)
				elif mdiSubWin.TYPE == mdiSubWin.TYPE_LIBSEL:
					printVerbose("Single libSelections download.")
					self.loadLibraryBlocks(libSelections)
				else:
					assert(0)

				self.guiRunState.setState(prevGuiRunState)
			except AwlParserError as e:
				with MessageBox.awlSimErrorBlocked:
					self.guiRunState.setState(GuiRunState.STATE_ONLINE)
					self.action_goStop()
				MessageBox.handleAwlParserError(self.__mainWindow, e)
				return False
			except AwlSimError as e:
				with MessageBox.awlSimErrorBlocked:
					self.guiRunState.setState(GuiRunState.STATE_ONLINE)
					self.action_goStop()
				MessageBox.handleAwlSimError(self.__mainWindow,
					"Error while loading code (single source)", e)
				return False
			except MaintenanceRequest as e:
				self.handleMaintenance(e)
				return False
			except Exception:
				with suppressAllExc:
					self.shutdown()
				handleFatalException(self.__mainWindow)
			return True

	def action_resetCpu(self):
		"""Reset the CPU.
		"""
		if self.__actionResetCpuBlocked:
			return True
		with self.__actionResetCpuBlocked:

			# Make sure we are online.
			self.action_goOnline()
			if self.guiRunState < GuiRunState.STATE_ONLINE:
				return False

			try:
				self.setRunState(False)
				self.reset()
			except AwlParserError as e:
				MessageBox.handleAwlParserError(self.__mainWindow, e)
				return False
			except AwlSimError as e:
				MessageBox.handleAwlSimError(self.__mainWindow,
					"Error while reseting CPU", e)
				return False
			except MaintenanceRequest as e:
				self.handleMaintenance(e)
				return False
			except Exception:
				with suppressAllExc:
					self.shutdown()
				handleFatalException(self.__mainWindow)

			return True

	def action_goRun(self):
		if self.__actionGoRunBlocked:
			return True
		with self.__actionGoRunBlocked:

			self.action_goOnline()
			if self.guiRunState < GuiRunState.STATE_ONLINE:
				self.action_goStop()
				return False

			# Put the CPU and the GUI into RUN state.
			try:
				# Put CPU into RUN mode, if it's not already there.
				self.setRunState(True)

				# Put the GUI into RUN mode.
				self.guiRunState.setState(GuiRunState.STATE_RUN)

				# Re-Start the message handler.
				self.__startCoreMessageHandler()
			except AwlSimError as e:
				with MessageBox.awlSimErrorBlocked:
					self.guiRunState.setState(GuiRunState.STATE_EXCEPTION)
				MessageBox.handleAwlSimError(self.__mainWindow,
					"Could not start CPU", e)
				with MessageBox.awlSimErrorBlocked:
					self.action_goStop()
			except MaintenanceRequest as e:
				self.handleMaintenance(e)

			return True

	def action_goStop(self):
		if self.__actionGoStopBlocked:
			return True
		with self.__actionGoStopBlocked:

			if self.guiRunState >= GuiRunState.STATE_ONLINE:
				try:
					self.setRunState(False)
				except AwlSimError as e:
					MessageBox.handleAwlSimError(self.__mainWindow,
						"Could not stop CPU", e)

			self.guiRunState.setState(GuiRunState.STATE_ONLINE)

			# Re-Start the message handler.
			self.__startCoreMessageHandler()

			return True

	def __handleCpuException(self, exception):
		# The CPU is in an exception state.
		# Set our state to exception/stopped.
		# This will stop the CPU, if it wasn't already stopped.
		# Subsequent exception handlers might do additional steps.
		with MessageBox.awlSimErrorBlocked:
			self.guiRunState.setState(GuiRunState.STATE_EXCEPTION)
			self.action_goStop()

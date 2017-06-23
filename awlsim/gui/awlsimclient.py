# -*- coding: utf-8 -*-
#
# AWL simulator - GUI simulator client access
#
# Copyright 2014-2016 Michael Buesch <m@bues.ch>
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

from awlsim.coreclient.client import *
from awlsim.coreclient.sshtunnel import *


def sleepWithEventLoop(seconds, excludeInput=True):
	end = monotonic_time() + seconds
	eventFlags = QEventLoop.AllEvents |\
		(QEventLoop.ExcludeUserInputEvents if excludeInput else 0)
	while monotonic_time() < end:
		QApplication.processEvents(eventFlags, 10)
		QThread.msleep(10)

class GuiSSHTunnel(SSHTunnel, QDialog):
	"""SSH tunnel helper with GUI.
	"""

	def __init__(self, parent, *args, **kwargs):
		QDialog.__init__(self, parent)
		SSHTunnel.__init__(self, *args, **kwargs)

		self.setLayout(QGridLayout())
		self.setWindowTitle("Establishing SSH tunnel...")

		self.log = QPlainTextEdit(self)
		self.log.setFont(getDefaultFixedFont())
		self.log.setReadOnly(True)
		self.layout().addWidget(self.log, 0, 0)

		self.resize(750, 180)

	def sleep(self, seconds):
		sleepWithEventLoop(seconds, excludeInput=True)

	def connect(self):
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

class GuiAwlSimClient(AwlSimClient, QObject):
	# CPU exception signal.
	haveException = Signal(AwlSimError)

	# CPU-dump signal.
	# Parameter: The dump text.
	haveCpuDump = Signal(str)

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

		self.onlineData = OnlineData(self)

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

	# Override memory update handler
	def handle_MEMORY(self, memAreas):
		self.haveMemoryUpdate.emit(memAreas)

	# Override instruction state handler
	def handle_INSNSTATE(self, msg):
		self.haveInsnDump.emit(msg)

	# Override ident hashes handler
	def handle_IDENTS(self, msg):
		self.onlineData.handle_IDENTS(msg)
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
		self.onlineData.reset()

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
			self.onlineData.symTabsUpdate.connect(self.__blockTreeModel.handle_symTabInfo)

		return ObjRef.make("BlockTreeModel", self.__blockTreeModelManager,
				   self.__blockTreeModel)

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

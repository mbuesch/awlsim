# -*- coding: utf-8 -*-
#
# AWL simulator - GUI Awlsim link configuration widget
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

from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim.common.compat import *

from awlsim.gui.configdialog import *
from awlsim.gui.util import *
from awlsim.gui.awlsimclient import *

import sys


class _SpawnConfigWidget(QGroupBox):
	def __init__(self, parent=None):
		QGroupBox.__init__(self, parent)
		self.setLayout(QGridLayout())

		toolTip = "A semicolon (;) separated list of Python "\
			  "interpreters used to run the simulator core.\n"\
			  "The list is tried first to last element, until "\
			  "one working interpreter is found.\n\n"\
			  "The special value $CURRENT is the "\
			  "interpreter that is used to run the frontend.\n"\
			  "The special value $DEFAULT will expand to this list:\n"\
			  "    %s\n\n"\
			  "---> If you are unsure, leave this as $DEFAULT <---" %\
			  CoreLinkSettings.DEFAULT_INTERPRETERS
		label = QLabel("Python interpreter list:", self)
		label.setToolTip(toolTip)
		self.layout().addWidget(label, 0, 0)
		self.interpreterList = QLineEdit(self)
		self.interpreterList.setFont(getDefaultFixedFont(
			self.interpreterList.font().pointSize()))
		self.interpreterList.setToolTip(toolTip)
		self.layout().addWidget(self.interpreterList, 0, 1)

		toolTip = "Spawn the new simulator core server "\
			  "on any port within this range.\n\n"\
			  "---> If you are unsure, do not change the defaults. <---"
		label = QLabel("Port range:", self)
		label.setToolTip(toolTip)
		self.layout().addWidget(label, 1, 0)
		hbox = QHBoxLayout()
		self.portRangeStart = QSpinBox(self)
		self.portRangeStart.setPrefix("from ")
		self.portRangeStart.setRange(0, 0xFFFF)
		self.portRangeStart.setToolTip(toolTip)
		hbox.addWidget(self.portRangeStart)
		self.portRangeEnd = QSpinBox(self)
		self.portRangeEnd.setPrefix("to ")
		self.portRangeEnd.setRange(0, 0xFFFF)
		self.portRangeEnd.setToolTip(toolTip)
		hbox.addWidget(self.portRangeEnd)
		self.layout().addLayout(hbox, 1, 1)

		self.portRangeStart.valueChanged.connect(self.__startChanged)
		self.portRangeEnd.valueChanged.connect(self.__endChanged)

	def __startChanged(self, newStart):
		if newStart > self.portRangeEnd.value():
			self.portRangeEnd.setValue(newStart)

	def __endChanged(self, newEnd):
		if newEnd < self.portRangeStart.value():
			self.portRangeStart.setValue(newEnd)

class _SSHConfigWidget(QGroupBox):
	def __init__(self, parent=None):
		QGroupBox.__init__(self, parent)
		self.setLayout(QGridLayout())

		toolTip = "The SSH login user name of the remote server."
		label = QLabel("SSH login user:", self)
		label.setToolTip(toolTip)
		self.layout().addWidget(label, 0, 0)
		self.user = QLineEdit(self)
		self.user.setToolTip(toolTip)
		self.user.setText(SSHTunnel.SSH_DEFAULT_USER)
		self.layout().addWidget(self.user, 0, 1)

		toolTip = "Port number of the remote SSH server.\n"\
			  "Leave this as %d unless you know what "\
			  "you are doing." % SSHTunnel.SSH_PORT
		label = QLabel("SSH port:", self)
		label.setToolTip(toolTip)
		self.layout().addWidget(label, 1, 0)
		self.sshPort = QSpinBox(self)
		self.sshPort.setMinimum(0)
		self.sshPort.setMaximum(65535)
		self.sshPort.setValue(SSHTunnel.SSH_PORT)
		self.sshPort.setToolTip(toolTip)
		self.layout().addWidget(self.sshPort, 1, 1)

		toolTip = "The local SSH client executable.\n"\
			  "This can be the full path to the "\
			  "SSH client program."
		label = QLabel("SSH client executable:", self)
		label.setToolTip(toolTip)
		self.layout().addWidget(label, 2, 0)
		self.sshExecutable = QLineEdit(self)
		self.sshExecutable.setToolTip(toolTip)
		self.sshExecutable.setText(SSHTunnel.SSH_DEFAULT_EXECUTABLE)
		self.layout().addWidget(self.sshExecutable, 2, 1)

		toolTip = "Port number of the local tunnel end.\n"\
			  "It is recommended to use automatic port selection."
		label = QLabel("Local port:", self)
		label.setToolTip(toolTip)
		self.layout().addWidget(label, 3, 0)
		hbox = QHBoxLayout()
		self.localPort = QSpinBox(self)
		self.localPort.setMinimum(1024)
		self.localPort.setMaximum(65535)
		self.localPort.setValue(SSHTunnel.SSH_LOCAL_PORT_START)
		self.localPort.setToolTip(toolTip)
		hbox.addWidget(self.localPort)
		self.localPortAuto = QCheckBox("auto", self)
		self.localPortAuto.setToolTip(toolTip)
		hbox.addWidget(self.localPortAuto)
		self.layout().addLayout(hbox, 3, 1)

		self.localPortAuto.stateChanged.connect(self.__localPortAutoChanged)
		self.localPortAuto.setCheckState(Qt.Checked)

	def __localPortAutoChanged(self, newState):
		self.localPort.setEnabled(newState != Qt.Checked)

class _ConnectConfigWidget(QGroupBox):
	def __init__(self, parent=None):
		QGroupBox.__init__(self, parent)
		self.setLayout(QGridLayout())

		toolTip = "The host name or IP address of the core "\
			  "server to connect to."
		label = QLabel("Core server host:", self)
		label.setToolTip(toolTip)
		self.layout().addWidget(label, 0, 0)
		self.host = QLineEdit(self)
		self.host.setToolTip(toolTip)
		self.layout().addWidget(self.host, 0, 1)

		toolTip = "The port number of the core server to "\
			  "connect to."
		label = QLabel("Core server port:", self)
		label.setToolTip(toolTip)
		self.layout().addWidget(label, 1, 0)
		self.port = QSpinBox(self)
		self.port.setRange(0, 0xFFFF)
		self.port.setToolTip(toolTip)
		self.layout().addWidget(self.port, 1, 1)

		toolTip = "Connection timeout."
		label = QLabel("Timeout:", self)
		label.setToolTip(toolTip)
		self.layout().addWidget(label, 2, 0)
		self.timeout = QDoubleSpinBox(self)
		self.timeout.setRange(0.5, 60.0)
		self.timeout.setSingleStep(0.5)
		self.timeout.setDecimals(1)
		self.timeout.setSuffix(" s")
		self.timeout.setToolTip(toolTip)
		self.layout().addWidget(self.timeout, 2, 1)

		toolTip = "Establish an SSH tunnel to the core server "\
			  "and connect via this tunnel.\n"\
			  "SSH is a secure and encrypted way to connect "\
			  "to a server."
		self.sshTunnel = QCheckBox("via SSH t&unnel", self)
		self.sshTunnel.setToolTip(toolTip)
		self.layout().addWidget(self.sshTunnel, 3, 0, 1, 2)
		self.sshConfig = _SSHConfigWidget(self)
		self.sshConfig.hide()
		self.layout().addWidget(self.sshConfig, 4, 0, 1, 2)

		self.sshTunnel.stateChanged.connect(self.__sshChanged)

	def __sshChanged(self, newState):
		if newState == Qt.Checked:
			self.sshConfig.show()
		else:
			self.sshConfig.hide()

class LinkConfigWidget(QWidget):
	def __init__(self, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout())
		self.layout().setContentsMargins(QMargins())

		group = QGroupBox("Operation mode", self)
		group.setLayout(QVBoxLayout())
		self.spawnRadio = QRadioButton("Start a &simulator core", group)
		self.spawnRadio.setToolTip("This will start a simulator core "
					   "on-the-fly in the background.\n\n"
					   "---> If you don't know what to do, select this. <---")
		self.spawnRadio.setChecked(True)
		group.layout().addWidget(self.spawnRadio)
		self.connRadio = QRadioButton("Connect to an &external core", group)
		self.connRadio.setToolTip("Connect to an already running core server.\n"
					  "This server may be running locally or "
					  "somewhere else on the (trusted) network.")
		group.layout().addWidget(self.connRadio)
		self.layout().addWidget(group, 0, 0, 1, 2)

		self.advanced = QCheckBox("Show advanced &options", self)
		self.advanced.setToolTip("Show expert simulator core options.\n\n"
					 "You should not normally need to change any of these.\n"
					 "Changing them might break the execution "
					 "of the simulator core.")
		self.advanced.setCheckState(Qt.Unchecked)
		self.layout().addWidget(self.advanced, 1, 0, 1, 2)

		self.spawnConfig = _SpawnConfigWidget(self)
		self.layout().addWidget(self.spawnConfig, 2, 0, 1, 2)

		self.connConfig = _ConnectConfigWidget(self)
		self.connConfig.hide()
		self.layout().addWidget(self.connConfig, 3, 0, 1, 2)

		self.layout().setRowStretch(4, 1)

		self.askCheckBox = QCheckBox("Always as&k", self)
		self.askCheckBox.setCheckState(Qt.Checked if
			self.askWhenConnecting() else Qt.Unchecked)
		self.askCheckBox.setToolTip("Always open this dialog when "
					    "trying to connect to a CPU.")
		self.layout().addWidget(self.askCheckBox, 5, 0, 1, 2)

		self.__advancedChanged(self.advanced.checkState())

		self.advanced.stateChanged.connect(self.__advancedChanged)
		self.spawnRadio.toggled.connect(self.__spawnToggled)
		self.connRadio.toggled.connect(self.__connToggled)
		self.askCheckBox.stateChanged.connect(self.__askChanged)

	@classmethod
	def askWhenConnecting(cls):
		settings = QSettings()
		try:
			return bool(int(settings.value("connect_ask_details", 1)))
		except TypeError:
			return True

	def __advancedChanged(self, newState):
		if newState == Qt.Checked:
			self.spawnConfig.show()
		else:
			self.spawnConfig.hide()

	def __askChanged(self, newState):
		settings = QSettings()
		settings.setValue("connect_ask_details",
				  1 if newState == Qt.Checked else 0)

	def __spawnToggled(self, state):
		if state:
			self.advanced.show()
		else:
			self.advanced.hide()
		if state and self.advanced.checkState() == Qt.Checked:
			self.spawnConfig.show()
		else:
			self.spawnConfig.hide()

	def __connToggled(self, state):
		if state:
			self.connConfig.show()
		else:
			self.connConfig.hide()

	def loadFromProject(self, project):
		linkSettings = project.getCoreLinkSettings()

		if linkSettings.getSpawnLocalEn():
			self.spawnRadio.setChecked(True)
			self.connRadio.setChecked(False)
		else:
			self.spawnRadio.setChecked(False)
			self.connRadio.setChecked(True)

		interp = linkSettings.getSpawnLocalInterpreters()
		self.spawnConfig.interpreterList.setText(interp)
		pRange = linkSettings.getSpawnLocalPortRange()
		self.spawnConfig.portRangeStart.setValue(pRange[0])
		self.spawnConfig.portRangeEnd.setValue(pRange[-1])

		self.connConfig.host.setText(linkSettings.getConnectHost())
		self.connConfig.port.setValue(linkSettings.getConnectPort())
		self.connConfig.timeout.setValue(
			linkSettings.getConnectTimeoutMs() / 1000.0)
		self.connConfig.sshTunnel.setCheckState(
			Qt.Checked if
			(linkSettings.getTunnel() == linkSettings.TUNNEL_SSH)
			else Qt.Unchecked)

		sshConfig = self.connConfig.sshConfig
		sshConfig.user.setText(linkSettings.getSSHUser())
		sshConfig.sshPort.setValue(linkSettings.getSSHPort())
		sshConfig.sshExecutable.setText(linkSettings.getSSHExecutable())
		localPort = linkSettings.getTunnelLocalPort()
		sshConfig.localPortAuto.setCheckState(
			Qt.Checked if
			(localPort == linkSettings.TUNNEL_LOCPORT_AUTO)
			else Qt.Unchecked)
		sshConfig.localPort.setValue(
			localPort if
			(localPort != linkSettings.TUNNEL_LOCPORT_AUTO)
			else SSHTunnel.SSH_LOCAL_PORT_START)

	def storeToProject(self, project):
		linkSettings = project.getCoreLinkSettings()
		changed = False

		spawnLocalEn = bool(self.spawnRadio.isChecked())
		if spawnLocalEn != linkSettings.getSpawnLocalEn():
			linkSettings.setSpawnLocalEn(spawnLocalEn)
			changed = True
		interp = self.spawnConfig.interpreterList.text()
		if interp != linkSettings.getSpawnLocalInterpreters():
			linkSettings.setSpawnLocalInterpreters(interp)
			changed = True
		pRange = range(self.spawnConfig.portRangeStart.value(),
			       self.spawnConfig.portRangeEnd.value() + 1)
		if pRange != linkSettings.getSpawnLocalPortRange():
			linkSettings.setSpawnLocalPortRange(pRange)
			changed = True

		host = self.connConfig.host.text()
		if host != linkSettings.getConnectHost():
			linkSettings.setConnectHost(host)
			changed = True
		port = self.connConfig.port.value()
		if port != linkSettings.getConnectPort():
			linkSettings.setConnectPort(port)
			changed = True
		timeout = int(round(self.connConfig.timeout.value() * 1000))
		if timeout != linkSettings.getConnectTimeoutMs():
			linkSettings.setConnectTimeoutMs(timeout)
			changed = True
		tunnel = linkSettings.TUNNEL_SSH\
			 if (self.connConfig.sshTunnel.checkState() == Qt.Checked)\
			 else linkSettings.TUNNEL_NONE
		if tunnel != linkSettings.getTunnel():
			linkSettings.setTunnel(tunnel)
			changed = True

		sshConfig = self.connConfig.sshConfig
		sshUser = sshConfig.user.text()
		if sshUser != linkSettings.getSSHUser():
			linkSettings.setSSHUser(sshUser)
			changed = True
		sshPort = sshConfig.sshPort.value()
		if sshPort != linkSettings.getSSHPort():
			linkSettings.setSSHPort(sshPort)
			changed = True
		sshExecutable = sshConfig.sshExecutable.text()
		if sshExecutable != linkSettings.getSSHExecutable():
			linkSettings.setSSHExecutable(sshExecutable)
			changed = True
		if sshConfig.localPortAuto.checkState() == Qt.Checked:
			if linkSettings.getTunnelLocalPort() != linkSettings.TUNNEL_LOCPORT_AUTO:
				linkSettings.setTunnelLocalPort(linkSettings.TUNNEL_LOCPORT_AUTO)
				changed = True
		else:
			localPort = sshConfig.localPort.value()
			if linkSettings.getTunnelLocalPort() != localPort:
				linkSettings.setTunnelLocalPort(localPort)
				changed = True

		return changed

class LinkConfigDialog(AbstractConfigDialog):
	def __init__(self, project, parent=None):
		AbstractConfigDialog.__init__(self,
			project = project,
			iconName = "network",
			title = "Server connection setup",
			centralWidget = LinkConfigWidget(),
			parent = parent)
		self.resize(400, 400)

	def loadFromProject(self):
		self.centralWidget.loadFromProject(self.project)

	def storeToProject(self):
		if self.centralWidget.storeToProject(self.project):
			self.settingsChanged.emit()

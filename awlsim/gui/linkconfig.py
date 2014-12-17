# -*- coding: utf-8 -*-
#
# AWL simulator - GUI Awlsim link configuration widget
#
# Copyright 2014 Michael Buesch <m@bues.ch>
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
from awlsim.gui.icons import *

import sys


class _SpawnConfigWidget(QGroupBox):
	def __init__(self, parent=None):
		QGroupBox.__init__(self, parent)
		self.setLayout(QGridLayout())

		toolTip = "A semicolon (;) separated list of Python "\
			  "interpreters used to run the simulator core.\n"\
			  "The special value $CURRENT is the "\
			  "interpreter that is used to run the frontend.\n"\
			  "The list is tried first to last, until one "\
			  "working interpreter is found.\n\n"\
			  "---> If you are unsure, do not change the defaults. <---"
		label = QLabel("Python interpreter list:", self)
		label.setToolTip(toolTip)
		self.layout().addWidget(label, 0, 0)
		self.interpreterList = QLineEdit(self)
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

class LinkConfigDialog(QDialog):
	# Signal: Emitted, if any content changed.
	contentChanged = Signal()

	def __init__(self, project, parent=None):
		QDialog.__init__(self, parent)
		self.setWindowTitle("Awlsim core connection setup")

		self.__updateBlocked = 0
		self.setLayout(QGridLayout(self))

		hbox = QHBoxLayout()
		label = QLabel(self)
		label.setPixmap(getIcon("network").pixmap(QSize(48, 48)))
		hbox.addWidget(label)
		label = QLabel("Server connection", self)
		font = label.font()
		font.setPointSize(max(12, font.pointSize()))
		label.setFont(font)
		label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
		hbox.addWidget(label)
		self.layout().addLayout(hbox, 0, 0)

		group = QGroupBox("Operation mode", self)
		group.setLayout(QVBoxLayout())
		self.spawnRadio = QRadioButton("Start a simulator core", group)
		self.spawnRadio.setToolTip("This will start a simulator core "
					   "on-the-fly in the background.\n\n"
					   "---> If you don't know what to do, select this. <---")
		self.spawnRadio.setChecked(True)
		group.layout().addWidget(self.spawnRadio)
		self.connRadio = QRadioButton("Connect to an external core", group)
		self.connRadio.setToolTip("Connect to an already running core server.\n"
					  "This server may be running locally or "
					  "somewhere else on the (trusted) network.")
		group.layout().addWidget(self.connRadio)
		self.layout().addWidget(group, 1, 0, 1, 2)

		self.spawnConfig = _SpawnConfigWidget(self)
		self.layout().addWidget(self.spawnConfig, 2, 0, 1, 2)

		self.connConfig = _ConnectConfigWidget(self)
		self.connConfig.hide()
		self.layout().addWidget(self.connConfig, 3, 0, 1, 2)

		self.askCheckBox = QCheckBox("Always ask", self)
		self.askCheckBox.setCheckState(Qt.Checked if
			self.askWhenConnecting() else Qt.Unchecked)
		self.askCheckBox.setToolTip("Always open this dialog when "
					    "trying to connect to a CPU.")
		self.layout().addWidget(self.askCheckBox, 4, 0, 1, 2)

		self.acceptButton = QPushButton("Accept", self)
		self.layout().addWidget(self.acceptButton, 5, 0)

		self.cancelButton = QPushButton("Cancel", self)
		self.layout().addWidget(self.cancelButton, 5, 1)

		self.spawnRadio.toggled.connect(self.__spawnToggled)
		self.connRadio.toggled.connect(self.__connToggled)

		self.__loadFromProject(project)

		self.acceptButton.released.connect(self.accept)
		self.cancelButton.released.connect(self.reject)
		self.accepted.connect(self.__handleAccepted)
		self.askCheckBox.stateChanged.connect(self.__askChanged)

	def __spawnToggled(self, state):
		if state:
			self.spawnConfig.show()
		else:
			self.spawnConfig.hide()

	def __connToggled(self, state):
		if state:
			self.connConfig.show()
		else:
			self.connConfig.hide()

	@classmethod
	def askWhenConnecting(cls):
		settings = QSettings()
		try:
			return bool(int(settings.value("connect_ask_details", 1)))
		except TypeError:
			return True

	def __askChanged(self, newState):
		settings = QSettings()
		settings.setValue("connect_ask_details",
				  1 if newState == Qt.Checked else 0)

	def __loadFromProject(self, project):
		self.__project = project
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

	def __handleAccepted(self):
		linkSettings = self.__project.getCoreLinkSettings()
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

		if changed:
			self.contentChanged.emit()

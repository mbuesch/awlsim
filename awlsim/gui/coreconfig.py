# -*- coding: utf-8 -*-
#
# AWL simulator - GUI Awlsim core configuration widget
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
from awlsim.core.compat import *

from awlsim.gui.util import *

import sys


DEFAULT_INTERPRETERS = ("pypy", sys.executable, "python3", "python2", "python", "py")

class CoreConfigDialog(QDialog):
	def __init__(self, parent, simClient):
		QDialog.__init__(self, parent)
		self.simClient = simClient
		self.setWindowTitle("Awlsim core configuration")

		self.__updateBlocked = 0
		self.setLayout(QGridLayout(self))

		self.spawnServerCheckBox = QCheckBox("Spawn a new core server on RUN (recommended)",
						     self)
		self.layout().addWidget(self.spawnServerCheckBox, 0, 0, 1, 2)

		self.interpreterListLabel = QLabel("Python interpreter for core "
			"(semicolon separated list;\n"
			"First in list is tried first):", self)
		self.layout().addWidget(self.interpreterListLabel, 1, 0)
		self.interpreterList = QLineEdit(self)
		self.interpreterList.setText("; ".join(DEFAULT_INTERPRETERS))
		self.layout().addWidget(self.interpreterList, 1, 1)

		self.hostLabel = QLabel("Connect to awlsim core server host:", self)
		self.layout().addWidget(self.hostLabel, 2, 0)
		self.host = QLineEdit(self)
		self.host.setText(AwlSimServer.DEFAULT_HOST)
		self.layout().addWidget(self.host, 2, 1)

		self.portLabel = QLabel("Connect to awlsim core server port:", self)
		self.layout().addWidget(self.portLabel, 3, 0)
		self.port = QSpinBox(self)
		self.port.setRange(0, 0xFFFF)
		self.port.setValue(AwlSimServer.DEFAULT_PORT)
		self.layout().addWidget(self.port, 3, 1)

		self.portRangeLabel = QLabel("Spawn core server on one of these local ports:", self)
		self.layout().addWidget(self.portRangeLabel, 4, 0)
		hbox = QHBoxLayout()
		self.portRangeStart = QSpinBox(self)
		self.portRangeStart.setPrefix("from ")
		self.portRangeStart.setRange(0, 0xFFFF)
		self.portRangeStart.setValue(AwlSimServer.DEFAULT_PORT)
		hbox.addWidget(self.portRangeStart)
		self.portRangeEnd = QSpinBox(self)
		self.portRangeEnd.setPrefix("to ")
		self.portRangeEnd.setRange(0, 0xFFFF)
		self.portRangeEnd.setValue(AwlSimServer.DEFAULT_PORT + 4095)
		hbox.addWidget(self.portRangeEnd)
		self.layout().addLayout(hbox, 4, 1)

		self.closeButton = QPushButton("Close", self)
		self.layout().addWidget(self.closeButton, 5, 1)

		self.spawnServerCheckBox.stateChanged.connect(self.__spawnStateChanged)
		self.closeButton.released.connect(self.accept)

		self.spawnServerCheckBox.setCheckState(Qt.Checked)
		self.resize(600, 100)

	def shouldSpawnServer(self):
		return self.spawnServerCheckBox.checkState() == Qt.Checked

	def getInterpreterList(self):
		assert(self.shouldSpawnServer())
		return [ i.strip() for i in self.interpreterList.text().split(";") ]

	def getSpawnPortRange(self):
		assert(self.shouldSpawnServer())
		return (self.portRangeStart.value(),
			self.portRangeEnd.value())

	def getConnectHost(self):
		assert(not self.shouldSpawnServer())
		return self.host.text()

	def getConnectPort(self):
		assert(not self.shouldSpawnServer())
		return self.port.value()

	def __spawnStateChanged(self):
		if self.shouldSpawnServer():
			self.interpreterListLabel.show()
			self.interpreterList.show()
			self.hostLabel.hide()
			self.host.hide()
			self.portLabel.hide()
			self.port.hide()
			self.portRangeLabel.show()
			self.portRangeStart.show()
			self.portRangeEnd.show()
		else:
			self.interpreterListLabel.hide()
			self.interpreterList.hide()
			self.hostLabel.show()
			self.host.show()
			self.portLabel.show()
			self.port.show()
			self.portRangeLabel.hide()
			self.portRangeStart.hide()
			self.portRangeEnd.hide()

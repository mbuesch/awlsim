# -*- coding: utf-8 -*-
#
# AWL simulator - Abstract configuration widget
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


class AbstractConfigDialog(QDialog):
	# Signal: Emitted, if any setting changed.
	settingsChanged = Signal()

	def __init__(self, project, iconName, title,
		     centralWidget, parent=None):
		QDialog.__init__(self, parent)
		self.setWindowTitle("Awlsim - " + title)
		self.setLayout(QGridLayout(self))

		self.project = project
		self.centralWidget = centralWidget

		# Add dialog header label.
		grid = QGridLayout()
		label = QLabel(self)
		label.setPixmap(getIcon(iconName).pixmap(QSize(48, 48)))
		grid.addWidget(label, 0, 0)
		label = QLabel(title, self)
		font = label.font()
		font.setPointSize(max(13, font.pointSize()))
		label.setFont(font)
		label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
		grid.addWidget(label, 0, 1)
		# Try to center the text, regardless of the icon.
		grid.setColumnStretch(0, 1)
		grid.setColumnStretch(1, 2)
		grid.setColumnStretch(2, 1)
		self.layout().addLayout(grid, 0, 0, 1, 4)

		self.layout().addWidget(centralWidget, 1, 0, 1, 4)

		self.acceptButton = QPushButton("&Accept", self)
		self.layout().addWidget(self.acceptButton, 2, 0, 1, 3)

		self.cancelButton = QPushButton("&Cancel", self)
		self.layout().addWidget(self.cancelButton, 2, 3, 1, 1)

		self.loadFromProject()

		self.acceptButton.released.connect(self.accept)
		self.cancelButton.released.connect(self.reject)
		self.accepted.connect(self.storeToProject)

	def loadFromProject(self):
		if self.project:
			raise NotImplementedError

	def storeToProject(self):
		if self.project:
			raise NotImplementedError

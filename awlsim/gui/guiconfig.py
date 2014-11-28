# -*- coding: utf-8 -*-
#
# AWL simulator - GUI configuration widget
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


class GuiConfigDialog(QDialog):
	def __init__(self, parent):
		QDialog.__init__(self, parent)
		self.setWindowTitle("User interface configuration")

		self.setLayout(QGridLayout(self))

		label = QLabel(self)
		label.setPixmap(getIcon("prefs").pixmap(QSize(48, 48)))
		self.layout().addWidget(label, 0, 0)

		self.editAutoIndent = QCheckBox("Source editor auto indentation", self)
		self.layout().addWidget(self.editAutoIndent, 1, 0, 1, 2)

		self.editValidate = QCheckBox("Source editor code validation", self)
		self.layout().addWidget(self.editValidate, 2, 0, 1, 2)

		self.editFontLabel = QLabel("Set editor font:", self)
		self.editFontLabel.setFrameShape(QFrame.Panel)
		self.editFontLabel.setFrameShadow(QFrame.Sunken)
		self.layout().addWidget(self.editFontLabel, 3, 0)
		self.editFontButton = QPushButton("Select font...", self)
		self.layout().addWidget(self.editFontButton, 3, 1)
		self.__editFont = getDefaultFixedFont()

		self.closeButton = QPushButton("Close", self)
		self.layout().addWidget(self.closeButton, 4, 1)

		self.closeButton.released.connect(self.accept)
		self.editFontButton.released.connect(self.__openEditFontDialog)

	def __openEditFontDialog(self):
		font, ok = QFontDialog.getFont(self.__editFont, self, "Editor font")
		if ok:
			self.__editFont = font
			self.editFontLabel.setFont(self.__editFont)

	def loadFromProject(self, project):
		guiSettings = project.getGuiSettings()

		self.editAutoIndent.setCheckState(
			Qt.Checked if guiSettings.getEditorAutoIndentEn() else\
			Qt.Unchecked
		)

		self.editValidate.setCheckState(
			Qt.Checked if guiSettings.getEditorValidationEn() else\
			Qt.Unchecked
		)

		fontStr = guiSettings.getEditorFont()
		if fontStr:
			self.__editFont.fromString(fontStr)
		self.editFontLabel.setFont(self.__editFont)

	def saveToProject(self, project):
		autoIndentEn = self.editAutoIndent.checkState() == Qt.Checked
		validationEn = self.editValidate.checkState() == Qt.Checked

		guiSettings = project.getGuiSettings()
		guiSettings.setEditorAutoIndentEn(autoIndentEn)
		guiSettings.setEditorValidationEn(validationEn)
		guiSettings.setEditorFont(self.__editFont.toString())

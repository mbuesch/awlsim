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

		self.editGroup = QGroupBox("Source code editor")
		self.editGroup.setLayout(QVBoxLayout())

		self.editAutoIndent = QCheckBox("&Auto indentation", self)
		self.editGroup.layout().addWidget(self.editAutoIndent)

		self.pasteIndent = QCheckBox("Clipboard &paste "
			"auto indentation", self)
		self.editGroup.layout().addWidget(self.pasteIndent)

		self.editValidate = QCheckBox("Code &validation", self)
		self.editGroup.layout().addWidget(self.editValidate)

		hbox = QHBoxLayout()
		self.editFontLabel = QLabel(self)
		self.editFontLabel.setFrameShape(QFrame.Panel)
		self.editFontLabel.setFrameShadow(QFrame.Sunken)
		hbox.addWidget(self.editFontLabel)
		self.editFontButton = QPushButton("&Select...", self)
		hbox.addWidget(self.editFontButton)
		self.__editFont = getDefaultFixedFont()
		self.__updateEditFontLabel()
		self.editGroup.layout().addLayout(hbox)

		self.layout().addWidget(self.editGroup, 1, 0)

		self.closeButton = QPushButton("Close", self)
		self.layout().addWidget(self.closeButton, 2, 0)

		self.closeButton.released.connect(self.accept)
		self.editFontButton.released.connect(self.__openEditFontDialog)

	def __updateEditFontLabel(self):
		self.editFontLabel.setText("Font: %s, %d pt" %\
					   (self.__editFont.family(),
					    self.__editFont.pointSize()))
		self.editFontLabel.setFont(self.__editFont)

	def __openEditFontDialog(self):
		font, ok = QFontDialog.getFont(self.__editFont, self, "Editor font")
		if ok:
			self.__editFont = font
			self.__updateEditFontLabel()

	def loadFromProject(self, project):
		guiSettings = project.getGuiSettings()

		self.editAutoIndent.setCheckState(
			Qt.Checked if guiSettings.getEditorAutoIndentEn() else\
			Qt.Unchecked
		)

		self.pasteIndent.setCheckState(
			Qt.Checked if guiSettings.getEditorPasteIndentEn() else\
			Qt.Unchecked
		)

		self.editValidate.setCheckState(
			Qt.Checked if guiSettings.getEditorValidationEn() else\
			Qt.Unchecked
		)

		fontStr = guiSettings.getEditorFont()
		if fontStr:
			self.__editFont.fromString(fontStr)
			self.__editFont.setStyleHint(QFont.Courier)
		self.__updateEditFontLabel()

	def saveToProject(self, project):
		autoIndentEn = self.editAutoIndent.checkState() == Qt.Checked
		pasteIndentEn = self.pasteIndent.checkState() == Qt.Checked
		validationEn = self.editValidate.checkState() == Qt.Checked

		guiSettings = project.getGuiSettings()
		guiSettings.setEditorAutoIndentEn(autoIndentEn)
		guiSettings.setEditorPasteIndentEn(pasteIndentEn)
		guiSettings.setEditorValidationEn(validationEn)
		guiSettings.setEditorFont(self.__editFont.toString())

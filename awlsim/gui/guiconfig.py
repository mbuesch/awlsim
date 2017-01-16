# -*- coding: utf-8 -*-
#
# AWL simulator - GUI configuration widget
#
# Copyright 2014-2017 Michael Buesch <m@bues.ch>
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


class GuiConfigWidget(QWidget):
	def __init__(self, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout())
		self.layout().setContentsMargins(QMargins())

		self.editGroup = QGroupBox("Source code editor")
		self.editGroup.setLayout(QVBoxLayout())

		self.editAutoIndent = QCheckBox("&Auto indentation", self)
		self.editAutoIndent.setToolTip(
			"Automatically indent AWL/STL code as it is entered\n"
			"into the editor area.")
		self.editGroup.layout().addWidget(self.editAutoIndent)

		self.pasteIndent = QCheckBox("Clipboard &paste "
			"auto indentation", self)
		self.pasteIndent.setToolTip(
			"Automatically indent AWL/STL code as it is pasted\n"
			"into the editor area.")
		self.editGroup.layout().addWidget(self.pasteIndent)

		self.editValidate = QCheckBox("Live code &validation", self)
		self.editValidate.setToolTip(
			"Enable automatic compilation and verification of the\n"
			"AWL/STL code as it is entered into the editor.\n"
			"The verification completely runs in the background.")
		self.editGroup.layout().addWidget(self.editValidate)

		hbox = QHBoxLayout()
		self.editFontLabel = QLabel(self)
		self.editFontLabel.setFrameShape(QFrame.Panel)
		self.editFontLabel.setFrameShadow(QFrame.Sunken)
		self.editFontLabel.setToolTip(
			"Select the AWL/STL editor font.")
		hbox.addWidget(self.editFontLabel)
		self.editFontButton = QPushButton("&Select...", self)
		self.editFontButton.setToolTip(self.editFontLabel.toolTip())
		hbox.addWidget(self.editFontButton)
		self.__editFont = getDefaultFixedFont()
		self.__updateEditFontLabel()
		self.editGroup.layout().addLayout(hbox)

		self.layout().addWidget(self.editGroup, 0, 0)

		self.layout().setRowStretch(1, 1)

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

	def storeToProject(self, project):
		autoIndentEn = self.editAutoIndent.checkState() == Qt.Checked
		pasteIndentEn = self.pasteIndent.checkState() == Qt.Checked
		validationEn = self.editValidate.checkState() == Qt.Checked

		guiSettings = project.getGuiSettings()
		guiSettings.setEditorAutoIndentEn(autoIndentEn)
		guiSettings.setEditorPasteIndentEn(pasteIndentEn)
		guiSettings.setEditorValidationEn(validationEn)
		guiSettings.setEditorFont(self.__editFont.toString())

		return True

class GuiConfigDialog(AbstractConfigDialog):
	def __init__(self, project, parent=None):
		AbstractConfigDialog.__init__(self,
			project = project,
			iconName = "prefs",
			title = "User interface setup",
			centralWidget = GuiConfigWidget(),
			parent = parent)

	def loadFromProject(self):
		self.centralWidget.loadFromProject(self.project)

	def storeToProject(self):
		if self.centralWidget.storeToProject(self.project):
			self.settingsChanged.emit()

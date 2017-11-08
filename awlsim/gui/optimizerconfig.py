# -*- coding: utf-8 -*-
#
# AWL simulator - Optimizer configuration widget
#
# Copyright 2017 Michael Buesch <m@bues.ch>
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

from awlsim.awloptimizer.awloptimizer import *


__all__ = [
	"OptimizerConfigDialog",
]


class OptimizerConfigWidget(QWidget):
	def __init__(self, settingsContainer, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout())
		self.layout().setContentsMargins(QMargins())

		self.settingsContainer = settingsContainer

		label = QLabel("Available optimizers:")
		self.layout().addWidget(label, 0, 0)
		self.availOptList = QListWidget(self)
		self.layout().addWidget(self.availOptList, 1, 0, 2, 1)
		self.otherOpt = QLineEdit(self)
		self.otherOpt.setToolTip("Enter a custom optimizer here.\n"
					 "A wrong name will cause a build error "
					 "on the target CPU.")
		self.layout().addWidget(self.otherOpt, 3, 0)

		vbox = QVBoxLayout()
		self.addButton = QPushButton(self)
		self.addButton.setIcon(getIcon("next"))
		self.addButton.setToolTip("Enable the selected optimizer.")
		vbox.addWidget(self.addButton)
		self.delButton = QPushButton(self)
		self.delButton.setIcon(getIcon("previous"))
		self.delButton.setToolTip("Disable the selected optimizer.")
		vbox.addWidget(self.delButton)
		self.layout().addLayout(vbox, 0, 1, 4, 1)

		label = QLabel("Enabled optimizers:")
		self.layout().addWidget(label, 0, 2)
		self.enOptList = QListWidget(self)
		self.layout().addWidget(self.enOptList, 1, 2)
		self.allEnCheckBox = QCheckBox("Enable &all available optimizers (recommended)", self)
		self.allEnCheckBox.setToolTip(
			"If this box is ticked all available optimizers\n"
			"will be enabled.\n"
			"This is recommended.")
		self.allEnCheckBox.setCheckState(Qt.Checked
						 if settingsContainer.allEnable
						 else Qt.Unchecked)
		self.layout().addWidget(self.allEnCheckBox, 2, 2)
		self.globalEnCheckBox = QCheckBox("&Run enabled optimizers (recommended)", self)
		self.globalEnCheckBox.setToolTip(
			"If this box is not ticked, none of the \n"
			"enabled optimizers will actually be \n"
			"executed.")
		self.globalEnCheckBox.setCheckState(Qt.Checked
						    if settingsContainer.globalEnable
						    else Qt.Unchecked)
		self.layout().addWidget(self.globalEnCheckBox, 3, 2)

		enOptSettings = list(sorted(dictValues(self.settingsContainer.settingsDict),
					    key=lambda s: s.name))

		# All available optimizers
		for optClass in sorted(AwlOptimizer.ALL_OPTIMIZERS,
				       key=lambda o: o.NAME):
			if optClass.NAME in ( s.name for s in enOptSettings):
				continue # This opt is enabled already.
			item = self.__mkListEntry(optClass.NAME, optClass)
			self.availOptList.addItem(item)

		# All enabled optimizers
		for optSetting in enOptSettings:
			if not optSetting.enabled:
				continue # Not enabled.
			item = self.__mkListEntry(optSetting.name, optSetting)
			self.enOptList.addItem(item)

		self.__handleAllEnChange(self.allEnCheckBox.checkState())

		self.addButton.released.connect(self.__handleAdd)
		self.delButton.released.connect(self.__handleDel)
		self.allEnCheckBox.stateChanged.connect(self.__handleAllEnChange)
		self.globalEnCheckBox.stateChanged.connect(self.__handleGlobalEnChange)

	@classmethod
	def __getOptClass(cls, name):
		for optClass in AwlOptimizer.ALL_OPTIMIZERS:
			if optClass.NAME == name:
				return optClass
		return None

	@classmethod
	def __mkListEntry(cls, name, userData):
		optClass = cls.__getOptClass(name)
		if optClass:
			icon = getIcon("prefs")
			tip = "%s - %s\n\n"\
			      "%s" % (
				optClass.NAME,
				optClass.LONGNAME,
				optClass.DESC,
			)
		else:
			icon = getIcon("exit")
			tip = "WARNING: This optimizer is not known to Awlsim.\n"\
			      "It might cause a build error on the "\
			      "target CPU!"
		item = QListWidgetItem(icon, name)
		item.setToolTip(tip)
		item.setData(Qt.UserRole, userData)
		return item

	def __handleAdd(self):
		otherOptName = self.otherOpt.text().strip()
		if otherOptName:
			optName = otherOptName
			self.otherOpt.clear()
			fromItem = None
		else:
			fromItem = self.availOptList.currentItem()
			if not fromItem:
				return
			optClass = fromItem.data(Qt.UserRole)
			optName = optClass.NAME
		optSetting = AwlOptimizerSettings(
				name=optName,
				enabled=True)
		if not self.settingsContainer.add(optSetting):
			return
		if fromItem:
			self.availOptList.takeItem(self.availOptList.row(fromItem))
		item = self.__mkListEntry(optName, optSetting)
		self.enOptList.addItem(item)

	def __handleDel(self):
		item = self.enOptList.currentItem()
		if not item:
			return
		item = self.enOptList.takeItem(self.enOptList.row(item))
		optSetting = item.data(Qt.UserRole)
		optClass = self.__getOptClass(optSetting.name)
		if optClass:
			newItem = self.__mkListEntry(optClass.NAME, optClass)
			self.availOptList.addItem(newItem)
		self.settingsContainer.remove(optSetting)

	def __handleAllEnChange(self, state):
		en = bool(state == Qt.Checked)
		self.settingsContainer.allEnable = en
		self.availOptList.setEnabled(not en)
		self.otherOpt.setEnabled(not en)
		self.enOptList.setEnabled(not en)
		self.addButton.setEnabled(not en)
		self.delButton.setEnabled(not en)

	def __handleGlobalEnChange(self, state):
		self.settingsContainer.globalEnable = bool(state == Qt.Checked)

class OptimizerConfigDialog(AbstractConfigDialog):
	def __init__(self, settingsContainer, parent=None):
		AbstractConfigDialog.__init__(self,
			project=None,
			iconName="prefs",
			title="AWL optimizer setup",
			centralWidget=OptimizerConfigWidget(settingsContainer),
			parent=parent)
		self.resize(400, 400)

	def getSettingsContainer(self):
		return self.centralWidget.settingsContainer

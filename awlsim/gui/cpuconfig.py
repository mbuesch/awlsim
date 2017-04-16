# -*- coding: utf-8 -*-
#
# AWL simulator - GUI CPU configuration widget
#
# Copyright 2012-2017 Michael Buesch <m@bues.ch>
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


class ClockMemSpinBox(QSpinBox):
	OFF_TEXT = "none"

	def __init__(self, parent=None):
		QSpinBox.__init__(self, parent)

		self.valueChanged.connect(self.__handleValueChange)

		self.setMinimum(-1)
		self.setMaximum(0xFFFF)
		self.setValue(-1)

	def __handleValueChange(self, newValue):
		if newValue < 0:
			self.setPrefix("   ")
		else:
			self.setPrefix("MB ")

	def textFromValue(self, value):
		if value < 0:
			return self.OFF_TEXT
		return QSpinBox.textFromValue(self, value)

	def valueFromText(self, text):
		if text == self.OFF_TEXT:
			return -1
		return QSpinBox.valueFromText(self, text)

class CpuConfigWidget(QWidget):
	def __init__(self, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout())
		self.layout().setContentsMargins(QMargins())

		group = QGroupBox("Hardware", self)
		group.setLayout(QGridLayout())

		label = QLabel("Number of accumulator registers", self)
		label.setToolTip(
			"Select the number of ACCU registers the CPU will have.\n"
			"Note that this selection influences the semantics of some\n"
			"arithmetic instructions such as +I,-I,*I,/I and others.")
		group.layout().addWidget(label, 0, 0)
		self.accuCombo = QComboBox(self)
		self.accuCombo.addItem("2 accus", 2)
		self.accuCombo.addItem("4 accus", 4)
		self.accuCombo.setToolTip(label.toolTip())
		group.layout().addWidget(self.accuCombo, 0, 1)

		label = QLabel("Clock memory byte (Taktmerker)", self)
		label.setToolTip(
			"Select an M byte for use as clock memory byte (Taktmerker).")
		group.layout().addWidget(label, 1, 0)
		self.clockMemSpin = ClockMemSpinBox(self)
		self.clockMemSpin.setToolTip(label.toolTip())
		group.layout().addWidget(self.clockMemSpin, 1, 1)

		self.obTempCheckBox = QCheckBox("Enable writing of OB &TEMP "
			"entry-variables", self)
		self.obTempCheckBox.setToolTip(
			"If this box is not checked the entry variables in the\n"
			"ORGANIZATION_BLOCK's TEMP region will not be filled\n"
			"by the system on entry into the OB.")
		group.layout().addWidget(self.obTempCheckBox, 2, 0, 1, 2)

		self.layout().addWidget(group, 0, 0)

		group = QGroupBox("AWL language", self)
		group.setLayout(QGridLayout())

		label = QLabel("Mnemonics language", self)
		label.setToolTip(
			"Select the AWL/STL mnemonics type.\n"
			"This may be either German or International (English).\n"
			"Automatic will try to guess the mnemonics from the AWL/STL\n"
			"code. Note that this might fail, though.")
		group.layout().addWidget(label, 0, 0)
		self.mnemonicsCombo = QComboBox(self)
		self.mnemonicsCombo.addItem("Automatic", S7CPUConfig.MNEMONICS_AUTO)
		self.mnemonicsCombo.addItem("English", S7CPUConfig.MNEMONICS_EN)
		self.mnemonicsCombo.addItem("German", S7CPUConfig.MNEMONICS_DE)
		self.mnemonicsCombo.setToolTip(label.toolTip())
		group.layout().addWidget(self.mnemonicsCombo, 0, 1)

		self.extInsnsCheckBox = QCheckBox("Enable e&xtended "
			"non-standard instructions", self)
		self.extInsnsCheckBox.setToolTip(
			"Enable special Awlsim specific AWL/STL instructions that are not available\n"
			"in the standard S7 language. Enabling this option is harmless even\n"
			"if such instructions are not used.")
		group.layout().addWidget(self.extInsnsCheckBox, 1, 0, 1, 2)

		self.layout().addWidget(group, 1, 0)

		self.layout().setRowStretch(2, 1)

	def loadFromProject(self, project):
		specs = project.getCpuSpecs()
		conf = project.getCpuConf()

		index = self.accuCombo.findData(specs.nrAccus)
		assert(index >= 0)
		self.accuCombo.setCurrentIndex(index)

		self.clockMemSpin.setValue(conf.clockMemByte)

		index = self.mnemonicsCombo.findData(conf.getConfiguredMnemonics())
		assert(index >= 0)
		self.mnemonicsCombo.setCurrentIndex(index)

		self.obTempCheckBox.setCheckState(
			Qt.Checked if project.getObTempPresetsEn() else\
			Qt.Unchecked
		)

		self.extInsnsCheckBox.setCheckState(
			Qt.Checked if project.getExtInsnsEn() else\
			Qt.Unchecked
		)

	def storeToProject(self, project):
		specs = project.getCpuSpecs()
		conf = project.getCpuConf()

		mnemonics = self.mnemonicsCombo.itemData(self.mnemonicsCombo.currentIndex())
		nrAccus = self.accuCombo.itemData(self.accuCombo.currentIndex())
		clockMemByte = self.clockMemSpin.value()
		obTempEnabled = self.obTempCheckBox.checkState() == Qt.Checked
		extInsnsEnabled = self.extInsnsCheckBox.checkState() == Qt.Checked

		specs.setNrAccus(nrAccus)
		conf.setConfiguredMnemonics(mnemonics)
		conf.setClockMemByte(clockMemByte)
		project.setObTempPresetsEn(obTempEnabled)
		project.setExtInsnsEn(extInsnsEnabled)

		return True

class CpuConfigDialog(AbstractConfigDialog):
	def __init__(self, project, parent=None):
		AbstractConfigDialog.__init__(self,
			project = project,
			iconName = "cpu",
			title = "CPU setup",
			centralWidget = CpuConfigWidget(),
			parent = parent)

	def loadFromProject(self):
		self.centralWidget.loadFromProject(self.project)

	def storeToProject(self):
		if self.centralWidget.storeToProject(self.project):
			self.settingsChanged.emit()

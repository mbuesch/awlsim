# -*- coding: utf-8 -*-
#
# AWL simulator - GUI CPU configuration widget
#
# Copyright 2012-2020 Michael Buesch <m@bues.ch>
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
#from awlsim.common.cython_support cimport * #@cy
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

		group = QGroupBox("Hardware resource specification", self)
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

		label = QLabel("Number of S7 timers", self)
		label.setToolTip(
			"Set the number of S7 timers the CPU will have.\n"
			"This does only influence the number of S7 timers.\n"
			"There will always be an unlimited amount of IEC timers.")
		group.layout().addWidget(label, 1, 0)
		self.timersSpinBox = QSpinBox(self)
		self.timersSpinBox.setMinimum(0)
		self.timersSpinBox.setMaximum(0xFFFF)
		self.timersSpinBox.setToolTip(label.toolTip())
		group.layout().addWidget(self.timersSpinBox, 1, 1)

		label = QLabel("Number of S7 counters", self)
		label.setToolTip(
			"Set the number of S7 counters the CPU will have.\n"
			"This does only influence the number of S7 counters.\n"
			"There will always be an unlimited amount of IEC counters.")
		group.layout().addWidget(label, 2, 0)
		self.countersSpinBox = QSpinBox(self)
		self.countersSpinBox.setMinimum(0)
		self.countersSpinBox.setMaximum(0xFFFF)
		self.countersSpinBox.setToolTip(label.toolTip())
		group.layout().addWidget(self.countersSpinBox, 2, 1)

		label = QLabel("Number flag (Merker) memory bytes", self)
		label.setToolTip(
			"Set the number flag (Merker) memory bytes the CPU will have.")
		group.layout().addWidget(label, 3, 0)
		self.flagsSpinBox = QSpinBox(self)
		self.flagsSpinBox.setMinimum(0)
		self.flagsSpinBox.setMaximum(0x7FFFFFFF)
		self.flagsSpinBox.setToolTip(label.toolTip())
		group.layout().addWidget(self.flagsSpinBox, 3, 1)

		label = QLabel("Number process image input bytes", self)
		label.setToolTip(
			"Set the number process image input memory bytes the CPU will have.")
		group.layout().addWidget(label, 4, 0)
		self.inputsSpinBox = QSpinBox(self)
		self.inputsSpinBox.setMinimum(0)
		self.inputsSpinBox.setMaximum(0x7FFFFFFF)
		self.inputsSpinBox.setToolTip(label.toolTip())
		group.layout().addWidget(self.inputsSpinBox, 4, 1)

		label = QLabel("Number process image output bytes", self)
		label.setToolTip(
			"Set the number process image output memory bytes the CPU will have.")
		group.layout().addWidget(label, 5, 0)
		self.outputsSpinBox = QSpinBox(self)
		self.outputsSpinBox.setMinimum(0)
		self.outputsSpinBox.setMaximum(0x7FFFFFFF)
		self.outputsSpinBox.setToolTip(label.toolTip())
		group.layout().addWidget(self.outputsSpinBox, 5, 1)

		label = QLabel("Number local stack memory (TEMP) bytes", self)
		label.setToolTip(
			"Set the number local stack memory (TEMP) bytes the\n"
			"CPU will have per organization block invocation.")
		group.layout().addWidget(label, 6, 0)
		self.localbytesSpinBox = QSpinBox(self)
		self.localbytesSpinBox.setMinimum(0)
		self.localbytesSpinBox.setMaximum(0x7FFFFFFF)
		self.localbytesSpinBox.setToolTip(label.toolTip())
		group.layout().addWidget(self.localbytesSpinBox, 6, 1)

		label = QLabel("Parenthesis stack (Klammerstack) size", self)
		label.setToolTip(
			"Set the depth of the parenthesis stack (Klammerstack) the\n"
			"CPU will have per block invocation.")
		group.layout().addWidget(label, 7, 0)
		self.parenStackSpinBox = QSpinBox(self)
		self.parenStackSpinBox.setMinimum(0)
		self.parenStackSpinBox.setMaximum(0x7FFF)
		self.parenStackSpinBox.setToolTip(label.toolTip())
		group.layout().addWidget(self.parenStackSpinBox, 7, 1)

		label = QLabel("CALL stack size", self)
		label.setToolTip(
			"Set the depth of the CALL stack.\n"
			"This is the number of nested CALLs that can be made\n"
			"per OB invocation.")
		group.layout().addWidget(label, 8, 0)
		self.callStackSpinBox = QSpinBox(self)
		self.callStackSpinBox.setMinimum(1)
		self.callStackSpinBox.setMaximum(0x7FFFFFFF)
		self.callStackSpinBox.setToolTip(label.toolTip())
		group.layout().addWidget(self.callStackSpinBox, 8, 1)

		self.layout().addWidget(group, 0, 0, 3, 1)

		group = QGroupBox("Hardware configuration", self)
		group.setLayout(QGridLayout())

		label = QLabel("Clock memory byte (Taktmerker)", self)
		label.setToolTip(
			"Select an M byte for use as clock memory byte (Taktmerker).")
		group.layout().addWidget(label, 0, 0)
		self.clockMemSpin = ClockMemSpinBox(self)
		self.clockMemSpin.setToolTip(label.toolTip())
		group.layout().addWidget(self.clockMemSpin, 0, 1)

		self.obTempCheckBox = QCheckBox("Enable writing of OB &TEMP "
			"entry-variables", self)
		self.obTempCheckBox.setToolTip(
			"If this box is not checked the entry variables in the\n"
			"ORGANIZATION_BLOCK's TEMP region will not be filled\n"
			"by the system on entry into the OB.")
		group.layout().addWidget(self.obTempCheckBox, 1, 0, 1, 2)

		label = QLabel("Cycle (OB 1) time limit", self)
		label.setToolTip(
			"Time limit of one cycle (OB 1) run, in milliseconds.\n"
			"The CPU goes into exceptional state (STOP), if the\n"
			"cycle time limit is exceeded.")
		group.layout().addWidget(label, 2, 0)
		self.cycleTimeSpinBox = QDoubleSpinBox(self)
		self.cycleTimeSpinBox.setToolTip(label.toolTip())
		self.cycleTimeSpinBox.setSuffix(" ms")
		self.cycleTimeSpinBox.setSingleStep(1.0)
		self.cycleTimeSpinBox.setMinimum(1.0)
		self.cycleTimeSpinBox.setMaximum(900000.0)
		self.cycleTimeSpinBox.setDecimals(1)
		group.layout().addWidget(self.cycleTimeSpinBox, 2, 1)

		label = QLabel("Cycle (OB 1) time minimum", self)
		label.setToolTip(
			"Cycle time minimum target of one cycle (OB 1) run, in milliseconds.\n"
			"If this value is bigger than zero, then the CPU increases\n"
			"the cycle time to approximately this value.\n"
			"It does so by sleeping at the end of the cycle (OB 1).\n"
			"This decreases power consumption.\n"
			"But it also increases the OB 1 latency to the specified time.\n"
			"If the actual cycle time needed for calculations is bigger\n"
			"than this value, no sleep will happen.\n"
			"A value in the region of 10 ms is recommended.")
		group.layout().addWidget(label, 3, 0)
		self.cycleTimeTargetSpinBox = QDoubleSpinBox(self)
		self.cycleTimeTargetSpinBox.setToolTip(label.toolTip())
		self.cycleTimeTargetSpinBox.setSuffix(" ms")
		self.cycleTimeTargetSpinBox.setSingleStep(1.0)
		self.cycleTimeTargetSpinBox.setMinimum(0.0)
		self.cycleTimeTargetSpinBox.setMaximum(1000.0)
		self.cycleTimeTargetSpinBox.setDecimals(1)
		group.layout().addWidget(self.cycleTimeTargetSpinBox, 3, 1)

		self.layout().addWidget(group, 0, 1, 1, 1)

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

		group.layout().setRowStretch(2, 1)
		self.layout().addWidget(group, 1, 1, 1, 1)

		group = QGroupBox("Program", self)
		group.setLayout(QGridLayout())

		self.preDownloadValidationCheckBox = QCheckBox(
			"Enable pre-download program validation", self)
		self.preDownloadValidationCheckBox.setToolTip(
			"Validate program before downloading it to the CPU.\n"
			"This may catch certain program errors before download.")
		group.layout().addWidget(self.preDownloadValidationCheckBox, 0, 0, 1, 1)

		self.layout().addWidget(group, 2, 1, 1, 1)

		self.layout().setRowStretch(2, 1)

	def loadFromProject(self, project):
		specs = project.getCpuSpecs()
		conf = project.getCpuConf()
		guiSettings = project.getGuiSettings()

		index = self.accuCombo.findData(specs.nrAccus)
		self.accuCombo.setCurrentIndex(index if index >= 0 else 0)
		self.timersSpinBox.setValue(specs.nrTimers)
		self.countersSpinBox.setValue(specs.nrCounters)
		self.flagsSpinBox.setValue(specs.nrFlags)
		self.inputsSpinBox.setValue(specs.nrInputs)
		self.outputsSpinBox.setValue(specs.nrOutputs)
		self.localbytesSpinBox.setValue(specs.nrLocalbytes)
		self.parenStackSpinBox.setValue(specs.parenStackSize)
		self.callStackSpinBox.setValue(specs.callStackSize)

		self.clockMemSpin.setValue(conf.clockMemByte)

		index = self.mnemonicsCombo.findData(conf.getConfiguredMnemonics())
		self.mnemonicsCombo.setCurrentIndex(index if index >= 0 else 0)

		self.obTempCheckBox.setCheckState(
			Qt.Checked if conf.obStartinfoEn else Qt.Unchecked)
		self.extInsnsCheckBox.setCheckState(
			Qt.Checked if conf.extInsnsEn else Qt.Unchecked)
		self.cycleTimeSpinBox.setValue(conf.cycleTimeLimitUs / 1000.0)
		self.cycleTimeTargetSpinBox.setValue(conf.cycleTimeTargetUs / 1000.0)

		self.preDownloadValidationCheckBox.setCheckState(
			Qt.Checked if guiSettings.getPreDownloadValidationEn() else Qt.Unchecked)

	def storeToProject(self, project):
		specs = project.getCpuSpecs()
		conf = project.getCpuConf()
		guiSettings = project.getGuiSettings()

		mnemonics = self.mnemonicsCombo.itemData(self.mnemonicsCombo.currentIndex())
		nrAccus = self.accuCombo.itemData(self.accuCombo.currentIndex())
		nrTimers = self.timersSpinBox.value()
		nrCounters = self.countersSpinBox.value()
		nrFlags = self.flagsSpinBox.value()
		nrInputs = self.inputsSpinBox.value()
		nrOutputs = self.outputsSpinBox.value()
		nrLocalbytes = self.localbytesSpinBox.value()
		parenStackSize = self.parenStackSpinBox.value()
		callStackSize = self.callStackSpinBox.value()
		clockMemByte = self.clockMemSpin.value()
		obTempEnabled = self.obTempCheckBox.checkState() == Qt.Checked
		extInsnsEnabled = self.extInsnsCheckBox.checkState() == Qt.Checked
		cycleTimeLimit = self.cycleTimeSpinBox.value()
		cycleTimeTarget = self.cycleTimeTargetSpinBox.value()
		preDownloadValidation = self.preDownloadValidationCheckBox.checkState() == Qt.Checked

		specs.setNrAccus(nrAccus)
		specs.setNrTimers(nrTimers)
		specs.setNrCounters(nrCounters)
		specs.setNrFlags(nrFlags)
		specs.setNrInputs(nrInputs)
		specs.setNrOutputs(nrOutputs)
		specs.setNrLocalbytes(nrLocalbytes)
		specs.setParenStackSize(parenStackSize)
		specs.setCallStackSize(callStackSize)
		conf.setConfiguredMnemonics(mnemonics)
		conf.setClockMemByte(clockMemByte)
		conf.setOBStartinfoEn(obTempEnabled)
		conf.setExtInsnsEn(extInsnsEnabled)
		conf.setCycleTimeLimitUs(int(round(cycleTimeLimit * 1000.0)))
		conf.setCycleTimeTargetUs(int(round(cycleTimeTarget * 1000.0)))
		guiSettings.setPreDownloadValidationEn(preDownloadValidation)

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

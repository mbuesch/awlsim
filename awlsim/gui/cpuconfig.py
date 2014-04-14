# -*- coding: utf-8 -*-
#
# AWL simulator - GUI CPU configuration widget
#
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
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


class CpuConfigDialog(QDialog):
	def __init__(self, parent, sim):
		QDialog.__init__(self, parent)
		self.sim = sim
		self.setWindowTitle("CPU configuration")

		self.__updateBlocked = 0

		self.setLayout(QGridLayout(self))

		label = QLabel("Number of accumulator registers", self)
		self.layout().addWidget(label, 0, 0)
		self.accuCombo = QComboBox(self)
		self.accuCombo.addItem("2 accus", 2)
		self.accuCombo.addItem("4 accus", 4)
		self.layout().addWidget(self.accuCombo, 0, 1)

		label = QLabel("Mnemonics", self)
		self.layout().addWidget(label, 1, 0)
		self.mnemonicsCombo = QComboBox(self)
		self.mnemonicsCombo.addItem("Automatic", S7CPUSpecs.MNEMONICS_AUTO)
		self.mnemonicsCombo.addItem("English", S7CPUSpecs.MNEMONICS_EN)
		self.mnemonicsCombo.addItem("German", S7CPUSpecs.MNEMONICS_DE)
		self.layout().addWidget(self.mnemonicsCombo, 1, 1)

		self.obTempCheckBox = QCheckBox("Enable writing of OB TEMP "
			"entry-variables", self)
		self.layout().addWidget(self.obTempCheckBox, 2, 0, 1, 2)

		self.closeButton = QPushButton("Close", self)
		self.layout().addWidget(self.closeButton, 3, 1)

		self.accuCombo.currentIndexChanged.connect(self.__accuConfigChanged)
		self.mnemonicsCombo.currentIndexChanged.connect(self.__mnemonicsConfigChanged)
		self.obTempCheckBox.stateChanged.connect(self.__obTempConfigChanged)
		self.closeButton.released.connect(self.accept)

		self.loadConfig()

	def loadConfig(self):
		cpu = self.sim.getCPU()
		specs = cpu.getSpecs()
		self.__updateBlocked += 1

		index = self.accuCombo.findData(specs.nrAccus)
		assert(index >= 0)
		self.accuCombo.setCurrentIndex(index)

		index = self.mnemonicsCombo.findData(specs.getConfiguredMnemonics())
		assert(index >= 0)
		self.mnemonicsCombo.setCurrentIndex(index)

		self.obTempCheckBox.setCheckState(
			Qt.Checked if cpu.obTempPresetsEnabled() else\
			Qt.Unchecked
		)

		self.__updateBlocked -= 1

	def __accuConfigChanged(self):
		if self.__updateBlocked:
			return
		specs = self.sim.getCPU().getSpecs()
		index = self.accuCombo.currentIndex()
		specs.setNrAccus(self.accuCombo.itemData(index))

	def __mnemonicsConfigChanged(self):
		if self.__updateBlocked:
			return
		specs = self.sim.getCPU().getSpecs()
		index = self.mnemonicsCombo.currentIndex()
		specs.setConfiguredMnemonics(self.mnemonicsCombo.itemData(index))

	def __obTempConfigChanged(self):
		if self.__updateBlocked:
			return
		cpu = self.sim.getCPU()
		cpu.enableObTempPresets(self.obTempCheckBox.checkState() == Qt.Checked)

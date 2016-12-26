# -*- coding: utf-8 -*-
#
# AWL simulator - Block type edit widget
#
# Copyright 2016 Michael Buesch <m@bues.ch>
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


class BlockTypeWidget(QWidget):
	"""AWL block type edit widget.
	"""

	# Signal: Emitted, if the block type changed
	typeChanged = Signal()
	# Signal: Emitted, if the block index changed
	indexChanged = Signal()

	def __init__(self, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout())
		self.layout().setContentsMargins(QMargins())

		self.typeCombo = QComboBox(self)
		self.typeCombo.addItem("Block type: Function (FC)", "FC")
		self.typeCombo.addItem("Block type: Function block (FB)", "FB")
		self.typeCombo.addItem("Block type: Organization block (OB)", "OB")
		self.layout().addWidget(self.typeCombo, 0, 0)

		self.indexSpin = QSpinBox(self)
		self.indexSpin.setMinimum(0)
		self.indexSpin.setMaximum(0xFFFF)
		self.indexSpin.setValue(1)
		self.layout().addWidget(self.indexSpin, 0, 1)

		self.layout().setColumnStretch(99, 1)

		self.__handleTypeChange(self.typeCombo.currentIndex())
		self.typeCombo.currentIndexChanged.connect(self.__handleTypeChange)
		self.indexSpin.valueChanged.connect(self.__handleIndexChange)

	def __handleTypeChange(self, comboIndex):
		typeStr = self.typeCombo.itemData(comboIndex)
		self.indexSpin.setPrefix(typeStr + " ")
		self.typeChanged.emit()

	def __handleIndexChange(self, value):
		self.indexChanged.emit()

	def get(self):
		"""Get (blockTypeString, blockIndex)
		"""
		typeStr = self.typeCombo.itemData(self.typeCombo.currentIndex())
		index = self.indexSpin.value()
		return (typeStr, index)

	def set(self, blockTypeString, blockIndex):
		"""Set the block type and block index.
		"""
		index = self.typeCombo.findData(blockTypeString,
						Qt.UserRole, Qt.MatchFixedString)
		if index >= 0:
			self.typeCombo.setCurrentIndex(index)
			self.indexSpin.setValue(blockIndex)
			return True
		return False

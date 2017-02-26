# -*- coding: utf-8 -*-
#
# AWL simulator - Interface edit widget
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
from awlsim.gui.interfedit.interftabwidget import *
from awlsim.gui.interfedit.blocktypewidget import *


class AwlInterfWidget(QWidget):
	"""AWL block interface edit widget.
	"""

	# Signal: Emitted, if some content changed
	contentChanged = Signal()

	def __init__(self, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout())
		self.layout().setContentsMargins(QMargins())

		self.__changeSignalBlocked = Blocker()

		self.blockTypeEdit = BlockTypeWidget(self)
		self.layout().addWidget(self.blockTypeEdit, 0, 0)

		self.interfView = AwlInterfaceView(self)
		self.layout().addWidget(self.interfView, 1, 0)

		self.__reconfigInterfView()

		self.blockTypeEdit.typeChanged.connect(self.__handleBlockTypeChange)
		self.blockTypeEdit.nameChanged.connect(self.__handleBlockNameChange)
		self.blockTypeEdit.dbChanged.connect(self.__handleBlockDBChange)
		self.interfView.model().contentChanged.connect(self.contentChanged)

	@property
	def interfDef(self):
		"""Get the active AwlInterfDef().
		"""
		return self.interfView.model().interf

	def __handleBlockTypeChange(self):
		if self.__changeSignalBlocked:
			return
		blockTypeStr, blockName, instanceDBs = self.blockTypeEdit.get()
		if not self.interfView.isEmpty():
			ret = QMessageBox.warning(self,
				"Change block type?",
				"The block interface table is not empty.\n"
				"Changing the block type might delete interface fields.\n\n"
				"Change block type anyway?",
				QMessageBox.Yes | QMessageBox.No,
				QMessageBox.No)
			if ret != QMessageBox.Yes:
				# Revert the change
				with self.__changeSignalBlocked:
					self.blockTypeEdit.revertTypeChange()
				return
		with self.__changeSignalBlocked:
			self.__reconfigInterfView()
		self.contentChanged.emit()

	def __handleBlockNameChange(self):
		if self.__changeSignalBlocked:
			return
		self.contentChanged.emit()

	def __handleBlockDBChange(self):
		if self.__changeSignalBlocked:
			return
		self.contentChanged.emit()

	def __reconfigInterfView(self):
		blockTypeStr, blockName, instanceDBs = self.blockTypeEdit.get()
		if blockTypeStr.upper().strip() == "FC":
			self.interfView.model().configure(
				haveIn=True,
				haveOut=True,
				haveInOut=True,
				haveStat=False,
				haveTemp=True,
				haveRetVal=True,
				haveInitValue=False
			)
		elif blockTypeStr.upper().strip() == "FB":
			self.interfView.model().configure(
				haveIn=True,
				haveOut=True,
				haveInOut=True,
				haveStat=True,
				haveTemp=True,
				haveRetVal=False,
				haveInitValue=True
			)
		elif blockTypeStr.upper().strip() == "OB":
			self.interfView.model().configure(
				haveIn=False,
				haveOut=False,
				haveInOut=False,
				haveStat=False,
				haveTemp=True,
				haveRetVal=False,
				haveInitValue=False
			)
		else:
			assert(0)

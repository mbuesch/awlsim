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

from awlsim.common.xmlfactory import *

from awlsim.gui.util import *

import re


class BlockTypeWidget_factory(XmlFactory):
	def parser_open(self, tag=None):
		self.inInstanceDBs = False
		self.inDB = False
		self.blockTypeWidget.clear(noChangeSignals=True)
		if tag:
			self.blockTypeWidget.setBlockTypeString(
				blockTypeString=tag.getAttr("type", "FC").upper().strip(),
				noChangeSignals=True)
			self.blockTypeWidget.setBlockIndex(
				blockIndex=tag.getAttrInt("index", 0),
				noChangeSignals=True)
		XmlFactory.parser_open(self, tag)

	def parser_close(self):
		XmlFactory.parser_close(self)

	def parser_beginTag(self, tag):
		if self.inInstanceDBs:
			if tag.name == "db":
				dbIndex = tag.getAttrInt("index")
				self.blockTypeWidget.addInstanceDB(dbIndex)
				self.inDB = True
				return
		else:
			if tag.name == "instance_dbs":
				self.inInstanceDBs = True
				return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if self.inInstanceDBs:
			if self.inDB:
				if tag.name == "db":
					self.inDB = False
					return
			else:
				if tag.name == "instance_dbs":
					self.inInstanceDBs = False
					return
		else:
			if tag.name == "blockdecl":
				self.parser_finish()
				return
		XmlFactory.parser_endTag(self, tag)

	def composer_getTags(self):
		blockType, blockIndex, instanceDBs = self.blockTypeWidget.get()
		instanceDbTags = [ self.Tag(name="instance_dbs",
					    tags=[ self.Tag(name="db",
						   attrs={ "index" : str(int(index)) })
						   for index in instanceDBs ])
		]
		return [
			self.Tag(name="blockdecl",
				 attrs={
					"type" : str(blockType).upper().strip(),
					"index" : str(int(blockIndex)),
				 },
				 tags=instanceDbTags),
		]

class DBListValidator(QValidator):
	"""Validator for comma separated DB list strings.
	"""

	__reDB = re.compile(r'\s*((?:DB)|(?:DI))\s*(\d+)(.*)', re.IGNORECASE | re.DOTALL)

	def __init__(self, lineEdit):
		QValidator.__init__(self)
		self.lineEdit = lineEdit
		if lineEdit:
			self.defaultBgColor = lineEdit.palette().color(QPalette.Base)

	def __doFixup(self, input):
		valid, retList = True, []
		for dbStr in input.split(","):
			match = self.__reDB.match(dbStr)
			if match:
				if match.group(3).strip():
					valid = False # We have dangling data
				else:
					try:
						dbNr = int(match.group(2))
					except (ValueError, TypeError) as e:
						valid = False # Invalid index
					if dbNr < 0 or dbNr > 0xFFFF:
						valid = False # Invalid index
					dbStr = "%s %s" % (match.group(1).upper(),
							   match.group(2))
			else:
				dbStr = dbStr.upper().strip()
				if dbStr:
					valid = False # We have some crap
			retList.append(dbStr)
		return valid, ", ".join(retList)

	def fixup(self, input):
		valid, fixedInput = self.__doFixup(input)
		if self.lineEdit:
			self.lineEdit.setText(fixedInput)
		return fixedInput

	def validate(self, input, pos):
		valid, fixedInput = self.__doFixup(input)

		if self.lineEdit:
			palette = self.lineEdit.palette()
			if valid:
				palette.setColor(QPalette.Base, self.defaultBgColor)
			else:
				palette.setColor(QPalette.Base, getErrorColor())
			self.lineEdit.setPalette(palette)

		state = self.Acceptable
		if input != fixedInput:
			state = self.Intermediate
		return state, input.upper(), pos

class BlockTypeWidget(QWidget):
	"""AWL block type edit widget.
	"""

	factory = BlockTypeWidget_factory

	# Signal: Emitted, if the block type changed
	typeChanged = Signal()
	# Signal: Emitted, if the block index changed
	indexChanged = Signal()
	# Signal: Emitted, if the instance DBs changed
	dbChanged = Signal()

	def __init__(self, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout())
		self.layout().setContentsMargins(QMargins())

		self.__changeSignalsBlocked = Blocker()

		self.typeCombo = QComboBox(self)
		self.typeCombo.addItem("Block type: Function (FC)", "FC")
		self.typeCombo.addItem("Block type: Function block (FB)", "FB")
		self.typeCombo.addItem("Block type: Organization block (OB)", "OB")
		self.layout().addWidget(self.typeCombo, 0, 0)

		self.__prevTypeStr = "FC"

		self.indexSpin = QSpinBox(self)
		self.indexSpin.setMinimum(0)
		self.indexSpin.setMaximum(0xFFFF)
		self.layout().addWidget(self.indexSpin, 0, 1)

		self.dbEditLabel = QLabel("DIs:", self)
		self.layout().addWidget(self.dbEditLabel, 0, 2)

		self.dbEdit = QLineEdit(self)
		self.dbEdit.setToolTip(
			"Enter the instance DBs to create here.\n\n"
			"If this field is left empty, no DB will be generated.\n"
			"One DB or a comma separated list of DBs to create can be specified.\n\n"
			"For example:\n"
			"  DB 42\n"
			"or\n"
			"  DB 42, DB 43, DB 44")
		self.dbEditLabel.setToolTip(self.dbEdit.toolTip())
		self.dbEdit.setValidator(DBListValidator(self.dbEdit))
		self.layout().addWidget(self.dbEdit, 0, 3)

		self.layout().setColumnStretch(99, 1)

		self.clear(noChangeSignals=True)

		self.__handleTypeChange(self.typeCombo.currentIndex())
		self.typeCombo.currentIndexChanged.connect(self.__handleTypeChange)
		self.indexSpin.valueChanged.connect(self.__handleIndexChange)
		self.dbEdit.textChanged.connect(self.__handleDBChange)

	def __handleTypeChange(self, comboIndex):
		typeStr = self.typeCombo.itemData(comboIndex)
		self.indexSpin.setPrefix(typeStr + " ")
		if typeStr == "FB":
			self.dbEditLabel.show()
			self.dbEdit.show()
		else:
			self.dbEditLabel.hide()
			self.dbEdit.hide()
		if not self.__changeSignalsBlocked:
			self.typeChanged.emit()
		self.__prevTypeStr = typeStr

	def revertTypeChange(self):
		"""Revert type change. Can only be called from typeChanged signal.
		"""
		index = self.typeCombo.findData(self.__prevTypeStr,
						Qt.UserRole, Qt.MatchFixedString)
		if index >= 0:
			self.typeCombo.setCurrentIndex(index)

	def __handleIndexChange(self, value):
		if not self.__changeSignalsBlocked:
			self.indexChanged.emit()

	def __handleDBChange(self, text):
		if not self.__changeSignalsBlocked:
			self.dbChanged.emit()

	def get(self):
		"""Get (blockTypeString, blockIndex, instanceDBs)
		"""
		typeStr = self.typeCombo.itemData(self.typeCombo.currentIndex())
		index = self.indexSpin.value()
		instanceDBs = []
		if typeStr == "FB":
			for db in self.dbEdit.text().split(","):
				try:
					db = db.upper()
					for c in ("D", "I", "B"):
						db = db.replace(c, "")
					db = int(db.strip())
				except (ValueError, TypeError) as e:
					continue
				instanceDBs.append(db)
		return (typeStr, index, instanceDBs)

	def clear(self, noChangeSignals=False):
		"""Clear content.
		"""
		with self.__changeSignalsBlocked if noChangeSignals else nopContext:
			self.typeCombo.setCurrentIndex(0)
			self.indexSpin.setValue(1)
			self.dbEdit.clear()

	def setBlockTypeString(self, blockTypeString, noChangeSignals=False):
		"""Set the block type.
		"""
		with self.__changeSignalsBlocked if noChangeSignals else nopContext:
			index = self.typeCombo.findData(blockTypeString,
							Qt.UserRole, Qt.MatchFixedString)
			if index >= 0:
				self.typeCombo.setCurrentIndex(index)
				return True
			return False

	def setBlockIndex(self, blockIndex, noChangeSignals=False):
		"""Set the block index.
		"""
		with self.__changeSignalsBlocked if noChangeSignals else nopContext:
			self.indexSpin.setValue(blockIndex)

	def addInstanceDB(self, dbIndex, noChangeSignals=False):
		"""Add an instance DB.
		"""
		with self.__changeSignalsBlocked if noChangeSignals else nopContext:
			typeStr = self.typeCombo.itemData(self.typeCombo.currentIndex())
			if typeStr == "FB":
				newText = "DB %d" % dbIndex
				if self.dbEdit.text().strip():
					self.dbEdit.setText(self.dbEdit.text() + ", " + newText)
				else:
					self.dbEdit.setText(newText)
				return True
			return False

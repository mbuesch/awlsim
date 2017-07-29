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
			self.blockTypeWidget.setBlockName(
				blockName=tag.getAttr("name", "FC 1"),
				noChangeSignals=True)
		XmlFactory.parser_open(self, tag)

	def parser_close(self):
		XmlFactory.parser_close(self)

	def parser_beginTag(self, tag):
		if self.inInstanceDBs:
			if tag.name == "db":
				self.blockTypeWidget.addInstanceDB(tag.getAttr("name", ""))
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
		blockType, blockName, instanceDBs = self.blockTypeWidget.get()
		instanceDbTags = [ self.Tag(name="instance_dbs",
					    tags=[ self.Tag(name="db",
						   attrs={ "name" : str(dbName) })
						   for dbName in instanceDBs ])
		]
		return [
			self.Tag(name="blockdecl",
				 attrs={
					"type" : str(blockType).upper().strip(),
					"name" : str(blockName),
				 },
				 tags=instanceDbTags),
		]

class BlockValidator(QValidator):
	"""Validator for a block string.
	"""

	__reBase = r'\s*(BLOCKTYPE)\s*(\d+)(.*)'

	def __init__(self, lineEdit=None, blockTypes=()):
		QValidator.__init__(self)
		self.lineEdit = lineEdit
		if lineEdit:
			self.defaultBgColor = lineEdit.palette().color(QPalette.Base)
		self.blockTypes = blockTypes or ()

	def doFixup(self, input):
		valid, blockStr = True, input
		regex = self.__reBase.replace(r'BLOCKTYPE',
					      r'|'.join(r'(?:' + t + r')'
							for t in self.blockTypes))
		regex = re.compile(regex, re.IGNORECASE | re.DOTALL)
		match = regex.match(blockStr)
		if match:
			if match.group(3).strip():
				valid = False # We have dangling data
			else:
				try:
					blockNr = int(match.group(2))
				except (ValueError, TypeError) as e:
					valid = False # Invalid index
				if blockNr < 0 or blockNr > 0xFFFF:
					valid = False # Invalid index
				blockStr = "%s %s" % (match.group(1).upper(),
						      match.group(2))
		else:
			blockStr = blockStr.strip()
			if blockStr:
				if len(blockStr) >= 3 and\
				   blockStr.startswith('"') and\
				   blockStr.endswith('"') and\
				   blockStr[1:-1].find('"') < 0:
					pass # The name is symbolic
				else:
					if not blockStr.startswith('"'):
						blockStr = blockStr.upper()
					valid = False # We have some crap
		return valid, blockStr

	def fixup(self, input):
		valid, fixedInput = self.doFixup(input)
		if self.lineEdit:
			self.lineEdit.setText(fixedInput)
		return fixedInput

	def validate(self, input, pos):
		valid, fixedInput = self.doFixup(input)

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
		return state, input, pos

class BlockListValidator(BlockValidator):
	"""Validator for comma separated block list strings.
	"""

	def doFixup(self, input):
		valid, retList = True, []
		for blockStr in input.split(","):
			v, fix = BlockValidator.doFixup(self, blockStr)
			if not v:
				valid = False
			if fix.strip():
				retList.append(fix)
		return valid, ", ".join(retList)

class BlockTypeWidget(QWidget):
	"""AWL block type edit widget.
	"""

	factory = BlockTypeWidget_factory

	# Signal: Emitted, if the block type changed
	typeChanged = Signal()
	# Signal: Emitted, if the block name changed
	nameChanged = Signal()
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

		self.blockNameEdit = QLineEdit(self)
		self.blockNameEdit.setToolTip(
			"Enter the block name here.\n\n"
			"This can be an absolute block name like\n"
			"  FB 42   or   FC 42   or   OB 100\n"
			"or a symbolic block name like\n"
			"  \"My function block\"\n"
			"(The symbolic name must be present in the symbol table.)")
		self.layout().addWidget(self.blockNameEdit, 0, 1)

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
			"  DB 42, DB 43, DB 44\n"
			"or a symbolic block name like\n"
			"  \"First data block\", \"Second data block\"\n"
			"(The symbolic name must be present in the symbol table.)")
		self.dbEditLabel.setToolTip(self.dbEdit.toolTip())
		self.dbEdit.setValidator(BlockListValidator(self.dbEdit,
							    ("DB", "DI")))
		self.layout().addWidget(self.dbEdit, 0, 3)

		self.layout().setColumnStretch(99, 1)

		self.clear(noChangeSignals=True)

		self.__handleTypeChange(self.typeCombo.currentIndex())
		self.typeCombo.currentIndexChanged.connect(self.__handleTypeChange)
		self.blockNameEdit.textChanged.connect(self.__handleNameChange)
		self.dbEdit.textChanged.connect(self.__handleDBChange)

	def __handleTypeChange(self, comboIndex):
		typeStr = self.typeCombo.itemData(comboIndex)
		self.blockNameEdit.setValidator(BlockValidator(self.blockNameEdit,
							       (typeStr,)))
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

	def __handleNameChange(self, text):
		if not self.__changeSignalsBlocked:
			self.nameChanged.emit()

	def __handleDBChange(self, text):
		if not self.__changeSignalsBlocked:
			self.dbChanged.emit()

	def get(self):
		"""Get (blockTypeString, blockName, instanceDBs)
		"""
		typeStr = self.typeCombo.itemData(self.typeCombo.currentIndex())
		nameStr = self.blockNameEdit.text()
		instanceDBs = []
		if typeStr == "FB":
			for db in self.dbEdit.text().split(","):
				instanceDBs.append(db.strip())
		return (typeStr, nameStr, instanceDBs)

	def clear(self, noChangeSignals=False):
		"""Clear content.
		"""
		with self.__changeSignalsBlocked if noChangeSignals else nopContext:
			self.typeCombo.setCurrentIndex(0)
			self.blockNameEdit.setText("FC 1")
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

	def setBlockName(self, blockName, noChangeSignals=False):
		"""Set the block name.
		"""
		with self.__changeSignalsBlocked if noChangeSignals else nopContext:
			self.blockNameEdit.setText(blockName)

	def addInstanceDB(self, dbName, noChangeSignals=False):
		"""Add an instance DB.
		"""
		if not dbName.strip():
			return False
		with self.__changeSignalsBlocked if noChangeSignals else nopContext:
			typeStr = self.typeCombo.itemData(self.typeCombo.currentIndex())
			if typeStr == "FB":
				if self.dbEdit.text().strip():
					self.dbEdit.setText(self.dbEdit.text() + ", " + dbName)
				else:
					self.dbEdit.setText(dbName)
				return True
			return False

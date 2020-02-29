# -*- coding: utf-8 -*-
#
# AWL simulator - Operand edit widget
#
# Copyright 2020 Michael Buesch <m@bues.ch>
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

from awlsim.gui.util import *

import itertools


class OperCompletionWidget(QWidget):
	"""Operand auto-completion widget.
	"""

	# A new completion has been selected.
	# Parameter: The operand string.
	newSelection = Signal(str)

	# A new completion has been selected
	# and the edit dialog should accept it.
	# Parameter: The operand string.
	newSelectionFinal = Signal(str)

	def __init__(self,
		     parent,
		     interfDef,
		     symTabSources):
		"""parent: Parent widget.
		interfDef: AwlInterfDef() instance
		symTabSources: List of SymTabSource()s.
		"""
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout())
		self.layout().setContentsMargins(QMargins())

		self.__interfDef = interfDef
		try:
			self.__symTabs = [
				SymTabParser.parseTextCached(source.sourceText)
				for source in (symTabSources or [])
			]
		except AwlSimError as e:
			printError("Failed to parse symbol table: %s" % str(e))
			self.__symTabs = []

		self.__list = QListWidget(self)
		self.__list.setFont(getDefaultFixedFont())
		self.layout().addWidget(self.__list, 0, 0)

		self.__list.currentItemChanged.connect(self.__handleCurrentItemChanged)
		self.__list.itemDoubleClicked.connect(self.__handleItemDoubleClicked)

	def __handleCurrentItemChanged(self, cur, prev):
		self.newSelection.emit(cur.data(Qt.UserRole) if cur else "")

	def __handleItemDoubleClicked(self, item):
		if item:
			self.newSelectionFinal.emit(item.data(Qt.UserRole))

	def setFilterText(self, filterText):
		self.__filterText = filterText.strip()
		self.__rebuild()

	def __rebuild(self):
		self.__list.clear()

		filterText = self.__filterText.lower().strip()

		def add(symName, addrText, typeText, commentText):
			symNameLower = symName.lower()
			if filterText:
				if filterText.startswith("#"):
					if not symNameLower.startswith(filterText):
						return
				elif filterText.startswith('"'):
					if not symNameLower.startswith(filterText):
						return
				else:
					if not filterText in symNameLower:
						return
			firstPadding = " " * (15 - len(symName))
			sep = " | "
			itemDesc = [ symName, ]
			if addrText:
				itemDesc.append(firstPadding)
				itemDesc.append(sep)
				itemDesc.append(addrText)
			if typeText:
				if not addrText:
					itemDesc.append(firstPadding)
				itemDesc.append(sep)
				itemDesc.append(typeText)
			if commentText:
				itemDesc.append(sep)
				itemDesc.append(commentText)
			item = QListWidgetItem("".join(itemDesc))
			item.setData(Qt.UserRole, symName)
			self.__list.addItem(item)

		for field in sorted(self.__interfDef.allFields,
				    key=lambda f: f.name):
			add(symName=('#%s' % field.name),
			    addrText="",
			    typeText=field.typeStr,
			    commentText=field.comment)

		for symbol in sorted(itertools.chain(*self.__symTabs),
				     key=lambda s: s.getName()):
			add(symName=('"%s"' % symbol.getName()),
			    addrText=symbol.getOperatorString(),
			    typeText=symbol.getTypeString(),
			    commentText=symbol.getComment())

	def moveSelection(self, offset):
		curRow = self.__list.currentRow()
		if curRow < 0:
			if offset >= 0:
				curRow = 0
			else:
				curRow = self.__list.count() - 1
		else:
			curRow += offset
		curRow = clamp(curRow, 0, self.__list.count() - 1)
		self.__list.setCurrentRow(curRow)

class OperEditWidget(QWidget):
	"""Operand edit widget with auto-completion.
	"""

	cancel = Signal()
	accept = Signal()

	def __init__(self,
		     parent,
		     interfDef,
		     symTabSources,
		     text=""):
		"""parent: Parent widget.
		interfDef: AwlInterfDef() instance
		symTabSources: List of SymTabSource()s.
		text: Initial operand text.
		"""
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout())
		self.layout().setContentsMargins(QMargins())

		self.__filterChangeBlocked = Blocker()

		self.__lineEdit = QLineEdit(self)
		self.__lineEdit.setFont(getDefaultFixedFont())
		self.__lineEdit.setClearButtonEnabled(True)
		self.__lineEdit.setPlaceholderText("Enter operand here...")
		self.__lineEdit.setText(text)
		self.layout().addWidget(self.__lineEdit, 0, 0)

		self.__completion = OperCompletionWidget(parent=self,
							 interfDef=interfDef,
							 symTabSources=symTabSources)
		self.__completion.setFilterText(text)
		self.layout().addWidget(self.__completion, 1, 0)

		self.__lineEdit.textChanged.connect(self.__handleTextChange)
		self.__completion.newSelection.connect(self.__handleNewCompletion)
		self.__completion.newSelectionFinal.connect(self.__handleNewCompletionAndAccept)

	def keyPressEvent(self, event):
		if event.matches(QKeySequence.Cancel):
			self.cancel.emit()
			event.accept()
			return

		key = event.key()
		if key in (Qt.Key_Enter, Qt.Key_Return):
			self.accept.emit()
			event.accept()
			return
		elif key == Qt.Key_Up:
			self.__completion.moveSelection(-1)
			event.accept()
			return
		elif key == Qt.Key_Down:
			self.__completion.moveSelection(1)
			event.accept()
			return
		elif key == Qt.Key_PageUp:
			self.__completion.moveSelection(-5)
			event.accept()
			return
		elif key == Qt.Key_PageDown:
			self.__completion.moveSelection(5)
			event.accept()
			return

		QWidget.keyPressEvent(self, event)

	def __handleTextChange(self, text):
		if not self.__filterChangeBlocked:
			self.__completion.setFilterText(text)

	def __handleNewCompletion(self, text):
		if text:
			with self.__filterChangeBlocked:
				self.__lineEdit.setText(text)
				self.__lineEdit.setFocus()

	def __handleNewCompletionAndAccept(self, text):
		if text:
			self.__handleNewCompletion(text)
			self.accept.emit()

	def getText(self):
		return self.__lineEdit.text()

class OperEditDialog(QDialog):
	"""Operand edit dialog with auto-completion.
	"""

	def __init__(self,
		     parent,
		     interfDef,
		     symTabSources,
		     text="",
		     title="Operand",
		     label="Change operand:"):
		"""parent: Parent widget.
		interfDef: AwlInterfDef() instance
		symTabSources: List of SymTabSource()s.
		text: Initial operand text.
		title: Dialog title.
		label: Dialog description text.
		"""
		QDialog.__init__(self, parent)
		self.setLayout(QGridLayout())
		self.setWindowTitle(title)

		self.__label = QLabel(label, self)
		self.layout().addWidget(self.__label, 0, 0, 1, 2)

		self.__edit = OperEditWidget(parent=self,
					     interfDef=interfDef,
					     symTabSources=symTabSources,
					     text=text)
		self.layout().addWidget(self.__edit, 1, 0, 1, 2)

		self.__okButton = QPushButton("&Ok", self)
		self.layout().addWidget(self.__okButton, 2, 0)

		self.__cancelButton = QPushButton("&Cancel", self)
		self.layout().addWidget(self.__cancelButton, 2, 1)

		self.__edit.cancel.connect(self.reject)
		self.__edit.accept.connect(self.accept)
		self.__okButton.released.connect(self.accept)
		self.__cancelButton.released.connect(self.reject)

	def getText(self):
		return self.__edit.getText()

# -*- coding: utf-8 -*-
#
# AWL simulator - GUI symbol table edit widget
#
# Copyright 2014 Michael Buesch <m@bues.ch>
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


class SymTabModel(QAbstractTableModel):
	# Signal: Emitted, if the source code changed.
	sourceChanged = Signal()

	def __init__(self, symTab):
		QAbstractTableModel.__init__(self)
		self.symTab = symTab
		self.__source = SymTabSource(SymTabSource.newIdentNr(),
					     "Unnamed symbol table")

	def getSymTab(self):
		return self.symTab

	def deleteSymbol(self, row):
		if row >= 0 and row < len(self.symTab.symbols):
			self.beginResetModel()
			del self.symTab.symbols[row]
			self.endResetModel()
			self.sourceChanged.emit()

	def rowCount(self, parent=QModelIndex()):
		return len(self.symTab.symbols) + 1

	def columnCount(self, parent=QModelIndex()):
		return 4

	def data(self, index, role=Qt.DisplayRole):
		if not index:
			return None
		if role == Qt.DisplayRole:
			row, column = index.row(), index.column()
			if row >= len(self.symTab.symbols):
				return None
			sym = self.symTab.symbols[row]
			if column == 0:
				return sym.getName()
			elif column == 1:
				return sym.getOperatorString()
			elif column == 2:
				return sym.getTypeString()
			else:
				return sym.getComment()
		return None

	def headerData(self, section, orientation, role=Qt.DisplayRole):
		if role != Qt.DisplayRole:
			return None
		if orientation == Qt.Horizontal:
			return ("Symbol", "Address", "Data type", "Comment")[section]
		else:
			if section >= len(self.symTab.symbols):
				return "new"
			return "%d" % (section + 1)

	def setData(self, index, value, role=Qt.EditRole):
		if not index:
			return False
		if role == Qt.EditRole:
			row, column = index.row(), index.column()
			if row >= len(self.symTab.symbols):
				sym = Symbol()
				self.symTab.add(sym)
				self.rowsInserted.emit(None,
					len(self.symTab.symbols),
					len(self.symTab.symbols))
			else:
				sym = self.symTab.symbols[row]
			try:
				if column == 0:
					sym.setName(value)
				elif column == 1:
					sym.setOperatorString(value)
				elif column == 2:
					sym.setTypeString(value)
				else:
					sym.setComment(value)
			except AwlSimError as e:
				MessageBox.handleAwlSimError(None,
					"Invalid symbol information", e)
				return False
			self.sourceChanged.emit()
			return True
		return False

	def flags(self, index):
		if not index:
			return Qt.ItemIsEnabled
		return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

	def getSourceRef(self):
		return self.__source

	def getFullSource(self):
		source = self.__source.dup()
		try:
			source.sourceBytes = self.symTab.toReadableCSV()
		except AwlSimError as e:
			MessageBox.handleAwlSimError(None,
				"Symbol table contains invalid characters", e)
			return None
			source.sourceBytes = self.symTab.toBytes("ignore")
		return source

	def setSource(self, newSource):
		self.beginResetModel()
		try:
			self.symTab = SymbolTable()
			self.__source = newSource.dup()
			self.__source.sourceBytes = b""
			self.symTab = SymTabParser.parseData(newSource.sourceBytes)
		except AwlSimError as e:
			MessageBox.handleAwlSimError(None,
				"Could not parse symbol table information", e)
		finally:
			self.endResetModel()

class SymTabView(QTableView):
	def __init__(self, parent=None):
		QTableView.__init__(self, parent)

		self.pressed.connect(self.__handleMousePress)

	def resizeEvent(self, event):
		hdr = self.horizontalHeader()
		if hdr.sectionSize(0) < 150:
			hdr.resizeSection(0, 150)
		if hdr.sectionSize(3) < 200:
			hdr.resizeSection(3, 200)

	def deleteSym(self, index=None):
		if not index:
			index = self.currentIndex()
		if not index:
			return
		self.model().deleteSymbol(index.row())

	def __handleMousePress(self, index):
		btns = QApplication.mouseButtons()
		if btns & Qt.RightButton:
			pass#TODO context menu

	def keyPressEvent(self, ev):
		if ev.key() == Qt.Key_Delete:
			self.deleteSym()

	def setSymTab(self, symTab):
		self.setModel(SymTabModel(symTab))

	def getSourceRef(self):
		return self.model().getSourceRef()

	def getFullSource(self):
		return self.model().getFullSource()

	def setSource(self, newSource):
		return self.model().setSource(newSource)

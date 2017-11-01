# -*- coding: utf-8 -*-
#
# AWL simulator - Library selection table widget
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
from awlsim.common.compat import *

from awlsim.gui.util import *

from awlsim.library.libentry import *
from awlsim.library.libselection import *


class LibTableModel(QAbstractTableModel):
	# Signal: Emitted, if the content changed.
	contentChanged = Signal()

	def __init__(self):
		QAbstractTableModel.__init__(self)

		self.libSelections = []

	def getLibSelections(self):
		return self.libSelections

	def setLibSelections(self, libSelections):
		self.beginResetModel()
		self.libSelections = libSelections
		self.endResetModel()
		self.contentChanged.emit()

	def deleteEntry(self, row):
		if row >= 0 and row < len(self.libSelections):
			self.beginResetModel()
			del self.libSelections[row]
			self.endResetModel()
			self.contentChanged.emit()
			return True
		return False

	def deleteEntries(self, rows):
		offset = 0
		for row in sorted(rows):
			if self.deleteEntry(row + offset):
				offset -= 1

	def addEntry(self, libSelection):
		for sel in self.libSelections:
			if sel.getLibName() == libSelection.getLibName() and\
			   sel.getEntryType() == libSelection.getEntryType() and\
			   sel.getEntryIndex() == libSelection.getEntryIndex():
				return
		self.libSelections.append(libSelection)
		self.rowsInserted.emit(QModelIndex(),
			len(self.libSelections),
			len(self.libSelections))
		self.contentChanged.emit()

	def moveEntry(self, fromRow, toRow):
		self.beginResetModel()
		sel = self.libSelections.pop(fromRow)
		self.libSelections.insert(toRow, sel)
		self.endResetModel()
		self.contentChanged.emit()

	def rowCount(self, parent=QModelIndex()):
		return len(self.libSelections) + 1

	def columnCount(self, parent=QModelIndex()):
		return 4

	def data(self, index, role=Qt.DisplayRole):
		if not index:
			return None
		row, column = index.row(), index.column()
		if role in (Qt.DisplayRole, Qt.EditRole):
			if row >= len(self.libSelections):
				return None
			sel = self.libSelections[row]
			if column == 0:
				return sel.getLibName()
			elif column == 1:
				eTypeStr = sel.getEntryTypeStr()
				eIndex = sel.getEntryIndex()
				if eTypeStr == "UNKNOWN" or eIndex < 1 or eIndex > 0xFFFF:
					return ""
				return "%s %d" % (eTypeStr, eIndex)
			elif column == 2:
				eTypeStr = sel.getEntryTypeStr()
				eIndex = sel.getEffectiveEntryIndex()
				if eTypeStr == "UNKNOWN" or eIndex < 1 or eIndex > 0xFFFF:
					return ""
				return "%s %d" % (eTypeStr, eIndex)
			elif column == 3:
				try:
					libEntCls = AwlLib.getEntryBySelection(sel)
				except AwlSimError as e:
					return "Library or block not found!"
				return "\"%s\" - %s" % (
					libEntCls.symbolName,
					libEntCls.description,
				)
			else:
				assert(0)
		elif role in {Qt.BackgroundRole,
			      Qt.ForegroundRole}:
			if row < len(self.libSelections):
				sel = self.libSelections[row]
				if not sel.isValid():
					if role == Qt.BackgroundRole:
						return QBrush(QColor("red"))
					return QBrush(QColor("black"))
				try:
					AwlLib.getEntryBySelection(sel)
				except AwlSimError as e:
					if role == Qt.BackgroundRole:
						return QBrush(QColor("orange"))
					return QBrush(QColor("black"))
		elif role in (Qt.ToolTipRole, Qt.WhatsThisRole):
			return (
				# Library name
				"The name of the library.\n(The name is case insensitive.)",
				# Block name
				"The name of the block from the library to include.\n"\
				"For example:  FC 10  or  FB 42",
				# Effective block name
				"The local name of the block.\nThe block can be CALLed "
				"by this name from within the user program.\n"\
				"For example:  FC 110  or  FB 142",
				# Description
				"",
			)[column]
		return None

	def headerData(self, section, orientation, role=Qt.DisplayRole):
		if role != Qt.DisplayRole:
			return None
		if orientation == Qt.Horizontal:
			return ("Library", "Library block",
				"Use as block", "Description")[section]
		else:
			if section >= len(self.libSelections):
				return "new"
			return "%d" % (section + 1)

	def __strToTypeIndex(self, string):
		string = string.upper().strip()
		try:
			if string.startswith("FC"):
				eType = AwlLibEntrySelection.TYPE_FC
			elif string.startswith("FB"):
				eType = AwlLibEntrySelection.TYPE_FB
			else:
				raise ValueError
			index = int(string[2:].strip())
			if index < 1 or index > 0xFFFF:
				raise ValueError
			return eType, index
		except ValueError:
			raise AwlSimError("Invalid block selection: %s" %\
				string)

	def setData(self, index, value, role=Qt.EditRole):
		if not index:
			return False
		if role == Qt.EditRole:
			row, column = index.row(), index.column()
			if row >= len(self.libSelections):
				sel = AwlLibEntrySelection()
				self.libSelections.append(sel)
				self.rowsInserted.emit(QModelIndex(),
					len(self.libSelections),
					len(self.libSelections))
			else:
				sel = self.libSelections[row]
			try:
				if column == 0:
					sel.setLibName(value.strip())
				elif column == 1:
					if not value:
						return False
					eType, index = self.__strToTypeIndex(value)
					sel.setEntryType(eType)
					sel.setEntryIndex(index)
					if sel.getEffectiveEntryIndex() < 0:
						sel.setEffectiveEntryIndex(index)
				elif column == 2:
					if not value:
						return False
					eType, index = self.__strToTypeIndex(value)
					if sel.getEntryType() != sel.TYPE_UNKNOWN and\
					   eType != sel.getEntryType():
						raise AwlSimError("Effective block type "
							"does not match the library's "
							"block type '%s'." %\
							sel.getEntryTypeStr())
					sel.setEntryType(eType)
					sel.setEffectiveEntryIndex(index)
				else:
					assert(0)
			except AwlSimError as e:
				MessageBox.handleAwlSimError(None,
					"Invalid library information", e)
				return False
			self.contentChanged.emit()
			return True
		return False

	def flags(self, index):
		if not index:
			return Qt.ItemIsEnabled
		if index.column() >= 3:
			return Qt.ItemIsEnabled
		return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

class LibTableView(QTableView):
	# Signal: Keyboard focus in/out event.
	focusChanged = Signal(bool)

	def __init__(self, model=None, parent=None):
		QTableView.__init__(self, parent)

		if not model:
			model = LibTableModel()
		self.setModel(model)

		if isQt4:
			self.verticalHeader().setMovable(True)
		else:
			self.verticalHeader().setSectionsMovable(True)
		self.verticalHeader().sectionMoved.connect(self.__rowMoved)

		self.pressed.connect(self.__handleMousePress)

	def __rebuild(self):
		model = self.model()
		yscroll = self.verticalScrollBar().value()
		xscroll = self.horizontalScrollBar().value()
		self.setModel(None)
		self.setModel(model)
		self.verticalScrollBar().setValue(yscroll)
		self.horizontalScrollBar().setValue(xscroll)

	def __rowMoved(self, logicalIndex, oldVisualIndex, newVisualIndex):
		self.model().moveEntry(oldVisualIndex, newVisualIndex)
		self.__rebuild()

	def resizeEvent(self, ev):
		QTableView.resizeEvent(self, ev)
		hdr = self.horizontalHeader()
		if hdr.sectionSize(0) < 100:
			hdr.resizeSection(0, 100)
		if hdr.sectionSize(3) < 350:
			hdr.resizeSection(3, 350)

	def focusInEvent(self, ev):
		QTableView.focusInEvent(self, ev)
		self.focusChanged.emit(True)

	def focusOutEvent(self, ev):
		QTableView.focusOutEvent(self, ev)
		self.focusChanged.emit(False)

	def deleteEntries(self, rows=None):
		if rows is None:
			rows = set()
			for index in self.selectedIndexes():
				rows.add(index.row())
		self.model().deleteEntries(rows)

	def addEntry(self, libSelection):
		self.model().addEntry(libSelection)

	def __handleMousePress(self, index):
		btns = QApplication.mouseButtons()
		if btns & Qt.RightButton:
			pass#TODO context menu

	def keyPressEvent(self, ev):
		QTableView.keyPressEvent(self, ev)

		if ev.key() == Qt.Key_Delete:
			self.deleteEntries()

	def handleValidationResult(self, exception):
		pass

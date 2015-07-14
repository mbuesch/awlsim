# -*- coding: utf-8 -*-
#
# AWL simulator - Block tree widget
#
# Copyright 2015 Michael Buesch <m@bues.ch>
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
from awlsim.gui.icons import *


class BlockTreeModel(QAbstractItemModel):
	EnumGen.start
	INDEXID_SRCS			= EnumGen.item
	INDEXID_SRCS_AWL		= EnumGen.item
	INDEXID_SRCS_SYMTAB		= EnumGen.item
	INDEXID_SRCS_LIBSEL		= EnumGen.item
	INDEXID_BLOCKS			= EnumGen.item
	INDEXID_BLOCKS_OBS		= EnumGen.item
	INDEXID_BLOCKS_FCS		= EnumGen.item
	INDEXID_BLOCKS_FBS		= EnumGen.item
	INDEXID_BLOCKS_DBS		= EnumGen.item
	INDEXID_HWMODS			= EnumGen.item
	EnumGen.end

	# Base ID mask for dynamic elements
	INDEXID_BASE_MASK		= 0xFF0000
	# ID bases for dynamic elements
	INDEXID_SRCS_AWL_BASE		= 0x010000
	INDEXID_SRCS_SYMTAB_BASE	= 0x020000
	INDEXID_SRCS_LIBSEL_BASE	= 0x030000
	INDEXID_BLOCKS_OBS_BASE		= 0x040000
	INDEXID_BLOCKS_FCS_BASE		= 0x050000
	INDEXID_BLOCKS_FBS_BASE		= 0x060000
	INDEXID_BLOCKS_DBS_BASE		= 0x070000
	INDEXID_HWMODS_BASE		= 0x080000

	row2id_toplevel = {
		0	: INDEXID_SRCS,
#TODO		1	: INDEXID_BLOCKS,
		1	: INDEXID_HWMODS,
	}
	id2row_toplevel = pivotDict(row2id_toplevel)

	row2id_srcs = {
		0	: INDEXID_SRCS_AWL,
		1	: INDEXID_SRCS_SYMTAB,
		2	: INDEXID_SRCS_LIBSEL,
	}
	id2row_srcs = pivotDict(row2id_srcs)

	row2id_blocks = {
		0	: INDEXID_BLOCKS_OBS,
		1	: INDEXID_BLOCKS_FCS,
		2	: INDEXID_BLOCKS_FBS,
		3	: INDEXID_BLOCKS_DBS,
	}
	id2row_blocks = pivotDict(row2id_blocks)

	EnumGen.start
	COLUMN_NAME	= EnumGen.item
	COLUMN_DESC	= EnumGen.item
	COLUMN_IDENT	= EnumGen.item
	EnumGen.end

	def __init__(self, client, parent=None):
		QAbstractItemModel.__init__(self, parent)
		self.client = client

		self.__awlSources = []		# List of AwlSource()s
		self.__symTabSources = []	# List of SymTabSource()s
		self.__libSelections = []	# List of AwlLibEntrySelection()s
		self.__hwMods = []		# List of HwmodDescriptor()s

	def handle_IDENTS(self, msg):
		def updateData(localList, newList, parentIndex):
			for i, newItem in enumerate(newList):
				if i >= len(localList):
					self.beginInsertRows(parentIndex, i, i)
					localList.append(newItem)
					self.endInsertRows()
					continue
				if newItem != localList[i]:
					self.beginRemoveRows(parentIndex, i, i)
					localList.pop(i)
					self.endRemoveRows()
					self.beginInsertRows(parentIndex, i, i)
					localList.insert(i, newItem)
					self.endInsertRows()
					continue

		updateData(self.__awlSources, msg.awlSources,
			   self.idToIndex(self.INDEXID_SRCS_AWL))
		updateData(self.__symTabSources, msg.symTabSources,
			   self.idToIndex(self.INDEXID_SRCS_SYMTAB))
		updateData(self.__libSelections, msg.libSelections,
			   self.idToIndex(self.INDEXID_SRCS_LIBSEL))

		pass#TODO OB
		pass#TODO FC
		pass#TODO FB
		pass#TODO DB

		updateData(self.__hwMods, msg.hwMods,
			   self.idToIndex(self.INDEXID_HWMODS))

	def idToIndex(self, idxId, column = 0):
		for table in (self.id2row_toplevel,
			      self.id2row_srcs,
			      self.id2row_blocks):
			if idxId in table:
				return self.createIndex(table[idxId],
							column, idxId)
		assert(0)

	def indexToId(self, index):
		return index.internalId()

	def flags(self, index):
		if not index.isValid():
			return Qt.NoItemFlags

		idxId = self.indexToId(index)
		idxIdBase = idxId & self.INDEXID_BASE_MASK

		if index.column() == self.COLUMN_IDENT:
			if idxIdBase != 0:
				# We set the 'editable' flag for the ident column.
				# However it not really is editable (see setData).
				# We just do this to make the ident easily copy-able.
				return Qt.ItemIsEnabled |\
				       Qt.ItemIsSelectable |\
				       Qt.ItemIsEditable

		return Qt.ItemIsEnabled |\
		       Qt.ItemIsSelectable

	def columnCount(self, parentIndex=QModelIndex()):
		return 3

	def rowCount(self, parentIndex=QModelIndex()):
		if parentIndex.isValid():
			parentId = self.indexToId(parentIndex)
			if parentId == self.INDEXID_SRCS:
				return len(self.row2id_srcs)
			elif parentId == self.INDEXID_SRCS_AWL:
				return len(self.__awlSources)
			elif parentId == self.INDEXID_SRCS_SYMTAB:
				return len(self.__symTabSources)
			elif parentId == self.INDEXID_SRCS_LIBSEL:
				return len(self.__libSelections)
			elif parentId == self.INDEXID_BLOCKS:
#TODO				return len(self.row2id_blocks)
				pass#TODO
			elif parentId == self.INDEXID_BLOCKS_OBS:
				pass#TODO
			elif parentId == self.INDEXID_BLOCKS_FCS:
				pass#TODO
			elif parentId == self.INDEXID_BLOCKS_FBS:
				pass#TODO
			elif parentId == self.INDEXID_BLOCKS_DBS:
				pass#TODO
			elif parentId == self.INDEXID_HWMODS:
				return len(self.__hwMods)
		else:
			return len(self.row2id_toplevel)
		return 0

	def index(self, row, column, parentIndex=QModelIndex()):
		if row < 0 or column < 0:
			return QModelIndex()
		if parentIndex.isValid():
			parentId = self.indexToId(parentIndex)
			if parentId == self.INDEXID_SRCS:
				row2idTable = self.row2id_srcs
			elif parentId == self.INDEXID_BLOCKS:
				row2idTable = self.row2id_blocks
			elif parentId == self.INDEXID_SRCS_AWL:
				return self.createIndex(row, column,
					self.INDEXID_SRCS_AWL_BASE + row)
			elif parentId == self.INDEXID_SRCS_SYMTAB:
				return self.createIndex(row, column,
					self.INDEXID_SRCS_SYMTAB_BASE + row)
			elif parentId == self.INDEXID_SRCS_LIBSEL:
				return self.createIndex(row, column,
					self.INDEXID_SRCS_LIBSEL_BASE + row)
			elif parentId == self.INDEXID_HWMODS:
				return self.createIndex(row, column,
					self.INDEXID_HWMODS_BASE + row)
			else:
				return QModelIndex()
		else:
			row2idTable = self.row2id_toplevel
		try:
			idxId = row2idTable[row]
		except KeyError as e:
			return QModelIndex()
		return self.createIndex(row, column, idxId)

	def parent(self, index):
		if not index.isValid():
			return QModelIndex()
		idxId = self.indexToId(index)
		idxIdBase = idxId & self.INDEXID_BASE_MASK
		if idxId in self.id2row_toplevel:
			return QModelIndex()
		elif idxId in self.id2row_srcs:
			return self.idToIndex(self.INDEXID_SRCS)
		elif idxId in self.id2row_blocks:
			return self.idToIndex(self.INDEXID_BLOCKS)
		elif idxIdBase == self.INDEXID_SRCS_AWL_BASE:
			return self.idToIndex(self.INDEXID_SRCS_AWL)
		elif idxIdBase == self.INDEXID_SRCS_SYMTAB_BASE:
			return self.idToIndex(self.INDEXID_SRCS_SYMTAB)
		elif idxIdBase == self.INDEXID_SRCS_LIBSEL_BASE:
			return self.idToIndex(self.INDEXID_SRCS_LIBSEL)
		elif idxIdBase == self.INDEXID_BLOCKS_OBS_BASE:
			return self.idToIndex(self.INDEXID_BLOCKS_OBS)
		elif idxIdBase == self.INDEXID_BLOCKS_FCS_BASE:
			return self.idToIndex(self.INDEXID_BLOCKS_FCS)
		elif idxIdBase == self.INDEXID_BLOCKS_FBS_BASE:
			return self.idToIndex(self.INDEXID_BLOCKS_FBS)
		elif idxIdBase == self.INDEXID_BLOCKS_DBS_BASE:
			return self.idToIndex(self.INDEXID_BLOCKS_DBS)
		elif idxIdBase == self.INDEXID_HWMODS_BASE:
			return self.idToIndex(self.INDEXID_HWMODS)
		return QModelIndex()

	def data(self, index, role=Qt.DisplayRole):
		if role in (Qt.DisplayRole, Qt.EditRole):
			idxId = self.indexToId(index)
			idxIdBase = idxId & self.INDEXID_BASE_MASK

			if index.column() == self.COLUMN_NAME:
				# Name column

				if idxIdBase == self.INDEXID_SRCS_AWL_BASE:
					index = idxId - idxIdBase
					if index >= len(self.__awlSources):
						return None
					return self.__awlSources[index].name
				elif idxIdBase == self.INDEXID_SRCS_SYMTAB_BASE:
					index = idxId - idxIdBase
					if index >= len(self.__symTabSources):
						return None
					return self.__symTabSources[index].name
				elif idxIdBase == self.INDEXID_SRCS_LIBSEL_BASE:
					index = idxId - idxIdBase
					if index >= len(self.__libSelections):
						return None
					return str(self.__libSelections[index])
				elif idxIdBase == self.INDEXID_BLOCKS_OBS_BASE:
					pass#TODO
				elif idxIdBase == self.INDEXID_BLOCKS_FCS_BASE:
					pass#TODO
				elif idxIdBase == self.INDEXID_BLOCKS_FBS_BASE:
					pass#TODO
				elif idxIdBase == self.INDEXID_BLOCKS_DBS_BASE:
					pass#TODO
				elif idxIdBase == self.INDEXID_HWMODS_BASE:
					index = idxId - idxIdBase
					if index >= len(self.__hwMods):
						return None
					return self.__hwMods[index].getModuleName()

				names = {
				  self.INDEXID_SRCS		: "Sources",
				  self.INDEXID_SRCS_AWL		: "AWL/STL",
				  self.INDEXID_SRCS_SYMTAB	: "Symbol tables",
				  self.INDEXID_SRCS_LIBSEL	: "Libraries",
				  self.INDEXID_BLOCKS		: "Blocks",
				  self.INDEXID_BLOCKS_OBS	: "OBs",
				  self.INDEXID_BLOCKS_FCS	: "FCs",
				  self.INDEXID_BLOCKS_FBS	: "FBs",
				  self.INDEXID_BLOCKS_DBS	: "DBs",
				  self.INDEXID_HWMODS		: "Hardware",
				}
				try:
					name = names[idxId]
				except KeyError as e:
					return None
				return name

			if index.column() == self.COLUMN_DESC:
				# Description column

				descs = {
				  self.INDEXID_SRCS		: "Source files",
				  self.INDEXID_SRCS_AWL		: "AWL/STL sources",
				  self.INDEXID_SRCS_SYMTAB	: "Symbol table sources",
				  self.INDEXID_SRCS_LIBSEL	: "Library selections",
				  self.INDEXID_BLOCKS		: "Compiled blocks",
				  self.INDEXID_BLOCKS_OBS	: "OBs",
				  self.INDEXID_BLOCKS_FCS	: "FCs",
				  self.INDEXID_BLOCKS_FBS	: "FBs",
				  self.INDEXID_BLOCKS_DBS	: "DBs",
				  self.INDEXID_HWMODS		: "Hardware modules",
				}
				try:
					desc = descs[idxId]
				except KeyError as e:
					return None
				return desc

			if index.column() == self.COLUMN_IDENT:
				# Ident column

				if idxIdBase == self.INDEXID_SRCS_AWL_BASE:
					index = idxId - idxIdBase
					if index >= len(self.__awlSources):
						return None
					return self.__awlSources[index].identHashStr
				elif idxIdBase == self.INDEXID_SRCS_SYMTAB_BASE:
					index = idxId - idxIdBase
					if index >= len(self.__symTabSources):
						return None
					return self.__symTabSources[index].identHashStr
				elif idxIdBase == self.INDEXID_SRCS_LIBSEL_BASE:
					index = idxId - idxIdBase
					if index >= len(self.__libSelections):
						return None
					return self.__libSelections[index].getIdentHashStr()
				elif idxIdBase == self.INDEXID_BLOCKS_OBS_BASE:
					pass#TODO
				elif idxIdBase == self.INDEXID_BLOCKS_FCS_BASE:
					pass#TODO
				elif idxIdBase == self.INDEXID_BLOCKS_FBS_BASE:
					pass#TODO
				elif idxIdBase == self.INDEXID_BLOCKS_DBS_BASE:
					pass#TODO
				elif idxIdBase == self.INDEXID_HWMODS_BASE:
					index = idxId - idxIdBase
					if index >= len(self.__hwMods):
						return None
					return self.__hwMods[index].getIdentHashStr()

		elif role == Qt.DecorationRole:
			idxId = self.indexToId(index)
			idxIdBase = idxId & self.INDEXID_BASE_MASK
			if index.column() == 0:
				if idxId == self.INDEXID_SRCS:
					return getIcon("textsource")
				elif idxId == self.INDEXID_SRCS_AWL or\
				     idxIdBase == self.INDEXID_SRCS_AWL_BASE:
					return getIcon("textsource")
				elif idxId == self.INDEXID_SRCS_SYMTAB or\
				     idxIdBase == self.INDEXID_SRCS_SYMTAB_BASE:
					return getIcon("tag")
				elif idxId == self.INDEXID_SRCS_LIBSEL or\
				     idxIdBase == self.INDEXID_SRCS_LIBSEL_BASE:
					return getIcon("stdlib")
				elif idxId == self.INDEXID_BLOCKS:
					return getIcon("plugin")
				elif idxId == self.INDEXID_BLOCKS_OBS or\
				     idxIdBase == self.INDEXID_BLOCKS_OBS_BASE:
					return getIcon("plugin")
				elif idxId == self.INDEXID_BLOCKS_FCS or\
				     idxIdBase == self.INDEXID_BLOCKS_FCS_BASE:
					return getIcon("plugin")
				elif idxId == self.INDEXID_BLOCKS_FBS or\
				     idxIdBase == self.INDEXID_BLOCKS_FBS_BASE:
					return getIcon("plugin")
				elif idxId == self.INDEXID_BLOCKS_DBS or\
				     idxIdBase == self.INDEXID_BLOCKS_DBS_BASE:
					return getIcon("datablock")
				elif idxId == self.INDEXID_HWMODS or\
				     idxIdBase == self.INDEXID_HWMODS_BASE:
					return getIcon("hwmod")
		return None

	def setData(self, index, value, role=Qt.EditRole):
		if not index.isValid():
			return False
		if role != Qt.EditRole:
			return False
		if index.column() == self.COLUMN_IDENT:
			# We never allow edit of the ident hash.
			return False
		return QAbstractItemModel.setData(self, index, value, role)

	def headerData(self, section, orientation, role=Qt.DisplayRole):
		if role == Qt.DisplayRole:
			return (
				"Block name",
				"Description",
				"Unique identification hash",
			)[section]
		return None

class BlockTreeView(QTreeView):
	def __init__(self, model, parent=None):
		QTreeView.__init__(self, parent)
		self.setModel(model)
		if model:
			self.expand(model.idToIndex(model.INDEXID_SRCS))
#TODO			self.expand(model.idToIndex(model.INDEXID_BLOCKS))
		self.setColumnWidth(0, 200)
		self.setColumnWidth(1, 150)
		self.setColumnWidth(2, 530)

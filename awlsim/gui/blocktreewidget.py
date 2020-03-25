# -*- coding: utf-8 -*-
#
# AWL simulator - Block tree widget
#
# Copyright 2015-2018 Michael Buesch <m@bues.ch>
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

from awlsim.common.locale import _

from awlsim.gui.util import *
from awlsim.gui.icons import *


class BlockTreeModel(QAbstractItemModel):
	EnumGen.start
	INDEXID_SRCS			= EnumGen.item
	INDEXID_SRCS_AWL		= EnumGen.item
	INDEXID_SRCS_FUP		= EnumGen.item
	INDEXID_SRCS_SYMTAB		= EnumGen.item
	INDEXID_SRCS_LIBSEL		= EnumGen.item
	INDEXID_BLOCKS			= EnumGen.item
	INDEXID_BLOCKS_OBS		= EnumGen.item
	INDEXID_BLOCKS_FCS		= EnumGen.item
	INDEXID_BLOCKS_FBS		= EnumGen.item
	INDEXID_BLOCKS_DBS		= EnumGen.item
	INDEXID_BLOCKS_UDTS		= EnumGen.item
	INDEXID_HWMODS			= EnumGen.item
	EnumGen.end

	# Base ID mask for dynamic elements
	INDEXID_BASE_MASK		= 0xFF0000
	# ID bases for dynamic elements
	INDEXID_SRCS_AWL_BASE		= 0x010000
	INDEXID_SRCS_FUP_BASE		= 0x020000
	INDEXID_SRCS_SYMTAB_BASE	= 0x030000
	INDEXID_SRCS_LIBSEL_BASE	= 0x040000
	INDEXID_BLOCKS_OBS_BASE		= 0x050000
	INDEXID_BLOCKS_FCS_BASE		= 0x060000
	INDEXID_BLOCKS_FBS_BASE		= 0x070000
	INDEXID_BLOCKS_DBS_BASE		= 0x080000
	INDEXID_BLOCKS_UDTS_BASE	= 0x090000
	INDEXID_HWMODS_BASE		= 0x0A0000

	row2id_toplevel = {
		0	: INDEXID_SRCS,
		1	: INDEXID_BLOCKS,
		2	: INDEXID_HWMODS,
	}
	id2row_toplevel = pivotDict(row2id_toplevel)

	row2id_srcs = {
		0	: INDEXID_SRCS_AWL,
		1	: INDEXID_SRCS_FUP,
		2	: INDEXID_SRCS_SYMTAB,
		3	: INDEXID_SRCS_LIBSEL,
	}
	id2row_srcs = pivotDict(row2id_srcs)

	row2id_blocks = {
		0	: INDEXID_BLOCKS_OBS,
		1	: INDEXID_BLOCKS_FCS,
		2	: INDEXID_BLOCKS_FBS,
		3	: INDEXID_BLOCKS_DBS,
		4	: INDEXID_BLOCKS_UDTS,
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
		self.__fupSources = []		# List of FupSource()s
		self.__symTabSources = []	# List of SymTabSource()s
		self.__symTabInfoList = []	# List of (SymTabSource(), SymbolTable())
		self.__libSelections = []	# List of AwlLibEntrySelection()s
		self.__obInfos = []		# List of BlockInfo()s for OBs
		self.__fcInfos = []		# List of BlockInfo()s for FCs
		self.__fbInfos = []		# List of BlockInfo()s for FBs
		self.__dbInfos = []		# List of BlockInfo()s for DBs
		self.__udtInfos = []		# List of BlockInfo()s for UDTs
		self.__hwMods = []		# List of HwmodDescriptor()s

	def getAwlSource(self, indexNr):
		return self.__awlSources[indexNr]

	def getFupSource(self, indexNr):
		return self.__fupSources[indexNr]

	def getSymTabSource(self, indexNr):
		return self.__symTabSources[indexNr]

	def getOBBlockInfo(self, indexNr):
		return self.__obInfos[indexNr]

	def getFCBlockInfo(self, indexNr):
		return self.__fcInfos[indexNr]

	def getFBBlockInfo(self, indexNr):
		return self.__fbInfos[indexNr]

	def getDBBlockInfo(self, indexNr):
		return self.__dbInfos[indexNr]

	def getUDTBlockInfo(self, indexNr):
		return self.__udtInfos[indexNr]

	def __getSymbolsByType(self, dataType):
		return itertools.chain.from_iterable(
			symTab.getByDataType(dataType)
			for symTabSrc, symTab in self.__symTabInfoList
		)

	def __getSymbolsByTypeName(self, typeNameString):
		dataType = AwlDataType.makeByName(typeNameString.split())
		return self.__getSymbolsByType(dataType)

	def __updateData(self, localList, newList, parentIndex):
		for i, newItem in enumerate(newList):
			# Add new items.
			if i >= len(localList):
				self.beginInsertRows(parentIndex, i, i)
				localList.append(newItem)
				self.endInsertRows()
				continue
			# Change modified items.
			if newItem != localList[i]:
				self.beginRemoveRows(parentIndex, i, i)
				localList.pop(i)
				self.endRemoveRows()
				self.beginInsertRows(parentIndex, i, i)
				localList.insert(i, newItem)
				self.endInsertRows()
				continue
		while len(localList) > len(newList) and\
		      len(localList) >= 1:
			# Remove removed items.
			i = len(localList) - 1
			self.beginRemoveRows(parentIndex, i, i)
			localList.pop(i)
			self.endRemoveRows()

	def handle_IDENTS(self, msg):
		self.__updateData(self.__awlSources, msg.awlSources,
				  self.idToIndex(self.INDEXID_SRCS_AWL))
		self.__updateData(self.__fupSources, msg.fupSources,
				  self.idToIndex(self.INDEXID_SRCS_FUP))
		self.__updateData(self.__symTabSources, msg.symTabSources,
				  self.idToIndex(self.INDEXID_SRCS_SYMTAB))
		self.__updateData(self.__libSelections, msg.libSelections,
				  self.idToIndex(self.INDEXID_SRCS_LIBSEL))
		self.__updateData(self.__hwMods, msg.hwMods,
				  self.idToIndex(self.INDEXID_HWMODS))

	def handle_BLOCKINFO(self, msg):
		newBlockInfos = [ bi for bi in msg.blockInfos \
				  if bi.blockType == bi.TYPE_OB ]
		self.__updateData(self.__obInfos, newBlockInfos,
				  self.idToIndex(self.INDEXID_BLOCKS_OBS))

		newBlockInfos = [ bi for bi in msg.blockInfos \
				  if bi.blockType == bi.TYPE_FC ]
		self.__updateData(self.__fcInfos, newBlockInfos,
				  self.idToIndex(self.INDEXID_BLOCKS_FCS))

		newBlockInfos = [ bi for bi in msg.blockInfos \
				  if bi.blockType == bi.TYPE_FB ]
		self.__updateData(self.__fbInfos, newBlockInfos,
				  self.idToIndex(self.INDEXID_BLOCKS_FBS))

		newBlockInfos = [ bi for bi in msg.blockInfos \
				  if bi.blockType == bi.TYPE_DB ]
		self.__updateData(self.__dbInfos, newBlockInfos,
				  self.idToIndex(self.INDEXID_BLOCKS_DBS))

		newBlockInfos = [ bi for bi in msg.blockInfos \
				  if bi.blockType == bi.TYPE_UDT ]
		self.__updateData(self.__udtInfos, newBlockInfos,
				  self.idToIndex(self.INDEXID_BLOCKS_UDTS))

	def handle_symTabInfo(self, symTabInfoList):
		self.__symTabInfoList = symTabInfoList
		#TODO we probably need to trigger row update here.

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
			elif parentId == self.INDEXID_SRCS_FUP:
				return len(self.__fupSources)
			elif parentId == self.INDEXID_SRCS_SYMTAB:
				return len(self.__symTabSources)
			elif parentId == self.INDEXID_SRCS_LIBSEL:
				return len(self.__libSelections)
			elif parentId == self.INDEXID_BLOCKS:
				return len(self.row2id_blocks)
			elif parentId == self.INDEXID_BLOCKS_OBS:
				return len(self.__obInfos)
			elif parentId == self.INDEXID_BLOCKS_FCS:
				return len(self.__fcInfos)
			elif parentId == self.INDEXID_BLOCKS_FBS:
				return len(self.__fbInfos)
			elif parentId == self.INDEXID_BLOCKS_DBS:
				return len(self.__dbInfos)
			elif parentId == self.INDEXID_BLOCKS_UDTS:
				return len(self.__udtInfos)
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
			elif parentId == self.INDEXID_SRCS_AWL:
				return self.createIndex(row, column,
					self.INDEXID_SRCS_AWL_BASE + row)
			elif parentId == self.INDEXID_SRCS_FUP:
				return self.createIndex(row, column,
					self.INDEXID_SRCS_FUP_BASE + row)
			elif parentId == self.INDEXID_SRCS_SYMTAB:
				return self.createIndex(row, column,
					self.INDEXID_SRCS_SYMTAB_BASE + row)
			elif parentId == self.INDEXID_SRCS_LIBSEL:
				return self.createIndex(row, column,
					self.INDEXID_SRCS_LIBSEL_BASE + row)
			elif parentId == self.INDEXID_BLOCKS:
				row2idTable = self.row2id_blocks
			elif parentId == self.INDEXID_BLOCKS_OBS:
				return self.createIndex(row, column,
					self.INDEXID_BLOCKS_OBS_BASE + row)
			elif parentId == self.INDEXID_BLOCKS_FCS:
				return self.createIndex(row, column,
					self.INDEXID_BLOCKS_FCS_BASE + row)
			elif parentId == self.INDEXID_BLOCKS_FBS:
				return self.createIndex(row, column,
					self.INDEXID_BLOCKS_FBS_BASE + row)
			elif parentId == self.INDEXID_BLOCKS_DBS:
				return self.createIndex(row, column,
					self.INDEXID_BLOCKS_DBS_BASE + row)
			elif parentId == self.INDEXID_BLOCKS_UDTS:
				return self.createIndex(row, column,
					self.INDEXID_BLOCKS_UDTS_BASE + row)
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
		elif idxIdBase == self.INDEXID_SRCS_FUP_BASE:
			return self.idToIndex(self.INDEXID_SRCS_FUP)
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
		elif idxIdBase == self.INDEXID_BLOCKS_UDTS_BASE:
			return self.idToIndex(self.INDEXID_BLOCKS_UDTS)
		elif idxIdBase == self.INDEXID_HWMODS_BASE:
			return self.idToIndex(self.INDEXID_HWMODS)
		return QModelIndex()

	def __data_columnName(self, index, idxId, idxIdBase):
		if idxIdBase == self.INDEXID_SRCS_AWL_BASE:
			index = idxId - idxIdBase
			if index >= len(self.__awlSources):
				return None
			return self.__awlSources[index].name
		elif idxIdBase == self.INDEXID_SRCS_FUP_BASE:
			index = idxId - idxIdBase
			if index >= len(self.__fupSources):
				return None
			return self.__fupSources[index].name
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
			index = idxId - idxIdBase
			if index >= len(self.__obInfos):
				return None
			return self.__obInfos[index].blockName
		elif idxIdBase == self.INDEXID_BLOCKS_FCS_BASE:
			index = idxId - idxIdBase
			if index >= len(self.__fcInfos):
				return None
			return self.__fcInfos[index].blockName
		elif idxIdBase == self.INDEXID_BLOCKS_FBS_BASE:
			index = idxId - idxIdBase
			if index >= len(self.__fbInfos):
				return None
			return self.__fbInfos[index].blockName
		elif idxIdBase == self.INDEXID_BLOCKS_DBS_BASE:
			index = idxId - idxIdBase
			if index >= len(self.__dbInfos):
				return None
			return self.__dbInfos[index].blockName
		elif idxIdBase == self.INDEXID_BLOCKS_UDTS_BASE:
			index = idxId - idxIdBase
			if index >= len(self.__udtInfos):
				return None
			return self.__udtInfos[index].blockName
		elif idxIdBase == self.INDEXID_HWMODS_BASE:
			index = idxId - idxIdBase
			if index >= len(self.__hwMods):
				return None
			return self.__hwMods[index].getModuleName()

		names = {
		  self.INDEXID_SRCS		: _("Sources"),
		  self.INDEXID_SRCS_AWL		: _("AWL/STL"),
		  self.INDEXID_SRCS_FUP		: _("FUP/FBD"),
		  self.INDEXID_SRCS_SYMTAB	: _("Symbols"),
		  self.INDEXID_SRCS_LIBSEL	: _("Libraries"),
		  self.INDEXID_BLOCKS		: _("Blocks"),
		  self.INDEXID_BLOCKS_OBS	: _("OBs"),
		  self.INDEXID_BLOCKS_FCS	: _("FCs"),
		  self.INDEXID_BLOCKS_FBS	: _("FBs"),
		  self.INDEXID_BLOCKS_DBS	: _("DBs"),
		  self.INDEXID_BLOCKS_UDTS	: _("UDTs"),
		  self.INDEXID_HWMODS		: _("Hardware"),
		}
		return names.get(idxId)

	def __tryGetBlockSymName(self, blockName):
		syms = list(self.__getSymbolsByTypeName(blockName))
		if syms:
			return '"%s"' % syms[-1].getName()
		return None

	def __data_columnDesc(self, index, idxId, idxIdBase):
		if idxIdBase == self.INDEXID_BLOCKS_OBS_BASE:
			obInfoIndex = idxId - idxIdBase
			descs = {
				1	: _("Main cycle: \"CYCL_EXC\""),
				100	: _("Warm start: \"COMPLETE RESTART\""),
				101	: _("Restart: \"RESTART\""),
				102	: _("Cold restart: \"COLD RESTART\""),
			}
			obInfo = self.__obInfos[obInfoIndex]
			desc = self.__tryGetBlockSymName("OB %d" % obInfo.blockIndex)
			return desc or descs.get(obInfo.blockIndex)
		elif idxIdBase == self.INDEXID_BLOCKS_FCS_BASE:
			fcInfoIndex = idxId - idxIdBase
			fcInfo = self.__fcInfos[fcInfoIndex]
			return self.__tryGetBlockSymName("FC %d" % fcInfo.blockIndex)
		elif idxIdBase == self.INDEXID_BLOCKS_FBS_BASE:
			fbInfoIndex = idxId - idxIdBase
			fbInfo = self.__fbInfos[fbInfoIndex]
			return self.__tryGetBlockSymName("FB %d" % fbInfo.blockIndex)
		elif idxIdBase == self.INDEXID_BLOCKS_DBS_BASE:
			dbInfoIndex = idxId - idxIdBase
			descs = {
				0 : "System data block",
			}
			dbInfo = self.__dbInfos[dbInfoIndex]
			desc = self.__tryGetBlockSymName("DB %d" % dbInfo.blockIndex)
			return desc or descs.get(dbInfo.blockIndex)
		elif idxIdBase == self.INDEXID_BLOCKS_UDTS_BASE:
			udtInfoIndex = idxId - idxIdBase
			udtInfo = self.__udtInfos[udtInfoIndex]
			return self.__tryGetBlockSymName("UDT %d" % udtInfo.blockIndex)
		descs = {
		  self.INDEXID_SRCS		: _("Source files"),
		  self.INDEXID_SRCS_AWL		: _("AWL/STL sources"),
		  self.INDEXID_SRCS_FUP		: _("FUP/FBD sources"),
		  self.INDEXID_SRCS_SYMTAB	: _("Symbol table sources"),
		  self.INDEXID_SRCS_LIBSEL	: _("Library selections"),
		  self.INDEXID_BLOCKS		: _("Compiled blocks"),
		  self.INDEXID_BLOCKS_OBS	: _("Organization Blocks"),
		  self.INDEXID_BLOCKS_FCS	: _("Functions"),
		  self.INDEXID_BLOCKS_FBS	: _("Function Blocks"),
		  self.INDEXID_BLOCKS_DBS	: _("Data Blocks"),
		  self.INDEXID_BLOCKS_UDTS	: _("User defined Data Types"),
		  self.INDEXID_HWMODS		: _("Hardware modules"),
		}
		return descs.get(idxId)

	def __data_columnIdent(self, index, idxId, idxIdBase):
		if idxIdBase == self.INDEXID_SRCS_AWL_BASE:
			index = idxId - idxIdBase
			if index >= len(self.__awlSources):
				return None
			return self.__awlSources[index].identHashStr
		elif idxIdBase == self.INDEXID_SRCS_FUP_BASE:
			index = idxId - idxIdBase
			if index >= len(self.__fupSources):
				return None
			return self.__fupSources[index].identHashStr
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
			index = idxId - idxIdBase
			if index >= len(self.__obInfos):
				return None
			return self.__obInfos[index].identHashStr
		elif idxIdBase == self.INDEXID_BLOCKS_FCS_BASE:
			index = idxId - idxIdBase
			if index >= len(self.__fcInfos):
				return None
			return self.__fcInfos[index].identHashStr
		elif idxIdBase == self.INDEXID_BLOCKS_FBS_BASE:
			index = idxId - idxIdBase
			if index >= len(self.__fbInfos):
				return None
			return self.__fbInfos[index].identHashStr
		elif idxIdBase == self.INDEXID_BLOCKS_DBS_BASE:
			index = idxId - idxIdBase
			if index >= len(self.__dbInfos):
				return None
			return self.__dbInfos[index].identHashStr
		elif idxIdBase == self.INDEXID_BLOCKS_UDTS_BASE:
			index = idxId - idxIdBase
			if index >= len(self.__udtInfos):
				return None
			return self.__udtInfos[index].identHashStr
		elif idxIdBase == self.INDEXID_HWMODS_BASE:
			index = idxId - idxIdBase
			if index >= len(self.__hwMods):
				return None
			return self.__hwMods[index].getIdentHashStr()
		return None

	def data(self, index, role=Qt.DisplayRole):
		column = index.column()
		idxId = self.indexToId(index)
		idxIdBase = idxId & self.INDEXID_BASE_MASK

		if role in (Qt.DisplayRole, Qt.EditRole):
			if column == self.COLUMN_NAME:
				return self.__data_columnName(index, idxId, idxIdBase)
			if column == self.COLUMN_DESC:
				return self.__data_columnDesc(index, idxId, idxIdBase)
			if column == self.COLUMN_IDENT:
				return self.__data_columnIdent(index, idxId, idxIdBase)

		elif role == Qt.DecorationRole:
			if column == self.COLUMN_NAME:
				if idxId == self.INDEXID_SRCS:
					return getIcon("textsource")
				elif idxId == self.INDEXID_SRCS_AWL or\
				     idxIdBase == self.INDEXID_SRCS_AWL_BASE:
					return getIcon("textsource")
				elif idxId == self.INDEXID_SRCS_FUP or\
				     idxIdBase == self.INDEXID_SRCS_FUP_BASE:
					return getIcon("fup")
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
				elif idxId == self.INDEXID_BLOCKS_UDTS or\
				     idxIdBase == self.INDEXID_BLOCKS_UDTS_BASE:
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
				_("Block name"),
				_("Symbol / description"),
				_("Unique identification hash"),
			)[section]
		return None

class BlockTreeView(QTreeView):
	"""CPU block tree-view.
	"""

	# Signal: Open an item.
	#	Argument: identHash
	openItem = Signal(object)

	def __init__(self, model, parent=None):
		QTreeView.__init__(self, parent)
		self.setModel(model)
		if model:
			self.expand(model.idToIndex(model.INDEXID_SRCS))
			self.expand(model.idToIndex(model.INDEXID_BLOCKS))
		self.setColumnWidth(0, 170)
		self.setColumnWidth(1, 220)
		self.setColumnWidth(2, 530)

		self.__currentIdxId = None

		self.__blockMenu = QMenu(self)
		self.__blockMenu.addAction(_("&Remove block from CPU..."),
					   self.__removeBlock)

		self.__srcMenu = QMenu(self)
		self.__srcMenu.addAction(_("&Remove source from CPU..."),
					 self.__removeSource)

		self.pressed.connect(self.__mouseBtnPressed)
		self.doubleClicked.connect(self.__mouseBtnDoubleClicked)

	def __mouseBtnPressed(self, index):
		buttons = QApplication.mouseButtons()
		model = self.model()
		if not model:
			return

		try:
			idxId = model.indexToId(index)
			idxIdBase = idxId & model.INDEXID_BASE_MASK
			self.__currentIdxId = idxId

			if buttons & Qt.RightButton:
				if idxIdBase == model.INDEXID_BLOCKS_OBS_BASE or\
				   idxIdBase == model.INDEXID_BLOCKS_FCS_BASE or\
				   idxIdBase == model.INDEXID_BLOCKS_FBS_BASE or\
				   idxIdBase == model.INDEXID_BLOCKS_DBS_BASE or\
				   idxIdBase == model.INDEXID_BLOCKS_UDTS_BASE:
					self.__blockMenu.exec_(QCursor.pos() + QPoint(3, 3))
				elif idxIdBase == model.INDEXID_SRCS_AWL_BASE or\
				     idxIdBase == model.INDEXID_SRCS_FUP_BASE or\
				     idxIdBase == model.INDEXID_SRCS_SYMTAB_BASE:
					self.__srcMenu.exec_(QCursor.pos() + QPoint(3, 3))
		finally:
			self.__currentIdxId = None

	def __mouseBtnDoubleClicked(self, index):
		model = self.model()
		if not model:
			return

		if index.column() == model.COLUMN_NAME:
			idxId = model.indexToId(self.currentIndex())
			idxIdBase = idxId & model.INDEXID_BASE_MASK
			indexNr = idxId - idxIdBase

			identHash = None
			if idxIdBase == model.INDEXID_SRCS_AWL_BASE:
				identHash = model.getAwlSource(indexNr).identHash
			elif idxIdBase == model.INDEXID_SRCS_FUP_BASE:
				identHash = model.getFupSource(indexNr).identHash
			elif idxIdBase == model.INDEXID_SRCS_SYMTAB_BASE:
				identHash = model.getSymTabSource(indexNr).identHash

			if identHash is not None:
				# Double-clicked on something.
				# Try to open it.
				self.openItem.emit(identHash)

	def keyPressEvent(self, ev):
		QTreeView.keyPressEvent(self, ev)

		model = self.model()
		if not model:
			return
		idxId = model.indexToId(self.currentIndex())
		idxIdBase = idxId & model.INDEXID_BASE_MASK

		if ev.key() == Qt.Key_Delete:
			if idxIdBase == model.INDEXID_BLOCKS_OBS_BASE or\
			   idxIdBase == model.INDEXID_BLOCKS_FCS_BASE or\
			   idxIdBase == model.INDEXID_BLOCKS_FBS_BASE or\
			   idxIdBase == model.INDEXID_BLOCKS_DBS_BASE or\
			   idxIdBase == model.INDEXID_BLOCKS_UDTS_BASE:
				self.__removeBlock()
			if idxIdBase == model.INDEXID_SRCS_AWL_BASE or\
			   idxIdBase == model.INDEXID_SRCS_FUP_BASE or\
			   idxIdBase == model.INDEXID_SRCS_SYMTAB_BASE:
				self.__removeSource()

	def __removeSource(self):
		model = self.model()
		if not model:
			return
		client = model.client

		res = QMessageBox.question(self,
			_("Remove selected source?"),
			_("Remove the selected source from the CPU?\n"
			"This will also remove all associated compiled "
			"blocks from the CPU."),
			QMessageBox.Yes | QMessageBox.No,
			QMessageBox.Yes)
		if res != QMessageBox.Yes:
			return

		if self.__currentIdxId is None:
			idxId = model.indexToId(self.currentIndex())
		else:
			idxId = self.__currentIdxId
		idxIdBase = idxId & model.INDEXID_BASE_MASK
		indexNr = idxId - idxIdBase

		if idxIdBase == model.INDEXID_SRCS_AWL_BASE:
			identHash = model.getAwlSource(indexNr).identHash
		elif idxIdBase == model.INDEXID_SRCS_FUP_BASE:
			identHash = model.getFupSource(indexNr).identHash
		elif idxIdBase == model.INDEXID_SRCS_SYMTAB_BASE:
			identHash = model.getSymTabSource(indexNr).identHash
		else:
			return
		try:
			client.removeSource(identHash)
		except AwlSimError as e:
			MessageBox.handleAwlSimError(self,
				_("An error occurred while removing a source"), e)

	def __removeBlock(self):
		model = self.model()
		if not model:
			return
		client = model.client

		res = QMessageBox.question(self,
			_("Remove selected block?"),
			_("Remove the selected block from the CPU?"),
			QMessageBox.Yes | QMessageBox.No,
			QMessageBox.Yes)
		if res != QMessageBox.Yes:
			return

		if self.__currentIdxId is None:
			idxId = model.indexToId(self.currentIndex())
		else:
			idxId = self.__currentIdxId
		idxIdBase = idxId & model.INDEXID_BASE_MASK
		indexNr = idxId - idxIdBase

		if idxIdBase == model.INDEXID_BLOCKS_OBS_BASE:
			blockInfo = model.getOBBlockInfo(indexNr)
		elif idxIdBase == model.INDEXID_BLOCKS_FCS_BASE:
			blockInfo = model.getFCBlockInfo(indexNr)
		elif idxIdBase == model.INDEXID_BLOCKS_FBS_BASE:
			blockInfo = model.getFBBlockInfo(indexNr)
		elif idxIdBase == model.INDEXID_BLOCKS_DBS_BASE:
			blockInfo = model.getDBBlockInfo(indexNr)
		elif idxIdBase == model.INDEXID_BLOCKS_UDTS_BASE:
			blockInfo = model.getUDTBlockInfo(indexNr)
		else:
			return
		try:
			client.removeBlock(blockInfo)
		except AwlSimError as e:
			MessageBox.handleAwlSimError(self,
				_("An error occurred while removing a block"), e)

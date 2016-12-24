# -*- coding: utf-8 -*-
#
# AWL simulator - Block interface table model
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


class AwlInterfFieldDef(object):
	def __init__(self, name="", typeStr="", initValueStr="", comment=""):
		self.name = name
		self.typeStr = typeStr
		self.initValueStr = initValueStr
		self.comment = comment

	def isValid(self):
		return self.name and self.typeStr and self.initValueStr

class AwlInterfDef(object):
	def __init__(self):
		self.inFields = []
		self.outFields = []
		self.inOutFields = []
		self.statFields = []
		self.tempFields = []

class AwlInterfaceModel(QAbstractTableModel):
	def __init__(self,
		     haveIn=True, haveOut=True, haveInOut=True,
		     haveStat=True, haveTemp=True,
		     haveInitValue=True):
		QAbstractTableModel.__init__(self)
		self.haveIn = haveIn
		self.haveOut = haveOut
		self.haveInOut = haveInOut
		self.haveStat = haveStat
		self.haveTemp = haveTemp
		self.haveInitValue = haveInitValue
		self.interf = AwlInterfDef()

	@property
	def __nrRows_IN(self):
		if self.haveIn:
			return len(self.interf.inFields) + 1
		return 0

	@property
	def __nrRows_OUT(self):
		if self.haveOut:
			return len(self.interf.outFields) + 1
		return 0

	@property
	def __nrRows_INOUT(self):
		if self.haveInOut:
			return len(self.interf.inOutFields) + 1
		return 0

	@property
	def __nrRows_STAT(self):
		if self.haveStat:
			return len(self.interf.statFields) + 1
		return 0

	@property
	def __nrRows_TEMP(self):
		if self.haveTemp:
			return len(self.interf.tempFields) + 1
		return 0

	def __isRow_IN(self, row):
		return self.haveIn and\
		       row < self.__nrRows_IN - 1

	def __isRow_newIN(self, row):
		return self.haveIn and\
		       row == self.__nrRows_IN - 1

	def __isRow_OUT(self, row):
		return self.haveOut and\
		       row >= self.__nrRows_IN and\
		       row < self.__nrRows_IN +\
			     self.__nrRows_OUT - 1

	def __isRow_newOUT(self, row):
		interf = self.interf
		return self.haveOut and\
		       row == self.__nrRows_IN +\
			      self.__nrRows_OUT - 1

	def __isRow_INOUT(self, row):
		interf = self.interf
		return self.haveInOut and\
		       row >= self.__nrRows_IN +\
			      self.__nrRows_OUT and\
		       row < self.__nrRows_IN +\
			     self.__nrRows_OUT +\
			     self.__nrRows_INOUT - 1

	def __isRow_newINOUT(self, row):
		interf = self.interf
		return self.haveInOut and\
		       row == self.__nrRows_IN +\
			      self.__nrRows_OUT +\
			      self.__nrRows_INOUT - 1

	def __isRow_STAT(self, row):
		interf = self.interf
		return self.haveStat and\
		       row >= self.__nrRows_IN +\
			      self.__nrRows_OUT +\
			      self.__nrRows_INOUT and\
		       row < self.__nrRows_IN +\
			     self.__nrRows_OUT +\
			     self.__nrRows_INOUT +\
			     self.__nrRows_STAT - 1

	def __isRow_newSTAT(self, row):
		interf = self.interf
		return self.haveStat and\
		       row == self.__nrRows_IN +\
			      self.__nrRows_OUT +\
			      self.__nrRows_INOUT +\
			      self.__nrRows_STAT - 1

	def __isRow_TEMP(self, row):
		interf = self.interf
		return self.haveTemp and\
		       row >= self.__nrRows_IN +\
			      self.__nrRows_OUT +\
			      self.__nrRows_INOUT +\
			      self.__nrRows_STAT and\
		       row < self.__nrRows_IN +\
			     self.__nrRows_OUT +\
			     self.__nrRows_INOUT +\
			     self.__nrRows_STAT +\
			     self.__nrRows_TEMP - 1

	def __isRow_newTEMP(self, row):
		interf = self.interf
		return self.haveTemp and\
		       row == self.__nrRows_IN +\
			      self.__nrRows_OUT +\
			      self.__nrRows_INOUT +\
			      self.__nrRows_STAT +\
			      self.__nrRows_TEMP - 1

	def __row2field(self, row):
		interf = self.interf
		localRow = row
		if self.__isRow_IN(row):
			return interf.inFields[localRow]
		localRow -= self.__nrRows_IN
		if self.__isRow_OUT(row):
			return interf.outFields[localRow]
		localRow -= self.__nrRows_OUT
		if self.__isRow_INOUT(row):
			return interf.inOutFields[localRow]
		localRow -= self.__nrRows_INOUT
		if self.__isRow_STAT(row):
			return interf.statFields[localRow]
		localRow -= self.__nrRows_STAT
		if self.__isRow_TEMP(row):
			return interf.tempFields[localRow]
		return None

	def __isColumn_name(self, column):
		return column == 0

	def __isColumn_type(self, column):
		return column == 1

	def __isColumn_initValue(self, column):
		return self.haveInitValue and column == 2

	def __isColumn_comment(self, column):
		return column == 2 + (1 if self.haveInitValue else 0)

	def deleteRow(self, row):
		localRow = row
		if self.__isRow_IN(row):
			self.beginResetModel()
			del self.interf.inFields[localRow]
			self.endResetModel()
		localRow -= self.__nrRows_IN
		if self.__isRow_OUT(row):
			self.beginResetModel()
			del self.interf.outFields[localRow]
			self.endResetModel()
		localRow -= self.__nrRows_OUT
		if self.__isRow_INOUT(row):
			self.beginResetModel()
			del self.interf.inOutFields[localRow]
			self.endResetModel()
		localRow -= self.__nrRows_INOUT
		if self.__isRow_STAT(row):
			self.beginResetModel()
			del self.interf.statFields[localRow]
			self.endResetModel()
		localRow -= self.__nrRows_STAT
		if self.__isRow_TEMP(row):
			self.beginResetModel()
			del self.interf.tempFields[localRow]
			self.endResetModel()

	def moveEntry(self, fromRow, toRow):
		self.beginResetModel()
		pass#TODO
		self.endResetModel()

	def rowCount(self, parent=QModelIndex()):
		return sum((self.__nrRows_IN,
			    self.__nrRows_OUT,
			    self.__nrRows_INOUT,
			    self.__nrRows_STAT,
			    self.__nrRows_TEMP))

	def columnCount(self, parent=QModelIndex()):
		return 1 + 1 + (1 if self.haveInitValue else 0) + 1

	def data(self, index, role=Qt.DisplayRole):
		if not index:
			return None
		row, column = index.row(), index.column()
		if role in (Qt.DisplayRole, Qt.EditRole):
			field = self.__row2field(row)
			if field:
				if self.__isColumn_name(column):
					return field.name
				if self.__isColumn_type(column):
					return field.typeStr
				if self.__isColumn_initValue(column):
					return field.initValueStr
				if self.__isColumn_comment(column):
					return field.comment
				assert(0)
		elif role == Qt.BackgroundRole:
			field = self.__row2field(row)
			if field:
				if not field.isValid():
					return QBrush(QColor("red"))
			return QBrush(QColor("white"))
		elif role in (Qt.ToolTipRole, Qt.WhatsThisRole):
			if self.__isColumn_name(column):
				return "The interface field name."
			elif self.__isColumn_type(column):
				return "The interface field data type.\nFor example: BOOL  or  INT"
			elif self.__isColumn_initValue(column):
				return "The initial value in the associated DB."
			elif self.__isColumn_comment(column):
				return ""
			assert(0)
		return None

	def headerData(self, section, orientation, role=Qt.DisplayRole):
		column = section
		if role != Qt.DisplayRole:
			return None
		if orientation == Qt.Horizontal:
			if self.__isColumn_name(column):
				return "Name"
			elif self.__isColumn_type(column):
				return "Data type"
			elif self.__isColumn_initValue(column):
				return "Init value"
			elif self.__isColumn_comment(column):
				return "Comment"
			assert(0)
		else:
			interf = self.interf
			localRow = column
			if self.__isRow_IN(column):
				return "IN %d" % (localRow + 1)
			if self.__isRow_newIN(column):
				return "IN..."
			localRow -= self.__nrRows_IN
			if self.__isRow_OUT(column):
				return "OUT %d" % (localRow + 1)
			if self.__isRow_newOUT(column):
				return "OUT..."
			localRow -= self.__nrRows_OUT
			if self.__isRow_INOUT(column):
				return "IN_OUT %d" % (localRow + 1)
			if self.__isRow_newINOUT(column):
				return "IN_OUT..."
			localRow -= self.__nrRows_INOUT
			if self.__isRow_STAT(column):
				return "STAT %d" % (localRow + 1)
			if self.__isRow_newSTAT(column):
				return "STAT..."
			localRow -= self.__nrRows_STAT
			if self.__isRow_TEMP(column):
				return "TEMP %d" % (localRow + 1)
			if self.__isRow_newTEMP(column):
				return "TEMP..."
			assert(0)

	def setData(self, index, value, role=Qt.EditRole):
		if not index:
			return False
		if role == Qt.EditRole:
			row, column = index.row(), index.column()

			# Handle NEW field creation
			field = None
			insertRow = self.__nrRows_IN
			if self.__isRow_newIN(row):
				field = AwlInterfFieldDef()
				self.interf.inFields.append(field)
				self.rowsInserted.emit(QModelIndex(),
						       insertRow - 1, insertRow - 1)
			insertRow += self.__nrRows_OUT
			if self.__isRow_newOUT(row):
				field = AwlInterfFieldDef()
				self.interf.outFields.append(field)
				self.rowsInserted.emit(QModelIndex(),
						       insertRow - 1, insertRow - 1)
			insertRow += self.__nrRows_INOUT
			if self.__isRow_newINOUT(row):
				field = AwlInterfFieldDef()
				self.interf.inOutFields.append(field)
				self.rowsInserted.emit(QModelIndex(),
						       insertRow - 1, insertRow - 1)
			insertRow += self.__nrRows_STAT
			if self.__isRow_newSTAT(row):
				field = AwlInterfFieldDef()
				self.interf.statFields.append(field)
				self.rowsInserted.emit(QModelIndex(),
						       insertRow - 1, insertRow - 1)
			insertRow += self.__nrRows_TEMP
			if self.__isRow_newTEMP(row):
				field = AwlInterfFieldDef()
				self.interf.tempFields.append(field)
				self.rowsInserted.emit(QModelIndex(),
						       insertRow - 1, insertRow - 1)

			# Handle existing field modification
			if not field:
				field = self.__row2field(row)
				assert(field)

			# Set the field data
			if self.__isColumn_name(column):
				field.name = value.strip()
			elif self.__isColumn_type(column):
				field.typeStr = value.strip()
			elif self.__isColumn_initValue(column):
				field.initValueStr = value
			elif self.__isColumn_comment(column):
				field.comment = value
			else:
				assert(0)
			return True
		return False

	def flags(self, index):
		if not index:
			return Qt.ItemIsEnabled
		return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

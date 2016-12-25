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

from awlsim.common.xmlfactory import *

from awlsim.gui.util import *


class AwlInterfaceModel_factory(XmlFactory):
	def parser_open(self, tag=None):
		self.inSection = "interface"
		self.model.beginResetModel()
		self.model.clear()
		if tag:
			self.model.configure(
				haveIn=tag.getAttr("allow_inputs", False),
				haveOut=tag.getAttr("allow_outputs", False),
				haveInOut=tag.getAttr("allow_inouts", False),
				haveStat=tag.getAttr("allow_stats", False),
				haveTemp=tag.getAttr("allow_temps", False),
				haveInitValue=tag.getAttr("allow_initvalue", False))

		XmlFactory.parser_open(self, tag)

	def parser_close(self):
		self.model.endResetModel()
		XmlFactory.parser_close(self)

	def parser_beginTag(self, tag):
		interf = self.model.interf

		def mkField(tag):
			return AwlInterfFieldDef(
				name=tag.getAttr("name"),
				typeStr=tag.getAttr("type"),
				initValueStr=tag.getAttr("init", ""),
				comment=tag.getAttr("comment", ""))

		if self.inSection == "interface":
			if (tag.name == "inputs" and self.model.haveIn) or\
			   (tag.name == "outputs" and self.model.haveOut) or\
			   (tag.name == "inouts" and self.model.haveInOut) or\
			   (tag.name == "stats" and self.model.haveStat) or\
			   (tag.name == "temps" and self.model.haveTemp):
				self.inSection = tag.name
				return
		elif self.inSection == "inputs":
			if tag.name == "field":
				interf.inFields.append(mkField(tag))
				return
		elif self.inSection == "outputs":
			if tag.name == "field":
				interf.outFields.append(mkField(tag))
				return
		elif self.inSection == "inouts":
			if tag.name == "field":
				interf.inOutFields.append(mkField(tag))
				return
		elif self.inSection == "stats":
			if tag.name == "field":
				interf.statFields.append(mkField(tag))
				return
		elif self.inSection == "temps":
			if tag.name == "field":
				interf.tempFields.append(mkField(tag))
				return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if self.inSection == "interface":
			if tag.name == self.inSection:
				self.parser_finish()
				return
		else:
			if tag.name == self.inSection:
				self.inSection = "interface"
				return
			if tag.name == "field":
				return
		XmlFactory.parser_endTag(self, tag)

	def composer_getTags(self):
		model = self.model
		interf = model.interf

		def makeFields(fields):
			tags = []
			for field in fields:
				tags.append(self.Tag(name="field",
						     attrs={
					"name" : str(field.name),
					"type" : str(field.typeStr),
					"init" : str(field.initValueStr),
					"comment" : str(field.comment),
				}))
			return tags

		inputTags = makeFields(interf.inFields)
		outputTags = makeFields(interf.outFields)
		inOutTags = makeFields(interf.inOutFields)
		statTags = makeFields(interf.statFields)
		tempTags = makeFields(interf.tempFields)
		return [
			self.Tag(name="interface",
				 attrs={
					"allow_inputs" : str(int(model.haveIn)),
					"allow_outputs" : str(int(model.haveOut)),
					"allow_inouts" : str(int(model.haveInOut)),
					"allow_stats" : str(int(model.haveStat)),
					"allow_temps" : str(int(model.haveTemp)),
					"allow_initvalue" : str(int(model.haveInitValue)),
				 },
				 tags=[
					self.Tag(name="inputs",
						 tags=inputTags),
					self.Tag(name="outputs",
						 tags=outputTags),
					self.Tag(name="inouts",
						 tags=inOutTags),
					self.Tag(name="stats",
						 tags=statTags),
					self.Tag(name="temps",
						 tags=tempTags),
				 ]),
		]

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
		self.clear()

	def clear(self):
		self.inFields = []
		self.outFields = []
		self.inOutFields = []
		self.statFields = []
		self.tempFields = []

class AbstractTableModel(QAbstractTableModel):
	def __init__(self, *args, **kwargs):
		self.__resetCount = 0
		QAbstractTableModel.__init__(self, *args, **kwargs)

	def beginResetModel(self):
		try:
			if self.__resetCount <= 0:
				QAbstractTableModel.beginResetModel(self)
		finally:
			self.__resetCount += 1

	def endResetModel(self):
		self.__resetCount -= 1
		if self.__resetCount <= 0:
			self.__resetCount = 0
			QAbstractTableModel.endResetModel(self)

class AwlInterfaceModel(QAbstractTableModel):
	factory = AwlInterfaceModel_factory

	# Signal: Emitted, if some data in the model changed.
	contentChanged = Signal()

	def __init__(self,
		     haveIn=True, haveOut=True, haveInOut=True,
		     haveStat=True, haveTemp=True,
		     haveInitValue=True):
		AbstractTableModel.__init__(self)
		self.configure(haveIn, haveOut, haveInOut,
			       haveStat, haveTemp, haveInitValue)
		self.interf = AwlInterfDef()

	def clear(self):
		self.beginResetModel()
		self.interf.clear()
		self.endResetModel()
		self.contentChanged.emit()

	def configure(self,
		      haveIn=True, haveOut=True, haveInOut=True,
		      haveStat=True, haveTemp=True,
		      haveInitValue=True):
		self.beginResetModel()
		self.haveIn = haveIn
		self.haveOut = haveOut
		self.haveInOut = haveInOut
		self.haveStat = haveStat
		self.haveTemp = haveTemp
		self.haveInitValue = haveInitValue
		self.endResetModel()
		self.contentChanged.emit()

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
		self.contentChanged.emit()

	def moveEntry(self, fromRow, toRow):
		self.beginResetModel()
		pass#TODO
		self.endResetModel()
		self.contentChanged.emit()

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
				if field.isValid():
					return QBrush(QColor("white"))
				else:
					return QBrush(QColor("red"))
			return QBrush(QColor("lightgray"))
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
			self.contentChanged.emit()
			return True
		return False

	def flags(self, index):
		if not index:
			return Qt.ItemIsEnabled
		return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

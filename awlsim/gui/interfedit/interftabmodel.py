# -*- coding: utf-8 -*-
#
# AWL simulator - Block interface table model
#
# Copyright 2016-2017 Michael Buesch <m@bues.ch>
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

from awlsim.core.datatypes import *

from awlsim.gui.interfedit.interfdef import *
from awlsim.gui.util import *


class AwlInterfaceModel_factory(XmlFactory):
	def parser_open(self, tag=None):
		self.inSection = "interface"
		self.model.beginResetModel()
		self.model.clear()
		if tag:
			self.model.configure(
				haveIn=tag.getAttrBool("allow_inputs", False),
				haveOut=tag.getAttrBool("allow_outputs", False),
				haveInOut=tag.getAttrBool("allow_inouts", False),
				haveStat=tag.getAttrBool("allow_stats", False),
				haveTemp=tag.getAttrBool("allow_temps", False),
				haveRetVal=tag.getAttrBool("allow_retval", False),
				haveInitValue=tag.getAttrBool("allow_initvalue", False))

		XmlFactory.parser_open(self, tag)

	def parser_close(self):
		self.model.endResetModel()
		XmlFactory.parser_close(self)

	def parser_beginTag(self, tag):
		interf = self.model.interf

		def mkField(tag):
			return AwlInterfFieldDef(
				name=tag.getAttr("name", ""),
				typeStr=tag.getAttr("type", ""),
				initValueStr=tag.getAttr("init", ""),
				comment=tag.getAttr("comment", ""),
				uuid=tag.getAttr("uuid", None))

		if self.inSection == "interface":
			if (tag.name == "inputs" and self.model.haveIn) or\
			   (tag.name == "outputs" and self.model.haveOut) or\
			   (tag.name == "inouts" and self.model.haveInOut) or\
			   (tag.name == "stats" and self.model.haveStat) or\
			   (tag.name == "temps" and self.model.haveTemp) or\
			   (tag.name == "retval" and self.model.haveRetVal):
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
		elif self.inSection == "retval":
			if tag.name == "field":
				interf.retValField = mkField(tag)
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
				if not field:
					continue
				tags.append(self.Tag(name="field",
						     attrs={
					"name" : str(field.name),
					"type" : str(field.typeStr),
					"init" : str(field.initValueStr),
					"comment" : str(field.comment),
					"uuid" : str(field.uuid),
				}))
			return tags

		inputTags = makeFields(interf.inFields)
		outputTags = makeFields(interf.outFields)
		inOutTags = makeFields(interf.inOutFields)
		statTags = makeFields(interf.statFields)
		tempTags = makeFields(interf.tempFields)
		retValTags = makeFields([interf.retValField])
		return [
			self.Tag(name="interface",
				 attrs={
					"allow_inputs" : str(int(model.haveIn)),
					"allow_outputs" : str(int(model.haveOut)),
					"allow_inouts" : str(int(model.haveInOut)),
					"allow_stats" : str(int(model.haveStat)),
					"allow_temps" : str(int(model.haveTemp)),
					"allow_retval" : str(int(model.haveRetVal)),
					"allow_initvalue" : str(int(model.haveInitValue)),
				 },
				 attrLineBreak=True,
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
					self.Tag(name="retval",
						 tags=retValTags),
				 ]),
		]

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
			try:
				QAbstractTableModel.endResetModel(self)
			finally:
				self.__resetCount = 0

class AwlInterfaceModel(AbstractTableModel):
	factory = AwlInterfaceModel_factory

	# Signal: Emitted, if some data in the model changed.
	contentChanged = Signal()

	def __init__(self,
		     haveIn=True, haveOut=True, haveInOut=True,
		     haveStat=True, haveTemp=True, haveRetVal=True,
		     haveInitValue=True):
		AbstractTableModel.__init__(self)
		self.interf = AwlInterfDef()
		self.configure(haveIn, haveOut, haveInOut,
			       haveStat, haveTemp, haveRetVal,
			       haveInitValue)

	def clear(self):
		self.beginResetModel()
		self.interf.clear()
		self.endResetModel()
		self.contentChanged.emit()

	def configure(self,
		      haveIn=True, haveOut=True, haveInOut=True,
		      haveStat=True, haveTemp=True, haveRetVal=True,
		      haveInitValue=True):
		self.beginResetModel()
		self.haveIn = haveIn
		if not haveIn:
			self.interf.inFields = []
		self.haveOut = haveOut
		if not haveOut:
			self.interf.outFields = []
		self.haveInOut = haveInOut
		if not haveInOut:
			self.interf.inOutFields = []
		self.haveStat = haveStat
		if not haveStat:
			self.interf.statFields = []
		self.haveTemp = haveTemp
		if not haveTemp:
			self.interf.tempFields = []
		self.haveRetVal = haveRetVal
		if haveRetVal:
			self.interf.retValField = AwlInterfFieldDef("RET_VAL", "VOID")
		else:
			self.interf.retValField = None
		self.haveInitValue = haveInitValue
		if not haveInitValue:
			for field in self.interf.allFields:
				field.initValueStr = ""
		self.endResetModel()
		self.contentChanged.emit()

	def isEmpty(self):
		return self.interf.isEmpty()

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

	@property
	def __nrRows_RETVAL(self):
		if self.haveRetVal:
			return 1
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
		return self.haveOut and\
		       row == self.__nrRows_IN +\
			      self.__nrRows_OUT - 1

	def __isRow_INOUT(self, row):
		return self.haveInOut and\
		       row >= self.__nrRows_IN +\
			      self.__nrRows_OUT and\
		       row < self.__nrRows_IN +\
			     self.__nrRows_OUT +\
			     self.__nrRows_INOUT - 1

	def __isRow_newINOUT(self, row):
		return self.haveInOut and\
		       row == self.__nrRows_IN +\
			      self.__nrRows_OUT +\
			      self.__nrRows_INOUT - 1

	def __isRow_STAT(self, row):
		return self.haveStat and\
		       row >= self.__nrRows_IN +\
			      self.__nrRows_OUT +\
			      self.__nrRows_INOUT and\
		       row < self.__nrRows_IN +\
			     self.__nrRows_OUT +\
			     self.__nrRows_INOUT +\
			     self.__nrRows_STAT - 1

	def __isRow_newSTAT(self, row):
		return self.haveStat and\
		       row == self.__nrRows_IN +\
			      self.__nrRows_OUT +\
			      self.__nrRows_INOUT +\
			      self.__nrRows_STAT - 1

	def __isRow_TEMP(self, row):
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
		return self.haveTemp and\
		       row == self.__nrRows_IN +\
			      self.__nrRows_OUT +\
			      self.__nrRows_INOUT +\
			      self.__nrRows_STAT +\
			      self.__nrRows_TEMP - 1

	def __isRow_RETVAL(self, row):
		return self.haveRetVal and\
		       row == self.__nrRows_IN +\
			      self.__nrRows_OUT +\
			      self.__nrRows_INOUT +\
			      self.__nrRows_STAT +\
			      self.__nrRows_TEMP +\
			      self.__nrRows_RETVAL - 1

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
		if self.__isRow_RETVAL(row):
			return interf.retValField
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
			self.contentChanged.emit()
			return True
		localRow -= self.__nrRows_IN
		if self.__isRow_OUT(row):
			self.beginResetModel()
			del self.interf.outFields[localRow]
			self.endResetModel()
			self.contentChanged.emit()
			return True
		localRow -= self.__nrRows_OUT
		if self.__isRow_INOUT(row):
			self.beginResetModel()
			del self.interf.inOutFields[localRow]
			self.endResetModel()
			self.contentChanged.emit()
			return True
		localRow -= self.__nrRows_INOUT
		if self.__isRow_STAT(row):
			self.beginResetModel()
			del self.interf.statFields[localRow]
			self.endResetModel()
			self.contentChanged.emit()
			return True
		localRow -= self.__nrRows_STAT
		if self.__isRow_TEMP(row):
			self.beginResetModel()
			del self.interf.tempFields[localRow]
			self.endResetModel()
			self.contentChanged.emit()
			return True
		return False

	def deleteRows(self, rows):
		offset = 0
		for row in sorted(rows):
			if self.deleteRow(row + offset):
				offset -= 1

	def moveEntry(self, fromRow, toRow):
		if fromRow == toRow:
			return

		if toRow > fromRow:
			toRow += 1

		fromList = fromListIndex = None
		toList = toListIndex = None

		# Get the from-list
		localRow = fromRow
		if self.__isRow_IN(fromRow):
			fromList = self.interf.inFields
			fromListIndex = localRow
		localRow -= self.__nrRows_IN
		if self.__isRow_OUT(fromRow):
			fromList = self.interf.outFields
			fromListIndex = localRow
		localRow -= self.__nrRows_OUT
		if self.__isRow_INOUT(fromRow):
			fromList = self.interf.inOutFields
			fromListIndex = localRow
		localRow -= self.__nrRows_INOUT
		if self.__isRow_STAT(fromRow):
			fromList = self.interf.statFields
			fromListIndex = localRow
		localRow -= self.__nrRows_STAT
		if self.__isRow_TEMP(fromRow):
			fromList = self.interf.tempFields
			fromListIndex = localRow

		# Get the to-list
		localRow = toRow
		if self.__isRow_IN(toRow):
			toList = self.interf.inFields
			toListIndex = localRow
		if self.__isRow_newIN(toRow):
			toList = self.interf.inFields
			toListIndex = len(toList)
		localRow -= self.__nrRows_IN
		if self.__isRow_OUT(toRow):
			toList = self.interf.outFields
			toListIndex = localRow
		if self.__isRow_newOUT(toRow):
			toList = self.interf.outFields
			toListIndex = len(toList)
		localRow -= self.__nrRows_OUT
		if self.__isRow_INOUT(toRow):
			toList = self.interf.inOutFields
			toListIndex = localRow
		if self.__isRow_newINOUT(toRow):
			toList = self.interf.inOutFields
			toListIndex = len(toList)
		localRow -= self.__nrRows_INOUT
		if self.__isRow_STAT(toRow):
			toList = self.interf.statFields
			toListIndex = localRow
		if self.__isRow_newSTAT(toRow):
			toList = self.interf.statFields
			toListIndex = len(toList)
		localRow -= self.__nrRows_STAT
		if self.__isRow_TEMP(toRow):
			toList = self.interf.tempFields
			toListIndex = localRow
		if self.__isRow_newTEMP(toRow):
			toList = self.interf.tempFields
			toListIndex = len(toList)

		# If we have both a from-list and a to-list
		# remove the field from the from-list
		# and insert it into the to-list.
		if fromList is not None and toList is not None:
			self.beginResetModel()

			if fromList is toList and\
			   fromListIndex < toListIndex:
				toListIndex -= 1

			field = fromList.pop(fromListIndex)
			toList.insert(toListIndex, field)

			self.endResetModel()
			self.contentChanged.emit()

	def rowCount(self, parent=QModelIndex()):
		return sum((self.__nrRows_IN,
			    self.__nrRows_OUT,
			    self.__nrRows_INOUT,
			    self.__nrRows_STAT,
			    self.__nrRows_TEMP,
			    self.__nrRows_RETVAL))

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
		elif role in {Qt.BackgroundRole,
			      Qt.ForegroundRole}:
			field = self.__row2field(row)
			if field:
				if (self.__isRow_RETVAL(row) and self.__isColumn_name(column)) or\
				   (self.__isRow_TEMP(row) and self.__isColumn_initValue(column)):
					if role == Qt.BackgroundRole:
						return QBrush(QColor("#C0C0C0"))
					return QBrush(QColor("black"))
				if not field.isValid() and\
				   not self.__isColumn_comment(column):
					if role == Qt.BackgroundRole:
						return QBrush(QColor("red"))
					return QBrush(QColor("black"))
			else:
				if role == Qt.BackgroundRole:
					return QBrush(QColor("#E0E0E0"))
				return QBrush(QColor("black"))
		elif role in (Qt.ToolTipRole, Qt.WhatsThisRole):
			if self.__isRow_newIN(row):
				return "Create a new INPUT field here..."
			elif self.__isRow_newOUT(row):
				return "Create a new OUTPUT field here..."
			elif self.__isRow_newINOUT(row):
				return "Create a new IN_OUT field here..."
			elif self.__isRow_newSTAT(row):
				return "Create a new STAT field here..."
			elif self.__isRow_newTEMP(row):
				return "Create a new TEMP field here..."
			else:
				if self.__isColumn_name(column):
					if self.__isRow_RETVAL(row):
						return "Function (FC) return value."
					else:
						return "The interface field name."
				elif self.__isColumn_type(column):
					return "The interface field data type.\nFor example: BOOL  or  INT"
				elif self.__isColumn_initValue(column):
					return "The initial value in the associated DB."
				elif self.__isColumn_comment(column):
					return "Comment"
			assert(0)
		return None

	def headerData(self, section, orientation, role=Qt.DisplayRole):
		if role != Qt.DisplayRole:
			return None
		if orientation == Qt.Horizontal:
			column = section
			if self.__isColumn_name(column):
				return "Interface field name"
			elif self.__isColumn_type(column):
				return "Data type"
			elif self.__isColumn_initValue(column):
				return "Init value"
			elif self.__isColumn_comment(column):
				return "Comment"
			assert(0)
		else:
			row = section
			interf = self.interf
			localRow = row
			if self.__isRow_IN(row):
				return "IN %d" % (localRow + 1)
			if self.__isRow_newIN(row):
				return "IN ..."
			localRow -= self.__nrRows_IN
			if self.__isRow_OUT(row):
				return "OUT %d" % (localRow + 1)
			if self.__isRow_newOUT(row):
				return "OUT ..."
			localRow -= self.__nrRows_OUT
			if self.__isRow_INOUT(row):
				return "IN_OUT %d" % (localRow + 1)
			if self.__isRow_newINOUT(row):
				return "IN_OUT ..."
			localRow -= self.__nrRows_INOUT
			if self.__isRow_STAT(row):
				return "STAT %d" % (localRow + 1)
			if self.__isRow_newSTAT(row):
				return "STAT ..."
			localRow -= self.__nrRows_STAT
			if self.__isRow_TEMP(row):
				return "TEMP %d" % (localRow + 1)
			if self.__isRow_newTEMP(row):
				return "TEMP ..."
			if self.__isRow_RETVAL(row):
				return "RET_VAL"
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
				name = value.strip()
				if name.startswith("#"):
					# Permit the user to add the # prefix,
					# but remove it automatically.
					name = name[1:]
				field.name = name
			elif self.__isColumn_type(column):
				# Try to parse the type and use the actual type name
				# But only do this, if the type does not start with
				# a space. This way the user can disable
				# this automatic matching.
				if not value.startswith(" "):
					try:
						dataType = AwlDataType.makeByName(value.split())
						if dataType:
							value = str(dataType)
					except AwlSimError as e:
						pass
				field.typeStr = value
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
		row, column = index.row(), index.column()
		if (self.__isRow_RETVAL(row) and self.__isColumn_name(column)) or\
		   (self.__isRow_TEMP(row) and self.__isColumn_initValue(column)):
			return Qt.ItemIsEnabled | Qt.ItemIsSelectable
		return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

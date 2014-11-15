# -*- coding: utf-8 -*-
#
# AWL simulator - GUI standard library window
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
from awlsim.gui.icons import *

from awlsim.core.systemblocks.system_sfc import *
from awlsim.core.systemblocks.system_sfb import *


class GenericActionWidget(QWidget):
	# Signal: Code paste request.
	paste = Signal(str)
	# Signal: Finish the library selection
	finish = Signal()

	def __init__(self, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout())
		self.layout().setContentsMargins(QMargins(5, 0, 5, 0))

	def _pasteCallGeneric(self, targetName, needDB, interfaceFields):
		fields = []
		for ftype in (BlockInterfaceField.FTYPE_IN,
			      BlockInterfaceField.FTYPE_OUT,
			      BlockInterfaceField.FTYPE_INOUT):
			try:
				fields.extend(interfaceFields[ftype])
			except KeyError:
				pass
		ret = [ "\tCALL %s%s%s" %\
			(targetName,
			 ", DB ..." if needDB else "",
			 " (" if fields else "")
		]
		for field in fields:
			ret.append("\t\t%s := ...\t, // %s" % (field.name, str(field.dataType)))
		if fields:
			ret.append("\t)")
		ret.append("")
		self.paste.emit("\n".join(ret))

	def defaultPaste(self):
		pass

class SysActionWidget(GenericActionWidget):
	def __init__(self, parent=None):
		GenericActionWidget.__init__(self, parent)

		self.systemBlockCls = None
		self.blockPrefix = None

		self.desc = QLabel(self)
		font = self.desc.font()
		setFixedFontParams(font)
		self.desc.setFont(font)
		self.layout().addWidget(self.desc, 0, 0)

		self.pasteCallButton = QPushButton(self)
		self.layout().addWidget(self.pasteCallButton, 1, 0)

		self.pasteCallSymButton = QPushButton(self)
		self.layout().addWidget(self.pasteCallSymButton, 2, 0)

		self.pasteCallButton.released.connect(self.__pasteCall)
		self.pasteCallSymButton.released.connect(self.__pasteCallSym)

	def update(self, prefix, systemBlockCls):
		self.systemBlockCls = systemBlockCls
		self.blockPrefix = prefix

		blockNumber, blockName, blockDesc = systemBlockCls.name
		desc = [ "%s %d \"%s\"" % (prefix, blockNumber, blockName) ]
		for ftype, fname in ((BlockInterfaceField.FTYPE_IN, "VAR_INPUT"),
				     (BlockInterfaceField.FTYPE_OUT, "VAR_OUTPUT"),
				     (BlockInterfaceField.FTYPE_INOUT, "VAR_IN_OUT")):
			try:
				fields = systemBlockCls.interfaceFields[ftype]
			except KeyError:
				continue
			if not fields:
				continue
			desc.append("  " + fname)
			for field in fields:
				field.fieldType = ftype
				desc.append("    %s : %s;" % (field.name, str(field.dataType)))
		self.desc.setText("\n".join(desc))
		self.pasteCallButton.setText("Paste  CALL %s %d" %\
					     (prefix, blockNumber))
		self.pasteCallSymButton.setText("Paste  CALL \"%s\"" % blockName)

	def __pasteCall(self):
		blockNumber, blockName, blockDesc = self.systemBlockCls.name
		self._pasteCallGeneric("%s %d" % (self.blockPrefix, blockNumber),
				       self.systemBlockCls.isFB,
				       self.systemBlockCls.interfaceFields)
		self.finish.emit()

	def __pasteCallSym(self):
		#TODO add the symbol to the symbol table
		blockNumber, blockName, blockDesc = self.systemBlockCls.name
		self._pasteCallGeneric('"%s"' % blockName,
				       self.systemBlockCls.isFB,
				       self.systemBlockCls.interfaceFields)
		self.finish.emit()

	def defaultPaste(self):
		self.__pasteCall()

class LibraryDialog(QDialog):
	ITEM_SFC	= QListWidgetItem.UserType + 0
	ITEM_SFB	= QListWidgetItem.UserType + 1

	BLOCK_OFFSET	= QListWidgetItem.UserType + 0xFFFF

	def __init__(self, withExtensions, parent=None):
		QDialog.__init__(self, parent)
		self.setLayout(QGridLayout())
		self.setWindowTitle("AWL/STL - Standard library")
		self.setWindowIcon(getIcon("stdlib"))

		self.withExtensions = withExtensions
		self.pasteText = None
		self.currentActionWidget = None

		self.libList = QListWidget(self)
		QListWidgetItem("System functions (SFC)", self.libList, self.ITEM_SFC)
		QListWidgetItem("System function blocks (SFB)", self.libList, self.ITEM_SFB)
		self.layout().addWidget(self.libList, 0, 0, 2, 1)

		self.libElemList = QListWidget(self)
		font = self.libElemList.font()
		setFixedFontParams(font)
		self.libElemList.setFont(font)
		self.layout().addWidget(self.libElemList, 0, 1, 2, 1)

		self.iconLabel = QLabel(self)
		self.iconLabel.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
		self.iconLabel.setPixmap(getIcon("stdlib").pixmap(QSize(64, 64)))
		self.layout().addWidget(self.iconLabel, 0, 2)

		self.sysAction = SysActionWidget(self)
		self.sysAction.hide()
		self.layout().addWidget(self.sysAction, 1, 2)

		self.libList.currentItemChanged.connect(self.__libItemChanged)
		self.libElemList.currentItemChanged.connect(self.__libElemItemChanged)
		self.libElemList.itemDoubleClicked.connect(self.__libElemDoubleClicked)
		self.sysAction.paste.connect(self.__actionPaste)
		self.sysAction.finish.connect(self.accept)

		self.libList.setCurrentRow(0)

		self.libList.setMinimumWidth(200)
		self.libElemList.setMinimumWidth(380)
		self.iconLabel.setMinimumWidth(220)
		self.sysAction.setMinimumWidth(self.iconLabel.minimumWidth())

	def __addSystemBlockTable(self, prefix, table):
		biggestNum = ""
		biggestName = ""
		for blockCls in table.values():
			if blockCls.broken:
				continue
			number, name, desc = blockCls.name
			if number < 0 and not self.withExtensions:
				continue

			number = "%d" % number
			if len(number) > len(biggestNum):
				biggestNum = number
			if len(name) > len(biggestName):
				biggestName = name

		for blockCls in sorted(table.values(), key=lambda c: c.name[0]):
			if blockCls.broken:
				continue
			number, name, desc = blockCls.name
			if number < 0 and not self.withExtensions:
				continue

			absName = "%s %d" % (prefix, number)
			absName += " " * (len(prefix) + 1 + len(biggestNum) - len(absName))
			symName = '"%s"' % name
			symName += " " * (len(biggestName) - len(name))
			if desc:
				desc = "  (%s)" % desc
			else:
				desc = ""
			QListWidgetItem("%s  %s%s" % (absName, symName, desc),
					self.libElemList,
					number + self.BLOCK_OFFSET)

	def __libItemChanged(self, item, prevItem):
		self.currentActionWidget = None
		self.sysAction.hide()
		self.libElemList.clear()
		if item.type() == self.ITEM_SFC:
			self.__addSystemBlockTable("SFC", SFC_table)
		elif item.type() == self.ITEM_SFB:
			self.__addSystemBlockTable("SFB", SFB_table)
		else:
			assert(0)

	def __libElemItemChanged(self, item, prevItem):
		if not item:
			self.currentActionWidget = None
			self.sysAction.hide()
			return
		libType = self.libList.currentItem().type()
		if libType in (self.ITEM_SFC, self.ITEM_SFB):
			blockNum = item.type() - self.BLOCK_OFFSET
			self.sysAction.show()
			self.currentActionWidget = self.sysAction
			if libType == self.ITEM_SFC:
				self.sysAction.update("SFC", SFC_table[blockNum])
			else:
				self.sysAction.update("SFB", SFB_table[blockNum])
		else:
			assert(0)

	def __libElemDoubleClicked(self, item):
		if self.currentActionWidget:
			self.currentActionWidget.defaultPaste()

	def __actionPaste(self, text):
		self.pasteText = text

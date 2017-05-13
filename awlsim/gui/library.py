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

from awlsim.library.libentry import *
from awlsim.library.libselection import *


class GenericActionWidget(QWidget):
	# Signal: Code paste request.
	paste = Signal(str)
	# Signal: Add a symbol to the symbol table
	# Arguments: symbolName, address, dataType, comment
	addSymbol = Signal(str, str, str, str)
	# Signal: Add library selection
	addLibrary = Signal(AwlLibEntrySelection)
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
			with contextlib.suppress(KeyError):
				fields.extend(interfaceFields[ftype])
		ret = [ "CALL %s%s%s" %\
			(targetName,
			 ", DB ..." if needDB else "",
			 " (" if fields else "")
		]
		for field in fields:
			ret.append("\t%s := ...\t, // %s" %\
				   (field.name, str(field.dataType)))
		if fields:
			ret.append(")")
		ret.append("")
		self.paste.emit("\n".join(ret))

	def _blockToInterfaceText(self, blockIdent, blockSym,
				  verboseText,
				  interfaceFields):
		desc = [ "%s \"%s\"" % (blockIdent, blockSym) ]
		if verboseText:
			desc.append(verboseText)
		desc.append("")
		for ftype, fname in ((BlockInterfaceField.FTYPE_IN, "VAR_INPUT"),
				     (BlockInterfaceField.FTYPE_OUT, "VAR_OUTPUT"),
				     (BlockInterfaceField.FTYPE_INOUT, "VAR_IN_OUT")):
			try:
				fields = interfaceFields[ftype]
			except KeyError:
				continue
			if not fields:
				continue
			desc.append("  " + fname)
			for field in fields:
				field.fieldType = ftype
				desc.append("    %s" % field.varDeclString())
		return "\n".join(desc)

	def defaultPaste(self):
		pass

class SysActionWidget(GenericActionWidget):
	def __init__(self, parent=None):
		GenericActionWidget.__init__(self, parent)

		self.systemBlockCls = None
		self.blockPrefix = None

		self.desc = QLabel(self)
		self.desc.setFont(getDefaultFixedFont())
		self.layout().addWidget(self.desc, 0, 0, 1, 2)

		self.layout().setRowStretch(1, 1)

		label = QLabel("Paste at cursor position:", self)
		self.layout().addWidget(label, 2, 0, 1, 2)

		self.pasteCallSymButton = QPushButton(self)
		self.layout().addWidget(self.pasteCallSymButton, 3, 0)

		self.pasteCallButton = QPushButton(self)
		self.layout().addWidget(self.pasteCallButton, 3, 1)

		self.pasteCallSymButton.released.connect(self.__pasteCallSym)
		self.pasteCallButton.released.connect(self.__pasteCall)

	def updateData(self, prefix, systemBlockCls):
		self.systemBlockCls = systemBlockCls
		self.blockPrefix = prefix

		blockNumber, symbolName, blockDesc = systemBlockCls.name
		desc = self._blockToInterfaceText("%s %d" % (prefix, blockNumber),
						  symbolName, blockDesc,
						  systemBlockCls.interfaceFields)
		self.desc.setText(desc)
		self.pasteCallButton.setText("CALL %s %d" %\
					     (prefix, blockNumber))
		self.pasteCallSymButton.setText("CALL \"%s\"" % symbolName)

	def __pasteCall(self):
		blockNumber, symbolName, blockDesc = self.systemBlockCls.name
		self._pasteCallGeneric("%s %d" % (self.blockPrefix, blockNumber),
				       self.systemBlockCls._isFB,
				       self.systemBlockCls.interfaceFields)
		self.finish.emit()

	def __pasteCallSym(self):
		blockNumber, symbolName, blockDesc = self.systemBlockCls.name
		self._pasteCallGeneric('"%s"' % symbolName,
				       self.systemBlockCls._isFB,
				       self.systemBlockCls.interfaceFields)
		self.addSymbol.emit(symbolName,
				    "%s %s" % (self.blockPrefix, blockNumber),
				    "%s %s" % (self.blockPrefix, blockNumber),
				    blockDesc)
		self.finish.emit()

	def defaultPaste(self):
		self.__pasteCallSym()

class LibActionWidget(GenericActionWidget):
	def __init__(self, parent=None):
		GenericActionWidget.__init__(self, parent)

		self.libEntryCls = None

		self.desc = QLabel(self)
		self.desc.setFont(getDefaultFixedFont())
		self.layout().addWidget(self.desc, 0, 0, 1, 2)

		self.layout().setRowStretch(1, 1)

		label = QLabel("Paste at cursor position:", self)
		self.layout().addWidget(label, 2, 0, 1, 2)

		self.pasteCallSymButton = QPushButton(self)
		self.layout().addWidget(self.pasteCallSymButton, 3, 0)

		self.pasteCallButton = QPushButton(self)
		self.layout().addWidget(self.pasteCallButton, 3, 1)

		self.pasteCodeSymButton = QPushButton(self)
		self.layout().addWidget(self.pasteCodeSymButton, 4, 0)

		self.pasteCodeButton = QPushButton(self)
		self.layout().addWidget(self.pasteCodeButton, 4, 1)

		self.pasteCallSymButton.released.connect(self.__pasteCallSym)
		self.pasteCallButton.released.connect(self.__pasteCall)
		self.pasteCodeSymButton.released.connect(self.__pasteCodeSym)
		self.pasteCodeButton.released.connect(self.__pasteCode)

	def updateData(self, libEntryCls):
		self.libEntryCls = libEntryCls

		prefix = "FC" if libEntryCls._isFC else "FB"
		typeStr = "FUNCTION" if libEntryCls._isFC else "FUNCTION_BLOCK"
		self.blockName = "%s %d" % (prefix, libEntryCls.staticIndex)

		desc = self._blockToInterfaceText(self.blockName,
						  libEntryCls.symbolName,
						  libEntryCls.description,
						  libEntryCls.interfaceFields)
		self.desc.setText(desc)

		self.pasteCodeButton.setText("%s %s" %\
					     (typeStr, self.blockName))
		self.pasteCodeSymButton.setText("%s \"%s\"" %\
						(typeStr, libEntryCls.symbolName))
		self.pasteCallButton.setText("CALL %s" % self.blockName)
		self.pasteCallSymButton.setText("CALL \"%s\"" %\
						libEntryCls.symbolName)

	def __pasteCodeWarning(self):
		res = QMessageBox.warning(self,
			"Paste library code body?",
			"Warning: It is not recommended to paste library "
			"code into the project sources. You should instead "
			"just import the library (via library selection table) "
			"and CALL the imported function.\n\n"
			"See the 'CALL \"%s\"' or 'CALL %s' buttons.\n\n"
			"Do you want to paste the code nevertheless?" % (
			self.libEntryCls.symbolName, self.blockName),
			QMessageBox.Yes | QMessageBox.No,
			QMessageBox.No)
		return res == QMessageBox.Yes

	def __pasteCode(self):
		if not self.__pasteCodeWarning():
			return
		self.paste.emit(self.libEntryCls().getCode(False))
		self.finish.emit()

	def __pasteCodeSym(self):
		if not self.__pasteCodeWarning():
			return
		self.paste.emit(self.libEntryCls().getCode(True))
		self.addSymbol.emit(self.libEntryCls.symbolName,
				    self.blockName,
				    self.blockName,
				    self.libEntryCls.description)
		self.finish.emit()

	def __pasteCall(self):
		self._pasteCallGeneric(self.blockName,
				       self.libEntryCls._isFB,
				       self.libEntryCls.interfaceFields)
		self.addLibrary.emit(self.libEntryCls().makeSelection())
		self.finish.emit()

	def __pasteCallSym(self):
		self._pasteCallGeneric('"%s"' % self.libEntryCls.symbolName,
				       self.libEntryCls._isFB,
				       self.libEntryCls.interfaceFields)
		self.addSymbol.emit(self.libEntryCls.symbolName,
				    self.blockName,
				    self.blockName,
				    self.libEntryCls.description)
		self.addLibrary.emit(self.libEntryCls().makeSelection())
		self.finish.emit()

	def defaultPaste(self):
		self.__pasteCallSym()

class LibraryDialog(QDialog):
	ITEM_SFC	= QListWidgetItem.UserType + 0
	ITEM_SFB	= QListWidgetItem.UserType + 1
	ITEM_LIB_BASE	= QListWidgetItem.UserType + 100

	BLOCK_OFFSET	= QListWidgetItem.UserType + 0xFFFF

	def __init__(self, project, parent=None):
		QDialog.__init__(self, parent)
		self.setLayout(QGridLayout())
		self.setWindowTitle("AWL/STL - Standard library")
		self.setWindowIcon(getIcon("stdlib"))

		self.project = project

		self.pasteText = None
		self.pasteSymbol = None
		self.pasteLibSel = None

		self.currentActionWidget = None
		self.__nr2lib = {}
		self.__nr2entry = {}

		self.libList = QListWidget(self)
		QListWidgetItem("System functions (SFC)", self.libList, self.ITEM_SFC)
		QListWidgetItem("System function blocks (SFB)", self.libList, self.ITEM_SFB)
		for i, libName in enumerate(("IEC",)):
			try:
				lib = AwlLib.getByName(libName)
			except AwlSimError as e:
				MessageBox.handleAwlSimError(self, "Library error", e)
				continue
			self.__nr2lib[self.ITEM_LIB_BASE + i] = lib
			QListWidgetItem(lib.description, self.libList,
					self.ITEM_LIB_BASE + i)
		self.layout().addWidget(self.libList, 0, 0, 3, 1)

		self.libElemList = QListWidget(self)
		self.libElemList.setFont(getDefaultFixedFont())
		self.layout().addWidget(self.libElemList, 0, 1, 3, 1)

		self.iconLabel = QLabel(self)
		self.iconLabel.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
		self.iconLabel.setPixmap(getIcon("stdlib").pixmap(QSize(64, 64)))
		self.layout().addWidget(self.iconLabel, 0, 2)

		self.sysAction = SysActionWidget(self)
		self.sysAction.hide()
		self.layout().addWidget(self.sysAction, 1, 2)

		self.libAction = LibActionWidget(self)
		self.libAction.hide()
		self.layout().addWidget(self.libAction, 2, 2)

		self.libList.currentItemChanged.connect(self.__libItemChanged)
		self.libElemList.currentItemChanged.connect(self.__libElemItemChanged)
		self.libElemList.itemDoubleClicked.connect(self.__libElemDoubleClicked)
		for actionWidget in (self.sysAction, self.libAction):
			actionWidget.paste.connect(self.__actionPaste)
			actionWidget.addSymbol.connect(self.__actionAddSym)
			actionWidget.addLibrary.connect(self.__actionAddLib)
			actionWidget.finish.connect(self.accept)

		self.libList.setCurrentRow(0)

		self.libList.setMinimumWidth(190)
		self.libElemList.setMinimumWidth(350)
		self.iconLabel.setMinimumWidth(400)
		self.sysAction.setMinimumWidth(self.iconLabel.minimumWidth())
		self.libAction.setMinimumWidth(self.iconLabel.minimumWidth())
		self.resize(self.size().width(), 360)

	def __addLibElemList(self, entries):
		# Figure out the padding.
		maxA = maxB = ""
		for number, textA, textB, textC in entries:
			if len(textA) > len(maxA):
				maxA = textA
			if len(textB) > len(maxB):
				maxB = textB
		# Pad the entries and add them to the widget.
		for number, textA, textB, textC in entries:
			textA += " " * (len(maxA) - len(textA))
			textB += " " * (len(maxB) - len(textB))
			QListWidgetItem("%s  %s%s" % (textA, textB, textC),
					self.libElemList,
					number)

	def __addSystemBlockTable(self, prefix, table):
		entries = []
		for blockCls in sorted(dictValues(table), key=lambda c: c.name[0]):
			if blockCls.broken:
				continue
			number, name, desc = blockCls.name
			if number < 0 and not self.project.getExtInsnsEn():
				continue

			absName = "%s %d" % (prefix, number)
			symName = '"%s"' % name
			if desc:
				desc = "  (%s)" % desc
			else:
				desc = ""
			entries.append((number + self.BLOCK_OFFSET,
					absName, symName, desc))
		self.__addLibElemList(entries)

	def __addLibraryTable(self, lib):
		entries = []
		for i, libCls in enumerate(sorted(lib.entries(),
						  key=lambda c: c.staticIndex)):
			if libCls.broken:
				continue
			absName = "%s %d" % ("FC" if libCls._isFC else "FB",\
					     libCls.staticIndex)
			symName = '"%s"' % libCls.symbolName
			if libCls.description:
				desc = "  (%s)" % libCls.description
			else:
				desc = ""
			entries.append((i + self.BLOCK_OFFSET,
					absName, symName, desc))
			self.__nr2entry[i + self.BLOCK_OFFSET] = libCls
		self.__addLibElemList(entries)

	def __hideAllActionWidgets(self):
		self.currentActionWidget = None
		self.sysAction.hide()
		self.libAction.hide()

	def __libItemChanged(self, item, prevItem):
		self.__hideAllActionWidgets()
		self.libElemList.clear()
		if item.type() == self.ITEM_SFC:
			self.__addSystemBlockTable("SFC", SFC_table)
		elif item.type() == self.ITEM_SFB:
			self.__addSystemBlockTable("SFB", SFB_table)
		elif item.type() >= self.ITEM_LIB_BASE:
			lib = self.__nr2lib[item.type()]
			self.__addLibraryTable(lib)
		else:
			assert(0)

	def __libElemItemChanged(self, item, prevItem):
		if not item:
			self.__hideAllActionWidgets()
			return
		libType = self.libList.currentItem().type()
		if libType in (self.ITEM_SFC, self.ITEM_SFB):
			blockNum = item.type() - self.BLOCK_OFFSET
			self.sysAction.show()
			self.currentActionWidget = self.sysAction
			if libType == self.ITEM_SFC:
				self.sysAction.updateData("SFC", SFC_table[blockNum])
			else:
				self.sysAction.updateData("SFB", SFB_table[blockNum])
		elif libType >= self.ITEM_LIB_BASE:
			entryCls = self.__nr2entry[item.type()]
			self.libAction.show()
			self.currentActionWidget = self.libAction
			self.libAction.updateData(entryCls)
		else:
			assert(0)

	def __libElemDoubleClicked(self, item):
		if self.currentActionWidget:
			self.currentActionWidget.defaultPaste()

	def __actionPaste(self, text):
		assert(self.pasteText is None)
		self.pasteText = text

	def __actionAddSym(self, symbolName, address, dataType, comment):
		assert(self.pasteSymbol is None)
		self.pasteSymbol = (symbolName, address, dataType, comment)

	def __actionAddLib(self, libSelection):
		assert(self.pasteLibSel is None)
		self.pasteLibSel = libSelection

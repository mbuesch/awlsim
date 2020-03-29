# -*- coding: utf-8 -*-
#
# AWL simulator - Project tree widget
#
# Copyright 2017-2020 Michael Buesch <m@bues.ch>
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

from awlsim.core.symbolparser import SymTabParser, Symbol
from awlsim.library.libselection import AwlLibEntrySelection

from awlsim.gui.cpuwidget import GuiRunState
from awlsim.gui.util import *
from awlsim.gui.icons import *
from awlsim.gui.runstate import *
from awlsim.gui.fup.fupwidget import FupFactory, FupWidget
from awlsim.gui.validatorsched import *


__all__ = [
	"ProjectTreeModel",
	"ProjectTreeView",
]


class ProjectTreeModel(QAbstractItemModel):
	"""Main project tree model.
	"""

	# Signal: Project has just been loaded.
	projectLoaded = Signal()

	# Signal: Some project data changed.
	projectContentChanged = Signal()


	EnumGen.start
	INDEXID_SRCS			= EnumGen.item
	INDEXID_SRCS_AWL		= EnumGen.item
	INDEXID_SRCS_FUP		= EnumGen.item
	INDEXID_SRCS_KOP		= EnumGen.item
	INDEXID_SRCS_SYMTAB		= EnumGen.item
	INDEXID_SRCS_LIBSEL		= EnumGen.item
	INDEXID_CPU			= EnumGen.item
	INDEXID_CONN			= EnumGen.item
	INDEXID_HW			= EnumGen.item
	INDEXID_GUICONF			= EnumGen.item
	EnumGen.end

	# Base ID mask for dynamic elements
	INDEXID_BASE_MASK		= 0xFF0000
	# ID bases for dynamic elements
	INDEXID_SRCS_AWL_BASE		= 0x010000
	INDEXID_SRCS_FUP_BASE		= 0x020000
	INDEXID_SRCS_KOP_BASE		= 0x030000
	INDEXID_SRCS_SYMTAB_BASE	= 0x040000

	row2id_toplevel = {
		0	: INDEXID_SRCS,
		1	: INDEXID_CPU,
		2	: INDEXID_CONN,
		3	: INDEXID_HW,
		4	: INDEXID_GUICONF,
	}
	id2row_toplevel = pivotDict(row2id_toplevel)

	row2id_srcs = {
		0	: INDEXID_SRCS_AWL,
		1	: INDEXID_SRCS_FUP,
#		2	: INDEXID_SRCS_KOP,
		2	: INDEXID_SRCS_SYMTAB,
		3	: INDEXID_SRCS_LIBSEL,
	}
	id2row_srcs = pivotDict(row2id_srcs)

	id2childBase = {
		INDEXID_SRCS_AWL	: INDEXID_SRCS_AWL_BASE,
		INDEXID_SRCS_FUP	: INDEXID_SRCS_FUP_BASE,
		INDEXID_SRCS_KOP	: INDEXID_SRCS_KOP_BASE,
		INDEXID_SRCS_SYMTAB	: INDEXID_SRCS_SYMTAB_BASE,
	}
	base2parentId = pivotDict(id2childBase)

	EnumGen.start
	COLUMN_NAME	= EnumGen.item
	EnumGen.end

	def __init__(self, mainWidget, project=None, parent=None):
		QAbstractItemModel.__init__(self, parent)
		self.mainWidget = mainWidget

		self.__reset(project)

		self.mainWidget.dirtyChanged.connect(self.__handleProjectDirtyChanged)

		self.dataChanged.connect(self.__handleDataChanged)
		self.modelReset.connect(self.__projectContentChanged)
		self.rowsInserted.connect(self.__projectContentChanged)
		self.rowsMoved.connect(self.__projectContentChanged)
		self.rowsRemoved.connect(self.__projectContentChanged)

	@property
	def editMdiArea(self):
		"""Get EditMdiArea instance.
		"""
		return self.mainWidget.editMdiArea

	def handleAwlSimError(self, exception):
		"""An AwlSimError occurred (due to normal operation or validation).
		"""
		anyChanged = False
		project = self.getProject()
		for source in project.getAllSources():
			# Set error flag on corresponding source.
			if exception and exception.getSourceId() == source.identHash:
				# Set error flag.
				if not source.userData.get("gui-erroneous", False):
					anyChanged = True
				source.userData["gui-erroneous"] = True
			else:
				# Clear error flag.
				if source.userData.get("gui-erroneous", False):
					anyChanged = True
				source.userData["gui-erroneous"] = False

		# Mark the program container as changed.
		if anyChanged:
			#FIXME this doesn't always work correctly. Do we need to mark all sub-items as changed?
			index = self.idToIndex(self.INDEXID_SRCS)
			roles = (Qt.DecorationRole, Qt.ToolTipRole)
			self.dataChanged.emit(index, index, roles)

	def handleIdentsMsg(self, identsMsg):
		"""Handle a new identifier message from AwlSimClient().
		identsMsg: AwlSimMessage_IDENTS() instance.
		"""
		identsMsgAwlSources = identsMsg.awlSources if identsMsg else []
		identsMsgFupSources = identsMsg.fupSources if identsMsg else []
		identsMsgKopSources = identsMsg.kopSources if identsMsg else []
		identsMsgSymTabSources = identsMsg.symTabSources if identsMsg else []

		awlIdentHashes = [ s.identHash for s in identsMsgAwlSources ]
		fupIdentHashes = [ s.identHash for s in identsMsgFupSources ]
		kopIdentHashes = [ s.identHash for s in identsMsgKopSources ]
		symTabIdentHashes = [ s.identHash for s in identsMsgSymTabSources ]

		# Iterate over all sources in the project and check if the
		# identHash matches what's in the CPU.
		project = self.getProject()
		roles = (Qt.DecorationRole, Qt.ToolTipRole)
		anyChanged = False
		for getSources, identHashes, idxId in (
				(project.getAwlSources, awlIdentHashes, self.INDEXID_SRCS_AWL),
				(project.getFupSources, fupIdentHashes, self.INDEXID_SRCS_FUP),
				(project.getKopSources, kopIdentHashes, self.INDEXID_SRCS_KOP),
				(project.getSymTabSources, symTabIdentHashes, self.INDEXID_SRCS_SYMTAB)):
			anySourceChanged = False
			for i, source in enumerate(getSources()):
				# Update the match state in the source user data.
				oldMatchState = source.userData.get("gui-cpu-idents-match", None)
				newMatchState = source.identHash in identHashes
				source.userData["gui-cpu-idents-match"] = newMatchState

				# If the match state changed, emit the dataChanged signal.
				if oldMatchState != newMatchState:
					anyChanged = anySourceChanged = True
					parentIndex = self.idToIndex(idxId)
					if parentIndex.isValid():
						index = self.index(i, 0, parentIndex)
						self.dataChanged.emit(index, index, roles)
			# Mark the parent source container as changed.
			if anySourceChanged:
				parentIndex = self.idToIndex(idxId)
				if parentIndex.isValid():
					self.dataChanged.emit(parentIndex, parentIndex, roles)
		# Mark the program container as changed.
		if anyChanged:
			index = self.idToIndex(self.INDEXID_SRCS)
			self.dataChanged.emit(index, index, roles)

	def setGuiRunState(self, guiRunState):
		"""Handle a CPU run state change.
		guiRunState: GuiRunState() instance.
		"""

		# Store the run state object.
		self.__guiRunState = guiRunState

		# Emit the dataChanged signal for all sources
		# and all parent source containers.
		project = self.getProject()
		roles = (Qt.DecorationRole, Qt.ToolTipRole)
		for getSources, idxId in (
				(project.getAwlSources, self.INDEXID_SRCS_AWL),
				(project.getFupSources, self.INDEXID_SRCS_FUP),
				(project.getKopSources, self.INDEXID_SRCS_KOP),
				(project.getSymTabSources, self.INDEXID_SRCS_SYMTAB)):
			parentIndex = self.idToIndex(idxId)
			if parentIndex.isValid():
				for i, source in enumerate(getSources()):
					index = self.index(i, 0, parentIndex)
					self.dataChanged.emit(index, index, roles)
				self.dataChanged.emit(parentIndex, parentIndex, roles)
		index = self.idToIndex(self.INDEXID_SRCS)
		self.dataChanged.emit(index, index, roles)
		self.headerDataChanged.emit(Qt.Horizontal, 0, 0)

	def entryActivate(self, index, parentWidget=None):
		if not index or not index.isValid():
			return False
		idxIdBase, idxId, itemNr = self.indexToId(index)

		editMdiArea = self.editMdiArea
		project = self.getProject()

		def connectMdiSubWinSignals(mdiSubWin):
			# Connect signals from newly created mdiSubWin
			# to this project tree.
			mdiSubWin.sourceChanged.connect(
				lambda: self.__handleMdiSubWinSourceChanged(mdiSubWin))

		if idxId == self.INDEXID_CPU:
			self.mainWidget.cpuConfig()
			return True
		elif idxId == self.INDEXID_CONN:
			self.mainWidget.linkConfig()
			return True
		elif idxId == self.INDEXID_HW:
			self.mainWidget.hwmodConfig()
			return True
		elif idxId == self.INDEXID_GUICONF:
			self.mainWidget.guiConfig()
			return True
		elif idxId == self.INDEXID_SRCS_LIBSEL:
			libSelMdiSubWin = self.__libSelMdiSubWin
			if libSelMdiSubWin:
				editMdiArea.setActiveSubWindow(libSelMdiSubWin)
			else:
				libSelections = project.getLibSelections()
				def removeLibSelMdiSubWin(w):
					self.__libSelMdiSubWin = None
				libSelMdiSubWin = editMdiArea.newWin_Libsel(libSelections)
				libSelMdiSubWin.closed.connect(removeLibSelMdiSubWin)
				self.__libSelMdiSubWin = libSelMdiSubWin
				connectMdiSubWinSignals(libSelMdiSubWin)
			return True

		def handleSourceWindowActivation(sources, makeNewWin):
			source = sources[itemNr]
			mdiSubWin = source.userData.get("gui-edit-window")
			if mdiSubWin:
				editMdiArea.setActiveSubWindow(mdiSubWin)
			else:
				# Create a new MDI window.
				mdiSubWin = makeNewWin(source)
				mdiSubWin.closed.connect(lambda w:
					source.userData.pop("gui-edit-window", None))
				source.userData["gui-edit-window"] = mdiSubWin
				connectMdiSubWinSignals(mdiSubWin)

		if idxIdBase == self.INDEXID_SRCS_AWL_BASE:
			handleSourceWindowActivation(
				sources=project.getAwlSources(),
				makeNewWin=lambda source: editMdiArea.newWin_AWL(source))
			return True
		elif idxIdBase == self.INDEXID_SRCS_FUP_BASE:
			handleSourceWindowActivation(
				sources=project.getFupSources(),
				makeNewWin=lambda source: editMdiArea.newWin_FUP(source))
			return True
		elif idxIdBase == self.INDEXID_SRCS_KOP_BASE:
			handleSourceWindowActivation(
				sources=project.getKopSources(),
				makeNewWin=lambda source: editMdiArea.newWin_KOP(source))
			return True
		elif idxIdBase == self.INDEXID_SRCS_SYMTAB_BASE:
			handleSourceWindowActivation(
				sources=project.getSymTabSources(),
				makeNewWin=lambda source: editMdiArea.newWin_SymTab(source))
			return True

		# If an empty source container is activated,
		# we add a new source to that container and activate it.
		addNew = False
		if idxId == self.INDEXID_SRCS_AWL:
			if not project.getAwlSources():
				addNew = True
		elif idxId == self.INDEXID_SRCS_FUP:
			if not project.getFupSources():
				addNew = True
		elif idxId == self.INDEXID_SRCS_KOP:
			if not project.getKopSources():
				addNew = True
		elif idxId == self.INDEXID_SRCS_SYMTAB:
			if not project.getSymTabSources():
				addNew = True
		if addNew:
			newIndex = self.entryAdd(self.id2childBase[idxId],
						 parentWidget=parentWidget)
			self.entryActivate(newIndex, parentWidget=parentWidget)

		return False

	def entryDelete(self, index, force=False, parentWidget=None):
		if not index or not index.isValid():
			return False
		idxIdBase, idxId, itemNr = self.indexToId(index)

		getter, setter = self.sourceGetter(idxIdBase)
		if not getter or not setter:
			return False

		sourceList = getter()
		source = sourceList[itemNr]
		if not force:
			res = QMessageBox.question(parentWidget or self.mainWidget,
				"Remove selected source?",
				"Remove the selected source '%s' from the project?\n"
				"This can't be undone.\n" % (
				source.name),
				QMessageBox.Yes | QMessageBox.No,
				QMessageBox.Yes)
			if res != QMessageBox.Yes:
				return False

		self.beginRemoveRows(index.parent(), itemNr, itemNr)
		try:
			# Close the MDI edit window, if one is open.
			mdiSubWin = source.userData.get("gui-edit-window")
			if mdiSubWin:
				mdiSubWin.forceClose()
				del mdiSubWin
			# Remove source from project.
			sourceList.pop(itemNr)
			setter(sourceList)
		finally:
			self.endRemoveRows()
		return True

	def entryAdd(self, idxIdBase, source=None, pos=-1, parentWidget=None):
		if idxIdBase == self.INDEXID_SRCS_AWL_BASE:
			parentIdxId = self.INDEXID_SRCS_AWL
			if not source:
				source = AwlSource()
		elif idxIdBase == self.INDEXID_SRCS_FUP_BASE:
			parentIdxId = self.INDEXID_SRCS_FUP
			if not source:
				source = FupSource()
		elif idxIdBase == self.INDEXID_SRCS_KOP_BASE:
			parentIdxId = self.INDEXID_SRCS_KOP
			if not source:
				source = KopSource()
		elif idxIdBase == self.INDEXID_SRCS_SYMTAB_BASE:
			parentIdxId = self.INDEXID_SRCS_SYMTAB
			if not source:
				source = SymTabSource()
		else:
			return None

		if not source.name:
			source.name = ">>> New source <<<"

		getter, setter = self.sourceGetter(idxIdBase)
		parentIndex = self.idToIndex(parentIdxId)

		sources = getter()
		if pos < 0:
			pos = len(sources)
		pos = min(pos, len(sources))
		self.beginInsertRows(parentIndex, pos, pos)
		try:
			sources.insert(pos, source)
			setter(sources)
		finally:
			self.endInsertRows()
		return self.index(pos, 0, parentIndex)

	def entryRename(self, index, newName=None, parentWidget=None):
		idxIdBase, idxId, itemNr = self.indexToId(index)
		getter, setter = self.sourceGetter(idxIdBase)
		if getter and setter:
			sources = getter()
			source = sources[itemNr]
			if newName is None:
				newName, ok = QInputDialog.getText(parentWidget,
					"Name for %s source" % source.SRCTYPE,
					"Name for %s source" % source.SRCTYPE,
					QLineEdit.Normal,
					source.name)
				if not ok:
					newName = None
			if newName is not None:
				# Set the new name in the project.
				source.name = newName
				setter(sources)

				# Update the MDI window, if any.
				mdiSubWin = source.userData.get("gui-edit-window")
				if mdiSubWin:
					mdiSubWin.getSource().name = newName
					mdiSubWin.updateTitle()

				self.dataChanged.emit(index, index, (Qt.EditRole,))
				return True
		return False

	def entryIntegrate(self, index, parentWidget=None):
		idxIdBase, idxId, itemNr = self.indexToId(index)
		getter, setter = self.sourceGetter(idxIdBase)
		if getter:
			# Remove the file backing reference.
			source = getter()[itemNr]
			source.forceNonFileBacked(source.name)

			# Update the MDI window, if any.
			mdiSubWin = source.userData.get("gui-edit-window")
			if mdiSubWin:
				mdiSubWin.setSource(source)

			self.__projectContentChanged()
			return True
		return False

	def entryEnable(self, index, enable=True, parentWidget=None):
		idxIdBase, idxId, itemNr = self.indexToId(index)
		getter, setter = self.sourceGetter(idxIdBase)
		if getter:
			# Set the new enable status in the project.
			source = getter()[itemNr]
			source.enabled = enable

			# Update the MDI window, if any.
			mdiSubWin = source.userData.get("gui-edit-window")
			if mdiSubWin:
				mdiSubWin.getSource().enabled = enable
				mdiSubWin.updateTitle()

			self.__projectContentChanged()
			return True
		return False

	def entryImport(self, idxIdBase, parentWidget=None):
		"""Import an entry from an external file.
		"""
		# Create a new entry that we import the data to.
		newIndex = self.entryAdd(idxIdBase, parentWidget=parentWidget)
		if not newIndex:
			return False

		def error():
			self.entryDelete(newIndex, force=True, parentWidget=parentWidget)
			return False

		# Activate the new entry.
		if not self.entryActivate(newIndex, parentWidget=parentWidget):
			return error()
		# Get the source of the new item.
		source = self.indexToSource(newIndex)
		if not source:
			return error()
		# Get the MDI sub window of the new entry.
		mdiSubWin = source.userData.get("gui-edit-window")
		if not mdiSubWin:
			return error()
		# Call import of the new entry.
		if not mdiSubWin.importSource():
			return error()
		self.dataChanged.emit(newIndex, newIndex)
		return True

	def entryExport(self, index, filePath=None, parentWidget=None):
		"""Export an entry to an external file.
		"""
		# Activate the export entry.
		if not self.entryActivate(index, parentWidget=parentWidget):
			return False
		# Get the source of the export item.
		source = self.indexToSource(index)
		if not source:
			return False
		# Get the MDI sub window of the export entry.
		mdiSubWin = source.userData.get("gui-edit-window")
		if not mdiSubWin:
			return False
		# Call export of the new entry.
		if not mdiSubWin.exportSource():
			return False
		return True

	def entryClipboardCopy(self, index, parentWidget=None):
		"""Copy the item at 'index' into the global clipboard.
		"""
		mimeData = self.mimeData((index,))
		if not mimeData:
			return False

		# Write the data to the clipboard.
		clipboard = QGuiApplication.clipboard()
		if not clipboard:
			return False
		clipboard.setMimeData(mimeData, QClipboard.Clipboard)
		if clipboard.supportsSelection():
			clipboard.setMimeData(mimeData, QClipboard.Selection)
		return True

	def entryClipboardCut(self, index, parentWidget=None):
		"""Cut the item at 'index' into the global clipboard.
		"""
		if self.entryClipboardCopy(index, parentWidget=parentWidget):
			if self.entryDelete(index, force=True, parentWidget=parentWidget):
				return True
		return False

	def entryClipboardPaste(self, parentIndex, parentWidget=None):
		"""Try to paste an entry from the global clipboard.
		Returns the index of the pasted item, or None.
		"""
		# Get the data from the clipboard.
		clipboard = QGuiApplication.clipboard()
		if not clipboard:
			return None
		mimeData = clipboard.mimeData(QClipboard.Clipboard)
		if not mimeData:
			return None

		parentIdxIdBase, parentIdxId, parentItemNr = self.indexToId(parentIndex)
		if parentIdxIdBase == 0:
			# Append to the end of the container.
			row = -1
		else:
			# Paste it after this element.
			row = parentIndex.row() + 1
			parentIndex = self.parent(parentIndex)

		return self.__dropMimeData(mimeData, Qt.CopyAction, row, 0, parentIndex)

	def symbolAdd(self, symbol, parentWidget=None):
		"""Try to add the symbol to a symbol table.
		symbol: The Symbol() instance to add.
		Returns True, if adding was successfull.
		"""
		project = self.getProject()
		mnemonics = project.getCpuConf().getConfiguredMnemonics()
		symTabSources = project.getSymTabSources()

		# Check if we already have this symbol.
		for symTabSource in symTabSources:
			try:
				symTab = SymTabParser.parseSource(symTabSource,
								  mnemonics=mnemonics)
			except AwlSimError as e:
				MessageBox.handleAwlSimError(parentWidget,
					"Failed to parse symbol table", e)
			if symbol in symTab:
				# We already have this symbol.
				#TODO modify it, if needed
				return True

		if not symTabSources:
			# We don't have a symbol table.
			#TODO add one
			return False

		if len(symTabSources) == 1:
			# We only have one table. Add the symbol to that table.
			symTabIndex = 0
		else:
			# Ask which table to add the symbol to.
			entries = [ "%d: %s" % (i + 1, symTabSource.name)
				for i, symTabSource in enumerate(symTabSources)
			]
			entry, ok = QInputDialog.getItem(parentWidget,
				"Select symbol table",
				"Please select the symbol table "\
				"where to add the symbol to:"
				"\n%s  \"%s\"" %\
				(symbol.getOperatorString(), symbol.getName()),
				entries, 0, False)
			if not ok or not entry:
				return False
			symTabIndex = int(entry.split(":")[0]) - 1

		# Add the symbol to the sym tab source.
		symTabSource = symTabSources[symTabIndex]
		try:
			symTab = SymTabParser.parseSource(symTabSource,
							  mnemonics=mnemonics)
		except AwlSimError as e:
			MessageBox.handleAwlSimError(parentWidget,
				"Failed to parse symbol table", e)
		symTab.add(symbol, True)

		# Update the sym tab source.
		try:
			symTab.toSource(symTabSource)
		except AwlSimError as e:
			MessageBox.handleAwlSimError(parentWidget,
				"Failed to update symbol table", e)

		# If an MDI edit window is open for this source, update it.
		mdiSubWin = symTabSource.userData.get("gui-edit-window")
		if mdiSubWin:
			mdiSubWin.setSource(symTabSource)

		self.__projectContentChanged()
		return True

	def libSelectionAdd(self, libSelection, parentWidget=None):
		"""Try to add the library selection to the library selection table.
		libSelection: The AwlLibEntrySelection() to add.
		Returns True, if adding was successfull.
		"""
		project = self.getProject()
		libSelections = project.getLibSelections()

		# Check if we already have this selection.
		if libSelection in libSelections:
			return True # We already have this lib.

		# Add the library selection to the table.
		libSelections.append(libSelection)
		project.setLibSelections(libSelections)

		# If an MDI edit window is open, update it.
		if self.__libSelMdiSubWin:
			self.__libSelMdiSubWin.setLibSelections(libSelections)

		self.__projectContentChanged()
		return True

	def sourceGetter(self, idxIdBase):
		project = self.getProject()
		if idxIdBase == self.INDEXID_SRCS_AWL_BASE:
			getter = project.getAwlSources
			setter = project.setAwlSources
		elif idxIdBase == self.INDEXID_SRCS_FUP_BASE:
			getter = project.getFupSources
			setter = project.setFupSources
		elif idxIdBase == self.INDEXID_SRCS_KOP_BASE:
			getter = project.getKopSources
			setter = project.setKopSources
		elif idxIdBase == self.INDEXID_SRCS_SYMTAB_BASE:
			getter = project.getSymTabSources
			setter = project.setSymTabSources
		else:
			getter = None
			setter = None
		return getter, setter

	def __handleMdiSubWinSourceChanged(self, mdiSubWin):
		# Handle sourceChanged signal of an edit area MDI window.
		self.__projectContentChanged()
		self.__setProjectNeedRefresh()

	def __handleDataChanged(self, topLeftIndex, bottomRightIndex, roles=()):
		# Handle the self.dataChanged signal.
		if not roles or\
		   Qt.EditRole in roles or\
		   Qt.DisplayRole in roles:
			self.__projectContentChanged()

	def __projectContentChanged(self):
		self.projectContentChanged.emit()

	def refreshProject(self):
		"""Copy the modified sources from the edit widgets.
		"""
		ret = True

		# Temporarily set the refresh flag to false to avoid recursions.
		self.__projectNeedRefresh = False

		# Refresh the sources in the project from
		# the edit widgets (if any).
		for source in self.__project.getAllSources():
			mdiSubWin = source.userData.get("gui-edit-window")
			if mdiSubWin:
				newSource = mdiSubWin.getSource()
				if newSource is not None:
					source.copyFrom(newSource,
							copyUserData=False,
							updateUserData=False)
				else:
					ret = False

		# Refresh the library selections.
		libSelMdiSubWin = self.__libSelMdiSubWin
		if libSelMdiSubWin:
			libSelections = libSelMdiSubWin.getLibSelections()
			if libSelections is not None:
				self.__project.setLibSelections(libSelections)
			else:
				ret = False

		# Set the refresh-flag to False, if we succeeded.
		self.__projectNeedRefresh = not ret
		return ret

	def __setProjectNeedRefresh(self):
		self.__projectNeedRefresh = True

	def getProject(self):
		"""Get the Project() instance that is being represented by this tree.
		"""
		if self.__projectNeedRefresh:
			self.refreshProject()
		return self.__project

	def __reset(self, project=None):
		if not project:
			project = Project(None) # Empty project
		self.__project = project
		self.__setProjectNeedRefresh()
		self.__libSelMdiSubWin = None
		self.__isAdHocProject = False
		self.__warnedFileBacked = False
		self.__guiRunState = GuiRunState()
		self.handleIdentsMsg(None)

	def reset(self, project=None):
		"""Completely reset the data model.
		"""
		self.beginResetModel()
		self.__reset(project)
		self.endResetModel()
		self.projectLoaded.emit()
		self.__projectContentChanged()

	def __loadProject(self, project):
		self.beginResetModel()
		try:
			self.__project = project

			# Close all possibly open edit windows.
			editMdiArea = self.editMdiArea
			editMdiArea.resetArea()

			editMdiArea.setGuiSettings(project.getGuiSettings())

			self.__warnedFileBacked = False
			self.__isAdHocProject = False
		except Exception as e:
			self.__reset()
		finally:
			self.endResetModel()

	def __loadPlainAwlSourceFile(self, filename, parentWidget):
		project = Project(None) # Create an ad-hoc project
		source = AwlSource.fromFile(name=filename,
					    filepath=filename,
					    compatReEncode=True)
		project.setAwlSources([ source, ])
		self.__loadProject(project)
		self.__isAdHocProject = True
		QMessageBox.information(parentWidget,
			"Opened plain AWL/STL file",
			"The plain AWL/STL source file \n'%s'\n has sucessfully "
			"been opened.\n\n"
			"If you click on 'save', you will be asked to create "
			"a project file for this source." % filename)

	def loadProjectFile(self, filename, parentWidget):
		if Project.fileIsProject(filename):
			self.__loadProject(Project.fromFile(filename))
		else:
			# This might be a plain AWL-file.
			# Try to load it.
			self.__loadPlainAwlSourceFile(filename, parentWidget)
		self.projectLoaded.emit()
		GuiValidatorSched.get().startAsyncValidation(self.getProject)

	def saveProjectFile(self, filename, parentWidget):
		if self.__isAdHocProject:
			srcs = self.__project.getAwlSources()
			assert(len(srcs) == 1)
			if filename == srcs[0].filepath:
				# This is an ad-hoc project, that was created from
				# a plain AWL file. Do not overwrite the AWL file.
				# Ask the user to create an .awlpro file.
				res = QMessageBox.question(parentWidget,
					"Create Awlsim project file?",
					"The current project was created ad-hoc from a "
					"plain AWL/STL file.\n"
					"Can not save without creating a project file.\n\n"
					"Do you want to create a project file?",
					QMessageBox.Yes, QMessageBox.No)
				if res != QMessageBox.Yes:
					return 0
				# The user has to choose a new project file name.
				# Signal this to our caller.
				return -1

		if not self.refreshProject():
			# Failed to generate some sources
			return 0
		project = self.__project

		# Check if there is any deprecated file-backing.
		if (any(src.isFileBacked() for src in project.getAwlSources()) or\
		    any(src.isFileBacked() for src in project.getSymTabSources())) and\
		    not self.__warnedFileBacked:
			QMessageBox.information(parentWidget,
				"Project contains external sources",
				"The project contains external sources.\n"
				"It is strongly recommended to integrate "
				"external sources into the project.\n"
				"Click on 'integrate source into project' "
				"in the source menu.")
			self.__warnedFileBacked = True

		# Re-generate UUIDs, if we are saving to a new file.
		if project.getProjectFile() != filename:
			printInfo("Save-file name changed. "
				  "Re-generating project file UUIDs.")
			self.__regenAllUUIDs()

		# Set the new file name and write to that file.
		project.setProjectFile(filename)
		project.toFile()
		self.__isAdHocProject = False

		return 1

	def __regenAllUUIDs(self):
		"""Re-generate all UUIDs in all sources.
		"""
		for source in self.__project.getFupSources():
			# Parse the FUP source and regenerate all UUIDs.
			fupWidget = FupWidget(None, None)
			factory = FupFactory(fupWidget=fupWidget)
			factory.parse(source.sourceBytes)
			fupWidget.regenAllUUIDs()
			source.sourceBytes = factory.compose()

			# Update the source in the MDI window, if any.
			mdiSubWin = source.userData.get("gui-edit-window")
			if mdiSubWin:
				mdiSubWin.setSource(source)

	def idToIndex(self, idxId, column = 0):
		for table in (self.id2row_toplevel,
			      self.id2row_srcs):
			if idxId in table:
				return self.createIndex(table[idxId],
							column, idxId)
		return QModelIndex()

	def indexToId(self, index):
		idxId = index.internalId()
		idxIdBase = idxId & self.INDEXID_BASE_MASK
		itemNr = idxId - idxIdBase
		return idxIdBase, idxId, itemNr

	def indexToSource(self, index):
		"""Get the source that corresponds to an index, if any.
		"""
		idxIdBase, idxId, itemNr = self.indexToId(index)

		sources = None
		if idxIdBase == self.INDEXID_SRCS_AWL_BASE:
			sources = self.getProject().getAwlSources()
		elif idxIdBase == self.INDEXID_SRCS_FUP_BASE:
			sources = self.getProject().getFupSources()
		elif idxIdBase == self.INDEXID_SRCS_KOP_BASE:
			sources = self.getProject().getKopSources()
		elif idxIdBase == self.INDEXID_SRCS_SYMTAB_BASE:
			sources = self.getProject().getSymTabSources()

		if sources is None or itemNr >= len(sources):
			return None
		return sources[itemNr]

	def identHashToIndex(self, identHash):
		"""Get the index that corresponds to an identHash.
		Returns an invalid index, if no such item was found.
		"""
		project = self.getProject()
		for getSources, parentIdxId in (
				(project.getAwlSources, self.INDEXID_SRCS_AWL),
				(project.getFupSources, self.INDEXID_SRCS_FUP),
				(project.getKopSources, self.INDEXID_SRCS_KOP),
				(project.getSymTabSources, self.INDEXID_SRCS_SYMTAB)):
			for i, source in enumerate(getSources()):
				if source.identHash == identHash:
					parentIndex = self.idToIndex(parentIdxId)
					if parentIndex.isValid():
						return self.index(i, 0, parentIndex)
		return QModelIndex()

	def flags(self, index):
		if not index.isValid():
			return Qt.NoItemFlags

		idxIdBase, idxId, itemNr = self.indexToId(index)

		flags = Qt.ItemIsEnabled
		if idxIdBase in {self.INDEXID_SRCS_AWL_BASE,
				 self.INDEXID_SRCS_FUP_BASE,
				 self.INDEXID_SRCS_KOP_BASE,
				 self.INDEXID_SRCS_SYMTAB_BASE,}:
			flags |= Qt.ItemIsEditable |\
				 Qt.ItemIsDragEnabled |\
				 Qt.ItemIsSelectable
		if idxId in {self.INDEXID_SRCS_AWL,
			     self.INDEXID_SRCS_FUP,
			     self.INDEXID_SRCS_KOP,
			     self.INDEXID_SRCS_SYMTAB,}:
			flags |= Qt.ItemIsDropEnabled
		return flags

	def supportedDragActions(self):
		return Qt.CopyAction | Qt.MoveAction

	def supportedDropActions(self):
		return Qt.CopyAction | Qt.MoveAction

	def columnCount(self, parentIndex=QModelIndex()):
		return 1

	def rowCount(self, parentIndex=QModelIndex()):
		if parentIndex.isValid():
			parentIdBase, parentId, parentItemNr, = self.indexToId(parentIndex)
			project = self.getProject()
			if parentId == self.INDEXID_SRCS:
				return len(self.row2id_srcs)
			elif parentId == self.INDEXID_SRCS_AWL:
				return len(project.getAwlSources())
			elif parentId == self.INDEXID_SRCS_FUP:
				return len(project.getFupSources())
			elif parentId == self.INDEXID_SRCS_KOP:
				return len(project.getKopSources())
			elif parentId == self.INDEXID_SRCS_SYMTAB:
				return len(project.getSymTabSources())
		else:
			return len(self.row2id_toplevel)
		return 0

	def index(self, row, column, parentIndex=QModelIndex()):
		if row < 0 or column < 0:
			return QModelIndex()
		if parentIndex.isValid():
			parentIdBase, parentId, parentItemNr = self.indexToId(parentIndex)
			if parentId == self.INDEXID_SRCS:
				row2idTable = self.row2id_srcs
			elif parentId == self.INDEXID_SRCS_AWL:
				return self.createIndex(row, column,
					self.INDEXID_SRCS_AWL_BASE + row)
			elif parentId == self.INDEXID_SRCS_FUP:
				return self.createIndex(row, column,
					self.INDEXID_SRCS_FUP_BASE + row)
			elif parentId == self.INDEXID_SRCS_KOP:
				return self.createIndex(row, column,
					self.INDEXID_SRCS_KOP_BASE + row)
			elif parentId == self.INDEXID_SRCS_SYMTAB:
				return self.createIndex(row, column,
					self.INDEXID_SRCS_SYMTAB_BASE + row)
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
		idxIdBase, idxId, itemNr = self.indexToId(index)
		if idxId in self.id2row_toplevel:
			return QModelIndex()
		elif idxId in self.id2row_srcs:
			return self.idToIndex(self.INDEXID_SRCS)
		elif idxIdBase == self.INDEXID_SRCS_AWL_BASE:
			return self.idToIndex(self.INDEXID_SRCS_AWL)
		elif idxIdBase == self.INDEXID_SRCS_FUP_BASE:
			return self.idToIndex(self.INDEXID_SRCS_FUP)
		elif idxIdBase == self.INDEXID_SRCS_KOP_BASE:
			return self.idToIndex(self.INDEXID_SRCS_KOP)
		elif idxIdBase == self.INDEXID_SRCS_SYMTAB_BASE:
			return self.idToIndex(self.INDEXID_SRCS_SYMTAB)
		return QModelIndex()

	def __data_columnName(self, role, index, idxId, idxIdBase, itemNr):
		source = self.indexToSource(index)
		if source:
			name = source.name
			if role != Qt.EditRole:
				if not source.enabled:
					name += " (DISABLED)"
			return name

		names = {
		  self.INDEXID_SRCS		: "Program",
		  self.INDEXID_SRCS_AWL		: "AWL / STL",
		  self.INDEXID_SRCS_FUP		: "FUP / FBD",
		  self.INDEXID_SRCS_KOP		: "KOP / LAD",
		  self.INDEXID_SRCS_SYMTAB	: "Symbols",
		  self.INDEXID_SRCS_LIBSEL	: "Library selections",
		  self.INDEXID_CPU		: "CPU",
		  self.INDEXID_CONN		: "Connection",
		  self.INDEXID_HW		: "Hardware",
		  self.INDEXID_GUICONF		: "Editor settings",
		}
		return names.get(idxId)

	def __data_icon(self, role, index, idxId, idxIdBase, itemNr):
		"""Get the QIcon for displaying in the tree.
		"""

		def getSourceContainerIcon(sourceList, okIconName):
			# If there is an error in the source, show error icon.
			# If the identHash of any source does not match what's on the CPU,
			# use a warning icon. But only do that, if the CPU is
			# in RUN state.
			if any(source.userData.get("gui-erroneous", False)
			       for source in sourceList):
				return getIcon("exit")
			elif (self.__guiRunState == GuiRunState.STATE_RUN and
			      any(not source.userData.get("gui-cpu-idents-match", True)
				  for source in sourceList)):
				return getIcon("warning")
			return getIcon(okIconName)

		def getSourceIcon(sourceList, okIconName):
			if itemNr >= len(sourceList):
				return None
			source = sourceList[itemNr]
			if not source.enabled:
				return getIcon("disable")
			return getSourceContainerIcon((source,), okIconName)

		def getProgramContainerIcon(okIconName):
			project = self.getProject()
			return getSourceContainerIcon(
				itertools.chain(
					project.getAwlSources(),
					project.getFupSources(),
					project.getKopSources(),
					project.getSymTabSources()),
				okIconName)

		if idxId == self.INDEXID_SRCS:
			return getProgramContainerIcon("textsource")
		elif idxId == self.INDEXID_SRCS_AWL:
			return getSourceContainerIcon(self.getProject().getAwlSources(),
						      "textsource")
		elif idxIdBase == self.INDEXID_SRCS_AWL_BASE:
			return getSourceIcon(self.getProject().getAwlSources(),
					     "textsource")
		elif idxId == self.INDEXID_SRCS_FUP:
			return getSourceContainerIcon(self.getProject().getFupSources(),
						      "fup")
		elif idxIdBase == self.INDEXID_SRCS_FUP_BASE:
			return getSourceIcon(self.getProject().getFupSources(),
					     "fup")
		elif idxId == self.INDEXID_SRCS_KOP:
			return getSourceContainerIcon(self.getProject().getKopSources(),
						      "kop")
		elif idxIdBase == self.INDEXID_SRCS_KOP_BASE:
			return getSourceIcon(self.getProject().getKopSources(),
					     "kop")
		elif idxId == self.INDEXID_SRCS_SYMTAB:
			return getSourceContainerIcon(self.getProject().getSymTabSources(),
						      "tag")
		elif idxIdBase == self.INDEXID_SRCS_SYMTAB_BASE:
			return getSourceIcon(self.getProject().getSymTabSources(),
					     "tag")
		elif idxId == self.INDEXID_SRCS_LIBSEL:
			return getIcon("stdlib")
		elif idxId == self.INDEXID_CPU:
			return getIcon("cpu")
		elif idxId == self.INDEXID_CONN:
			return getIcon("network")
		elif idxId == self.INDEXID_HW:
			return getIcon("hwmod")
		elif idxId == self.INDEXID_GUICONF:
			return getIcon("prefs")
		return None

	def __data_toolTip(self, role, index, idxId, idxIdBase, itemNr):
		"""Get the tool-tip for displaying in the tree.
		"""

		def getSourceContainerTip(sourceList, okToolTip):
			# If there is an error in the source, show error tool tip.
			# If the identHash of any source does not match what's on the CPU,
			# use a warning tool tip. But only do that, if the CPU is
			# in RUN state.
			if any(source.userData.get("gui-erroneous", False)
			       for source in sourceList):
				return "ERROR: There is an error in the source file.\n"\
				       "Please open it to fix the problem."
			if self.__guiRunState == GuiRunState.STATE_RUN and\
			   any(not source.userData.get("gui-cpu-idents-match", True)
			       for source in sourceList):
				return "WARNING: The source contained in the project\n"\
				       "does not match the source on the CPU.\n"\
				       "That means the CPU is currenly running an outdated program.\n"\
				       "Please re-download the sources to the CPU\n"\
				       "by clicking the download button in the tool bar."
			return okToolTip

		def getSourceTip(sourceList, okToolTip):
			if itemNr >= len(sourceList):
				return False
			source = sourceList[itemNr]
			okToolTip += "\nSource hash: %s..." % source.identHashStr[:10]
			return getSourceContainerTip((source,), okToolTip)

		def getProgramContainerTip(okToolTip):
			project = self.getProject()
			return getSourceContainerTip(
				itertools.chain(
					project.getAwlSources(),
					project.getFupSources(),
					project.getKopSources(),
					project.getSymTabSources()),
				okToolTip)

		if idxId == self.INDEXID_SRCS:
			return getProgramContainerTip(None)
		elif idxId == self.INDEXID_SRCS_AWL:
			return getSourceContainerTip(self.getProject().getAwlSources(),
				"Right click here to add new AWL source.")
		elif idxIdBase == self.INDEXID_SRCS_AWL_BASE:
			return getSourceTip(self.getProject().getAwlSources(),
				"Double click here to edit this AWL source.")
		elif idxId == self.INDEXID_SRCS_FUP:
			return getSourceContainerTip(self.getProject().getFupSources(),
				"Right click here to add new FUP source.")
		elif idxIdBase == self.INDEXID_SRCS_FUP_BASE:
			return getSourceTip(self.getProject().getFupSources(),
				"Double click here to edit this FUP diagram.")
		elif idxId == self.INDEXID_SRCS_KOP:
			return getSourceContainerTip(self.getProject().getKopSources(),
				"Right click here to add new KOP source.")
		elif idxIdBase == self.INDEXID_SRCS_KOP_BASE:
			return getSourceTip(self.getProject().getKopSources(),
				"Double click here to edit this KOP diagram.")
		elif idxId == self.INDEXID_SRCS_SYMTAB:
			return getSourceContainerTip(self.getProject().getSymTabSources(),
				"Right click here to add new symbol table.")
		elif idxIdBase == self.INDEXID_SRCS_SYMTAB_BASE:
			return getSourceTip(self.getProject().getSymTabSources(),
				"Double click here to edit this symbol table.")
		elif idxId == self.INDEXID_SRCS_LIBSEL:
			return "Double click here to edit system library selections."
		elif idxId == self.INDEXID_CPU:
			return "Double click here to edit CPU settings."
		elif idxId == self.INDEXID_CONN:
			return "Double click here to edit core server connection settings."
		elif idxId == self.INDEXID_HW:
			return "Double click here to edit hardware module settings."
		elif idxId == self.INDEXID_GUICONF:
			return "Double click here to edit GUI settings."
		return None

	def data(self, index, role=Qt.DisplayRole):
		column = index.column()
		idxIdBase, idxId, itemNr = self.indexToId(index)

		if role in (Qt.DisplayRole, Qt.EditRole):
			if column == self.COLUMN_NAME:
				return self.__data_columnName(role, index, idxId, idxIdBase, itemNr)
		elif role == Qt.DecorationRole:
			if column == self.COLUMN_NAME:
				return self.__data_icon(role, index, idxId, idxIdBase, itemNr)
		elif role == Qt.ToolTipRole:
			if column == self.COLUMN_NAME:
				return self.__data_toolTip(role, index, idxId, idxIdBase, itemNr)
		return None

	def setData(self, index, value, role=Qt.EditRole):
		if not index or not index.isValid():
			return False

		if role == Qt.EditRole:
			if not self.entryRename(index, newName=value):
				return False
		else:
			return False
		return True

	def setHeaderData(self, section, orientation, value, role=Qt.EditRole):
		return False

	def headerData(self, section, orientation, role=Qt.DisplayRole):
		if role == Qt.DisplayRole:
			project = self.getProject()
			filename = project.getProjectFile()
			if filename:
				title = os.path.basename(filename)
			else:
				title = "Project"
			if self.mainWidget.isDirty():
				title += "*"
			return title
		return None

	def __handleProjectDirtyChanged(self, dirtyLevel):
		self.headerDataChanged.emit(Qt.Horizontal, 0, 0)

	def mimeData(self, indexes):
		if not indexes:
			return None
		mimeData = QMimeData()
		for index in indexes:
			if not index.isValid():
				continue
			idxIdBase, idxId, itemNr = self.indexToId(index)

			getter, _ = self.sourceGetter(idxIdBase)
			if not getter:
				return False
			sources = getter()
			source = sources[itemNr]

			# Squash the file backing (if any)
			source = source.dup()
			source.forceNonFileBacked(source.filepath)

			# Generate XML data
			try:
				mimeType = {
					self.INDEXID_SRCS_AWL_BASE : "application/x-awlsim-xml-awl",
					self.INDEXID_SRCS_FUP_BASE : "application/x-awlsim-xml-fup",
					self.INDEXID_SRCS_KOP_BASE : "application/x-awlsim-xml-kop",
					self.INDEXID_SRCS_SYMTAB_BASE : "application/x-awlsim-xml-symtab",
				}[idxIdBase]
				factory = source.factory(project=self.getProject(),
							 source=source)

				# Store the data as Awlsim object.
				dataBytes = factory.compose()
				mimeData.setData(mimeType, dataBytes)

				# Store the data as plain XML.
				mimeData.setData("application/xml", dataBytes)

				# Store the source bytes as plain text.
				mimeData.setText(source.sourceText)

			except (XmlFactory.Error, KeyError) as e:
				return None
		return mimeData

	def __getExpectedMimeFormat(self, parentIndex):
		parentIdxIdBase, parentIdxId, parentItemNr = self.indexToId(parentIndex)

		if parentIdxId == self.INDEXID_SRCS_AWL or\
		   parentIdxIdBase == self.INDEXID_SRCS_AWL_BASE:
			return "application/x-awlsim-xml-awl"
		if parentIdxId == self.INDEXID_SRCS_FUP or\
		   parentIdxIdBase == self.INDEXID_SRCS_FUP_BASE:
			return "application/x-awlsim-xml-fup"
		if parentIdxId == self.INDEXID_SRCS_KOP or\
		   parentIdxIdBase == self.INDEXID_SRCS_KOP_BASE:
			return "application/x-awlsim-xml-kop"
		if parentIdxId == self.INDEXID_SRCS_SYMTAB or\
		   parentIdxIdBase == self.INDEXID_SRCS_SYMTAB_BASE:
			return "application/x-awlsim-xml-symtab"
		return None

	def canDropMimeData(self, mimeData, action, row, column, parentIndex):
		if not parentIndex.isValid():
			return False
		if action not in {Qt.MoveAction, Qt.CopyAction}:
			return False
		expectedMimeFormat = self.__getExpectedMimeFormat(parentIndex)
		if not expectedMimeFormat:
			return False
		if expectedMimeFormat not in mimeData.formats():
			return False
		return True

	def __dropMimeData(self, mimeData, action, row, column, parentIndex):
		if not self.canDropMimeData(mimeData, action, row, column, parentIndex):
			return None
		parentIdxIdBase, parentIdxId, parentItemNr = self.indexToId(parentIndex)

		# Parse the MIME data.
		mimeFormat = self.__getExpectedMimeFormat(parentIndex)
		data = bytes(mimeData.data(mimeFormat))
		try:
			if mimeFormat == "application/x-awlsim-xml-awl":
				source = AwlSource()
			elif mimeFormat == "application/x-awlsim-xml-fup":
				source = FupSource()
			elif mimeFormat == "application/x-awlsim-xml-kop":
				source = KopSource()
				return None # Not yet
			elif mimeFormat == "application/x-awlsim-xml-symtab":
				source = SymTabSource()
			else:
				return None
			factory = source.factory(project=self.getProject(),
						 source=source)
			if not factory.parse(data):
				return None
		except XmlFactory.Error as e:
			return None

		if action == Qt.CopyAction:
			source.name += " (Copy)"

		# Insert the new element
		return self.entryAdd(idxIdBase=self.id2childBase[parentIdxId],
				     source=source, pos=row)

	def dropMimeData(self, mimeData, action, row, column, parentIndex):
		if self.__dropMimeData(mimeData, action, row, column, parentIndex):
			return True
		return False

	def mimeTypes(self):
		return [
			"application/x-awlsim-xml-awl",
			"application/x-awlsim-xml-fup",
			"application/x-awlsim-xml-kop",
			"application/x-awlsim-xml-symtab",
		]

	def removeRows(self, row, count, parentIndex):
		for i in range(count):
			index = self.index(row, 0, parentIndex)
			if not self.entryDelete(index, force=True):
				return False
		return True

class SourceContextMenu(QMenu):
	# Signal: Opem the edit for the selected source
	edit = Signal()
	# Signal: Add new source
	add = Signal()
	# Signal: Delete current source
	delete = Signal()
	# Signal: Rename current source
	rename = Signal()
	# Signal: Copy source
	copy = Signal()
	# Signal: Cut source
	cut = Signal()
	# Signal: Paste source
	paste = Signal()
	# Signal: Integrate source
	integrate = Signal()
	# Signal: Import source
	import_ = Signal()
	# Signal: Export source
	export = Signal()
	# Signal: Enable/disable source
	enable = Signal(bool)

	def __init__(self, itemCategoryName, itemName,
		     withEditButton=False,
		     withAddButton=False,
		     withDeleteButton=False,
		     withRenameButton=False,
		     withIntegrateButton=False,
		     withCopyButton=False,
		     withCutButton=False,
		     withPasteButton=False,
		     withImportButton=False,
		     withExportButton=False,
		     withEnableButton=False,
		     withDisableButton=False,
		     parent=None):
		QMenu.__init__(self, parent)

		self.itemCategoryName = itemCategoryName
		self.itemName = itemName

		if withEditButton:
			self.addAction(getIcon("doc_edit"),
				       "&Edit...", self.__edit)
		self.addSeparator()
		if withAddButton:
			self.addAction(getIcon("doc_new"),
				       "&Add new %s" % itemCategoryName, self.__add)
		if withDeleteButton:
			self.addAction(getIcon("doc_close"),
				       "&Delete...", self.__delete)
		if withRenameButton:
			self.addAction(getIcon("doc_edit"),
				       "&Rename...", self.__rename)
		self.addSeparator()
		if withCopyButton:
			self.addAction(getIcon("copy"),
				       "&Copy", self.__copy)
		if withCutButton:
			self.addAction(getIcon("cut"),
				       "&Cut", self.__cut)
		if withPasteButton:
			self.addAction(getIcon("paste"),
				       "&Paste", self.__paste)
		self.addSeparator()
		if withImportButton:
			self.addAction(getIcon("doc_import"),
				       "&Import...", self.__import)
		if withExportButton:
			self.addAction(getIcon("doc_export"),
				       "&Export...", self.__export)
		if withIntegrateButton:
			self.addAction("&Integrate '%s' into project..." % itemName,
				       self.__integrate)
		self.addSeparator()
		if withEnableButton:
			self.addAction(getIcon("enable"),
				       "E&nable", self.__enable)
		if withDisableButton:
			self.addAction(getIcon("disable"),
				       "D&isable", self.__disable)

	def __edit(self):
		self.edit.emit()

	def __add(self):
		self.add.emit()

	def __delete(self):
		self.delete.emit()

	def __rename(self):
		self.rename.emit()

	def __copy(self):
		self.copy.emit()

	def __cut(self):
		self.cut.emit()

	def __paste(self):
		self.paste.emit()

	def __import(self):
		self.import_.emit()

	def __export(self):
		self.export.emit()

	def __integrate(self):
		res = QMessageBox.question(self,
			"Integrate current %s" % self.itemName,
			"The current %s is stored in an external file.\n"
			"Do you want to integrate this file info "
			"the awlsim project file (.awlpro)?" %\
			self.itemName,
			QMessageBox.Yes, QMessageBox.No)
		if res == QMessageBox.Yes:
			self.integrate.emit()

	def __enable(self):
		self.enable.emit(True)

	def __disable(self):
		self.enable.emit(False)

class ProjectTreeView(QTreeView):
	def __init__(self, model, parent=None):
		QTreeView.__init__(self, parent)
		self.setModel(model)

		self.setSelectionMode(QAbstractItemView.SingleSelection)

		# Disable double-click-edit
		self.setEditTriggers(self.editTriggers() & ~QTreeView.DoubleClicked)

		self.setDragDropMode(QAbstractItemView.DragDrop)
		self.setDefaultDropAction(Qt.MoveAction)
		self.setAcceptDrops(True)
		self.setDragEnabled(True)
		self.setDropIndicatorShown(True)

		self.__currentIndex = None

		self.pressed.connect(self.__mouseBtnPressed)
		self.doubleClicked.connect(self.__mouseBtnDoubleClicked)

	def setModel(self, model):
		oldModel = self.model()
		if oldModel:
			oldModel.projectLoaded.disconnect(self.__handleProjectLoaded)
		QTreeView.setModel(self, model)
		if model:
			model.projectLoaded.connect(self.__handleProjectLoaded)

	def __handleProjectLoaded(self):
		model = self.model()
		if model:
			self.expand(model.idToIndex(model.INDEXID_SRCS))
			self.expand(model.idToIndex(model.INDEXID_SRCS_AWL))
			self.expand(model.idToIndex(model.INDEXID_SRCS_FUP))

	baseToCatName = {
		ProjectTreeModel.INDEXID_SRCS_AWL_BASE		: "AWL source",
		ProjectTreeModel.INDEXID_SRCS_FUP_BASE		: "FUP source",
		ProjectTreeModel.INDEXID_SRCS_KOP_BASE		: "KOP source",
		ProjectTreeModel.INDEXID_SRCS_SYMTAB_BASE	: "Symbol Table",
	}
	idToCatName = {
		ProjectTreeModel.INDEXID_SRCS_AWL	: baseToCatName[ProjectTreeModel.INDEXID_SRCS_AWL_BASE],
		ProjectTreeModel.INDEXID_SRCS_FUP	: baseToCatName[ProjectTreeModel.INDEXID_SRCS_FUP_BASE],
		ProjectTreeModel.INDEXID_SRCS_KOP	: baseToCatName[ProjectTreeModel.INDEXID_SRCS_KOP_BASE],
		ProjectTreeModel.INDEXID_SRCS_SYMTAB	: baseToCatName[ProjectTreeModel.INDEXID_SRCS_SYMTAB_BASE],
	}

	def __showSourceContextMenu(self, index,
				    catName=None,
				    itemName=None,
				    onContainer=False,
				    onSource=False,
				    onStaticItem=False):
		model = self.model()
		idxIdBase, idxId, itemNr = model.indexToId(index)

		# Get the source, if any.
		source = None
		if onSource:
			getter, setter = model.sourceGetter(idxIdBase)
			if getter:
				source = getter()[itemNr]

		# Extract source information
		itemIsEnabled = bool(source and source.enabled)
		itemIsFileBacked = bool(source and source.isFileBacked())
		if not itemName:
			itemName = source.name if source else None

		# Source-edit handler
		def handleEdit():
			model.entryActivate(index, parentWidget=self)

		# Source-add handler
		def handleAdd():
			base = idxIdBase
			if base == 0:
				base = model.id2childBase[idxId]
			newIndex = model.entryAdd(base, parentWidget=self)
			if newIndex:
				self.expand(index)
				model.entryRename(newIndex, parentWidget=self)
				model.entryActivate(newIndex, parentWidget=self)

		# Source-remove handler
		def handleDelete():
			model.entryDelete(index, parentWidget=self)

		# Source-rename handler
		def handleRename():
			self.edit(index)

		# Source-copy handler
		def handleCopy():
			model.entryClipboardCopy(index, parentWidget=self)

		# Source-cut handler
		def handleCut():
			model.entryClipboardCut(index, parentWidget=self)

		# Source-paste handler
		def handlePaste():
			pastedIndex = model.entryClipboardPaste(index, parentWidget=self)
			if pastedIndex:
				self.expand(index)
				self.setCurrentIndex(pastedIndex)
			else:
				QMessageBox.critical(self,
					"Clipboard paste failed",
					"The clipboard does not seem to contain data "
					"that can be pasted here.")

		# Source-integrate handler
		def handleIntegrate():
			model.entryIntegrate(index, parentWidget=self)

		# Source-import handler
		def handleImport():
			base = idxIdBase
			if base == 0:
				base = model.id2childBase[idxId]
			model.entryImport(base, parentWidget=self)

		# Source-export handler
		def handleExport():
			model.entryExport(index, parentWidget=self)

		# Source-enable/disable handler
		def handleEnable(enable):
			model.entryEnable(index, enable, parentWidget=self)

		# Construct the context menu and show it modally.
		menu = SourceContextMenu(
				itemCategoryName=catName,
				itemName=itemName,
				withEditButton=(onSource or onStaticItem),
				withAddButton=(onContainer or onSource),
				withDeleteButton=onSource,
				withRenameButton=onSource,
				withCopyButton=onSource,
				withCutButton=onSource,
				withPasteButton=(onSource or onContainer),
				withIntegrateButton=(onSource and itemIsFileBacked),
				withImportButton=(onContainer or onSource),
				withExportButton=onSource,
				withEnableButton=(onSource and not itemIsEnabled),
				withDisableButton=(onSource and itemIsEnabled),
				parent=self)
		menu.edit.connect(handleEdit)
		menu.add.connect(handleAdd)
		menu.delete.connect(handleDelete)
		menu.rename.connect(handleRename)
		menu.copy.connect(handleCopy)
		menu.cut.connect(handleCut)
		menu.paste.connect(handlePaste)
		menu.integrate.connect(handleIntegrate)
		menu.import_.connect(handleImport)
		menu.export.connect(handleExport)
		menu.enable.connect(handleEnable)
		menu.exec_(QCursor.pos() + QPoint(3, 3))

	def __mouseBtnPressed(self, index):
		model, buttons = self.model(), QApplication.mouseButtons()
		if not model:
			return
		try:
			self.__currentIndex = index

			if buttons & Qt.RightButton:
				idxIdBase, idxId, itemNr = model.indexToId(index)

				# Open the context menu.
				onContainer, onSource = False, True
				catName = self.baseToCatName.get(idxIdBase)
				if not catName:
					catName = self.idToCatName.get(idxId)
					if catName:
						onContainer, onSource = True, False
				if catName:
					self.__showSourceContextMenu(index=index,
								     catName=catName,
								     onContainer=onContainer,
								     onSource=onSource)
				elif idxId in {ProjectTreeModel.INDEXID_CPU,
					       ProjectTreeModel.INDEXID_CONN,
					       ProjectTreeModel.INDEXID_HW,
					       ProjectTreeModel.INDEXID_GUICONF,
					       ProjectTreeModel.INDEXID_SRCS_LIBSEL}:
					itemName = model.data(index)
					self.__showSourceContextMenu(index=index,
								     itemName=itemName,
								     onStaticItem=True)
		finally:
			self.__currentIndex = None

	def __mouseBtnDoubleClicked(self, index):
		model = self.model()
		if model:
			self.__currentIndex = index
			model.entryActivate(index, self)

	def keyPressEvent(self, ev):
		QTreeView.keyPressEvent(self, ev)

		model = self.model()
		if model:
			index = self.currentIndex()
			if ev.matches(QKeySequence.Delete):
				model.entryDelete(index, parentWidget=self)
			elif ev.matches(QKeySequence.Copy):
				model.entryClipboardCopy(index, parentWidget=self)
			elif ev.matches(QKeySequence.Cut):
				model.entryClipboardCut(index, parentWidget=self)
			elif ev.matches(QKeySequence.Paste):
				pastedIndex = model.entryClipboardPaste(index, parentWidget=self)
				if pastedIndex:
					self.expand(index)
					self.setCurrentIndex(pastedIndex)

	def __removeSource(self):
		model = self.model()
		if model:
			index = self.__currentIndex
			if index is None:
				index = self.currentIndex()
			model.entryDelete(index, parentWidget=self)

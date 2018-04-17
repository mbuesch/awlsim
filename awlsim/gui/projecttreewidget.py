# -*- coding: utf-8 -*-
#
# AWL simulator - Project tree widget
#
# Copyright 2017-2018 Michael Buesch <m@bues.ch>
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

		self.__libSelMdiSubWin = None

		self.__reset(project)

		self.dataChanged.connect(self.__projectContentChanged)
		self.modelReset.connect(self.__projectContentChanged)
		self.rowsInserted.connect(self.__projectContentChanged)
		self.rowsMoved.connect(self.__projectContentChanged)
		self.rowsRemoved.connect(self.__projectContentChanged)

	@property
	def editMdiArea(self):
		"""Get EditMdiArea instance.
		"""
		return self.mainWidget.editMdiArea

	def entryActivate(self, index, parentWidget=None):
		if not index or not index.isValid():
			return
		idxIdBase, idxId, itemNr = self.indexToId(index)

		editMdiArea = self.editMdiArea

		if idxId == self.INDEXID_CPU:
			self.mainWidget.cpuConfig()
			return True
		elif idxId == self.INDEXID_CONN:
			self.mainWidget.linkConfig()
			return True
		elif idxId == self.INDEXID_HW:
			self.mainWidget.hwmodConfig()
			return True
		elif idxId == self.INDEXID_SRCS_LIBSEL:
			libSelMdiSubWin = self.__libSelMdiSubWin
			if libSelMdiSubWin:
				editMdiArea.setActiveSubWindow(libSelMdiSubWin)
			else:
				libSelections = self.__project.getLibSelections()
				def removeLibSelMdiSubWin(w):
					self.__libSelMdiSubWin = None
				libSelMdiSubWin = editMdiArea.newWin_Libsel(libSelections)
				libSelMdiSubWin.closed.connect(removeLibSelMdiSubWin)
				self.__libSelMdiSubWin = libSelMdiSubWin
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

				# Connect signals.
				mdiSubWin.sourceChanged.connect(self.projectContentChanged)

		if idxIdBase == self.INDEXID_SRCS_AWL_BASE:
			handleSourceWindowActivation(
				sources=self.__project.getAwlSources(),
				makeNewWin=lambda source: editMdiArea.newWin_AWL(source))
			return True
		elif idxIdBase == self.INDEXID_SRCS_FUP_BASE:
			handleSourceWindowActivation(
				sources=self.__project.getFupSources(),
				makeNewWin=lambda source: editMdiArea.newWin_FUP(source))
			return True
		elif idxIdBase == self.INDEXID_SRCS_KOP_BASE:
			handleSourceWindowActivation(
				sources=self.__project.getKopSources(),
				makeNewWin=lambda source: editMdiArea.newWin_KOP(source))
			return True
		elif idxIdBase == self.INDEXID_SRCS_SYMTAB_BASE:
			handleSourceWindowActivation(
				sources=self.__project.getSymTabSources(),
				makeNewWin=lambda source: editMdiArea.newWin_SymTab(source))
			return True
		return False

	def entryDelete(self, index, parentWidget=None):
		if not index or not index.isValid():
			return False
		idxIdBase, idxId, itemNr = self.indexToId(index)

		getter, setter = self.sourceGetter(idxIdBase)
		if not getter or not setter:
			return False

		sourceList = getter()
		source = sourceList[itemNr]
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
					"Rename %s source" % source.SRCTYPE,
					"Rename %s source" % source.SRCTYPE,
					QLineEdit.Normal,
					source.name)
				if not ok:
					newName = None
			if newName is not None:
				source.name = newName
				setter(sources)

				self.dataChanged.emit(index, index, [Qt.EditRole])
				return True
		return False

	def entryIntegrate(self, index, parentWidget=None):
		pass#TODO
		return True

	def entryEnable(self, index, enable=True, parentWidget=None):
		idxIdBase, idxId, itemNr = self.indexToId(index)
		getter, setter = self.sourceGetter(idxIdBase)
		if getter:
			source = getter()[itemNr]
			source.enabled = enable
			self.projectContentChanged.emit()
			return True
		return False

	def entryImport(self, idxIdBase, parentWidget=None):
		pass#TODO
		return True

	def entryExport(self, index, filePath=None, parentWidget=None):
		pass#TODO
		return True

	def sourceGetter(self, idxIdBase):
		if idxIdBase == self.INDEXID_SRCS_AWL_BASE:
			getter = self.__project.getAwlSources
			setter = self.__project.setAwlSources
		elif idxIdBase == self.INDEXID_SRCS_FUP_BASE:
			getter = self.__project.getFupSources
			setter = self.__project.setFupSources
		elif idxIdBase == self.INDEXID_SRCS_KOP_BASE:
			getter = self.__project.getKopSources
			setter = self.__project.setKopSources
		elif idxIdBase == self.INDEXID_SRCS_SYMTAB_BASE:
			getter = self.__project.getSymTabSources
			setter = self.__project.setSymTabSources
		else:
			getter = None
			setter = None
		return getter, setter

	def __projectContentChanged(self):
		self.projectContentChanged.emit()

	def refreshProject(self):
		"""Copy the modified sources from the edit widgets.
		"""
		ret = True
		# Refresh the sources in the project from
		# the edit widgets (if any).
		for source in self.__project.getAllSources():
			mdiSubWin = source.userData.get("gui-edit-window")
			if not mdiSubWin:
				continue
			newSource = mdiSubWin.getSource()
			if newSource:
				source.copyFrom(newSource,
						copyName=False,
						copyEnabled=False,
						copyFilepath=False,
						copySourceBytes=True,
						copyUserData=False)
			else:
				ret = False
		# Refresh the library selections.
		libSelMdiSubWin = self.__libSelMdiSubWin
		if libSelMdiSubWin:
			libSelections = libSelMdiSubWin.getLibSelections()
			if libSelections:
				self.__project.setLibSelections(libSelections)
			else:
				ret = False
		return ret

	def getProject(self, refresh=True):
		if refresh:
			self.refreshProject()
		return self.__project

	def __reset(self, project=None):
		if not project:
			project = Project(None) # Empty project
		self.__project = project
		self.__isAdHocProject = False
		self.__warnedFileBacked = False

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

		project.setProjectFile(filename)
		project.toFile()

		if self.__isAdHocProject:
			pass#TODO
			# We got converted to a real project. Update the tabs.
			#self.awlTabs.setSources(self.__project.getAwlSources())
			#self.symTabs.setSources(self.__project.getSymTabSources())
			self.__isAdHocProject = False
		return 1

	def idToIndex(self, idxId, column = 0):
		for table in (self.id2row_toplevel,
			      self.id2row_srcs):
			if idxId in table:
				return self.createIndex(table[idxId],
							column, idxId)
		assert(0)

	def indexToId(self, index):
		idxId = index.internalId()
		idxIdBase = idxId & self.INDEXID_BASE_MASK
		itemNr = idxId - idxIdBase
		return idxIdBase, idxId, itemNr

	def flags(self, index):
		if not index.isValid():
			return Qt.NoItemFlags
		idxIdBase, idxId, itemNr = self.indexToId(index)
		flags = Qt.ItemIsEnabled
		if idxIdBase in {self.INDEXID_SRCS_AWL_BASE,
				 self.INDEXID_SRCS_FUP_BASE,
				 self.INDEXID_SRCS_KOP_BASE,
				 self.INDEXID_SRCS_SYMTAB_BASE,}:
			flags |= Qt.ItemIsEditable
		return flags

	def columnCount(self, parentIndex=QModelIndex()):
		return 1

	def rowCount(self, parentIndex=QModelIndex()):
		if parentIndex.isValid():
			parentIdBase, parentId, parentItemNr, = self.indexToId(parentIndex)
			if parentId == self.INDEXID_SRCS:
				return len(self.row2id_srcs)
			elif parentId == self.INDEXID_SRCS_AWL:
				return len(self.__project.getAwlSources())
			elif parentId == self.INDEXID_SRCS_FUP:
				return len(self.__project.getFupSources())
			elif parentId == self.INDEXID_SRCS_KOP:
				return len(self.__project.getKopSources())
			elif parentId == self.INDEXID_SRCS_SYMTAB:
				return len(self.__project.getSymTabSources())
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

	def __data_columnName(self, index, idxId, idxIdBase, itemNr):
		if idxIdBase == self.INDEXID_SRCS_AWL_BASE:
			awlSources = self.__project.getAwlSources()
			if itemNr >= len(awlSources):
				return None
			return awlSources[itemNr].name
		elif idxIdBase == self.INDEXID_SRCS_FUP_BASE:
			fupSources = self.__project.getFupSources()
			if itemNr >= len(fupSources):
				return None
			return fupSources[itemNr].name
		elif idxIdBase == self.INDEXID_SRCS_KOP_BASE:
			kopSources = self.__project.getKopSources()
			if itemNr >= len(kopSources):
				return None
			return kopSources[itemNr].name
		elif idxIdBase == self.INDEXID_SRCS_SYMTAB_BASE:
			symTabSources = self.__project.getSymTabSources()
			if itemNr >= len(symTabSources):
				return None
			return symTabSources[itemNr].name

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
		}
		return names.get(idxId)

	def data(self, index, role=Qt.DisplayRole):
		column = index.column()
		idxIdBase, idxId, itemNr = self.indexToId(index)

		if role in (Qt.DisplayRole, Qt.EditRole):
			if column == self.COLUMN_NAME:
				return self.__data_columnName(index, idxId, idxIdBase, itemNr)

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
				elif idxId == self.INDEXID_SRCS_KOP or\
				     idxIdBase == self.INDEXID_SRCS_KOP_BASE:
					return getIcon("kop")
				elif idxId == self.INDEXID_SRCS_SYMTAB or\
				     idxIdBase == self.INDEXID_SRCS_SYMTAB_BASE:
					return getIcon("tag")
				elif idxId == self.INDEXID_SRCS_LIBSEL:
					return getIcon("stdlib")
				elif idxId == self.INDEXID_CPU:
					return getIcon("cpu")
				elif idxId == self.INDEXID_CONN:
					return getIcon("network")
				elif idxId == self.INDEXID_HW:
					return getIcon("hwmod")
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

	def headerData(self, section, orientation, role=Qt.DisplayRole):
		if role == Qt.DisplayRole:
			return "Project"
		return None

class SourceContextMenu(QMenu):
	# Signal: Opem the edit for the selected source
	edit = Signal()
	# Signal: Add new source
	add = Signal()
	# Signal: Delete current source
	delete = Signal()
	# Signal: Rename current source
	rename = Signal()
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
				       "&Edit '%s'..." % itemName, self.__edit)
		self.addSeparator()
		if withAddButton:
			self.addAction(getIcon("doc_new"),
				       "&Add %s" % itemCategoryName, self.__add)
		if withDeleteButton:
			self.addAction(getIcon("doc_close"),
				       "&Delete '%s'..." % itemName, self.__delete)
		if withRenameButton:
			self.addAction(getIcon("doc_edit"),
				       "&Rename '%s'..." % itemName, self.__rename)
		self.addSeparator()
		if withImportButton:
			self.addAction(getIcon("doc_import"),
				       "&Import %s..." % itemCategoryName, self.__import)
		if withExportButton:
			self.addAction(getIcon("doc_export"),
				       "&Export '%s'..." % itemName, self.__export)
		if withIntegrateButton:
			self.addAction("&Integrate '%s' into project..." % itemName,
				       self.__integrate)
		self.addSeparator()
		if withEnableButton:
			self.addAction("E&nable '%s'" % itemName,
				       self.__enable)
		if withDisableButton:
			self.addAction("D&isable '%s'" % itemName,
				       self.__disable)

	def __edit(self):
		self.edit.emit()

	def __add(self):
		self.add.emit()

	def __delete(self):
		self.delete.emit()

	def __rename(self):
		self.rename.emit()

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

		# Disable double-click-edit
		self.setEditTriggers(self.editTriggers() & ~QTreeView.DoubleClicked)

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
			model.entryRename(index, parentWidget=self)

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
		menu.integrate.connect(handleIntegrate)
		menu.import_.connect(handleImport)
		menu.export.connect(handleExport)
		menu.enable.connect(handleEnable)
		menu.exec_(QCursor.pos())

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
			if ev.key() == Qt.Key_Delete:
				model.entryDelete(index, self)

	def __removeSource(self):
		model = self.model()
		if model:
			index = self.__currentIndex
			if index is None:
				index = self.currentIndex()
			model.entryDelete(index, self)

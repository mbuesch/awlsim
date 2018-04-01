# -*- coding: utf-8 -*-
#
# AWL simulator - GUI project widget
#
# Copyright 2014-2016 Michael Buesch <m@bues.ch>
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

from awlsim.common.codevalidator import *

from awlsim.gui.util import *
from awlsim.gui.sourcetabs import *
from awlsim.gui.library import *
from awlsim.gui.libtablewidget import *
from awlsim.gui.icons import *


class ProjectWidget(QTabWidget):
	# Signal: Some source changed
	codeChanged = Signal()
	# Signal: Some FUP diagram changed
	fupChanged = Signal()
	# Signal: Some KOP diagram changed
	kopChanged = Signal()
	# Signal: Some symbol table changed
	symTabChanged = Signal()
	# Signal: The visible AWL line range changed
	#         Parameters are: source, visibleFromLine, visibleToLine
	visibleLinesChanged = Signal(AwlSource, int, int)
	# Signal: The library selection changed
	libTableChanged = Signal()
	# Signal: Source text focus changed
	textFocusChanged = Signal(bool)
	# Signal: The selected project resource changed
	#         Parameter is one of RES_...
	selResourceChanged = Signal(int)
	# Signal: UndoAvailable state changed
	undoAvailableChanged = Signal(bool)
	# Signal: RedoAvailable state changed
	redoAvailableChanged = Signal(bool)
	# Signal: CopyAvailable state changed
	copyAvailableChanged = Signal(bool)

	# Project resource identifier
	EnumGen.start
	RES_FUP		= EnumGen.item # FBD/FUP diagrams
	RES_KOP		= EnumGen.item # LAD/KOP diagrams
	RES_SOURCES	= EnumGen.item # Sources
	RES_SYMTABS	= EnumGen.item # Symbol tables
	RES_LIBSELS	= EnumGen.item # Library selections
	EnumGen.end

	def __init__(self, parent=None):
		QTabWidget.__init__(self, parent)

		self.__suppressValidation = False

		self.fupTabs = FupTabWidget(self, projectWidget=self)
		self.kopTabs = None #TODO
		self.awlTabs = AwlSourceTabWidget(self, projectWidget=self)
		self.symTabs = SymSourceTabWidget(self, projectWidget=self)
		self.libTable = LibTableView(None, self)

		i = 0
		if self.fupTabs:
			self.addTab(self.fupTabs, "FUP / FBD")
			self.setTabToolTip(i, "Create Function Block Diagrams here")
			self.setTabIcon(i, getIcon("fup"))
			i += 1
		if self.kopTabs:
			self.addTab(self.kopTabs, "KOP / LAD")
			self.setTabToolTip(i, "Create Ladder logic here")
			self.setTabIcon(i, getIcon("kop"))
			i += 1
		if self.awlTabs:
			self.addTab(self.awlTabs, "AWL / STL")
			self.setTabToolTip(i, "Enter your AWL/STL program here")
			self.setTabIcon(i, getIcon("textsource"))
			i += 1
		if self.symTabs:
			self.addTab(self.symTabs, "Symbol tables")
			self.setTabToolTip(i, "Enter your symbol table here")
			self.setTabIcon(i, getIcon("tag"))
			i += 1
		if self.libTable:
			self.addTab(self.libTable, "Library selections")
			self.setTabToolTip(i, "Select standard libraries to include")
			self.setTabIcon(i, getIcon("stdlib"))
			i += 1

		self.reset()

		self.currentChanged.connect(self.__handleTabChange)
		if self.fupTabs:
			self.fupTabs.sourceChanged.connect(self.fupChanged)
		if self.kopTabs:
			self.kopTabs.sourceChanged.connect(self.kopChanged)
		if self.awlTabs:
			self.awlTabs.sourceChanged.connect(self.codeChanged)
			self.awlTabs.visibleLinesChanged.connect(self.visibleLinesChanged)
			self.awlTabs.focusChanged.connect(self.textFocusChanged)
			self.awlTabs.undoAvailableChanged.connect(self.undoAvailableChanged)
			self.awlTabs.redoAvailableChanged.connect(self.redoAvailableChanged)
			self.awlTabs.copyAvailableChanged.connect(self.copyAvailableChanged)
			self.awlTabs.resizeFont.connect(self.__doSourceCodeFontResize)
			self.awlTabs.validateDocument.connect(self.__doDocumentValidation)
		if self.symTabs:
			self.symTabs.sourceChanged.connect(self.symTabChanged)
		if self.libTable:
			self.libTable.model().contentChanged.connect(self.libTableChanged)

		# Send an initial tab-change notification signal.
		QTimer.singleShot(0,
			lambda: self.__handleTabChange(self.currentIndex()))

	# Run a background source validation.
	def __doDocumentValidation(self, editWidget):
		if not editWidget or self.__suppressValidation:
			return
		validator = AwlValidator.get()
		if validator:
			validator.validate(project=self.__project,
					   symTabSources=self.getSymTabSources(),
					   libSelections=self.getLibSelections(),
					   awlSources=self.getAwlSources(),
					   fupSources=self.getFupSources(),
					   kopSources=self.getKopSources())
			QTimer.singleShot(100, self.__checkValidationResult)

	# Poll the validation result
	def __checkValidationResult(self):
		validator = AwlValidator.get()
		if validator:
			running, exception = validator.getState()
			self.__handleValidationResult(exception)
			if running:
				QTimer.singleShot(100, self.__checkValidationResult)

	# Handle a validator exception
	def __handleValidationResult(self, exception):
		if self.__suppressValidation:
			return
		self.awlTabs.handleValidationResult(exception)
		self.symTabs.handleValidationResult(exception)
		self.libTable.handleValidationResult(exception)

	# Resize project editor font.
	def __doSourceCodeFontResize(self, bigger):
		font = getDefaultFixedFont()
		fontStr = self.__project.getGuiSettings().getEditorFont()
		if fontStr:
			font.fromString(fontStr)
			font.setStyleHint(QFont.Courier)
		if bigger:
			font.setPointSize(font.pointSize() + 1)
			if font.pointSize() > 72:
				return
		else:
			font.setPointSize(font.pointSize() - 1)
			if font.pointSize() < 6:
				return
		self.__project.getGuiSettings().setEditorFont(font.toString())
		self.setSettings(self.__project.getGuiSettings())

		self.codeChanged.emit()
		self.symTabChanged.emit()

	def __setSelectedResource(self, res):
		self.__selectedResource = res
		self.selResourceChanged.emit(res)

	def getSelectedResource(self):
		return self.__selectedResource

	def __handleTabChange(self, newTabIndex):
		widget = self.widget(newTabIndex)
		if not widget:
			return
		if widget is self.fupTabs:
			self.__setSelectedResource(self.RES_FUP)
			self.undoAvailableChanged.emit(False)
			self.redoAvailableChanged.emit(False)
			self.copyAvailableChanged.emit(False)
		elif widget is self.kopTabs:
			self.__setSelectedResource(self.RES_KOP)
			self.undoAvailableChanged.emit(False)
			self.redoAvailableChanged.emit(False)
			self.copyAvailableChanged.emit(False)
		elif widget is self.awlTabs:
			self.__setSelectedResource(self.RES_SOURCES)
			self.undoAvailableChanged.emit(self.awlTabs.undoIsAvailable())
			self.redoAvailableChanged.emit(self.awlTabs.redoIsAvailable())
			self.copyAvailableChanged.emit(self.awlTabs.copyIsAvailable())
			self.__doDocumentValidation(widget.currentWidget())
		elif widget is self.symTabs:
			self.__setSelectedResource(self.RES_SYMTABS)
			self.undoAvailableChanged.emit(self.symTabs.undoIsAvailable())
			self.redoAvailableChanged.emit(self.symTabs.redoIsAvailable())
			self.copyAvailableChanged.emit(self.symTabs.copyIsAvailable())
		elif widget is self.libTable:
			self.__setSelectedResource(self.RES_LIBSELS)
			self.undoAvailableChanged.emit(False)
			self.redoAvailableChanged.emit(False)
			self.copyAvailableChanged.emit(False)
		else:
			assert(0)

	def handleOnlineDiagChange(self, enabled):
		self.awlTabs.handleOnlineDiagChange(enabled)

	def handleInsnDump(self, insnDumpMsg):
		self.awlTabs.handleInsnDump(insnDumpMsg)

	def handleIdentsMsg(self, identsMsg):
		self.awlTabs.handleIdentsMsg(identsMsg)
		self.symTabs.handleIdentsMsg(identsMsg)

	def updateRunState(self, runState):
		self.awlTabs.updateRunState(runState)
		self.symTabs.updateRunState(runState)

	def getProject(self):
		"""Returns the project description object (class Project).
		Do _not_ use awlSources and symTabs from this project!"""
		return self.__project

	def getAwlSources(self):
		"Returns a list of AwlSource()s"
		if not self.awlTabs:
			return []
		return self.awlTabs.getSources()

	def getCurrentAwlSource(self):
		"Returns the currently selected AwlSource()."
		if not self.awlTabs:
			return []
		return self.awlTabs.getCurrentSource()

	def getFupSources(self):
		"Returns a list of FupSource()s"
		if not self.fupTabs:
			return []
		return self.fupTabs.getSources()

	def getCurrentFupSource(self):
		"Returns the currently selected FupSource()."
		if not self.fupTabs:
			return []
		return self.fupTabs.getCurrentSource()

	def getKopSources(self):
		"Returns a list of KopSource()s"
		if not self.kopTabs:
			return []
		return self.kopTabs.getSources()

	def getCurrentKopSource(self):
		"Returns the currently selected KopSource()."
		if not self.kopTabs:
			return []
		return self.kopTabs.getCurrentSource()

	def getSymTabSources(self):
		"Returns a list of SymTabSource()s"
		return self.symTabs.getSources()

	def getCurrentSymTabSource(self):
		"Returns the currently selected SymTabSource()."
		return self.symTabs.getCurrentSource()

	def getLibSelections(self):
		"Returns a list of AwlLibEntrySelection()s"
		return self.libTable.model().getLibSelections()

	def reset(self):
		self.__project = Project(None) # Empty project
		self.__isAdHocProject = False
		self.__warnedFileBacked = False
		self.__selectedResource = self.RES_SOURCES
		if self.fupTabs:
			self.fupTabs.reset()
		if self.kopTabs:
			self.kopTabs.reset()
		if self.awlTabs:
			self.awlTabs.reset()
		if self.symTabs:
			self.symTabs.reset()
		self.setCurrentIndex(self.indexOf(self.awlTabs))

	def setSettings(self, guiSettings):
		self.awlTabs.setSettings(guiSettings)
		self.symTabs.setSettings(guiSettings)

	def __loadProject(self, project):
		self.__suppressValidation = True
		try:
			self.__project = project
			self.setSettings(project.getGuiSettings())
			if self.awlTabs:
				self.awlTabs.setSources(self.__project.getAwlSources())
			if self.fupTabs:
				self.fupTabs.setSources(self.__project.getFupSources())
			if self.kopTabs:
				self.kopTabs.setSources(self.__project.getKopSources())
			if self.symTabs:
				self.symTabs.setSources(self.__project.getSymTabSources())
			self.libTable.model().setLibSelections(self.__project.getLibSelections())
			self.__warnedFileBacked = False
			self.__isAdHocProject = False
		finally:
			self.__suppressValidation = False

	def __loadPlainAwlSource(self, filename):
		project = Project(None) # Create an ad-hoc project
		source = AwlSource.fromFile(name=filename,
					    filepath=filename,
					    compatReEncode=True)
		project.setAwlSources([ source, ])
		self.__loadProject(project)
		self.__isAdHocProject = True
		QMessageBox.information(self,
			"Opened plain AWL/STL file",
			"The plain AWL/STL source file \n'%s'\n has sucessfully "
			"been opened.\n\n"
			"If you click on 'save', you will be asked to create "
			"a project file for this source." % filename)

	def loadProjectFile(self, filename):
		if Project.fileIsProject(filename):
			self.__loadProject(Project.fromFile(filename))
		else:
			# This might be a plain AWL-file.
			# Try to load it.
			self.__loadPlainAwlSource(filename)

	def saveProjectFile(self, filename):
		if self.__isAdHocProject:
			srcs = self.__project.getAwlSources()
			assert(len(srcs) == 1)
			if filename == srcs[0].filepath:
				# This is an ad-hoc project, that was created from
				# a plain AWL file. Do not overwrite the AWL file.
				# Ask the user to create an .awlpro file.
				res = QMessageBox.question(self,
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
		awlSrcs = self.getAwlSources()
		fupSrcs = self.getFupSources()
		kopSrcs = self.getKopSources()
		symTabSrcs = self.getSymTabSources()
		libSelections = self.getLibSelections()
		if not all(awlSrcs) or not all(symTabSrcs):
			# Failed to generate some sources
			return 0
		if (any(src.isFileBacked() for src in awlSrcs) or\
		    any(src.isFileBacked() for src in symTabSrcs)) and\
		    not self.__warnedFileBacked:
			QMessageBox.information(self,
				"Project contains external sources",
				"The project contains external sources.\n"
				"It is strongly recommended to integrate "
				"external sources into the project.\n"
				"Click on 'integrate source into project' "
				"in the source menu.")
			self.__warnedFileBacked = True
		self.__project.setAwlSources(awlSrcs)
		self.__project.setFupSources(fupSrcs)
		self.__project.setKopSources(kopSrcs)
		self.__project.setSymTabSources(symTabSrcs)
		self.__project.setLibSelections(libSelections)
		self.__project.setProjectFile(filename)
		self.__project.toFile()
		if self.__isAdHocProject:
			# We got converted to a real project. Update the tabs.
			self.awlTabs.setSources(self.__project.getAwlSources())
			self.symTabs.setSources(self.__project.getSymTabSources())
			self.__isAdHocProject = False
		return 1

	def __addSymbolToTabWidget(self, tabWidget, symbol):
		tabWidget.model().beginResetModel()
		tabWidget.getSymTab().add(symbol)
		tabWidget.model().revert()
		tabWidget.model().endResetModel()

# -*- coding: utf-8 -*-
#
# AWL simulator - GUI project widget
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
from awlsim.core.compat import *

from awlsim.core.templates import *

from awlsim.gui.util import *
from awlsim.gui.sourcetabs import *


class ProjectWidget(QTabWidget):
	# Signal: Some source changed
	codeChanged = Signal()
	# Signal: Some symbol table changed
	symTabChanged = Signal()
	# Signal: The visible AWL line range changed
	#         Parameters are: source, visibleFromLine, visibleToLine
	visibleLinesChanged = Signal(AwlSource, int, int)

	def __init__(self, parent=None):
		QTabWidget.__init__(self, parent)

		self.__project = Project(None) # Empty project
		self.__isAdHocProject = False

		self.awlTabs = AwlSourceTabWidget(self)
		self.symTabs = SymSourceTabWidget(self)

		self.addTab(self.awlTabs, "Sources")
		self.addTab(self.symTabs, "Symbol tables")
		self.setTabToolTip(0, "Enter your AWL/STL program here")
		self.setTabToolTip(1, "Enter your symbol table here")

		self.awlTabs.sourceChanged.connect(self.codeChanged)
		self.symTabs.sourceChanged.connect(self.symTabChanged)
		self.awlTabs.visibleLinesChanged.connect(self.visibleLinesChanged)

	def handleOnlineDiagChange(self, enabled):
		self.awlTabs.handleOnlineDiagChange(enabled)

	def handleInsnDump(self, insnDumpMsg):
		self.awlTabs.handleInsnDump(insnDumpMsg)

	def updateRunState(self, newRunState):
		self.awlTabs.updateRunState(newRunState)
		self.symTabs.updateRunState(newRunState)

	def getProject(self):
		"""Returns the project description object (class Project).
		Do _not_ use awlSources and symTabs from this project!"""
		return self.__project

	def getAwlSources(self):
		"Returns a list of AwlSource()s"
		return self.awlTabs.getSources()

	def getSymTabSources(self):
		"Returns a list of SymTabSource()s"
		return self.symTabs.getSources()

	def __loadProject(self, project):
		self.__project = project
		self.awlTabs.setSources(self.__project.getAwlSources())
		self.symTabs.setSources(self.__project.getSymTabSources())

	def __loadPlainAwlSource(self, filename):
		project = Project(None) # Create an ad-hoc project
		srcs = [ AwlSource.fromFile(identNr = AwlSource.newIdentNr(),
					    name = filename,
					    filepath = filename), ]
		project.setAwlSources(srcs)
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
		return 1

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
		symTabSrcs = self.getSymTabSources()
		if not all(awlSrcs) or not all(symTabSrcs):
			# Failed to generate some sources
			return 0
		if any(src.isFileBacked() for src in awlSrcs) or\
		   any(src.isFileBacked() for src in symTabSrcs):
			QMessageBox.information(self,
				"Project contains external sources",
				"The project contains external sources.\n"
				"It is strongly recommended to integrate "
				"external sources into the project.\n"
				"Click on 'integrate source into project' "
				"in the source menu.")
		self.__project.setAwlSources(awlSrcs)
		self.__project.setSymTabSources(symTabSrcs)
		self.__project.setProjectFile(filename)
		self.__project.toFile()
		if self.__isAdHocProject:
			# We got converted to a real project. Update the tabs.
			self.awlTabs.setSources(self.__project.getAwlSources())
			self.symTabs.setSources(self.__project.getSymTabSources())
			self.__isAdHocProject = False
		return 1

	def __pasteAwlText(self, text):
		if self.currentWidget() == self.awlTabs:
			self.awlTabs.pasteText(text)
		else:
			QMessageBox.information(self,
				"Please select AWL/STL source",
				"Can not paste template.\n\n"
				"Please move the text cursor to the place "
				"in the AWL/STL code where you want to paste "
				"the template to.")

	def insertOB(self):
		self.__pasteAwlText(awlTemplate_OB)

	def insertFC(self):
		self.__pasteAwlText(awlTemplate_FC)

	def insertFB(self):
		self.__pasteAwlText(awlTemplate_FB)

	def insertInstanceDB(self):
		self.__pasteAwlText(awlTemplate_instanceDB)

	def insertGlobalDB(self):
		self.__pasteAwlText(awlTemplate_globalDB)

	def insertFCcall(self):
		self.__pasteAwlText(awlTemplate_FCcall)

	def insertFBcall(self):
		self.__pasteAwlText(awlTemplate_FBcall)

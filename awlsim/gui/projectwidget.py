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

from awlsim.gui.util import *
from awlsim.gui.sourcetabs import *


class ProjectWidget(QWidget):
	# Signal: Some source changed
	codeChanged = Signal()
	# Signal: Some symbol table changed
	symTabChanged = Signal()
	# Signal: The visible AWL line range changed
	#         Parameters are: source, visibleFromLine, visibleToLine
	visibleLinesChanged = Signal(AwlSource, int, int)

	def __init__(self, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout())

		self.__project = Project(None) # Empty project

		hbox = QHBoxLayout()
		self.srcButton = QRadioButton("Sources", self)
		self.srcButton.setChecked(True)
		hbox.addWidget(self.srcButton)
		self.symTabButton = QRadioButton("Symbol tables", self)
		self.symTabButton.setEnabled(False)#TODO
		hbox.addWidget(self.symTabButton)
		hbox.addStretch()
		self.layout().addLayout(hbox, 0, 0)

		self.awlTabs = AwlSourceTabWidget(self)
		self.symTabs = SymSourceTabWidget(self)

		self.stack = QStackedWidget(self)
		self.stack.addWidget(self.awlTabs)
		self.stack.addWidget(self.symTabs)
		self.layout().addWidget(self.stack, 1, 0)

		self.srcButton.toggled.connect(self.__mainSelectionChanged)
		self.symTabButton.toggled.connect(self.__mainSelectionChanged)
		self.awlTabs.sourceChanged.connect(self.codeChanged)
		self.symTabs.sourceChanged.connect(self.symTabChanged)
		self.awlTabs.visibleLinesChanged.connect(self.visibleLinesChanged)

	def handleOnlineDiagChange(self, enabled):
		self.awlTabs.handleOnlineDiagChange(enabled)

	def handleInsnDump(self, insnDumpMsg):
		self.awlTabs.handleInsnDump(insnDumpMsg)

	def __mainSelectionChanged(self):
		if self.srcButton.isChecked():
			self.stack.setCurrentWidget(self.awlTabs)
		elif self.symTabButton.isChecked():
			self.stack.setCurrentWidget(self.symTabs)

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

	def __loadProject(self, project):
		self.__project = project
		if len(self.__project.getAwlSources()) > 1:
			#TODO
			raise AwlSimError("No support for projects with "
				"multiple AWL sources, yet.")
		if self.__project.getSymTabSources():
			#TODO
			raise AwlSimError("No support for projects with "
				"symbol tables, yet.")
		self.awlTabs.setSources(self.__project.getAwlSources())
#TODO		self.symTabs.setSources(self.__project.getSymTabSources())

	def __loadPlainAwlSource(self, filename):
		project = Project(None) # Create an ad-hoc project
		srcs = [ AwlSource.fromFile(filename, filename), ]
		project.setAwlSources(srcs)
		self.__loadProject(project)
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
		isAdHoc = not self.__project.getProjectFile()
		if isAdHoc:
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
		self.__project.setProjectFile(filename)
		self.__project.setAwlSources(self.getAwlSources())
#TODO		self.__project.setSymTabSources(
		self.__project.allFileBackingsToInternal()
		self.__project.toFile()
		if isAdHoc:
			# We got converted to a real project. Update the tabs.
			self.awlTabs.setSources(self.__project.getAwlSources())
#TODO			self.symTabs.setSources(self.__project.getSymTabSources())
		return 1

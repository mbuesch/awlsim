# -*- coding: utf-8 -*-
#
# AWL simulator - GUI editor MDI area
#
# Copyright 2017 Michael Buesch <m@bues.ch>
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

from awlsim.gui.editwidget import EditWidget
from awlsim.gui.symtabwidget import SymTabView
from awlsim.gui.libtablewidget import LibTableView
from awlsim.gui.fup.fupwidget import FupWidget
from awlsim.gui.util import *


__all__ = [
	"EditMdiArea",
]


class EditMdiArea(QMdiArea):
	"""Main editor MDI area.
	"""

	def __init__(self, mainWidget):
		QMdiArea.__init__(self, parent=mainWidget)
		self.mainWidget = mainWidget
		self.setViewMode(QMdiArea.TabbedView)
		self.setTabsClosable(True)
		self.setTabsMovable(True)

	def getProjectTreeModel(self):
		return self.mainWidget.projectTreeModel

	def __newWin(self, mdiSubWin):
		self.addSubWindow(mdiSubWin)
		mdiSubWin.show()
		return mdiSubWin

	def newWin_AWL(self, source):
		return self.__newWin(AwlEditMdiSubWindow(source))

	def newWin_FUP(self, source):
		return self.__newWin(FupEditMdiSubWindow(source))

	def newWin_KOP(self, source):
		return self.__newWin(KopEditMdiSubWindow(source))

	def newWin_SymTab(self, source):
		return self.__newWin(SymTabEditMdiSubWindow(source))

	def newWin_Libsel(self, libSelections):
		return self.__newWin(LibSelEditMdiSubWindow(libSelections))

class EditMdiSubWindow(QMdiSubWindow):
	closed = Signal(QMdiSubWindow)

	def __init__(self):
		self.__forceClose = False
		QMdiSubWindow.__init__(self)
		self.setAttribute(Qt.WA_DeleteOnClose)

	def setWidget(self, childWidget):
		QMdiSubWindow.setWidget(self, childWidget)
		childWidget.setParent(self)

	def closeEvent(self, ev):
		if not self.__forceClose:
			pass#TODO check if dirty
		self.closed.emit(self)
		QMdiSubWindow.closeEvent(self, ev)

	def forceClose(self):
		self.__forceClose = True
		return self.close()

	def getSource(self):
		raise NotImplementedError

class AwlEditMdiSubWindow(EditMdiSubWindow):
	def __init__(self, source):
		EditMdiSubWindow.__init__(self)

		self.editWidget = EditWidget(self)
		self.editWidget.setSource(source)
		self.setWidget(self.editWidget)

		self.setWindowTitle(source.name + " (AWL)")

	def getSource(self):
		return self.editWidget.getSource()

class FupEditMdiSubWindow(EditMdiSubWindow):
	def __init__(self, source):
		EditMdiSubWindow.__init__(self)

		def getSymTabSourcesFunc():
			projectTreeModel = self.mdiArea().getProjectTreeModel()
			project = projectTreeModel.getProject()
			return project.getSymTabSources()

		self.fupWidget = FupWidget(
			parent=self,
			getSymTabSourcesFunc=getSymTabSourcesFunc)
		self.fupWidget.setSource(source)
		self.setWidget(self.fupWidget)

		self.setWindowTitle(source.name + " (FUP)")

	def getSource(self):
		return self.fupWidget.getSource()

class KopEditMdiSubWindow(EditMdiSubWindow):
	pass#TODO

class SymTabEditMdiSubWindow(EditMdiSubWindow):
	def __init__(self, source):
		EditMdiSubWindow.__init__(self)

		self.symTabView = SymTabView(self)
		self.symTabView.setSymTab(SymbolTable())
		self.symTabView.model().setSource(source)
		self.setWidget(self.symTabView)

		self.setWindowTitle(source.name + " (Symbols)")

	def getSource(self):
		return self.symTabView.model().getSource()

class LibSelEditMdiSubWindow(EditMdiSubWindow):
	def __init__(self, libSelections):
		EditMdiSubWindow.__init__(self)

		self.libTabView = LibTableView(model=None, parent=self)
		self.libTabView.model().setLibSelections(libSelections)
		self.setWidget(self.libTabView)

		self.setWindowTitle("Library selections")

	def getLibSelections(self):
		return self.libTabView.model().getLibSelections()

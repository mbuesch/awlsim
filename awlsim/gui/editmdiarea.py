# -*- coding: utf-8 -*-
#
# AWL simulator - GUI editor MDI area
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
		self.resetArea()

	def getProjectTreeModel(self):
		return self.mainWidget.projectTreeModel

	def resetArea(self):
		"""Close all MDI sub windows and clear all state.
		"""
		for mdiSubWin in list(self.subWindowList()):
			mdiSubWin.forceClose()
			del mdiSubWin
		self._guiSettings = GuiSettings()

	def __newWin(self, mdiSubWin):
		self.addSubWindow(mdiSubWin)
		mdiSubWin.show()
		return mdiSubWin

	def newWin_AWL(self, source):
		return self.__newWin(AwlEditMdiSubWindow(self, source))

	def newWin_FUP(self, source):
		return self.__newWin(FupEditMdiSubWindow(self, source))

	def newWin_KOP(self, source):
		return self.__newWin(KopEditMdiSubWindow(self, source))

	def newWin_SymTab(self, source):
		return self.__newWin(SymTabEditMdiSubWindow(self, source))

	def newWin_Libsel(self, libSelections):
		return self.__newWin(LibSelEditMdiSubWindow(self, libSelections))

	def undoIsAvailable(self):
		mdiSubWin = self.activeSubWindow()
		return mdiSubWin.undoIsAvailable() if mdiSubWin else False

	def undo(self):
		mdiSubWin = self.activeSubWindow()
		return mdiSubWin.undo() if mdiSubWin else False

	def redoIsAvailable(self):
		mdiSubWin = self.activeSubWindow()
		return mdiSubWin.redoIsAvailable() if mdiSubWin else False

	def redo(self):
		mdiSubWin = self.activeSubWindow()
		return mdiSubWin.redo() if mdiSubWin else False

	def cutIsAvailable(self):
		mdiSubWin = self.activeSubWindow()
		return mdiSubWin.cutIsAvailable() if mdiSubWin else False

	def cut(self):
		mdiSubWin = self.activeSubWindow()
		return mdiSubWin.cut() if mdiSubWin else False

	def copyIsAvailable(self):
		mdiSubWin = self.activeSubWindow()
		return mdiSubWin.copyIsAvailable() if mdiSubWin else False

	def copy(self):
		mdiSubWin = self.activeSubWindow()
		return mdiSubWin.copy() if mdiSubWin else False

	def pasteIsAvailable(self):
		mdiSubWin = self.activeSubWindow()
		return mdiSubWin.pasteIsAvailable() if mdiSubWin else False

	def paste(self, text=None):
		mdiSubWin = self.activeSubWindow()
		return mdiSubWin.paste(text) if mdiSubWin else False

	def findTextIsAvailable(self):
		mdiSubWin = self.activeSubWindow()
		return mdiSubWin.findTextIsAvailable() if mdiSubWin else False

	def findText(self):
		mdiSubWin = self.activeSubWindow()
		return mdiSubWin.findText() if mdiSubWin else False

	def findReplaceTextIsAvailable(self):
		mdiSubWin = self.activeSubWindow()
		return mdiSubWin.findReplaceTextIsAvailable() if mdiSubWin else False

	def findReplaceText(self):
		mdiSubWin = self.activeSubWindow()
		return mdiSubWin.findReplaceText() if mdiSubWin else False

	def setGuiSettings(self, guiSettings):
		self._guiSettings = guiSettings
		for mdiSubWin in self.subWindowList():
			mdiSubWin.setGuiSettings(guiSettings)

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

	def undoIsAvailable(self):
		return False

	def undo(self):
		return False

	def redoIsAvailable(self):
		return False

	def redo(self):
		return False

	def cutIsAvailable(self):
		return False

	def cut(self):
		return False

	def copyIsAvailable(self):
		return False

	def copy(self):
		return False

	def pasteIsAvailable(self):
		return False

	def paste(self, text=None):
		return False

	def findTextIsAvailable(self):
		return False

	def findText(self):
		return False

	def findReplaceTextIsAvailable(self):
		return self.findTextIsAvailable()

	def findReplaceText(self):
		return False

	def setGuiSettings(self, guiSettings):
		pass

class AwlEditMdiSubWindow(EditMdiSubWindow):
	def __init__(self, mdiArea, source):
		EditMdiSubWindow.__init__(self)

		self.editWidget = EditWidget(self)
		self.editWidget.setSource(source)
		self.editWidget.setSettings(mdiArea._guiSettings)
		self.setWidget(self.editWidget)

#TODO		editWidget.codeChanged.connect(self.sourceChanged)
#TODO		editWidget.focusChanged.connect(self.focusChanged)
#TODO		editWidget.visibleRangeChanged.connect(self.__emitVisibleLinesSignal)
#TODO		editWidget.cpuCodeMatchChanged.connect(self.__handleCodeMatchChange)
#TODO		editWidget.undoAvailable.connect(self.undoAvailableChanged)
#TODO		editWidget.redoAvailable.connect(self.redoAvailableChanged)
#TODO		editWidget.copyAvailable.connect(self.copyAvailableChanged)
#TODO		editWidget.resizeFont.connect(self.resizeFont)
#TODO		editWidget.validateDocument.connect(
#TODO			lambda editWidget: self.validateDocument.emit(editWidget))

		self.setWindowTitle(source.name + " (AWL)")

	def getSource(self):
		return self.editWidget.getSource()

	def undoIsAvailable(self):
		return self.editWidget.undoIsAvailable()

	def undo(self):
		self.editWidget.undo()
		return True

	def redoIsAvailable(self):
		return self.editWidget.redoIsAvailable()

	def redo(self):
		self.editWidget.redo()
		return True

	def cutIsAvailable(self):
		return self.copyIsAvailable()

	def cut(self):
		self.editWidget.cut()
		return True

	def copyIsAvailable(self):
		return self.editWidget.copyIsAvailable()

	def copy(self):
		self.editWidget.copy()
		return True

	def pasteIsAvailable(self):
		return True

	def paste(self, text=None):
		if text:
			self.editWidget.pasteText(text)
		else:
			self.editWidget.paste()
		return True

	def findTextIsAvailable(self):
		return True

	def findText(self):
		self.editWidget.findText()
		return True

	def findReplaceText(self):
		self.editWidget.findReplaceText()
		return True

	def setGuiSettings(self, guiSettings):
		self.editWidget.setSettings(guiSettings)

class FupEditMdiSubWindow(EditMdiSubWindow):
	def __init__(self, mdiArea, source):
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
	def __init__(self, mdiArea, source):
		EditMdiSubWindow.__init__(self)

	pass#TODO

class SymTabEditMdiSubWindow(EditMdiSubWindow):
	def __init__(self, mdiArea, source):
		EditMdiSubWindow.__init__(self)

		self.symTabView = SymTabView(self)
		self.symTabView.setSymTab(SymbolTable())
		self.symTabView.model().setSource(source)
		self.setWidget(self.symTabView)

		self.setWindowTitle(source.name + " (Symbols)")

	def getSource(self):
		return self.symTabView.model().getSource()

class LibSelEditMdiSubWindow(EditMdiSubWindow):
	def __init__(self, mdiArea, libSelections):
		EditMdiSubWindow.__init__(self)

		self.libTabView = LibTableView(model=None, parent=self)
		self.libTabView.model().setLibSelections(libSelections)
		self.setWidget(self.libTabView)

		self.setWindowTitle("Library selections")

	def getLibSelections(self):
		return self.libTabView.model().getLibSelections()

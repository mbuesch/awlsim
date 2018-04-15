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
from awlsim.gui.sourcecodeedit import *


__all__ = [
	"EditMdiArea",
]


class EditMdiArea(QMdiArea):
	"""Main editor MDI area.
	"""

	# Signal: Keyboard focus in/out event.
	focusChanged = Signal(bool)

	# Signal: UndoAvailable state changed
	undoAvailableChanged = Signal(bool)

	# Signal: RedoAvailable state changed
	redoAvailableChanged = Signal(bool)

	# Signal: CopyAvailable state changed
	copyAvailableChanged = Signal(bool)

	# Signal: CutAvailable state changed
	cutAvailableChanged = Signal(bool)

	# Signal: PasteAvailable state changed
	pasteAvailableChanged = Signal(bool)

	def __init__(self, mainWidget):
		QMdiArea.__init__(self, parent=mainWidget)
		self.mainWidget = mainWidget
		self.setViewMode(QMdiArea.TabbedView)
		self.setTabsClosable(True)
		self.setTabsMovable(True)
		self.resetArea()

		self.subWindowActivated.connect(self.__handleSubWindowActivated)

	def getProjectTreeModel(self):
		return self.mainWidget.projectTreeModel

	@property
	def activeOpenSubWindow(self):
		"""Get the currently active and open sub window.
		"""
		mdiSubWin = self.activeSubWindow()
		if not mdiSubWin:
			return None
		if mdiSubWin.isClosing():
			return None
		return mdiSubWin

	def resetArea(self):
		"""Close all MDI sub windows and clear all state.
		"""
		for mdiSubWin in list(self.subWindowList()):
			mdiSubWin.forceClose()
			del mdiSubWin
		self._guiSettings = GuiSettings()

	def __handleSubWindowActivated(self, mdiSubWin):
		"""An MDI sub window has just been activated.
		"""
		self.__handleSubWinUndoAvailChanged(mdiSubWin)
		self.__handleSubWinRedoAvailChanged(mdiSubWin)
		self.__handleSubWinCopyAvailChanged(mdiSubWin)
		self.__handleSubWinCutAvailChanged(mdiSubWin)
		self.__handleSubWinPasteAvailChanged(mdiSubWin)

	def __handleSubWinFocusChanged(self, mdiSubWin, hasFocus):
		"""Text focus of one sub window has changed.
		"""
		self.focusChanged.emit((self.activeOpenSubWindow is mdiSubWin) and\
				       hasFocus)

	def __handleSubWinUndoAvailChanged(self, mdiSubWin):
		"""Undo-state of one sub window has changed.
		"""
		self.undoAvailableChanged.emit((self.activeOpenSubWindow is mdiSubWin) and\
					       self.undoIsAvailable())

	def __handleSubWinRedoAvailChanged(self, mdiSubWin):
		"""Redo-state of one sub window has changed.
		"""
		self.redoAvailableChanged.emit((self.activeOpenSubWindow is mdiSubWin) and\
					       self.redoIsAvailable())

	def __handleSubWinCopyAvailChanged(self, mdiSubWin):
		"""Copy-state of one sub window has changed.
		"""
		self.copyAvailableChanged.emit((self.activeOpenSubWindow is mdiSubWin) and\
					       self.copyIsAvailable())

	def __handleSubWinCutAvailChanged(self, mdiSubWin):
		"""Cut-state of one sub window has changed.
		"""
		self.cutAvailableChanged.emit((self.activeOpenSubWindow is mdiSubWin) and\
					      self.cutIsAvailable())

	def __handleSubWinPasteAvailChanged(self, mdiSubWin):
		"""Paste-state of one sub window has changed.
		"""
		self.pasteAvailableChanged.emit((self.activeOpenSubWindow is mdiSubWin) and\
					        self.pasteIsAvailable())

	def __newWin(self, mdiSubWin):
		self.addSubWindow(mdiSubWin)
		mdiSubWin.show()

		# Connect signals of sub window.
		mdiSubWin.focusChanged.connect(
			lambda hasFocus: self.__handleSubWinFocusChanged(mdiSubWin, hasFocus))
		mdiSubWin.undoAvailableChanged.connect(
			lambda undoAvail: self.__handleSubWinUndoAvailChanged(mdiSubWin))
		mdiSubWin.redoAvailableChanged.connect(
			lambda redoAvail: self.__handleSubWinRedoAvailChanged(mdiSubWin))
		mdiSubWin.copyAvailableChanged.connect(
			lambda copyAvail: self.__handleSubWinCopyAvailChanged(mdiSubWin))
		mdiSubWin.cutAvailableChanged.connect(
			lambda cutAvail: self.__handleSubWinCutAvailChanged(mdiSubWin))
		mdiSubWin.pasteAvailableChanged.connect(
			lambda pasteAvail: self.__handleSubWinPasteAvailChanged(mdiSubWin))

		self.__handleSubWinFocusChanged(mdiSubWin, True)

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
		mdiSubWin = self.activeOpenSubWindow
		return mdiSubWin.undoIsAvailable() if mdiSubWin else False

	def undo(self):
		mdiSubWin = self.activeOpenSubWindow
		return mdiSubWin.undo() if mdiSubWin else False

	def redoIsAvailable(self):
		mdiSubWin = self.activeOpenSubWindow
		return mdiSubWin.redoIsAvailable() if mdiSubWin else False

	def redo(self):
		mdiSubWin = self.activeOpenSubWindow
		return mdiSubWin.redo() if mdiSubWin else False

	def cutIsAvailable(self):
		mdiSubWin = self.activeOpenSubWindow
		return mdiSubWin.cutIsAvailable() if mdiSubWin else False

	def cut(self):
		mdiSubWin = self.activeOpenSubWindow
		return mdiSubWin.cut() if mdiSubWin else False

	def copyIsAvailable(self):
		mdiSubWin = self.activeOpenSubWindow
		return mdiSubWin.copyIsAvailable() if mdiSubWin else False

	def copy(self):
		mdiSubWin = self.activeOpenSubWindow
		return mdiSubWin.copy() if mdiSubWin else False

	def pasteIsAvailable(self):
		mdiSubWin = self.activeOpenSubWindow
		return mdiSubWin.pasteIsAvailable() if mdiSubWin else False

	def paste(self, text=None):
		mdiSubWin = self.activeOpenSubWindow
		return mdiSubWin.paste(text) if mdiSubWin else False

	def findTextIsAvailable(self):
		mdiSubWin = self.activeOpenSubWindow
		return mdiSubWin.findTextIsAvailable() if mdiSubWin else False

	def findText(self):
		mdiSubWin = self.activeOpenSubWindow
		return mdiSubWin.findText() if mdiSubWin else False

	def findReplaceTextIsAvailable(self):
		mdiSubWin = self.activeOpenSubWindow
		return mdiSubWin.findReplaceTextIsAvailable() if mdiSubWin else False

	def findReplaceText(self):
		mdiSubWin = self.activeOpenSubWindow
		return mdiSubWin.findReplaceText() if mdiSubWin else False

	def setGuiSettings(self, guiSettings):
		self._guiSettings = guiSettings
		for mdiSubWin in self.subWindowList():
			mdiSubWin.setGuiSettings(guiSettings)

class EditMdiSubWindow(QMdiSubWindow):
	"""Edit MDI sub window base class.
	"""

	# Signal: Emitted, if this MDI sub window is about to close.
	closed = Signal(QMdiSubWindow)

	# Signal: Emitted, if the source code changed.
	sourceChanged = Signal()

	# Signal: Keyboard focus in/out event.
	focusChanged = Signal(bool)

	# Signal: UndoAvailable state changed
	undoAvailableChanged = Signal(bool)

	# Signal: RedoAvailable state changed
	redoAvailableChanged = Signal(bool)

	# Signal: CopyAvailable state changed
	copyAvailableChanged = Signal(bool)

	# Signal: CutAvailable state changed
	cutAvailableChanged = Signal(bool)

	# Signal: PasteAvailable state changed
	pasteAvailableChanged = Signal(bool)

	# Signal: Change the font size.
	#         If the parameter is True, increase font size.
	resizeFont = Signal(bool)

	# Signal: Validation request.
	#	  A code validation should take place.
	#	  The parameter is the source editor.
	validateDocument = Signal(SourceCodeEdit)

	def __init__(self):
		self.__forceClose = False
		self.__isClosing = False
		QMdiSubWindow.__init__(self)
		self.setAttribute(Qt.WA_DeleteOnClose)

	def setWidget(self, childWidget):
		QMdiSubWindow.setWidget(self, childWidget)
		childWidget.setParent(self)

	def closeEvent(self, ev):
		if not self.__forceClose:
			pass#TODO check if dirty

		# No way back. We are closing.
		self.__isClosing = True
		self.closed.emit(self)
		QMdiSubWindow.closeEvent(self, ev)

	def forceClose(self):
		self.__forceClose = True
		return self.close()

	def isClosing(self):
		return self.__isClosing

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

	# Signal: The visible AWL line range changed
	#         Parameters are: source, visibleFromLine, visibleToLine
	visibleLinesChanged = Signal(object, int, int)

	def __init__(self, mdiArea, source):
		EditMdiSubWindow.__init__(self)

		self.editWidget = EditWidget(self)
		self.editWidget.setSource(source)
		self.editWidget.setSettings(mdiArea._guiSettings)
		self.setWidget(self.editWidget)

		self.editWidget.codeChanged.connect(self.sourceChanged)
		self.editWidget.focusChanged.connect(self.focusChanged)
#TODO		editWidget.visibleRangeChanged.connect(self.__emitVisibleLinesSignal)
#TODO		editWidget.cpuCodeMatchChanged.connect(self.__handleCodeMatchChange)
		self.editWidget.undoAvailable.connect(self.undoAvailableChanged)
		self.editWidget.redoAvailable.connect(self.redoAvailableChanged)
		self.editWidget.copyAvailable.connect(self.copyAvailableChanged)
		self.editWidget.copyAvailable.connect(self.cutAvailableChanged)
		self.editWidget.resizeFont.connect(self.resizeFont)
		self.editWidget.validateDocument.connect(
			lambda editWidget: self.validateDocument.emit(editWidget))

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

		self.symTabView.focusChanged.connect(self.focusChanged)
		self.symTabView.model().sourceChanged.connect(self.sourceChanged)

		self.setWindowTitle(source.name + " (Symbols)")

	def getSource(self):
		return self.symTabView.model().getSource()

class LibSelEditMdiSubWindow(EditMdiSubWindow):
	def __init__(self, mdiArea, libSelections):
		EditMdiSubWindow.__init__(self)

		self.libTabView = LibTableView(model=None, parent=self)
		self.libTabView.model().setLibSelections(libSelections)
		self.setWidget(self.libTabView)

		self.libTabView.focusChanged.connect(self.focusChanged)
		self.libTabView.model().contentChanged.connect(self.sourceChanged)

		self.setWindowTitle("Library selections")

	def getLibSelections(self):
		return self.libTabView.model().getLibSelections()

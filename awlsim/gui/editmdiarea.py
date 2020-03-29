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
#from awlsim.common.cython_support cimport * #@cy
from awlsim.common.compat import *

from awlsim.gui.editwidget import EditWidget
from awlsim.gui.symtabwidget import SymTabView
from awlsim.gui.libtablewidget import LibTableView
from awlsim.gui.fup.fupwidget import FupWidget
from awlsim.gui.sourcecodeedit import SourceCodeEdit
from awlsim.gui.icons import *
from awlsim.gui.util import *
from awlsim.gui.runstate import *
from awlsim.gui.validatorsched import *


__all__ = [
	"EditMdiArea",
]


class EditMdiArea(QMdiArea):
	"""Main editor MDI area.
	"""

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

	# Signal: The visible AWL line range changed
	#         Parameters are: AwlSource, visibleFromLine, visibleToLine
	visibleLinesChanged = Signal(object, int, int)

	def __init__(self, mainWidget):
		QMdiArea.__init__(self, parent=mainWidget)
		self.mainWidget = mainWidget

		self.__onlineDiagMdiSubWin = None

		GuiValidatorSched.get().haveValidationResult.connect(
			self.__handleDocumentValidationResult)

		# Init the editor find dialog.
		SourceCodeEdit.initFindDialog(self)

		self.setViewMode(QMdiArea.SubWindowView)
		self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.setTabsClosable(True)
		self.setTabsMovable(True)
		self.resetArea()

		self.subWindowActivated.connect(self.__handleSubWindowActivated)
		self.getSimClient().haveException.connect(self.__handleAwlSimError)

	def getMainWidget(self):
		return self.mainWidget

	def getProjectTreeModel(self):
		return self.mainWidget.projectTreeModel

	def getProject(self):
		return self.getProjectTreeModel().getProject()

	def getSimClient(self):
		return self.getMainWidget().getSimClient()

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
		self.__onlineDiagEnabled = False
		self.__guiRunState = None
		for mdiSubWin in list(self.subWindowList()):
			mdiSubWin.forceClose()
			del mdiSubWin
		self._guiSettings = GuiSettings()

	def __handleAwlSimError(self, e):
		for mdiSubWin in self.subWindowList():
			mdiSubWin.handleAwlSimError(e)

	def __handleSubWindowActivated(self, mdiSubWin):
		"""An MDI sub window has just been activated.
		"""
		self.__handleSubWinUndoAvailChanged(mdiSubWin)
		self.__handleSubWinRedoAvailChanged(mdiSubWin)
		self.__handleSubWinCopyAvailChanged(mdiSubWin)
		self.__handleSubWinCutAvailChanged(mdiSubWin)
		self.__handleSubWinPasteAvailChanged(mdiSubWin)
		GuiValidatorSched.get().startAsyncValidation(self.getProject,
							     delaySec=0.5)
		self.__refreshOnlineDiagState()
		self.__setFindDialogReference(mdiSubWin)

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
		mdiSubWin.sourceChanged.connect(self.sourceChanged)
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
		mdiSubWin.resizeFont.connect(self.__handleSourceCodeFontResize)
		mdiSubWin.validateDocument.connect(
			lambda delaySec: GuiValidatorSched.get().startAsyncValidation(project=self.getProject,
										      delaySec=delaySec))
		mdiSubWin.visibleLinesChanged.connect(self.__handleVisibleLinesChanged)

		self.__handleSubWinFocusChanged(mdiSubWin, True)
		GuiValidatorSched.get().startAsyncValidation(project=self.getProject,
							     delaySec=0.5)
		mdiSubWin.setGuiRunState(self.__guiRunState)

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

	def __handleSourceCodeFontResize(self, bigger):
		self.__sourceCodeFontResize(1 if bigger else -1)

	def __sourceCodeFontResize(self, increment):
		"""Resize the editor font.
		"""
		if increment == 0:
			return
		project = self.getProject()
		font = getDefaultFixedFont()
		fontStr = project.getGuiSettings().getEditorFont()
		if fontStr:
			font.fromString(fontStr)
			font.setStyleHint(QFont.Courier)
		font.setPointSize(font.pointSize() + increment)
		if (increment > 0 and font.pointSize() > 72) or\
		   (increment < 0 and font.pointSize() < 6):
			return
		project.getGuiSettings().setEditorFont(font.toString())
		self.setGuiSettings(project.getGuiSettings())

		self.sourceChanged.emit()

	def __handleDocumentValidationResult(self, exception):
		"""Handle a background source code validator exception.
		"""
		for mdiSubWin in self.subWindowList():
			mdiSubWin.handleDocumentValidationResult(exception)

	def __refreshOnlineDiagState(self):
		"""Refresh the online diagnosis state of the sub windows.
		"""
		activeMdiSubWin = self.activeOpenSubWindow

		# Disable all inactive sub windows.
		for mdiSubWin in self.subWindowList():
			if mdiSubWin.ONLINE_DIAG:
				if not self.__onlineDiagEnabled or\
				   mdiSubWin is not activeMdiSubWin:
					mdiSubWin.enableOnlineDiag(False)

		# Enable the active sub window, if possible.
		if activeMdiSubWin and activeMdiSubWin.ONLINE_DIAG:
			self.__onlineDiagMdiSubWin = activeMdiSubWin
			if self.__onlineDiagEnabled:
				activeMdiSubWin.enableOnlineDiag(True)
			source = activeMdiSubWin.getSource()
			fromLine, toLine = activeMdiSubWin.getVisibleLineRange()
			self.visibleLinesChanged.emit(source, fromLine, toLine)
		else:
			self.__onlineDiagMdiSubWin = None
			self.visibleLinesChanged.emit(None, -1, -1)

	def __handleVisibleLinesChanged(self, mdiSubWin, source, visibleFromLine, visibleToLine):
		self.visibleLinesChanged.emit(source, visibleFromLine, visibleToLine)

	def enableOnlineDiag(self, enabled):
		"""Enable or disable online diagnosis in the active sub window.
		"""
		self.__onlineDiagEnabled = enabled
		self.__refreshOnlineDiagState()

	def handleInsnDump(self, insnDumpMsg):
		mdiSubWin = self.__onlineDiagMdiSubWin
		if mdiSubWin:
			mdiSubWin.handleInsnDump(insnDumpMsg)

	def handleIdentsMsg(self, identsMsg):
		for mdiSubWin in self.subWindowList():
			mdiSubWin.handleIdentsMsg(identsMsg)

	def setGuiRunState(self, runState):
		"""Update the CPU run state.
		runState is a GuiRunState instance.
		"""
		self.__guiRunState = runState
		for mdiSubWin in self.subWindowList():
			mdiSubWin.setGuiRunState(runState)
			if runState in (GuiRunState.STATE_LOAD,
					GuiRunState.STATE_RUN):
				# Clear all errors.
				mdiSubWin.handleAwlSimError(None)

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

	def __setFindDialogReference(self, mdiSubWin):
		"""Switch the find dialog reference to the new window (or None).
		"""
		findDlg = SourceCodeEdit.getFindDialog()
		if findDlg:
			if mdiSubWin and mdiSubWin.TYPE == mdiSubWin.TYPE_AWL:
				findDlg.setTextEdit(mdiSubWin.editWidget)
			else:
				findDlg.setTextEdit(None)

	def setGuiSettings(self, guiSettings):
		self._guiSettings = guiSettings
		for mdiSubWin in self.subWindowList():
			mdiSubWin.setGuiSettings(guiSettings)

class EditMdiSubWindow(QMdiSubWindow):
	"""Edit MDI sub window base class.
	"""

	EnumGen.start
	TYPE_AWL	= EnumGen.item
	TYPE_FUP	= EnumGen.item
	TYPE_KOP	= EnumGen.item
	TYPE_SYMTAB	= EnumGen.item
	TYPE_LIBSEL	= EnumGen.item
	EnumGen.end
	TYPE		= None

	# True, if this sub window support online diagnosis.
	ONLINE_DIAG	= False

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
	#	  Parameter: Number of seconds to delay before validation start.
	validateDocument = Signal(float)

	# Signal: The visible AWL line range changed
	#         Parameters are: EditMdiSubWindow, AwlSource, visibleFromLine, visibleToLine
	visibleLinesChanged = Signal(object, object, int, int)

	def __init__(self):
		self.__forceClose = False
		self.__isClosing = False
		QMdiSubWindow.__init__(self)
		self.setAttribute(Qt.WA_DeleteOnClose)

	def setWidget(self, childWidget):
		QMdiSubWindow.setWidget(self, childWidget)
		childWidget.setParent(self)

	def closeEvent(self, ev):
		mdiArea = self.mdiArea()
		mainWidget = mdiArea.getMainWidget()
		projectTreeModel = mdiArea.getProjectTreeModel()

		if mainWidget.isDirty():
			# The closed window might contain changes that
			# have not yet been merged with the project.
			# Refresh the project now.
			refreshOk = projectTreeModel.refreshProject()
			if not refreshOk and not self.__forceClose:
				# Refresh failed.
				QMessageBox.critical(self,
					"Failed to refresh project",
					"Failed to refresh project data.\n"
					"Not closing the editor window "
					"to avoid loss of data.")
				# Do not close the sub window.
				ev.ignore()
				return

		# No way back. We are closing.
		self.__isClosing = True
		self.closed.emit(self)
		QMdiSubWindow.closeEvent(self, ev)

	def wheelEvent(self, ev):
		QMdiSubWindow.wheelEvent(self, ev)
		# Always accept the wheel event.
		# This avoids forwarding it to the parent MDI area,
		# if the scroll happened in this MDI sub window.
		ev.accept()

	def updateTitle(self):
		pass

	def forceClose(self):
		self.__forceClose = True
		return self.close()

	def isClosing(self):
		return self.__isClosing

	def getSource(self):
		raise NotImplementedError

	def setSource(self, source):
		raise NotImplementedError

	def importSource(self, fileName=None):
		return False

	def exportSource(self, fileName=None):
		return False

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

	def enableOnlineDiag(self, enabled):
		return False

	def getVisibleLineRange(self):
		return (-1, -1)

	def handleInsnDump(self, insnDumpMsg):
		pass

	def handleIdentsMsg(self, identsMsg):
		pass

	def handleAwlSimError(self, exception):
		pass

	def handleDocumentValidationResult(self, exception):
		self.handleAwlSimError(exception)

	def setGuiRunState(self, runState):
		pass

class AwlEditMdiSubWindow(EditMdiSubWindow):
	TYPE		= EditMdiSubWindow.TYPE_AWL
	ONLINE_DIAG	= True

	def __init__(self, mdiArea, source):
		EditMdiSubWindow.__init__(self)

		self.editWidget = EditWidget(self)
		self.editWidget.setSource(source)
		self.editWidget.setSettings(mdiArea._guiSettings)
		self.setWidget(self.editWidget)

		self.editWidget.codeChanged.connect(self.sourceChanged)
		self.editWidget.focusChanged.connect(self.focusChanged)
		self.editWidget.visibleRangeChanged.connect(self.__emitVisibleLinesSignal)
		self.editWidget.undoAvailable.connect(self.undoAvailableChanged)
		self.editWidget.redoAvailable.connect(self.redoAvailableChanged)
		self.editWidget.copyAvailable.connect(self.copyAvailableChanged)
		self.editWidget.copyAvailable.connect(self.cutAvailableChanged)
		self.editWidget.resizeFont.connect(self.resizeFont)
		self.editWidget.validateDocument.connect(
			lambda editWidget: self.validateDocument.emit(0.0))

		self.windowStateChanged.connect(self.__handleWindowStateChange)

		self.updateTitle()

	def sizeHint(self):
		return QSize(600, 500)

	def resizeEvent(self, ev):
		EditMdiSubWindow.resizeEvent(self, ev)
		self.__emitVisibleLinesSignal()

	def __handleWindowStateChange(self, oldState, newState):
		self.__emitVisibleLinesSignal()

	def updateTitle(self):
		title = ""
		source = self.editWidget.getSource()
		if source:
			title = source.name + " (AWL)" +\
				("" if source.enabled else " (DISABLED)")
		self.setWindowTitle(title)
		self.setWindowIcon(getIcon("textsource"))

	def getSource(self):
		return self.editWidget.getSource()

	def setSource(self, source):
		self.editWidget.setSource(source)
		self.updateTitle()
		self.sourceChanged.emit()

	def importSource(self, fileName=None):
		if not fileName:
			fileName, filt = QFileDialog.getOpenFileName(self,
				"Import AWL/STL source", "",
				"AWL source (*.awl);;"
				"All files (*)")
			if not fileName:
				return False
		source = self.getSource().fromFile(name=os.path.basename(fileName),
						   filepath=fileName,
						   compatReEncode=True)
		source.forceNonFileBacked(source.name)
		self.setSource(source)
		return True

	def exportSource(self, fileName=None):
		if not fileName:
			fileName, filt = QFileDialog.getSaveFileName(self,
				"AWL/STL source export", "",
				"AWL/STL source file (*.awl)",
				"*.awl")
			if not fileName:
				return False
			if not fileName.endswith(".awl"):
				fileName += ".awl"
		try:
			safeFileWrite(fileName,
				      self.getSource().compatSourceBytes)
		except AwlSimError as e:
			MessageBox.handleAwlSimError(self,
				"Failed to export source", e)
			return False
		return True

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

	def handleAwlSimError(self, exception):
		self.editWidget.handleValidationResult(exception)

	def enableOnlineDiag(self, enabled):
		self.editWidget.enableCpuStats(enabled)
		if not enabled:
			self.editWidget.resetCpuStats()
		return True

	def getVisibleLineRange(self):
		return self.editWidget.getVisibleLineRange()

	def __emitVisibleLinesSignal(self):
		fromLine, toLine = self.getVisibleLineRange()
		source = self.editWidget.getSource()
		self.visibleLinesChanged.emit(self, source, fromLine, toLine)

	def handleInsnDump(self, insnDumpMsg):
		self.editWidget.updateCpuStats_afterInsn(insnDumpMsg)

	def handleIdentsMsg(self, identsMsg):
		self.editWidget.handleIdentsMsg(identsMsg)

	def setGuiRunState(self, runState):
		if runState is not None:
			self.editWidget.runStateChanged(runState)

class FupEditMdiSubWindow(EditMdiSubWindow):
	TYPE = EditMdiSubWindow.TYPE_FUP

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

		self.fupWidget.diagramChanged.connect(self.sourceChanged)
		self.fupWidget.diagramChanged.connect(self.__handleDiagramChanged)
		self.fupWidget.undoAvailableChanged.connect(self.undoAvailableChanged)
		self.fupWidget.redoAvailableChanged.connect(self.redoAvailableChanged)
		self.fupWidget.clipboardCopyAvailableChanged.connect(self.copyAvailableChanged)
		self.fupWidget.clipboardCutAvailableChanged.connect(self.cutAvailableChanged)
		self.fupWidget.clipboardPasteAvailableChanged.connect(self.pasteAvailableChanged)

		self.updateTitle()

	def sizeHint(self):
		return QSize(1000, 500)

	def updateTitle(self):
		title = ""
		source = self.fupWidget.getSource()
		if source:
			title = source.name + " (FUP)" +\
				("" if source.enabled else " (DISABLED)")
		self.setWindowTitle(title)
		self.setWindowIcon(getIcon("fup"))

	def getSource(self):
		return self.fupWidget.getSource()

	def setSource(self, source):
		self.fupWidget.setSource(source)
		self.updateTitle()
		self.sourceChanged.emit()

	def importSource(self, fileName=None):
		if not fileName:
			fileName, filt = QFileDialog.getOpenFileName(self,
				"Import FUP/FBD XML source", "",
				"FUP/FBD XML source (*.fupxml);;"
				"All files (*)")
			if not fileName:
				return False
		source = self.getSource().fromFile(name=os.path.basename(fileName),
						   filepath=fileName,
						   compatReEncode=True)
		source.forceNonFileBacked(source.name)
		self.setSource(source)
		return True

	def exportSource(self, fileName=None):
		if not fileName:
			fileName, filt = QFileDialog.getSaveFileName(self,
				"fup/fbd xml source export", "",
				"fup/fbd xml source file (*.fupxml)",
				"*.fupxml")
			if not fileName:
				return False
			if not fileName.endswith(".fupxml"):
				fileName += ".fupxml"
		try:
			safeFileWrite(fileName,
				      self.getSource().compatSourceBytes)
		except AwlSimError as e:
			MessageBox.handleAwlSimError(self,
				"Failed to export source", e)
			return False
		return True

	def undoIsAvailable(self):
		return self.fupWidget.undoIsAvailable()

	def undo(self):
		return self.fupWidget.undo()

	def redoIsAvailable(self):
		return self.fupWidget.redoIsAvailable()

	def redo(self):
		return self.fupWidget.redo()

	def cutIsAvailable(self):
		return self.fupWidget.clipboardCutIsAvailable()

	def cut(self):
		return self.fupWidget.clipboardCut()

	def copyIsAvailable(self):
		return self.fupWidget.clipboardCopyIsAvailable()

	def copy(self):
		return self.fupWidget.clipboardCopy()

	def pasteIsAvailable(self):
		return self.fupWidget.clipboardPasteIsAvailable()

	def paste(self, text=None):
		return self.fupWidget.clipboardPaste(text)

	def handleAwlSimError(self, exception):
		self.fupWidget.handleAwlSimError(exception)

	def __handleDiagramChanged(self):
		self.validateDocument.emit(0.5)

class KopEditMdiSubWindow(EditMdiSubWindow):
	TYPE = EditMdiSubWindow.TYPE_KOP

	def __init__(self, mdiArea, source):
		EditMdiSubWindow.__init__(self)

	pass#TODO

class SymTabEditMdiSubWindow(EditMdiSubWindow):
	TYPE = EditMdiSubWindow.TYPE_SYMTAB

	def __init__(self, mdiArea, source):
		EditMdiSubWindow.__init__(self)

		self.symTabView = SymTabView(self)
		self.symTabView.setSymTab(SymbolTable())
		self.symTabView.model().setSource(source)
		self.setWidget(self.symTabView)

		self.symTabView.focusChanged.connect(self.focusChanged)
		self.symTabView.model().sourceChanged.connect(self.sourceChanged)

		self.updateTitle()

	def sizeHint(self):
		return QSize(650, 400)

	def updateTitle(self):
		title = ""
		model = self.symTabView.model()
		if model:
			source = model.getSource()
			if source:
				title = source.name + " (Symbol-table)" +\
					("" if source.enabled else " (DISABLED)")
		self.setWindowTitle(title)
		self.setWindowIcon(getIcon("tag"))

	def getSource(self):
		return self.symTabView.model().getSource()

	def setSource(self, source):
		self.symTabView.model().setSource(source)
		self.updateTitle()
		self.sourceChanged.emit()

	def importSource(self, fileName=None):
		if not fileName:
			fileName, filt = QFileDialog.getOpenFileName(self,
				"Import symbol table", "",
				"Symbol table file (*.asc);;"
				"All files (*)")
			if not fileName:
				return False
		source = self.getSource().fromFile(name=os.path.basename(fileName),
						   filepath=fileName,
						   compatReEncode=True)
		source.forceNonFileBacked(source.name)
		self.setSource(source)
		return True

	def exportSource(self, fileName=None):
		if not fileName:
			fileName, filt = QFileDialog.getSaveFileName(self,
				"symbol table export", "",
				"symbol table file (*.asc)",
				"*.asc")
			if not fileName:
				return False
			if not fileName.endswith(".asc"):
				fileName += ".asc"
		try:
			safeFileWrite(fileName,
				      self.getSource().compatSourceBytes)
		except AwlSimError as e:
			MessageBox.handleAwlSimError(self,
				"Failed to export source", e)
			return False
		return True

class LibSelEditMdiSubWindow(EditMdiSubWindow):
	TYPE = EditMdiSubWindow.TYPE_LIBSEL

	def __init__(self, mdiArea, libSelections):
		EditMdiSubWindow.__init__(self)

		self.libTabView = LibTableView(model=None, parent=self)
		self.libTabView.model().setLibSelections(libSelections)
		self.setWidget(self.libTabView)

		self.libTabView.focusChanged.connect(self.focusChanged)
		self.libTabView.model().contentChanged.connect(self.sourceChanged)

		self.setWindowTitle("Library selections")
		self.setWindowIcon(getIcon("stdlib"))

	def sizeHint(self):
		return QSize(650, 300)

	def getLibSelections(self):
		return self.libTabView.model().getLibSelections()

	def setLibSelections(self, libSelections):
		self.libTabView.model().setLibSelections(libSelections)
		self.sourceChanged.emit()

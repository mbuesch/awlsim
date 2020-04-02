# -*- coding: utf-8 -*-
#
# AWL simulator - GUI utility functions
#
# Copyright 2012-2020 Michael Buesch <m@bues.ch>
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

import sys
from awlsim_loader.common import *

if isPy2Compat:
	printError("ERROR: Python 2.x is not supported by awlsim-gui. "
		   "Please use Python 3.")
	sys.exit(1)

if isPyPy or isJython:
	printError("ERROR: Running awlsim-gui on the PyPy or Jython interpreter is not supported. "
		   "Please use Python 3.")
	sys.exit(1)

from awlsim_loader.coreclient import *
import awlsim_loader.cython_helper as cython_helper
from awlsim.common.monotonic import monotonic_time #+cimport
from awlsim.common.datatypehelpers import * #+cimport
from awlsim.common.profiler import *
from awlsim.core.datatypes import AwlDataType
from awlsim.core.symbolparser import SymbolTable, Symbol, SymTabParser

import traceback
import xml.sax.saxutils as saxutils

if cython_helper.shouldUseCython():
	print("*** Using accelerated CYTHON core "
	      "(AWLSIM_CYTHON environment variable is set)")

from awlsim.gui.qt_bindings import *


AWLSIM_HOME_DOMAIN = "awlsim.de"
AWLSIM_HOME_URL = "https://" + AWLSIM_HOME_DOMAIN


# Convert an integer to a dual-string
def intToDualString(value, bitWidth):
	string = []
	for bitnr in range(bitWidth - 1, -1, -1):
		string.append('1' if ((value >> bitnr) & 1) else '0')
		if bitnr and bitnr % 4 == 0:
			string.append('_')
	return ''.join(string)

# Get the default fixed font
def getDefaultFixedFont(pointSize=11, bold=False):
	font = QFont()
	font.setStyleHint(QFont.Courier)
	font.setFamily("Courier")
	font.setPointSize(pointSize)
	font.setWeight(QFont.Normal)
	font.setBold(bold)
	return font

def sleepWithEventLoop(seconds, excludeInput=True):
	"""Sleep for 'seconds', but run the Qt event loop to refresh the GUI.
	excludeInput: Do not process user input events.
	"""
	end = monotonic_time() + seconds
	eventFlags = QEventLoop.AllEvents
	if excludeInput:
		eventFlags |= QEventLoop.ExcludeUserInputEvents
	while monotonic_time() < end:
		QApplication.processEvents(eventFlags, 10)
		QThread.msleep(10)

# Color used for errors
def getErrorColor():
	return QColor("#FFC0C0")

def handleFatalException(parentWidget=None):
	text = str(traceback.format_exc())
	print("Fatal exception:\n", text)
	text = saxutils.escape(text)
	QMessageBox.critical(parentWidget,
		"A fatal exception occurred",
		"<pre>"
		"A fatal exception occurred:\n\n"
		"%s\n\n"
		"Awlsim will be terminated."
		"</pre>" % text)
	sys.exit(1)


class MessageBox(QDialog):
	def __init__(self,
		     parent,
		     title,
		     text,
		     verboseText=None,
		     icon=QMessageBox.Critical,
		     okButton=True,
		     continueButton=False,
		     cancelButton=False):
		QDialog.__init__(self, parent)
		self.setLayout(QGridLayout())
		self.setWindowTitle(title)

		self.text = "<pre>" + saxutils.escape(text) + "\n</pre>"
		self.verboseText = None
		if verboseText and verboseText.strip() != text.strip():
			self.verboseText = "<pre>" + saxutils.escape(verboseText) + "\n</pre>"

		self.textBox = QLabel(self)
		self.textBox.setTextInteractionFlags(Qt.TextSelectableByMouse |\
						     Qt.TextSelectableByKeyboard |\
						     Qt.LinksAccessibleByMouse |\
						     Qt.LinksAccessibleByKeyboard)
		self.layout().addWidget(self.textBox, 0, 0, 1, 3)

		if self.verboseText:
			self.verboseCheckBox = QCheckBox("Show verbose information", self)
			self.layout().addWidget(self.verboseCheckBox, 1, 0, 1, 3)
		else:
			self.verboseCheckBox = None

		buttonsLayout = QHBoxLayout()
		if okButton:
			self.okButton = QPushButton("&Ok", self)
			buttonsLayout.addWidget(self.okButton)
		if continueButton:
			self.continueButton = QPushButton("C&ontinue", self)
			buttonsLayout.addWidget(self.continueButton)
		if cancelButton:
			self.cancelButton = QPushButton("&Cancel", self)
			buttonsLayout.addWidget(self.cancelButton)
		self.layout().addLayout(buttonsLayout, 2, 1)

		self.__updateText()

		if okButton:
			self.okButton.released.connect(self.accept)
		if continueButton:
			self.continueButton.released.connect(self.accept)
		if cancelButton:
			self.cancelButton.released.connect(self.reject)
		if self.verboseCheckBox:
			self.verboseCheckBox.stateChanged.connect(self.__updateText)

	def __updateText(self):
		if self.verboseCheckBox and\
		   self.verboseCheckBox.checkState() == Qt.Checked:
			self.textBox.setText(self.verboseText)
		else:
			self.textBox.setText(self.text)

	@classmethod
	def error(cls, parent, text, verboseText=None, **kwargs):
		dlg = cls(parent=parent,
			  title="Awlsim - Error",
			  text=text,
			  verboseText=verboseText,
			  icon=QMessageBox.Critical,
			  **kwargs)
		res = dlg.exec_()
		dlg.deleteLater()
		return res

	@classmethod
	def warning(cls, parent, text, verboseText=None, **kwargs):
		dlg = cls(parent=parent,
			  title="Awlsim - Warning",
			  text=text,
			  verboseText=verboseText,
			  icon=QMessageBox.Warning,
			  **kwargs)
		res = dlg.exec_()
		dlg.deleteLater()
		return res

	awlSimErrorBlocked = Blocker()

	@classmethod
	def handleAwlSimError(cls, parent, description, exception, **kwargs):
		if exception.getSeenByUser() or cls.awlSimErrorBlocked:
			return cls.Accepted
		exception.setSeenByUser()
		def maketext(verbose):
			text = "An exception occurred:"
			if description:
				text += "\n"
				text += "  " + description + "."
			text += "\n\n"
			text += exception.getReport(verbose)
			return text
		return cls.error(parent=parent,
				 text=maketext(False),
				 verboseText=maketext(True),
				 **kwargs)

	@classmethod
	def handleAwlParserError(cls, parent, exception, **kwargs):
		return cls.handleAwlSimError(parent=parent,
					     description=None,
					     exception=exception,
					     **kwargs)

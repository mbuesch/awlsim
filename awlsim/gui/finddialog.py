# -*- coding: utf-8 -*-
#
# Find and replace dialog
#
# Copyright 2015 Michael Buesch <m@bues.ch>
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


class FindReplaceDialog(QDialog):
	"""Text find and replace dialog."""

	def __init__(self, textEdit, withReplace=True, parent=None):
		QDialog.__init__(self, parent)
		if withReplace:
			self.setWindowTitle("Find and replace text")
		else:
			self.setWindowTitle("Find text")
		self.setLayout(QGridLayout())

		label = QLabel("Find:", self)
		self.layout().addWidget(label, 0, 0)
		self.findText = QLineEdit(self)
		self.layout().addWidget(self.findText, 0, 1)

		self.regEx = QCheckBox("Regular &expression", self)
		self.layout().addWidget(self.regEx, 1, 1)

		if withReplace:
			label = QLabel("Replace with:", self)
			self.layout().addWidget(label, 2, 0)
			self.replaceText = QLineEdit(self)
			self.layout().addWidget(self.replaceText, 2, 1)

		optsLayout = QHBoxLayout()

		group = QGroupBox(self)
		group.setLayout(QVBoxLayout())
		self.fromCursor = QCheckBox("From &cursor", self)
		self.fromCursor.setCheckState(Qt.Checked)
		group.layout().addWidget(self.fromCursor)
		self.dirUp = QRadioButton("&Up", self)
		group.layout().addWidget(self.dirUp)
		self.dirDown = QRadioButton("&Down", self)
		self.dirDown.setChecked(True)
		group.layout().addWidget(self.dirDown)
		group.layout().addStretch()
		optsLayout.addWidget(group)

		group = QGroupBox(self)
		group.setLayout(QVBoxLayout())
		self.caseSensitive = QCheckBox("Case &sensitive", self)
		group.layout().addWidget(self.caseSensitive)
		self.wholeWords = QCheckBox("&Whole words only", self)
		group.layout().addWidget(self.wholeWords)
		group.layout().addStretch()
		optsLayout.addWidget(group)

		self.layout().addLayout(optsLayout, 3, 0, 1, 2)

		self.statusLabel = QLabel(self)
		self.layout().addWidget(self.statusLabel, 4, 0, 1, 3)

		buttonsLayout = QVBoxLayout()

		self.findButton = QPushButton(self)
		buttonsLayout.addWidget(self.findButton)

		if withReplace:
			self.replaceButton = QPushButton("&Replace", self)
			buttonsLayout.addWidget(self.replaceButton)

			self.replaceAllButton = QPushButton("Replace &all", self)
			buttonsLayout.addWidget(self.replaceAllButton)

		self.closeButton = QPushButton("C&lose", self)
		buttonsLayout.addWidget(self.closeButton)

		buttonsLayout.addStretch()
		self.layout().addLayout(buttonsLayout, 0, 2, 5, 1)

		self.__handleFromCursorChange(self.fromCursor.checkState())
		self.setTextEdit(textEdit)

		self.closeButton.released.connect(self.accept)
		self.findButton.released.connect(self.__handleFind)
		if withReplace:
			self.replaceButton.released.connect(self.__handleReplace)
			self.replaceAllButton.released.connect(self.__handleReplaceAll)
		self.fromCursor.stateChanged.connect(self.__handleFromCursorChange)

	def setTextEdit(self, textEdit):
		self.__textEdit = textEdit
		textCursor = self.__textEdit.textCursor()
		textCursor.clearSelection()
		self.__textEdit.setTextCursor(textCursor)
		self.statusLabel.clear()

	def __handleFind(self):
		self.statusLabel.clear()

		findFlags = QTextDocument.FindFlags()
		if not self.fromCursor.isChecked() and\
		   self.dirUp.isChecked():
			findFlags |= QTextDocument.FindBackward
		if self.caseSensitive.isChecked():
			findFlags |= QTextDocument.FindCaseSensitively
		if self.wholeWords.isChecked():
			findFlags |= QTextDocument.FindWholeWords

		if not self.fromCursor.isChecked():
			# Move the cursor to the start of the document.
			textCursor = self.__textEdit.textCursor()
			textCursor.setPosition(0)
			self.__textEdit.setTextCursor(textCursor)

		found = False
		if self.regEx.isChecked():
			# Find regular expression.
			re = QRegExp(self.findText.text(),
				     Qt.CaseSensitive if self.caseSensitive.isChecked() else\
				     Qt.CaseInsensitive)
			# QPlainTextEdit.find(QRegExp) is >= Qt 5.3.
			# So use the QTextDocument's find instead.
			textCursor = self.__textEdit.document().find(re,
					self.__textEdit.textCursor(), findFlags)
			if not textCursor.isNull():
				self.__textEdit.setTextCursor(textCursor)
				found = True
		else:
			# Find plain text.
			found = self.__textEdit.find(self.findText.text(), findFlags)

		if not found:
			if self.fromCursor.isChecked():
				# The next find should start at the beginning.
				textCursor = self.__textEdit.textCursor()
				textCursor.setPosition(0)
				self.__textEdit.setTextCursor(textCursor)
			self.statusLabel.setText("Reached end of document. "
						 "Text not found.")

	def __handleReplace(self):
		self.statusLabel.clear()
		textCursor = self.__textEdit.textCursor()
		result = False
		if textCursor.hasSelection():
			textCursor.insertText(self.replaceText.text())
			result = True
		self.__handleFind()
		return result

	def __handleReplaceAll(self):
		self.statusLabel.clear()
		count = 0
		while True:
			if self.__handleReplace():
				count += 1
			if not self.__textEdit.textCursor().hasSelection():
				break
		if count == 1:
			self.statusLabel.setText("1 occurrence replaced.")
		elif count > 1:
			self.statusLabel.setText("%d occurrences replaced." % count)
		else:
			self.statusLabel.setText("Reached end of document. "
						 "Text not found.")

	def __handleFromCursorChange(self, state):
		self.dirUp.setEnabled(state == Qt.Checked)
		self.dirDown.setEnabled(state == Qt.Checked)
		self.findButton.setText("&Find next" if state == Qt.Checked else "&Find")

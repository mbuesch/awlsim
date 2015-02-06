# -*- coding: utf-8 -*-
#
# AWL simulator - GUI text value line edit widget
#
# Copyright 2014-2015 Michael Buesch <m@bues.ch>
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


class ValidatorCallback(QValidator):
	def __init__(self, callback, parent=None):
		QValidator.__init__(self, parent)
		self.callback = callback

	def validate(self, inputString, pos):
		state = self.callback(inputString, pos)
		if isPySide:
			return state
		elif isPyQt:
			return (state, inputString, pos)
		assert(0)

class ValueLineEdit(QLineEdit):
	valueChanged = Signal(str)

	def __init__(self, validatorCallback=None, parent=None):
		QLineEdit.__init__(self, parent)

		self.setAlignment(Qt.AlignRight)
		if validatorCallback:
			self.__validatorCallback = validatorCallback
			self.setValidator(ValidatorCallback(self.__validator, self))

		self.__editing = False
		self.__activeText = ""

		self.setReadOnly(True)
		self.__setColors(True)

		self.returnPressed.connect(self.__handleReturnPressed)

	def __setColors(self, validInput):
		pal = self.palette()
		if self.isEnabledTo(None):
			if self.__editing:
				pal.setColor(QPalette.Base, QColor("#FFFFC0"))
			else:
				pal.setColor(QPalette.Base, Qt.white)
		else:
			pal.setColor(QPalette.Base, pal.color(QPalette.Window))
		if validInput:
			pal.setColor(QPalette.Text, Qt.black)
		else:
			pal.setColor(QPalette.Text, Qt.red)
		self.setPalette(pal)

	def changeEvent(self, ev):
		QLineEdit.changeEvent(self, ev)
		if not self.isEnabledTo(None):
			self.__setColors(True)

	def __validator(self, inputString, pos):
		res = self.__validatorCallback(inputString, pos)
		self.__setColors(res == QValidator.Acceptable)
		return res

	def __handleReturnPressed(self):
		if self.__editing:
			self.__editing = False
			self.__setColors(True)
			self.setReadOnly(True)
			self.__activeText = QLineEdit.text(self)
			self.valueChanged.emit(self.__activeText)

	def __cancelEdit(self):
		if self.__editing:
			self.__editing = False
			self.__setColors(True)
			self.setReadOnly(True)
			QLineEdit.setText(self, self.__activeText)

	def focusOutEvent(self, event):
		QLineEdit.focusOutEvent(self, event)
		self.__cancelEdit()

	def mousePressEvent(self, ev):
		QLineEdit.mousePressEvent(self, ev)
		if self.__editing:
			return
		if ev.button() & (Qt.LeftButton |
				  Qt.MidButton |
				  Qt.RightButton):
			self.__editing = True
			self.setReadOnly(False)
			self.__setColors(True)

	def keyPressEvent(self, ev):
		QLineEdit.keyPressEvent(self, ev)
		if ev.key() == Qt.Key_Escape:
			self.__cancelEdit()

	def text(self):
		return self.__activeText

	def setText(self, newText):
		self.__activeText = newText
		if not self.__editing:
			QLineEdit.setText(self, newText)

	def clear(self):
		self.setText("")

# -*- coding: utf-8 -*-
#
# AWL simulator - Generic source code edit widget
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
from awlsim.common.compat import *

from awlsim.gui.util import *


class SourceCodeEdit(QPlainTextEdit):
	def __init__(self, parent=None):
		QPlainTextEdit.__init__(self, parent)

		self.enableAutoIndent()

	def enableAutoIndent(self, enable=True):
		self.__autoIndentEn = enable

	def __getLineIndent(self, cursor):
		cursor.select(QTextCursor.LineUnderCursor)
		line = cursor.selectedText()
		if not line:
			return ""
		# Get the indent-string (that is the whitespace line prefix)
		for i, c in enumerate(line):
			if not c.isspace():
				break
		else:
			i += 1
		return line[:i]

	def __autoIndentHandleNewline(self):
		if not self.__autoIndentEn:
			return
		# Move cursor to previous line and get its indent string.
		cursor = self.textCursor()
		if not cursor.movePosition(QTextCursor.Up,
					   QTextCursor.MoveAnchor, 1):
			return
		indentStr = self.__getLineIndent(cursor)
		# Insert the indent string into the current line
		cursor = self.textCursor()
		cursor.insertText(indentStr)
		self.setTextCursor(cursor)

	def keyPressEvent(self, ev):
		QPlainTextEdit.keyPressEvent(self, ev)

		if ev.key() in (Qt.Key_Return, Qt.Key_Enter):
			self.__autoIndentHandleNewline()

	def pasteText(self, text, seamlessIndent=False):
		if seamlessIndent:
			# Add the current indent to all pasted lines.
			indentStr = self.__getLineIndent(self.textCursor())
			lines = []
			for i, line in enumerate(text.splitlines()):
				if i == 0:
					lines.append(line)
				else:
					lines.append(indentStr + line)
			text = "\n".join(lines)
		self.insertPlainText(text)

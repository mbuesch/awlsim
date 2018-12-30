# -*- coding: utf-8 -*-
#
# AWL simulator - FUP - Undo stack
#
# Copyright 2018 Michael Buesch <m@bues.ch>
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

from awlsim.gui.util import *
from awlsim.common.blocker import *

import datetime


__all__ = [
	"FupUndoStack",
]


class FupFullSourceUndoCommand(QUndoCommand):
	def __init__(self, stack, prevSource, newSource):
		QUndoCommand.__init__(self)
		self.__stack = stack
		self.__prevSource = prevSource
		self.__newSource = newSource
		self.blocked = Blocker()

		text = datetime.datetime.now().strftime(
			"[%Y-%m-%d %H:%M:%S.%f] FUP diagram change")
		self.setText(text)

	def id(self):
		return 0

	def mergeWith(self, other):
		if self.id() != other.id():
			return False
		if self.__prevSource == other.__prevSource and\
		   self.__newSource == other.__newSource:
			# The undo commands are equal. Just drop 'other'.
			return True
		return False

	def __apply(self, source, actionName):
		if self.blocked:
			return
		fupWidget = self.__stack.fupWidget
		try:
			with fupWidget.undoStackBlocked:
				fupWidget.setSource(source,
						    initUndoStack=False)
				self.__stack.setActiveSource(source)
		except AwlSimError as e:
			MessageBox.handleAwlSimError(fupWidget,
				"Failed to %s a FUP/FBD change" % actionName, e)

	def undo(self):
		"""Undo this change.
		"""
		self.__apply(self.__prevSource, "undo")

	def redo(self):
		"""Redo this change.
		"""
		self.__apply(self.__newSource, "redo")

class FupUndoStack(QUndoStack):
	def __init__(self, fupWidget):
		QUndoStack.__init__(self, fupWidget)
		self.fupWidget = fupWidget
		self.__activeSource = None
		self.appendBlocker = Blocker()

	def setActiveSource(self, source):
		"""Set the source that is currently active.
		"""
		# Duplicate the source
		self.__activeSource = source.dup()
		self.__activeSource.userData.clear()

	def initializeStack(self, source):
		"""Initialize the undo stack.
		"""
		self.setActiveSource(source)
		self.clear()

	def appendSourceChange(self, source):
		"""Append a change to the undo stack.
		"""
		# Duplicate the source
		source = source.dup()
		source.userData.clear()

		# Check if the source changed.
		prevSource = self.__activeSource
		if not prevSource:
			self.__activeSource = source
			return
		if source == prevSource:
			# The source did not change.
			return
		self.__activeSource = source

		# Append a full-source undo command
		cmd = FupFullSourceUndoCommand(self,
					       prevSource,
					       source)
		with cmd.blocked:
			self.push(cmd)

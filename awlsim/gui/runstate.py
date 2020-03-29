# -*- coding: utf-8 -*-
#
# AWL simulator - GUI CPU run state
#
# Copyright 2012-2019 Michael Buesch <m@bues.ch>
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


__all__ = [
	"GuiRunState",
]


class GuiRunState(QObject):
	# Signal: Emitted, if the state changed.
	# The parameter is 'self'.
	stateChanged = Signal(QObject)

	EnumGen.start
	STATE_OFFLINE	= EnumGen.item
	STATE_ONLINE	= EnumGen.item
	STATE_LOAD	= EnumGen.item
	STATE_RUN	= EnumGen.item
	STATE_EXCEPTION	= EnumGen.item
	EnumGen.end

	def __init__(self):
		QObject.__init__(self)
		self.state = self.STATE_OFFLINE
		self.setCoreDetails()

	def __emitStateChanged(self):
		self.stateChanged.emit(self)
		QApplication.processEvents(QEventLoop.ExcludeUserInputEvents,
					   50)

	def setState(self, newState):
		if self.state != newState:
			self.state = newState
			self.__emitStateChanged()

	def setCoreDetails(self, spawned=True,
			   host=None, port=None,
			   haveTunnel=False):
		self.spawned = spawned
		self.host = host
		self.port = port
		self.haveTunnel = haveTunnel
		self.__emitStateChanged()

	def __eq__(self, other):
		if isinstance(self, self.__class__):
			if isinstance(other, self.__class__):
				return self.state == other.state
			if isInteger(other):
				return self.state == other
		raise RuntimeError

	def __ne__(self, other):
		return not self.__eq__(other)

	def __ge__(self, other):
		if isinstance(self, self.__class__):
			if isinstance(other, self.__class__):
				return self.state >= other.state
			if isInteger(other):
				return self.state >= other
		raise RuntimeError

	def __lt__(self, other):
		return not self.__ge__(other)

	def __le__(self, other):
		if isinstance(self, self.__class__):
			if isinstance(other, self.__class__):
				return self.state <= other.state
			if isInteger(other):
				return self.state <= other
		raise RuntimeError

	def __gt__(self, other):
		return not self.__le__(other)

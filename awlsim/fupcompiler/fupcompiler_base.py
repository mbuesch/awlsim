# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - Base object
#
# Copyright 2016 Michael Buesch <m@bues.ch>
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

from awlsim.common.util import *
from awlsim.common.exceptions import *


class FupCompilerError(AwlSimError):
	"""FUP compiler exception.
	"""

	def __init__(self, message, fupObj=None):
		AwlSimError.__init__(self, message)
		self.fupObj = fupObj

class FupCompiler_BaseObj(object):
	"""FUP compiler base class.
	"""

	factory = None

	# compileState values
	EnumGen.start
	NOT_COMPILED		= EnumGen.item
	COMPILE_RUNNING		= EnumGen.item
	COMPILE_DONE		= EnumGen.item
	EnumGen.end

	def __init__(self):
		self.__compileState = self.NOT_COMPILED

	@property
	def compileState(self):
		return self.__compileState

	@compileState.setter
	def compileState(self, state):
		if state == self.NOT_COMPILED:
			raise FupCompilerError(
				"Tried to set FBD/FUP object (%s) state to "
				"NOT_COMPILED." % (
				type(self).__name__), self)
		elif state == self.COMPILE_RUNNING:
			if self.__compileState == self.COMPILE_RUNNING:
				raise FupCompilerError(
					"Tried to set FBD/FUP object (%s) state to "
					"COMPILE_RUNNING while already being in that state.\n"
					"This most likely happened due to some dependency "
					"loop in the FBD/FUP diagram." % (
					type(self).__name__), self)
			if self.__compileState == self.COMPILE_DONE:
				raise FupCompilerError(
					"Tried to set FBD/FUP object (%s) state to "
					"COMPILE_RUNNING while being in state COMPILE_DONE." % (
					type(self).__name__), self)
		elif state == self.COMPILE_DONE:
			if self.__compileState == self.COMPILE_DONE:
				raise FupCompilerError(
					"Tried to set FBD/FUP object (%s) state to "
					"COMPILE_DONE while already being in that state." % (
					type(self).__name__), self)
			if self.__compileState == self.NOT_COMPILED:
				raise FupCompilerError(
					"Tried to set FBD/FUP object (%s) state to "
					"COMPILE_DONE, but skipping COMPILE_RUNNING state." % (
					type(self).__name__), self)
		else:
			assert(0)
		self.__compileState = state

	def __eq__(self, other):
		return self is other

	def __ne__(self, other):
		return self is not other

	def __hash__(self):
		return id(self)

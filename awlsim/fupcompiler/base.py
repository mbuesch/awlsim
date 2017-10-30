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
from awlsim.common.enumeration import *
from awlsim.common.exceptions import *


class FupCompilerError(AwlSimError):
	"""FUP compiler exception.
	"""

	def __init__(self, message, fupObj=None):
		if fupObj:
			fupObjStr = str(fupObj).strip()
			if fupObjStr:
				message += "\n\nThe reporting FUP/FBD element is:\n"\
					   "%s" % fupObjStr
		AwlSimError.__init__(self, message)
		self.fupObj = fupObj

class FupInterfError(FupCompilerError):
	"""FUP compiler exception in FUP interface.
	"""

class FupDeclError(FupCompilerError):
	"""FUP compiler exception in FUP declaration.
	"""

class FupGridError(FupCompilerError):
	"""FUP compiler exception in FUP grid.
	"""

class FupConnError(FupCompilerError):
	"""FUP compiler exception in FUP connection.
	"""

class FupElemError(FupCompilerError):
	"""FUP compiler exception in FUP element.
	"""

class FupOperError(FupElemError):
	"""FUP compiler exception in FUP operator.
	"""

class FupCompiler_BaseObj(object):
	"""FUP compiler base class.
	"""

	factory = None

	# compileState values
	EnumGen.start
	COMPILE_IDLE		= EnumGen.item
	COMPILE_PREPROCESSING	= EnumGen.item
	COMPILE_PREPROCESSED	= EnumGen.item
	COMPILE_RUNNING		= EnumGen.item
	COMPILE_DONE		= EnumGen.item
	EnumGen.end

	compileState2name = {
		COMPILE_IDLE		: "COMPILE_IDLE",
		COMPILE_PREPROCESSING	: "COMPILE_PREPROCESSING",
		COMPILE_PREPROCESSED	: "COMPILE_PREPROCESSED",
		COMPILE_RUNNING		: "COMPILE_RUNNING",
		COMPILE_DONE		: "COMPILE_DONE",
	}

	# Set to True, if preprocessing is not used for this object.
	noPreprocessing = False

	# Allow certain state transitions?
	allowTrans_done2Running	= False # DONE -> RUNNING

	__slots__ = (
		"__uuid",
		"__compileState",
	)

	def __init__(self, uuid=None):
		self.__compileState = self.COMPILE_IDLE
		self.uuid = uuid

	@property
	def uuid(self):
		return self.__uuid

	@uuid.setter
	def uuid(self, uuid):
		self.__uuid = uuid or "00000000-0000-0000-0000-000000000000"

	@property
	def isCompileEntryPoint(self):
		"""Return True, if this element is a compilation entry point.
		Override this, if this element (possibly) is an entry point.
		The default implementation returns False.
		"""
		return False

	@property
	def needPreprocess(self):
		return self.__compileState < self.COMPILE_PREPROCESSING

	@property
	def needCompile(self):
		return self.__compileState < self.COMPILE_RUNNING

	@property
	def compileState(self):
		return self.__compileState

	@compileState.setter
	def compileState(self, state):
		if self.noPreprocessing:
			allowedTransitions_IDLE = (self.COMPILE_RUNNING, )
			allowedTransitions_PREPROCESSING = ()
			allowedTransitions_PREPROCESSED = ()
		else:
			allowedTransitions_IDLE = (self.COMPILE_PREPROCESSING, )
			allowedTransitions_PREPROCESSING = (self.COMPILE_PREPROCESSED, )
			allowedTransitions_PREPROCESSED = (self.COMPILE_RUNNING, )
		allowedTransitions_RUNNING = (self.COMPILE_DONE, )
		if self.allowTrans_done2Running:
			allowedTransitions_DONE = (self.COMPILE_RUNNING, )
		else:
			allowedTransitions_DONE = ()
		allowedTransitionsMap = {
			# fromState : (toStates)
			self.COMPILE_IDLE		: allowedTransitions_IDLE,
			self.COMPILE_PREPROCESSING	: allowedTransitions_PREPROCESSING,
			self.COMPILE_PREPROCESSED	: allowedTransitions_PREPROCESSED,
			self.COMPILE_RUNNING		: allowedTransitions_RUNNING,
			self.COMPILE_DONE		: allowedTransitions_DONE,
		}

		allowedTransitions = allowedTransitionsMap[self.__compileState]

		if self.__compileState == state:
			if state == self.COMPILE_RUNNING:
				raise FupCompilerError(
					"Tried to set FUP/FBD element state to "
					"%s while already being in that state.\n"
					"This most likely happened due to some dependency "
					"loop in the FBD/FUP diagram.\n"
					"Please check the diagram for signal loops." % (
					self.compileState2name[state]),
					self)

		if state not in allowedTransitions:
			raise FupCompilerError(
				"The FUP/FBD element compile state transition "
				"from %s to %s is not allowed." % (
				self.compileState2name[self.__compileState],
				self.compileState2name[state]),
				self)

		self.forceCompileState(state)

	def forceCompileState(self, state):
		self.__compileState = state

	def __eq__(self, other):
		return self is other

	def __ne__(self, other):
		return self is not other

	def __hash__(self):
		return id(self)

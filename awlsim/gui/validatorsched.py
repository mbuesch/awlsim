# -*- coding: utf-8 -*-
#
# AWL simulator - GUI code validator scheduling.
#
# Copyright 2017-2020 Michael Buesch <m@bues.ch>
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

from awlsim.common.codevalidator import *

from awlsim.gui.util import *


__all__ = [
	"GuiValidatorSched",
]


class GuiValidatorSched(QObject):
	"""Code validator scheduling.
	"""

	TIMEOUT = AwlValidator.TIMEOUT

	# A new result is available.
	# The parameter may be None: No error occurred.
	# Or an instance of AwlSimError.
	haveValidationResult = Signal(object)

	__singleton = None

	@classmethod
	def get(cls):
		instance = cls.__singleton
		if instance is None:
			cls.__singleton = instance = cls()
		return instance

	def __init__(self):
		QObject.__init__(self)

		self.__project = None

		self.__startTimer = QTimer(self)
		self.__startTimer.setSingleShot(True)
		self.__startTimer.timeout.connect(self.__startAsyncValidation)

		self.__pollTimer = QTimer(self)
		self.__pollTimer.setInterval(100)
		self.__pollTimer.setSingleShot(True)
		self.__pollTimer.timeout.connect(self.__pollValidationResult)

	def startAsyncValidation(self, project, delaySec=0.0):
		"""Start an asynchronous background document validation.
		"""
		printVerbose("Requesting asynchronous validation "
			     "(delay = %.1f s)" % delaySec)
		self.__project = project
		self.__startTimer.start(int(round(delaySec * 1000.0)))

	def __startAsyncValidation(self):
		project, self.__project = self.__project, None
		if project is None:
			return

		# Get the actual project.
		if callable(project):
			project = project()

		if not project.getGuiSettings().getEditorValidationEn():
			return # Validation disabled.

		validator = AwlValidator.get()
		if not validator:
			return
		printVerbose("Starting asynchronous validation.")
		validator.validate(project=project)
		self.__pollTimer.start()

	def __pollValidationResult(self):
		"""Poll the background source code validation result.
		"""
		validator = AwlValidator.get()
		if not validator:
			return
		running, exception = validator.getState()
		if not running:
			printVerbose("Finished asynchronous validation: %s" % (
				     "Not Ok" if exception else "Ok"))
		self.haveValidationResult.emit(exception)
		if running:
			self.__pollTimer.start()

	def syncValidation(self, project):
		"""Start a validation and synchronously wait for it.
		May return None: No error.
		AwlSimError instance: Validation detected an error.
		TIMEOUT: Validation failed due to timeout.
		"""
		validator = AwlValidator.get()
		if not validator:
			return None
		self.__project = None
		self.__startTimer.stop()
		exception = validator.validateSync(project=project,
						   sleepFunc=sleepWithEventLoop)
		if exception is self.TIMEOUT:
			printVerbose("Synchronous validation timeout.")
		else:
			printVerbose("Finished synchronous validation: %s" % (
				     "Not Ok" if exception else "Ok"))
			self.haveValidationResult.emit(exception)

		return exception

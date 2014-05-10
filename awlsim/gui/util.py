# -*- coding: utf-8 -*-
#
# AWL simulator - GUI utility functions
#
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
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
from awlsim.core.compat import *

import sys
from awlsim.core import *
import awlsim.cython_helper

if isPyPy or isJython:
	# PySide does not work on PyPy or Jython, yet.
	printError("Running awlsimgui on the PyPy or Jython interpreter is not supported.")
	printError("Please use CPython 2.7 or CPython 3.x")
	sys.exit(1)

if awlsim.cython_helper.shouldUseCython():
	print("*** Using accelerated CYTHON core "
	      "(AWLSIMCYTHON environment variable is set)")

try:
	from PySide.QtCore import *
	from PySide.QtGui import *
except ImportError as e:
	printError("PLEASE INSTALL PySide (http://www.pyside.org/)")
	input("Press enter to continue.")
	sys.exit(1)

import os
import traceback


def handleFatalException(parentWidget=None):
	QMessageBox.critical(parentWidget,
		"A fatal exception occurred",
		"A fatal exception occurred:\n\n"
		"%s\n\n"
		"Awlsim will be terminated." %\
		(traceback.format_exc(),))
	sys.exit(1)


class MessageBox(QMessageBox):
	def __init__(self, parent, title, text, details=None):
		QMessageBox.__init__(self, parent)

		self.setWindowTitle(title)

		self.setText(text)
		self.setIcon(QMessageBox.Critical)

		if details:
			self.setDetailedText(details)

	@classmethod
	def error(cls, parent, text, details=None):
		return cls(parent, "Awlsim - simulator error",
			   text, details).exec_()

	@classmethod
	def handleAwlSimError(cls, parent, description, exception):
		cpu = exception.getCpu()
		text = "A simulator exception occurred:"
		if description:
			text += "\n"
			text += "    " + description + "."
		text += "\n\n"
		text += "    " + str(exception)
		text += "\n\n"
		insnStr = exception.getFailingInsnStr()
		if insnStr:
			text += "    At statement:\n"
			text += "    AWL/STL line %s:    %s" % (exception.getLineNrStr(),
							    insnStr)
		else:
			text += "    At AWL/STL line %s" % exception.getLineNrStr()
		details = None
		if cpu:
			details = str(exception) + "\n\n" + str(cpu)
		return cls.error(parent, text, details)

	@classmethod
	def handleAwlParserError(cls, parent, exception):
		return cls.handleAwlSimError(parent = parent,
					     description = None,
					     exception = exception)

class StoreRequest(object):
	"""CPU store request buffer."""

	def __init__(self, operator, value, failureCallback=None):
		self.operator = operator
		self.value = value
		self.failureCallback = failureCallback

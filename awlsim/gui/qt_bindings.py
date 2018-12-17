# -*- coding: utf-8 -*-
#
# AWL simulator - QT bindings wrapper
#
# Copyright 2015-2018 Michael Buesch <m@bues.ch>
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

from awlsim.common import *

import sys
import os


def __frameworkError(msg):
	printError("awlsim-gui ERROR: " + msg)
	try:
		if osIsWindows:
			input("Press enter to exit.")
	except (KeyboardInterrupt, Exception) as e:
		pass
	sys.exit(1)

def __testQStringAPI(scope, silent=False):
	# Test for QString v2 API
	if "QString" in scope:
		# QString exists. This is v1 API.
		if silent:
			return False
		__frameworkError("Deprecated QString API detected.\n"
				 "Awlsim does not support PyQt QString v1 API.\n"
				 "---> Please use PySide2 or a newer PyQt5. <---")
	return True

def __autodetectGuiFramework():
	urls = {
		"pyside" : "http://www.pyside.org/",
		"pyqt"   : "http://www.riverbankcomputing.com/software/pyqt/download5",
	}
	with contextlib.suppress(ImportError):
		import PyQt5.QtCore as __pyQtCore
		if __testQStringAPI(dir(__pyQtCore), True):
			return "pyqt5"
	with contextlib.suppress(ImportError):
		import PySide2.QtCore as __pySideCore
		return "pyside2"
	__frameworkError("Neither PySide nor PyQt found.\n"
			 "PLEASE INSTALL PySide2 (%s)\n"
			 "            or PyQt5 (%s)" %\
			 (urls["pyside"],
			  urls["pyqt"]))

# The Qt bindings can be set via AWLSIM_GUI environment variable.
__guiFramework = AwlSimEnv.getGuiFramework()

# Run Qt autodetection
if __guiFramework == "auto":
	__guiFramework = __autodetectGuiFramework()
if __guiFramework == "pyside":
	__guiFramework = "pyside2"
if __guiFramework == "pyqt":
	__guiFramework = "pyqt5"

# Load the Qt modules
if __guiFramework == "pyside2":
	try:
		from PySide2.QtCore import *
		from PySide2.QtGui import *
		from PySide2.QtWidgets import *
	except ImportError as e:
		__frameworkError("Failed to import PySide2 modules:\n" + str(e))
elif __guiFramework == "pyqt5":
	try:
		from PyQt5.QtCore import *
		from PyQt5.QtGui import *
		from PyQt5.QtWidgets import *
	except ImportError as e:
		__frameworkError("Failed to import PyQt5 modules:\n" + str(e))
	__testQStringAPI(globals())
else:
	__frameworkError("Unknown GUI framework '%s' requested.\n"
			 "Please fix the AWLSIM_GUI environment variable." %\
			 __guiFramework)

def getGuiFrameworkName():
	return __guiFramework

# Helpers for distinction between PySide and PyQt API.
isPySide = __guiFramework.startswith("pyside")
isPyQt = __guiFramework.startswith("pyqt")

if isPyQt:
	Signal = pyqtSignal

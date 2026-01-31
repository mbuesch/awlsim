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

def __autodetectGuiFramework():
	urls = {
		"pyside" : "https://wiki.qt.io/Qt_for_Python",
		"pyqt"   : "https://www.riverbankcomputing.com/software/pyqt/",
	}
	with contextlib.suppress(ImportError):
		import PyQt6.QtCore as __pyQtCore
		return "pyqt6"
	with contextlib.suppress(ImportError):
		import PySide6.QtCore as __pySideCore
		return "pyside6"
	__frameworkError("Neither PySide6 nor PyQt6 found.\n"
			 "PLEASE INSTALL PySide6 (%s)\n"
			 "            or PyQt6 (%s)" %\
			 (urls["pyside"],
			  urls["pyqt"]))

# The Qt bindings can be set via AWLSIM_GUI environment variable.
__guiFramework = AwlSimEnv.getGuiFramework()

# Run Qt autodetection
if __guiFramework == "auto":
	__guiFramework = __autodetectGuiFramework()
if __guiFramework == "pyside":
	__guiFramework = "pyside6"
if __guiFramework == "pyqt":
	__guiFramework = "pyqt6"

# Load the Qt modules
if __guiFramework == "pyside6":
	try:
		from PySide6.QtCore import *
		from PySide6.QtGui import *
		from PySide6.QtWidgets import *
	except ImportError as e:
		__frameworkError("Failed to import PySide6 modules:\n" + str(e))
elif __guiFramework == "pyqt6":
	try:
		from PyQt6.QtCore import *
		from PyQt6.QtGui import *
		from PyQt6.QtWidgets import *
	except ImportError as e:
		__frameworkError("Failed to import PyQt6 modules:\n" + str(e))
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

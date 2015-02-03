#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# AWL simulator - GUI
#
# Copyright 2012-2015 Michael Buesch <m@bues.ch>
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

# Initialize multiprocessing freeze support.
# This must be at the very beginning.
import multiprocessing
multiprocessing.freeze_support()

# Initialize code validator.
# This must be done before expensive modules are imported
# for memory efficiency reasons. (The validator forks).
from awlsim.common.codevalidator import *
AwlValidator.startup()

# Import awlsim modules (compat first)
from awlsim.common.compat import *
from awlsim.common import *
from awlsim.gui.mainwindow import *

import getopt


def usage():
	print("awlsim-gui version %s" % VERSION_STRING)
	print("")
	print("Usage: awlsim-gui [OPTIONS] [PROJECT.awlpro]")
	print("")
	print("Options:")
	print(" -h|--help             Print this help text")
	print("")
	print("Environment variables:")
	print(" AWLSIMGUI             Select the GUI framework (default 'auto')")
	print("                       Can be either of:")
	print("                       auto: Autodetect")
	print("                       pyside: Use PySide 4")
	print("                       pyqt4: Use PyQt 4")
	print("                       pyqt5: Use PyQt 5")

qapp = QApplication(sys.argv)

opt_awlSource = None

try:
	(opts, args) = getopt.getopt(sys.argv[1:],
		"h",
		[ "help", ])
except getopt.GetoptError as e:
	printError(str(e))
	usage()
	sys.exit(1)
for (o, v) in opts:
	if o in ("-h", "--help"):
		usage()
		sys.exit(0)
if args:
	if len(args) == 1:
		opt_awlSource = args[0]
	else:
		usage()
		sys.exit(1)

mainwnd = MainWindow.start(initialAwlSource = opt_awlSource)
res = qapp.exec_()
AwlValidator.get().shutdown()
sys.exit(res)

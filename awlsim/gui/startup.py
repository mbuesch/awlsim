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

# Import awlsim modules (compat first)
from awlsim.common.compat import *
from awlsim.common import *
from awlsim.common.codevalidator import *
from awlsim.gui.mainwindow import *

import getopt


def usage():
	print("awlsim-gui version %s" % VERSION_STRING)
	print("")
	print("Usage: awlsim-gui [OPTIONS] [PROJECT.awlpro]")
	print("")
	print("Options:")
	print(" -h|--help             Print this help text")
	print(" -L|--loglevel LVL     Set the log level:")
	print("                       0: Log nothing")
	print("                       1: Log errors")
	print("                       2: Log errors and warnings")
	print("                       3: Log errors, warnings and info messages (default)")
	print("                       4: Verbose logging")
	print("                       5: Extremely verbose logging")
	print("")
	print("Environment variables:")
	print(" AWLSIM_GUI            Select the GUI framework (default 'auto')")
	print("                       Can be either of:")
	print("                       auto: Autodetect")
	print("                       pyside: Use PySide 4")
	print("                       pyqt4: Use PyQt 4")
	print("                       pyqt5: Use PyQt 5")

qapp = QApplication(sys.argv)

opt_awlSource = None
opt_loglevel = Logging.LOG_INFO

try:
	(opts, args) = getopt.getopt(sys.argv[1:],
		"hL:",
		[ "help", "loglevel=", ])
except getopt.GetoptError as e:
	printError(str(e))
	usage()
	sys.exit(ExitCodes.EXIT_ERR_CMDLINE)
for (o, v) in opts:
	if o in ("-h", "--help"):
		usage()
		sys.exit(ExitCodes.EXIT_OK)
	if o in ("-L", "--loglevel"):
		try:
			opt_loglevel = int(v)
		except ValueError:
			printError("-L|--loglevel: Invalid log level")
			sys.exit(ExitCodes.EXIT_ERR_CMDLINE)
if args:
	if len(args) == 1:
		opt_awlSource = args[0]
	else:
		usage()
		sys.exit(ExitCodes.EXIT_ERR_CMDLINE)

Logging.setPrefix("awlsim-gui: ")
Logging.setLoglevel(opt_loglevel)

mainwnd = MainWindow.start(initialAwlSource = opt_awlSource)
QToolTip.setFont(getDefaultFixedFont())
res = qapp.exec_()
AwlValidator.shutdown()
sys.exit(res)

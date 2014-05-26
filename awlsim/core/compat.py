# -*- coding: utf-8 -*-
#
# AWL simulator - utility functions
#
# Copyright 2012-2014 Michael Buesch <m@bues.ch>
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


# isPyPy is True, if the interpreter is PyPy.
isPyPy = "PyPy" in sys.version

# isJython is True, if the interpreter is Jython.
isJython = sys.platform.lower().startswith("java")

# isIronPython is True, if the interpreter is IronPython
isIronPython = "IronPython" in sys.version

# isPy3Compat is True, if the interpreter is Python 3 compatible.
isPy3Compat = sys.version_info[0] == 3

# isPy2Compat is True, if the interpreter is Python 2 compatible.
isPy2Compat = sys.version_info[0] == 2

# Python 2/3 helper selection
def py23(py2, py3):
	if isPy3Compat:
		return py3
	if isPy2Compat:
		return py2
	raise Exception("Failed to detect Python version")

# input() compatibility.
# Force Python3 behavior
if isPy2Compat:
	input = raw_input

# range() compatibility.
# Force Python3 behavior
if isPy2Compat:
	range = xrange

# Compat wrapper for monotonic time
import time
monotonic_time = getattr(time, "monotonic", time.clock)

# BlockingIOError dummy
try:
	BlockingIOError
except NameError:
	class BlockingIOError(object): pass

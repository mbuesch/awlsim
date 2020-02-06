# -*- coding: utf-8 -*-
#
# AWL simulator - Python library importer
#
# Copyright 2014-2018 Michael Buesch <m@bues.ch>
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

from awlsim.common.exceptions import *


__all__ = [
	"importModule",
]


def importModule(moduleName):
	"""Import a module with the name string 'moduleName'.
	Returns the module object.
	May raise importError."""

	import awlsim_loader.cython_helper as cython_helper
	if isMicroPython:
		importlib = None
	else:
		try:
			import importlib
		except ImportError as e: #@nocov
			importlib = None

	# If we are running in cython module,
	# translate the moduleName to its cython name.
#@cy	moduleName = cython_helper.cythonModuleName(moduleName)

	if importlib:
		mod = importlib.import_module(moduleName)
	else:
		mod = __import__(moduleName) #@nocov

	return mod

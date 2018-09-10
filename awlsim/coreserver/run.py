#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# AWL simulator - PLC core server
#
# Copyright 2013-2018 Michael Buesch <m@bues.ch>
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

if __name__ == "__main__":
	import awlsim_loader.coverage_helper
	import awlsim_loader.cython_helper as __cython
	import sys

	__modname = "awlsim.coreserver.server"
	__mod = None

	if __cython.shouldUseCython(__modname):
		__cymodname = __cython.cythonModuleName(__modname)
		try:
			exec("import %s as __mod" % __cymodname)
		except ImportError as e:
			__cython.cythonImportError(__cymodname, str(e))
	if not __cython.shouldUseCython(__modname):
		exec("import %s as __mod" % __modname)

	if __mod:
		sys.exit(__mod.AwlSimServer._execute())
	sys.exit(1)

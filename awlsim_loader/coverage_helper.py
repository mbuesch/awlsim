# -*- coding: utf-8 -*-
#
# AWL simulator - Code coverage tracing support
#
# Copyright 2018 Michael Buesch <m@bues.ch>
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

try:
	import coverage as coverage_mod
except ImportError as e:
	coverage_mod = None
import os
import sys
import atexit


__all__ = [ ]


coverageInstance = None


def coverageError(msg):
	if sys.stderr:
		sys.stderr.write(msg + "\n")
		sys.stderr.flush()

def coverageTryStart():
	global coverageInstance

	covPath = os.getenv("AWLSIM_COVERAGE", "")
	if covPath:
		if not coverage_mod:
			coverageError("Code coverage tracing is requested "
				"(AWLSIM_COVERAGE), but the Python 'coverage' "
				"module was not found. "
				"Please install Python 'coverage'.")
			return
		if not coverageInstance:
			atexit.register(coverageStop)
			try:
				omit = [
					"/usr/*",
					"awlsim-test",
					"awlsim/gui/*",
					"awlsim_loader/*",
					"libs/*",
					"submodules/*",
					"tests/*",
				]
				kwargs = {
					"data_file"		: covPath,
					"auto_data"		: True,
					"branch"		: False,
					"check_preimported"	: True,
					"config_file"		: False,
					"omit"			: omit,
				}
				for remove in ("", "check_preimported"):
					if remove:
						kwargs.pop(remove)
					try:
						coverageInstance = coverage_mod.Coverage(**kwargs)
						break
					except TypeError:
						pass
				else:
					coverageError("Failed to initialize code "
						"coverage tracing. It is unknown how to "
						"instantiate Coverage correctly.")
					sys.exit(1)
				coverageInstance.start()
			except coverage_mod.misc.CoverageException as e:
				coverageError("Coverage tracing exception: " + str(e))
				sys.exit(1)

def coverageStop():
	global coverageInstance

	if coverageInstance:
		try:
			coverageInstance.stop()
		except coverage_mod.misc.CoverageException as e:
			coverageError("Coverage tracing exception: " + str(e))
			sys.exit(1)
		finally:
			coverageInstance = None

coverageTryStart()

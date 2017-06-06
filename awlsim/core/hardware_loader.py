# -*- coding: utf-8 -*-
#
# AWL simulator - Hardware module loader
#
# Copyright 2013-2017 Michael Buesch <m@bues.ch>
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
from awlsim.common.compat import *

from awlsim.common.dynamic_import import *
from awlsim.common.util import *
from awlsim.common.exceptions import *


__all__ = [ "HwModLoader", ]


class HwModLoader(object):
	"""Awlsim hardware module loader.
	"""

	# Tuple of built-in awlsim hardware modules.
	builtinHwModules = (
		"debug",
		"dummy",
		"linuxcnc",
		"pyprofibus",
		"rpigpio",
	)

	def __init__(self, name, importName, mod):
		self.name = name
		self.importName = importName
		self.mod = mod

	@classmethod
	def loadModule(cls, name):
		"""Load a hardware module."""

		# Module name sanity check
		try:
			if not name.strip():
				raise ValueError
			for c in name:
				if not isalnum(c) and c != "_":
					raise ValueError
		except ValueError:
			raise AwlSimError("Hardware module name '%s' "
				"is invalid." % name)

		# Create import name (add prefix)
		importName = name
		prefix = "awlsimhw_"
		if importName.lower().startswith(prefix) and\
		   not importName.startswith(prefix):
			raise AwlSimError("Hardware module name: '%s' "
				"prefix of '%s' must be all-lower-case." %\
				(prefix, name))
		if not importName.startswith(prefix):
			importName = prefix + importName

		# Try to import the module
		try:
			mod = importModule(importName)
		except ImportError as e:
			raise AwlSimError("Failed to import hardware interface "
				"module '%s' (import name '%s'): %s" %\
				(name, importName, str(e)))
		return cls(name, importName, mod)

	def getInterface(self):
		"""Get the HardwareInterface class."""

		hwClassName = "HardwareInterface"
		hwClass = getattr(self.mod, hwClassName, None)
		if not hwClass:
			raise AwlSimError("Hardware module '%s' (import name '%s') "
				"does not have a '%s' class." %\
				(self.name, self.importName, hwClassName))
		return hwClass

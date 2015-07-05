# -*- coding: utf-8 -*-
#
# AWL simulator - Hardware module descriptors
#
# Copyright 2014-2015 Michael Buesch <m@bues.ch>
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

from awlsim.common.util import *


class HwmodDescriptor(object):
	"""Hardware module descriptor."""

	def __init__(self, moduleName, parameters = None):
		"""Hardware module descriptor initialization.
		moduleName -> module name string
		parameters -> parameter dict with
				keys -> parameter name
				values -> parameter value
		"""
		self.setModuleName(moduleName)
		self.setParameters(parameters)

	def dup(self):
		"""Duplicate this descriptor.
		"""
		return HwmodDescriptor(self.getModuleName(),
				       dict(self.getParameters()))

	def setModuleName(self, moduleName):
		"""Set the module name string.
		"""
		self.moduleName = moduleName

	def getModuleName(self):
		"""Get the module name string.
		"""
		return self.moduleName

	def setParameters(self, parameters):
		"""Set the parameters dict.
		"""
		if not parameters:
			parameters = {}
		self.parameters = parameters

	def addParameter(self, name, value):
		"""Add a parameter to the parameter dict.
		"""
		self.setParameterValue(name, value)

	def setParameterValue(self, name, value):
		"""Set the value of a parameter.
		"""
		self.parameters[name] = value

	def removeParameter(self, name):
		"""Remove a parameter from the parameter dict.
		"""
		self.parameters.pop(name, None)

	def getParameters(self):
		"""Get the parameters dict (reference).
		"""
		return self.parameters

	def getParameter(self, name):
		"""Get one parameter by name.
		"""
		return self.parameters.get(name)

#TODO hash

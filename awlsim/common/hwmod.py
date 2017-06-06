# -*- coding: utf-8 -*-
#
# AWL simulator - Hardware module descriptors
#
# Copyright 2014-2017 Michael Buesch <m@bues.ch>
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

from awlsim.common.xmlfactory import *
from awlsim.common.util import *
from awlsim.common.exceptions import *

import hashlib
import binascii


__all__ = [
	"HwmodDescriptorFactory",
	"HwmodDescriptor",
]


class HwmodDescriptorFactory(XmlFactory):
	def parser_open(self, tag=None):
		hwmodDesc = self.hwmodDesc
		self.inParams = False
		self.inOneParam = False
		if tag:
			name = tag.getAttr("name")
			hwmodDesc.setModuleName(name)
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		hwmodDesc = self.hwmodDesc
		if self.inParams:
			if not self.inOneParam:
				if tag.name == "param":
					name = tag.getAttr("name")
					value = tag.getAttr("value", "")
					hwmodDesc.addParameter(name, value)
					self.inOneParam = True
					return
		else:
			if tag.name == "params":
				hwmodDesc.setParameters([])
				self.inParams = True
				return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if self.inParams:
			if self.inOneParam:
				if tag.name == "param":
					self.inOneParam = False
					return
			else:
				if tag.name == "params":
					self.inParams = False
					return
		else:
			if tag.name == "module":
				self.parser_finish()
				return
		XmlFactory.parser_endTag(self, tag)

	def composer_getTags(self):
		hwmodDesc = self.hwmodDesc

		childTags = []

		hwmodParams = sorted(dictItems(hwmodDesc.getParameters()),
				     key = lambda p: p[0])
		paramsTags = []
		for modParamName, modParamValue in hwmodParams:
			if modParamValue is None:
				modParamValue = ""
			paramsTags.append(self.Tag(name="param",
						   attrs={
				"name"	: str(modParamName),
				"value"	: str(modParamValue),
			}))
		childTags.append(self.Tag(name="params",
					  tags=paramsTags))

		tags = [self.Tag(name="module",
				 comment="\nLoaded hardware module",
				 tags=childTags,
				 attrs={
					"name"	: str(hwmodDesc.getModuleName()),
		})]
		return tags

class HwmodDescriptor(object):
	"""Hardware module descriptor."""

	factory = HwmodDescriptorFactory

	IDENT_HASH	= hashlib.sha256

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
		self.__identHash = None

	def getModuleName(self):
		"""Get the module name string.
		"""
		return self.moduleName

	def setParameters(self, parameters):
		"""Set the parameters dict.
		"""
		if not parameters:
			parameters = {}
		self.parameters = {}
		for name, value in dictItems(parameters):
			self.addParameter(name, value)
		self.__identHash = None

	def addParameter(self, name, value):
		"""Add a parameter to the parameter dict.
		"""
		self.setParameterValue(name, value)

	def setParameterValue(self, name, value):
		"""Set the value of a parameter.
		"""
		self.parameters[name] = value or ""
		self.__identHash = None

	def removeParameter(self, name):
		"""Remove a parameter from the parameter dict.
		"""
		self.parameters.pop(name, None)
		self.__identHash = None

	def getParameters(self):
		"""Get the parameters dict (reference).
		"""
		return self.parameters

	def getParameter(self, name):
		"""Get one parameter by name.
		"""
		return self.parameters.get(name)

	def getIdentHash(self):
		"""Get the unique identification hash for this
		hardware module descriptor.
		"""
		if not self.__identHash:
			# Calculate the ident hash
			h = self.IDENT_HASH(b"HwmodDescriptor")
			h.update(self.moduleName.encode("utf-8", "ignore"))
			for pName, pValue in sorted(dictItems(self.parameters),
						    key = lambda item: item[0]):
				h.update(pName.encode("utf-8", "ignore"))
				h.update(pValue.encode("utf-8", "ignore"))
			self.__identHash = h.digest()
		return self.__identHash

	def getIdentHashStr(self):
		return binascii.b2a_hex(self.getIdentHash()).decode("ascii")

	def __eq__(self, other):
		return self.getIdentHash() == other.getIdentHash()

	def __ne__(self, other):
		return not self.__eq__(other)

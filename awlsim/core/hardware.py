# -*- coding: utf-8 -*-
#
# AWL simulator - Abstract hardware interface
#
# Copyright 2013-2016 Michael Buesch <m@bues.ch>
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

from awlsim.core.util import AwlSimError


class HwParamDesc(object):
	"""Abstract hardware parameter descriptor."""

	class ParseError(Exception):
		pass

	typeStr = "<NoType>"
	userEditable = True
	defaultValue = None

	def __init__(self, name, description="", mandatory=False):
		self.name = name
		self.description = description
		self.mandatory = mandatory

	def parse(self, value):
		"""Parse a value string.
		This must be overridden.
		"""
		raise NotImplementedError

	def match(self, matchName):
		"""Match a name string.
		The default implementation just compares the string to self.name.
		The parameter must not be 'mandatory', if this method is overridden.
		"""
		return self.name == matchName

class HwParamDesc_pyobject(HwParamDesc):
	"""Generic object parameter descriptor."""

	typeStr = "PyObject"
	userEditable = False

	def __init__(self, name, description="", mandatory=False):
		HwParamDesc.__init__(self, name, description, mandatory)

	def parse(self, value):
		return value

class HwParamDesc_str(HwParamDesc):
	"""String hardware parameter descriptor."""

	typeStr = "string"

	def __init__(self, name, defaultValue="", description="", mandatory=False):
		HwParamDesc.__init__(self, name, description, mandatory)
		self.defaultValue = defaultValue

	def parse(self, value):
		return value

class HwParamDesc_int(HwParamDesc):
	"""Integer hardware parameter descriptor."""

	typeStr = "integer"

	def __init__(self, name,
		     defaultValue=0, minValue=None, maxValue=None,
		     description="", mandatory=False):
		HwParamDesc.__init__(self, name, description, mandatory)
		self.defaultValue = defaultValue
		self.minValue = minValue
		self.maxValue = maxValue

	def parse(self, value):
		try:
			value = int(value)
		except ValueError:
			raise self.ParseError("Value '%s' is not a valid integer." %\
					      str(value))
		if self.minValue is not None:
			if value < self.minValue:
				raise self.ParseError("Value '%d' is too small." % value)
		if self.maxValue is not None:
			if value > self.maxValue:
				raise self.ParseError("Value '%d' is too big." % value)
		return value

class HwParamDesc_bool(HwParamDesc):
	"""Boolean hardware parameter descriptor."""

	typeStr = "boolean"

	def __init__(self, name, defaultValue=False,
		     description="", mandatory=False):
		HwParamDesc.__init__(self, name, description, mandatory)
		self.defaultValue = defaultValue

	def parse(self, value):
		value = value.strip()
		if value.lower() in ("true", "yes", "on"):
			return True
		if value.lower() in ("false", "no", "off"):
			return False
		try:
			value = int(value, 10)
		except ValueError:
			raise self.ParseError("Value '%s' is not a valid boolean." %\
				str(value))
		return bool(value)

class AbstractHardwareInterface(object):
	"""Abstract hardware interface class.
	This class must be subclassed in the hardware interface module.
	The subclass must be named 'HardwareInterface' for the automatic loading
	mechanism to work."""

	# The name of the module. Overload in the subclass.
	name = "<unnamed>"

	# The parameter descriptors.
	paramDescs = []
	# The standard parameters.
	__standardParamDescs = [
		HwParamDesc_bool("removeOnReset",
				 defaultValue = True,
				 description = "If set to 'True' the module will "
					       "be removed on CPU reset."),
		HwParamDesc_int("inputAddressBase",
				defaultValue = 0, minValue = 0,
				description = "Start address in input address range"),
		HwParamDesc_int("outputAddressBase",
				defaultValue = 0, minValue = 0,
				description = "Start address in output address range"),
	]

	@classmethod
	def getParamDescs(cls):
		"""Get all parameter descriptors for this class."""
		descs = cls.__standardParamDescs[:]
		descs.extend(cls.paramDescs)
		return descs

	@classmethod
	def getParamDesc(cls, paramName):
		"""Get one parameter descriptor."""
		for desc in cls.getParamDescs():
			if desc.match(paramName):
				return desc
		return None

	@classmethod
	def getModuleInfo(cls):
		"""Get module information. Returns a string."""
		ret = []
		ret.append("Hardware module '%s':" % cls.name)
		ret.append("")
		ret.append("Parameters:")
		for desc in cls.getParamDescs():
			if desc.mandatory:
				defStr = "mandatory"
			else:
				defStr = "default: %s" % str(getattr(desc, "defaultValue", None))
			ret.append(" %s = %s (%s)%s" %\
				(desc.name, desc.typeStr.upper(),
				 defStr,
				 ("  -  " + desc.description) if desc.description else ""))
		return "\n".join(ret)

	def __init__(self, sim, parameters={}):
		"""Constructs the abstract hardware interface.
		'sim' is the AwlSim instance.
		'parameters' is a dict of hardware specific parameters."""
		self.sim = sim
		self.__running = False
		self.__parseParameters(parameters)

		# Get the base addresses for convenience.
		self.inputAddressBase = self.getParamValueByName("inputAddressBase")
		self.outputAddressBase = self.getParamValueByName("outputAddressBase")

	def startup(self):
		"""Initialize access to the hardware."""
		if not self.__running:
			self.doStartup()
			self.__running = True

	def doStartup(self):
		"""Actually initialize access to hardware.
		Overload this method, if the hardware needs initialization"""
		pass

	def shutdown(self):
		"""Shutdown access to the hardware."""
		if self.__running:
			self.__running = False
			self.doShutdown()

	def doShutdown(self):
		"""Actually shutdown access to hardware.
		Overload this method, if the hardware needs initialization"""
		pass

	def readInputs(self):
		"""Read all hardware input data and store it in the PAE.
		The implementation is supposed to put the data directly
		into the cpu memory.
		Overload this method, if the hardware has inputs."""
		pass

	def writeOutputs(self):
		"""Write all hardware output data (read from PAA).
		The implementation is supposed to read the data directly
		from the cpu memory.
		Overload this method, if the hardware has outputs."""
		pass

	def directReadInput(self, accessWidth, accessOffset):
		"""Direct peripheral input data read operation.
		'accessWidth' is the width of the access, in bits.
		'accessOffset' is the byte offset of the access.
		The read data is returned.
		'None' is returned if the 'accessOffset' is not in
		this hardware's range.
		Overload this method, if the hardware has inputs and
		supports direct peripheral access."""
		return None

	def directWriteOutput(self, accessWidth, accessOffset, data):
		"""Direct peripheral output data write operation.
		'accessWidth' is the width of the access, in bits.
		'accessOffset' is the byte offset of the access.
		'data' is the data to write.
		True is returned, if the hardware successfully stored the value.
		False is returned, if the 'accessOffset' is not in this
		hardware's range.
		Overload this method, if the hardware has outputs and
		supports direct peripheral access."""
		return False

	def __repr__(self):
		return "HardwareInterface: %s" % self.name

	def raiseException(self, errorText):
		"""Throw an exception."""
		raise AwlSimError("['%s' hardware module] %s" %\
				  (self.name, errorText))

	def paramErrorHandler(self, name, errorText):
		"""Default parameter error handler."""
		self.raiseException("Parameter '%s': %s" % (name, errorText))

	def __parseParameters(self, parameters):
		# Parse the parameters.
		self.__paramsByName = {}
		self.__paramsByDescType = {}
		for name, value in dictItems(parameters):
			for desc in self.getParamDescs():
				if desc.match(name):
					break
			else:
				self.paramErrorHandler(name,
					"Invalid parameter. The parameter '%s' is "
					"unknown to the '%s' hardware module." %\
					(name, self.name))
			try:
				parsedValue = desc.parse(value)
			except HwParamDesc.ParseError as e:
				self.paramErrorHandler(name, str(e))
			self.__paramsByName[name] = parsedValue
			self.__paramsByDescType.setdefault(type(desc), []).append(
					(name, parsedValue))

		# Check mandatory parameters
		for desc in self.getParamDescs():
			if not desc.mandatory:
				continue
			if desc.name not in dictKeys(self.__paramsByName):
				self.paramErrorHandler(desc.name,
					"Mandatory parameter not specified")

	def getParamValueByName(self, name):
		"""This is the main method to get a parameter value by name
		from the hardware module.
		'name' is the name string of the parameter.
		"""

		descs = [ d for d in self.getParamDescs() if d.match(name) ]
		# Programming error, if getParamValueByName() was called with a name
		# that was not declared in paramDescs.
		assert(descs)

		# Get the value.
		try:
			return self.__paramsByName[name]
		except KeyError:
			return getattr(descs[0], "defaultValue", None)

	getParam = getParamValueByName # Old deprecated getParam() API

	def getParamsByDescType(self, descType):
		"""This is the main method to get parameter name/value pairs
		for a given param desc type.
		This returns a list of (name, value) tuples.
		"""
		try:
			return self.__paramsByDescType[descType]
		except KeyError:
			return []

class HwModLoader(object):
	"""Awlsim hardware module loader."""

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

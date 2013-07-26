# -*- coding: utf-8 -*-
#
# AWL simulator - Abstract hardware interface
#
# Copyright 2013 Michael Buesch <m@bues.ch>
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

from awlsim.util import AwlSimError


class HwParamDesc(object):
	"""Abstract hardware parameter descriptor."""

	class ParseError(Exception):
		pass

	def __init__(self, name):
		self.name = name

	def parse(self, value):
		raise NotImplementedError

class HwParamDesc_str(HwParamDesc):
	"""String hardware parameter descriptor."""

	def __init__(self, name, defaultValue=""):
		HwParamDesc.__init__(self, name)
		self.defaultValue = defaultValue

	def parse(self, value):
		return value

class HwParamDesc_int(HwParamDesc):
	"""Integer hardware parameter descriptor."""

	def __init__(self, name,
		     defaultValue=0, minValue=None, maxValue=None):
		HwParamDesc.__init__(self, name)
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

	def __init__(self, name, defaultValue=False):
		HwParamDesc.__init__(self, name)
		self.defaultValue = defaultValue

	def parse(self, value):
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
		HwParamDesc_int("inputAddressBase",
				defaultValue = 0, minValue = 0),
		HwParamDesc_int("outputAddressBase",
				defaultValue = 0, minValue = 0),
	]

	@classmethod
	def getParamDescs(cls):
		"""Get all parameter descriptors for this class."""
		descs = cls.__standardParamDescs[:]
		descs.extend(cls.paramDescs)
		return descs

	def __init__(self, sim, parameters={}):
		"""Constructs the abstract hardware interface.
		'sim' is the AwlSim instance.
		'parameters' is a dict of hardware specific parameters."""
		self.sim = sim
		self.__running = False
		self.__parseParameters(parameters)

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
		raise AwlSimError("[%s hardware module] %s" %\
				  (self.name, errorText))

	def paramErrorHandler(self, name, errorText):
		"""Default parameter error handler."""
		self.raiseException("Parameter '%s': %s" % (name, errorText))

	def __getParamDescFor(self, name):
		return [d for d in self.getParamDescs() if d.name == name][0]

	def __parseParameters(self, parameters):
		self.__parameters = {}
		for name, value in parameters.items():
			try:
				desc = self.__getParamDescFor(name)
			except IndexError:
				self.paramErrorHandler(name, "Invalid parameter")
			try:
				self.__parameters[name] = desc.parse(value)
			except HwParamDesc.ParseError as e:
				self.paramErrorHandler(name, str(e))

	def getParam(self, name):
		desc = self.__getParamDescFor(name)
		try:
			return self.__parameters[name]
		except KeyError:
			return desc.defaultValue

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


class AbstractHardwareInterface(object):
	"""Abstract hardware interface class.
	This class must be subclassed in the hardware interface module.
	The subclass must be named 'HardwareInterface' for the automatic loading
	mechanism to work."""

	# The name of the module. Overload in the subclass.
	name = "<unnamed>"

	def __init__(self, sim, parameters={}):
		"""Constructs the abstract hardware interface.
		'sim' is the AwlSim instance.
		'parameters' is a dict of hardware specific parameters."""
		self.sim = sim
		self.parameters = parameters
		self.__running = False

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
		The read data is returned. 'None' is returned on failure.
		Overload this method, if the hardware has inputs and
		supports direct peripheral access."""
		return None

	def directWriteOutput(self, accessWidth, accessOffset, data):
		"""Direct peripheral output data write operation.
		'accessWidth' is the width of the access, in bits.
		'accessOffset' is the byte offset of the access.
		'data' is the data to write.
		Overload this method, if the hardware has outputs and
		supports direct peripheral access."""
		pass

	def __repr__(self):
		return "HardwareInterface: %s" % self.name

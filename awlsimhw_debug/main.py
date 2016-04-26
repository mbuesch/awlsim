# -*- coding: utf-8 -*-
#
# AWL simulator - Debug hardware interface
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

from awlsim.core.hardware import *
from awlsim.core.operators import AwlOperator
from awlsim.core.datatypes import AwlOffset


class HardwareInterface(AbstractHardwareInterface):
	name = "debug"

	paramDescs = [
		HwParamDesc_bool("dummyParam",
				 description = "Unused dummy parameter"),
		HwParamDesc_int("startupErrorRate",
				defaultValue = 0,
				minValue = 0,
				description = "Error rate in startup (0 = none)"),
		HwParamDesc_int("shutdownErrorRate",
				defaultValue = 0,
				minValue = 0,
				description = "Error rate in shutdown (0 = none)"),
		HwParamDesc_int("inputErrorRate",
				defaultValue = 0,
				minValue = 0,
				description = "Error rate in input read (0 = none)"),
		HwParamDesc_int("outputErrorRate",
				defaultValue = 0,
				minValue = 0,
				description = "Error rate in output write (0 = none)"),
		HwParamDesc_int("directReadErrorRate",
				defaultValue = 0,
				minValue = 0,
				description = "Error rate in direct input read (0 = none)"),
		HwParamDesc_int("directWriteErrorRate",
				defaultValue = 0,
				minValue = 0,
				description = "Error rate in direct output write (0 = none)"),
	]

	def __init__(self, sim, parameters={}):
		AbstractHardwareInterface.__init__(self,
						   sim = sim,
						   parameters = parameters)
		self.__startupErrorRate = self.getParamValueByName("startupErrorRate")
		self.__startupErrorCount = 0
		self.__shutdownErrorRate = self.getParamValueByName("shutdownErrorRate")
		self.__shutdownErrorCount = 0
		self.__inputErrorRate = self.getParamValueByName("inputErrorRate")
		self.__inputErrorCount = 0
		self.__outputErrorRate = self.getParamValueByName("outputErrorRate")
		self.__outputErrorCount = 0
		self.__directReadErrorRate = self.getParamValueByName("directReadErrorRate")
		self.__directReadErrorCount = 0
		self.__directWriteErrorRate = self.getParamValueByName("directWriteErrorRate")
		self.__directWriteErrorCount = 0

	def doStartup(self):
		if self.__startupErrorRate:
			self.__startupErrorCount += 1
			if self.__startupErrorCount % self.__startupErrorRate == 0:
				self.raiseException("Synthetic startup error")

	def doShutdown(self):
		if self.__shutdownErrorRate:
			self.__shutdownErrorCount += 1
			if self.__shutdownErrorCount % self.__shutdownErrorRate == 0:
				self.raiseException("Synthetic shutdown error")

	def readInputs(self):
		if self.__inputErrorRate:
			self.__inputErrorCount += 1
			if self.__inputErrorCount % self.__inputErrorRate == 0:
				self.raiseException("Synthetic input error")

		# Get the first input dword and write it back.
		dword = self.sim.cpu.fetch(AwlOperator(AwlOperator.MEM_E,
						       32,
						       AwlOffset(self.inputAddressBase)))
		dwordBytes = bytearray( ( ((dword >> 24) & 0xFF),
					  ((dword >> 16) & 0xFF),
					  ((dword >> 8) & 0xFF),
					  (dword & 0xFF) ) )
		self.sim.cpu.storeInputRange(self.inputAddressBase,
					     dwordBytes)

	def writeOutputs(self):
		if self.__outputErrorRate:
			self.__outputErrorCount += 1
			if self.__outputErrorCount % self.__outputErrorRate == 0:
				self.raiseException("Synthetic output error")

		# Fetch a data range, but don't do anything with it.
		outData = self.sim.cpu.fetchOutputRange(self.outputAddressBase,
							512)
		assert(outData)

	def directReadInput(self, accessWidth, accessOffset):
		if accessOffset < self.inputAddressBase:
			return None

		if self.__directReadErrorRate:
			self.__directReadErrorCount += 1
			if self.__directReadErrorCount % self.__directReadErrorRate == 0:
				self.raiseException("Synthetic directRead error")

		# Just read the current value from the CPU and return it.
		return self.sim.cpu.fetch(AwlOperator(AwlOperator.MEM_E,
						      accessWidth,
						      AwlOffset(accessOffset)))

	def directWriteOutput(self, accessWidth, accessOffset, data):
		if accessOffset < self.outputAddressBase:
			return False

		if self.__directWriteErrorRate:
			self.__directWriteErrorCount += 1
			if self.__directWriteErrorCount % self.__directWriteErrorRate == 0:
				self.raiseException("Synthetic directWrite error")

		# Just pretend we wrote it somewhere.
		return True

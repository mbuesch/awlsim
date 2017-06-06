# -*- coding: utf-8 -*-
#
# AWL simulator - Debug hardware interface
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

from awlsim.common.util import *
from awlsim.common.exceptions import *

#from awlsimhw_debug.main cimport * #@cy

from awlsim.core.hardware_params import *
from awlsim.core.hardware import * #+cimport
from awlsim.core.operatortypes import * #+cimport
from awlsim.core.operators import * #+cimport
from awlsim.core.offset import * #+cimport
from awlsim.core.cpu import * #+cimport


class HardwareInterface_Debug(AbstractHardwareInterface): #+cdef
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

	def readInputs(self): #+cdef
		if self.__inputErrorRate:
			self.__inputErrorCount += 1
			if self.__inputErrorCount % self.__inputErrorRate == 0:
				self.raiseException("Synthetic input error")

		# Get the first input dword and write it back.
		dword = self.sim.cpu.fetch(make_AwlOperator(AwlOperatorTypes.MEM_E,
							    32,
							    make_AwlOffset(self.inputAddressBase, 0),
							    None),
					   AwlOperatorWidths.WIDTH_MASK_ALL)
		dwordBytes = bytearray( ( ((dword >> 24) & 0xFF),
					  ((dword >> 16) & 0xFF),
					  ((dword >> 8) & 0xFF),
					  (dword & 0xFF) ) )
		self.sim.cpu.storeInputRange(self.inputAddressBase,
					     dwordBytes)

	def writeOutputs(self): #+cdef
		if self.__outputErrorRate:
			self.__outputErrorCount += 1
			if self.__outputErrorCount % self.__outputErrorRate == 0:
				self.raiseException("Synthetic output error")

		# Fetch a data range, but don't do anything with it.
		outData = self.sim.cpu.fetchOutputRange(self.outputAddressBase, 2)
		assert(outData)

	def directReadInput(self, accessWidth, accessOffset): #@nocy
#@cy	cdef bytearray directReadInput(self, uint32_t accessWidth, uint32_t accessOffset):
		if accessOffset < self.inputAddressBase:
			return bytearray()

		if self.__directReadErrorRate:
			self.__directReadErrorCount += 1
			if self.__directReadErrorCount % self.__directReadErrorRate == 0:
				self.raiseException("Synthetic directRead error")

		# Just read the current value from the CPU and return it.
		try:
			return self.sim.cpu.fetchInputRange(accessOffset, accessWidth // 8)
		except AwlSimError as e:
			# We may be out of process image range. Just return 0.
			return bytearray( (0,) * (accessWidth // 8) )

	def directWriteOutput(self, accessWidth, accessOffset, data): #@nocy
#@cy	cdef ExBool_t directWriteOutput(self, uint32_t accessWidth, uint32_t accessOffset, bytearray data) except ExBool_val:
		if accessOffset < self.outputAddressBase:
			return False

		if self.__directWriteErrorRate:
			self.__directWriteErrorCount += 1
			if self.__directWriteErrorCount % self.__directWriteErrorRate == 0:
				self.raiseException("Synthetic directWrite error")

		# Just pretend we wrote it somewhere.
		return True

# Module entry point
HardwareInterface = HardwareInterface_Debug

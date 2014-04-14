# -*- coding: utf-8 -*-
#
# AWL simulator - LinuxCNC HAL interface
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

from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim.core.compat import *

from awlsim.core.hardware import *
from awlsim.core.util import *
from awlsim.core.datatypehelpers import *


class HardwareInterface(AbstractHardwareInterface):
	name = "LinuxCNC"

	paramDescs = [
		HwParamDesc_pyobject("hal", pyTypeDesc = "<class 'hal.component'>",
				     description = "LinuxCNC HAL instance object",
				     mandatory = True),
		HwParamDesc_int("inputSize",
				description = "Input area size",
				mandatory = True),
		HwParamDesc_int("outputSize",
				description = "Output area size",
				mandatory = True),
	]

	def __init__(self, sim, parameters={}):
		AbstractHardwareInterface.__init__(self,
						   sim = sim,
						   parameters = parameters)
		self.linuxCNC_initialized = False

	def doStartup(self):
		if not self.linuxCNC_initialized:
			try:
				import hal as LinuxCNC_HAL
				self.LinuxCNC_HAL = LinuxCNC_HAL
			except ImportError as e:
				self.raiseException("Failed to import LinuxCNC HAL module"
					":\n%s" % str(e))

			# Get the LinuxCNC-HAL-component object
			self.hal = self.getParam("hal")

			# Get parameters
			self.inputSize = self.getParam("inputSize")
			self.outputSize = self.getParam("outputSize")

			# Signal LinuxCNC that we are ready.
			self.hal.ready()

			self.linuxCNC_initialized = True

	def doShutdown(self):
		pass

	@staticmethod
	def __storeDWord(bytearr, offset, dword):
		bytearr[offset] = (dword >> 24) & 0xFF
		bytearr[offset + 1] = (dword >> 16) & 0xFF
		bytearr[offset + 2] = (dword >> 8) & 0xFF
		bytearr[offset + 3] = dword & 0xFF

	def readInputs(self):
		hal, base, size = self.hal, self.inputAddressBase, self.inputSize
		# Start with empty data
		inData = bytearray(size)
		# Get the data from the HAL pins
		for offset in range(size):
			address = base + offset
			for bitNr in range(8):
				if hal["input.bit.%d.%d.active" % (address, bitNr)]:
					if hal["input.bit.%d.%d" % (address, bitNr)]:
						inData[offset] |= 1 << bitNr
					else:
						inData[offset] &= ~(1 << bitNr)

			if size - offset < 4:
				continue

			if hal["input.u32.%d.active" % address]:
				self.__storeDWord(inData, offset,
						  hal["input.u32.%d" % address])
			if hal["input.s32.%d.active" % address]:
				self.__storeDWord(inData, offset,
						  hal["input.u32.%d" % address] & 0xFFFFFFFF)
			if hal["input.float.%d.active" % address]:
				self.__storeDWord(inData, offset,
						  pyFloatToDWord(hal["input.u32.%d" % address]))
		self.sim.cpu.storeInputRange(base, inData)

	def writeOutputs(self):
		hal, base, size = self.hal, self.outputAddressBase, self.outputSize
		# Get the output data from the CPU
		outData = self.sim.cpu.fetchOutputRange(base, size)
		# Copy the data to the HAL pins
		for offset in range(size):
			address = base + offset
			byteData = outData[offset]

			for bitNr in range(8):
				hal["output.bit.%d.%d" % (address, bitNr)] = (byteData >> bitNr) & 1

			if size - offset < 4:
				continue
			dwordData = (byteData << 24) | (outData[offset + 1] << 16) |\
				    (outData[offset + 2] << 8) | outData[offset + 3]

			hal["output.u32.%d" % address] = dwordData & 0x7FFFFFFF
			hal["output.s32.%d" % address] = dwordToSignedPyInt(dwordData)
			hal["output.float.%d" % address] = dwordToPyFloat(dwordData)

	def directReadInput(self, accessWidth, accessOffset):
		pass#TODO

	def directWriteOutput(self, accessWidth, accessOffset, data):
		pass#TODO

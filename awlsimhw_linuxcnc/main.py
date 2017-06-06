# -*- coding: utf-8 -*-
#
# AWL simulator - LinuxCNC HAL interface
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

#from awlsimhw_linuxcnc.main cimport * #@cy

from awlsim.common.datatypehelpers import * #+cimport

from awlsim.core.hardware_params import *
from awlsim.core.hardware import * #+cimport
from awlsim.core.operators import * #+cimport
from awlsim.core.offset import * #+cimport
from awlsim.core.cpu import * #+cimport


class SigBit(object):
	def __init__(self, hal, halName, byteOffset, bitOffset):
		self.hal = hal
		self.halName = halName
		self.byteOffset = byteOffset
		self.bitOffset = bitOffset
		self.setMask = 1 << bitOffset
		self.clrMask = ~(1 << bitOffset)

	def readInput(self, destBuf):
		if self.hal[self.halName]:
			destBuf[self.byteOffset] |= self.setMask
		else:
			destBuf[self.byteOffset] &= self.clrMask

	def writeOutput(self, srcBuf):
		self.hal[self.halName] = (srcBuf[self.byteOffset] >> self.bitOffset) & 1

class SigU8(object):
	def __init__(self, hal, halName, offset):
		self.hal = hal
		self.halName = halName
		self.offset = offset

	def readInput(self, destBuf):
		destBuf[self.offset] = self.hal[self.halName] & 0xFF

	def writeOutput(self, srcBuf):
		self.hal[self.halName] = srcBuf[self.offset] & 0xFF

class SigU16(object):
	def __init__(self, hal, halName, offset):
		self.hal = hal
		self.halName = halName
		self.offset = offset

	def readInput(self, destBuf):
		word = self.hal[self.halName] & 0xFFFF
		destBuf[self.offset] = (word >> 8) & 0xFF
		destBuf[self.offset + 1] = word & 0xFF

	def writeOutput(self, srcBuf):
		word = (srcBuf[self.offset] << 8) |\
		       srcBuf[self.offset + 1]
		self.hal[self.halName] = word & 0xFFFF

class SigS16(object):
	def __init__(self, hal, halName, offset):
		self.hal = hal
		self.halName = halName
		self.offset = offset

	def readInput(self, destBuf):
		word = self.hal[self.halName] & 0xFFFF
		destBuf[self.offset] = (word >> 8) & 0xFF
		destBuf[self.offset + 1] = word & 0xFF

	def writeOutput(self, srcBuf):
		word = (srcBuf[self.offset] << 8) |\
		       srcBuf[self.offset + 1]
		self.hal[self.halName] = wordToSignedPyInt(word)

class SigU31(object):
	def __init__(self, hal, halName, offset):
		self.hal = hal
		self.halName = halName
		self.offset = offset

	def readInput(self, destBuf):
		dword = self.hal[self.halName] & 0x7FFFFFFF
		destBuf[self.offset] = (dword >> 24) & 0xFF
		destBuf[self.offset + 1] = (dword >> 16) & 0xFF
		destBuf[self.offset + 2] = (dword >> 8) & 0xFF
		destBuf[self.offset + 3] = dword & 0xFF

	def writeOutput(self, srcBuf):
		dword = (srcBuf[self.offset] << 24) |\
		        (srcBuf[self.offset + 1] << 16) |\
		        (srcBuf[self.offset + 2] << 8) |\
		        srcBuf[self.offset + 3]
		self.hal[self.halName] = dword & 0x7FFFFFFF

class SigS32(object):
	def __init__(self, hal, halName, offset):
		self.hal = hal
		self.halName = halName
		self.offset = offset

	def readInput(self, destBuf):
		dword = self.hal[self.halName] & 0xFFFFFFFF
		destBuf[self.offset] = (dword >> 24) & 0xFF
		destBuf[self.offset + 1] = (dword >> 16) & 0xFF
		destBuf[self.offset + 2] = (dword >> 8) & 0xFF
		destBuf[self.offset + 3] = dword & 0xFF

	def writeOutput(self, srcBuf):
		dword = (srcBuf[self.offset] << 24) |\
		        (srcBuf[self.offset + 1] << 16) |\
		        (srcBuf[self.offset + 2] << 8) |\
		        srcBuf[self.offset + 3]
		self.hal[self.halName] = dwordToSignedPyInt(dword)

class SigFloat(object):
	def __init__(self, hal, halName, offset):
		self.hal = hal
		self.halName = halName
		self.offset = offset

	def readInput(self, destBuf):
		dword = pyFloatToDWord(self.hal[self.halName])
		destBuf[self.offset] = (dword >> 24) & 0xFF
		destBuf[self.offset + 1] = (dword >> 16) & 0xFF
		destBuf[self.offset + 2] = (dword >> 8) & 0xFF
		destBuf[self.offset + 3] = dword & 0xFF

	def writeOutput(self, srcBuf):
		dword = (srcBuf[self.offset] << 24) |\
		        (srcBuf[self.offset + 1] << 16) |\
		        (srcBuf[self.offset + 2] << 8) |\
		        srcBuf[self.offset + 3]
		self.hal[self.halName] = dwordToPyFloat(dword)

class HardwareInterface_LinuxCNC(AbstractHardwareInterface): #+cdef
	name = "LinuxCNC"

	paramDescs = [
		HwParamDesc_pyobject("hal",
				     description = "LinuxCNC HAL instance object",
				     mandatory = True),
		HwParamDesc_int("inputSize",
				description = "Input area size",
				defaultValue = 32,
				mandatory = True),
		HwParamDesc_int("outputSize",
				description = "Output area size",
				defaultValue = 32,
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
			self.hal = self.getParamValueByName("hal")

			# Get parameters
			self.inputSize = self.getParamValueByName("inputSize")
			self.outputSize = self.getParamValueByName("outputSize")

			self.__configDone = False

			# Signal LinuxCNC that we are ready.
			self.hal.ready()

			self.linuxCNC_initialized = True

	def doShutdown(self):
		pass

#TODO find overlappings
	def __buildTable(self, baseName, addressBase, size):
		tab = []
		for address in range(addressBase, addressBase + size):
			offset = address - addressBase
			for bitNr in range(8):
				if self.hal["%s.bit.%d.%d.active" % (baseName, address, bitNr)]:
					tab.append(SigBit(self.hal,
							  "%s.bit.%d.%d" % (baseName, address, bitNr),
							  offset, bitNr))
			if self.hal["%s.u8.%d.active" % (baseName, address)]:
				tab.append(SigU8(self.hal,
						 "%s.u8.%d" % (baseName, address),
						 offset))
			if address % 2:
				continue
			if size - offset < 2:
				continue
			if self.hal["%s.u16.%d.active" % (baseName, address)]:
				tab.append(SigU16(self.hal,
						  "%s.u16.%d" % (baseName, address),
						  offset))
			if self.hal["%s.s16.%d.active" % (baseName, address)]:
				tab.append(SigS16(self.hal,
						  "%s.s16.%d" % (baseName, address),
						  offset))
			if size - offset < 4:
				continue
			if self.hal["%s.u31.%d.active" % (baseName, address)]:
				tab.append(SigU31(self.hal,
						  "%s.u31.%d" % (baseName, address),
						  offset))
			if self.hal["%s.s32.%d.active" % (baseName, address)]:
				tab.append(SigS32(self.hal,
						  "%s.s32.%d" % (baseName, address),
						  offset))
			if self.hal["%s.float.%d.active" % (baseName, address)]:
				tab.append(SigFloat(self.hal,
						    "%s.float.%d" % (baseName, address),
						    offset))
		return tab

	def __tryBuildConfig(self):
		if not self.hal["config.ready"]:
			return

		self.__activeInputs = self.__buildTable("input",
			self.inputAddressBase, self.inputSize)
		#TODO dump the input table

		self.__activeOutputs = self.__buildTable("output",
			self.outputAddressBase, self.outputSize)
		#TODO dump the input table

		self.__configDone = True
		printInfo("HAL configuration done")

	def readInputs(self): #+cdef
		if not self.__configDone:
			self.__tryBuildConfig()
			if not self.__configDone:
				return

		data = bytearray(self.inputSize)
		for desc in self.__activeInputs:
			desc.readInput(data)
		self.sim.cpu.storeInputRange(self.inputAddressBase, data)

	def writeOutputs(self): #+cdef
		if not self.__configDone:
			return

		data = self.sim.cpu.fetchOutputRange(self.outputAddressBase,
						     self.outputSize)
		for desc in self.__activeOutputs:
			desc.writeOutput(data)

	def directReadInput(self, accessWidth, accessOffset): #@nocy
#@cy	cdef bytearray directReadInput(self, uint32_t accessWidth, uint32_t accessOffset):
		pass#TODO
		return bytearray()

	def directWriteOutput(self, accessWidth, accessOffset, data): #@nocy
#@cy	cdef ExBool_t directWriteOutput(self, uint32_t accessWidth, uint32_t accessOffset, bytearray data) except ExBool_val:
		pass#TODO
		return False

# Module entry point
HardwareInterface = HardwareInterface_LinuxCNC

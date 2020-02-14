# -*- coding: utf-8 -*-
#
# AWL simulator - LinuxCNC HAL interface
#
# Copyright 2013-2020 Michael Buesch <m@bues.ch>
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
#from awlsim.common.cython_support cimport * #@cy
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
	name		= "LinuxCNC"
	description	= "LinuxCNC and MachineKit hardware support.\n"\
			  "http://linuxcnc.org/\n"\
			  "http://www.machinekit.io/"

	paramDescs = [
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

	def __createHalPins(self):
		"""Create the LinuxCNC HAL pins.
		"""
		HAL_BIT, HAL_U32, HAL_S32, HAL_FLOAT = (
			linuxCNCHal.HAL_BIT, linuxCNCHal.HAL_U32,
			linuxCNCHal.HAL_S32, linuxCNCHal.HAL_FLOAT)
		HAL_IN, HAL_OUT, HAL_RO, HAL_RW = (
			linuxCNCHal.HAL_IN, linuxCNCHal.HAL_OUT,
			linuxCNCHal.HAL_RO, linuxCNCHal.HAL_RW)

		def newpin(name, *args):
			try:
				try:
					self.halComponent[name]
				except AttributeError:
					self.halComponent.newpin(name, *args)
			except linuxCNCHal.error as e:
				printWarning("Failed to create HAL pin '%s'. "
					     "Please restart LinuxCNC." % name)

		def newparam(name, *args):
			try:
				try:
					self.halComponent[name]
				except AttributeError:
					self.halComponent.newparam(name, *args)
			except linuxCNCHal.error as e:
				printWarning("Failed to create HAL param '%s'. "
					     "Please restart LinuxCNC." % name)

		printInfo("Mapped AWL/STL input area:  P#E %d.0 BYTE %d" %\
			  (self.inputAddressBase, self.inputSize))
		printInfo("Mapped AWL/STL output area:  P#A %d.0 BYTE %d" %\
			  (self.outputAddressBase, self.outputSize))

		# Create the input pins
		for i in range(self.inputAddressBase, self.inputAddressBase + self.inputSize):
			offset = i - self.inputAddressBase
			for bit in range(8):
				newpin("input.bit.%d.%d" % (i, bit), HAL_BIT, HAL_IN)
				newparam("input.bit.%d.%d.active" % (i, bit), HAL_BIT, HAL_RW)
			newpin("input.u8.%d" % i, HAL_U32, HAL_IN)
			newparam("input.u8.%d.active" % i, HAL_BIT, HAL_RW)
			if i % 2:
				continue
			if self.inputSize - offset < 2:
				continue
			newpin("input.u16.%d" % i, HAL_U32, HAL_IN)
			newparam("input.u16.%d.active" % i, HAL_BIT, HAL_RW)
			newpin("input.s16.%d" % i, HAL_S32, HAL_IN)
			newparam("input.s16.%d.active" % i, HAL_BIT, HAL_RW)
			if self.inputSize - offset < 4:
				continue
			newpin("input.u31.%d" % i, HAL_U32, HAL_IN)
			newparam("input.u31.%d.active" % i, HAL_BIT, HAL_RW)
			newpin("input.s32.%d" % i, HAL_S32, HAL_IN)
			newparam("input.s32.%d.active" % i, HAL_BIT, HAL_RW)
			newpin("input.float.%d" % i, HAL_FLOAT, HAL_IN)
			newparam("input.float.%d.active" % i, HAL_BIT, HAL_RW)

		# Create the output pins
		for i in range(self.outputAddressBase, self.outputAddressBase + self.outputSize):
			offset = i - self.outputAddressBase
			for bit in range(8):
				newpin("output.bit.%d.%d" % (i, bit), HAL_BIT, HAL_OUT)
				newparam("output.bit.%d.%d.active" % (i, bit), HAL_BIT, HAL_RW)
			newpin("output.u8.%d" % i, HAL_U32, HAL_OUT)
			newparam("output.u8.%d.active" % i, HAL_BIT, HAL_RW)
			if i % 2:
				continue
			if self.outputSize - offset < 2:
				continue
			newpin("output.u16.%d" % i, HAL_U32, HAL_OUT)
			newparam("output.u16.%d.active" % i, HAL_BIT, HAL_RW)
			newpin("output.s16.%d" % i, HAL_S32, HAL_OUT)
			newparam("output.s16.%d.active" % i, HAL_BIT, HAL_RW)
			if self.outputSize - offset < 4:
				continue
			newpin("output.u31.%d" % i, HAL_U32, HAL_OUT)
			newparam("output.u31.%d.active" % i, HAL_BIT, HAL_RW)
			newpin("output.s32.%d" % i, HAL_S32, HAL_OUT)
			newparam("output.s32.%d.active" % i, HAL_BIT, HAL_RW)
			newpin("output.float.%d" % i, HAL_FLOAT, HAL_OUT)
			newparam("output.float.%d.active" % i, HAL_BIT, HAL_RW)

		newparam("config.ready", HAL_BIT, HAL_RW)

	def doStartup(self):
		global linuxCNCHalComponent
		global linuxCNCHalComponentReady

		if not self.linuxCNC_initialized:
			if linuxCNCHalComponent is None:
				self.raiseException("LinuxCNC HAL component not set.")
			self.halComponent = linuxCNCHalComponent

			# Get parameters
			self.inputSize = self.getParamValueByName("inputSize")
			self.outputSize = self.getParamValueByName("outputSize")

			self.__createHalPins()

			self.__configDone = False

			# Signal LinuxCNC that we are ready.
			if not linuxCNCHalComponentReady:
				self.halComponent.ready()
				linuxCNCHalComponentReady = True

			self.linuxCNC_initialized = True

	def doShutdown(self):
		pass

#TODO find overlappings
	def __buildTable(self, baseName, addressBase, size):
		def isActive(name):
			activeName = "%s.active" % name
			try:
				return self.halComponent[activeName]
			except AttributeError:
				printWarning("Pin '%s' cannot be used without restart. "
					     "Please restart LinuxCNC." % name)
				return False

		tab = []
		for address in range(addressBase, addressBase + size):
			offset = address - addressBase
			for bitNr in range(8):
				if isActive("%s.bit.%d.%d" % (baseName, address, bitNr)):
					tab.append(SigBit(self.halComponent,
							  "%s.bit.%d.%d" % (baseName, address, bitNr),
							  offset, bitNr))
			if isActive("%s.u8.%d" % (baseName, address)):
				tab.append(SigU8(self.halComponent,
						 "%s.u8.%d" % (baseName, address),
						 offset))
			if address % 2:
				continue
			if size - offset < 2:
				continue
			if isActive("%s.u16.%d" % (baseName, address)):
				tab.append(SigU16(self.halComponent,
						  "%s.u16.%d" % (baseName, address),
						  offset))
			if isActive("%s.s16.%d" % (baseName, address)):
				tab.append(SigS16(self.halComponent,
						  "%s.s16.%d" % (baseName, address),
						  offset))
			if size - offset < 4:
				continue
			if isActive("%s.u31.%d" % (baseName, address)):
				tab.append(SigU31(self.halComponent,
						  "%s.u31.%d" % (baseName, address),
						  offset))
			if isActive("%s.s32.%d" % (baseName, address)):
				tab.append(SigS32(self.halComponent,
						  "%s.s32.%d" % (baseName, address),
						  offset))
			if isActive("%s.float.%d" % (baseName, address)):
				tab.append(SigFloat(self.halComponent,
						    "%s.float.%d" % (baseName, address),
						    offset))
		return tab

	def __tryBuildConfig(self):
		if not self.halComponent["config.ready"]:
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

# LinuxCNC HAL component singleton.
linuxCNCHal = None
linuxCNCHalComponent = None
linuxCNCHalComponentReady = False

def setLinuxCNCHalComponentSingleton(newHal, newHalComponent):
	global linuxCNCHal
	global linuxCNCHalComponent
	global linuxCNCHalComponentReady
	if linuxCNCHalComponent is not None:
		printWarning("linuxCNCHalComponent is already set to "
			     "%s (new = %s)" % (
			     str(linuxCNCHalComponent),
			     str(newHalComponent)))
	linuxCNCHal = newHal
	linuxCNCHalComponent = newHalComponent
	linuxCNCHalComponentReady = False

# Module entry point
HardwareInterface = HardwareInterface_LinuxCNC

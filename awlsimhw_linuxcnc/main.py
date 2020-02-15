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


class Sig(object):
	def __init__(self, hal, halName, address, offset):
		self.hal = hal
		self.halName = halName
		self.address = address
		self.offset = offset

	def __str__(self):
		return "awlsim.%s" % self.halName

class SigBit(Sig):
	width = 1

	def __init__(self, hal, halName, address, offset, bitOffset):
		Sig.__init__(self, hal, halName, address, offset)
		self.bitOffset = bitOffset
		self.setMask = 1 << bitOffset
		self.clrMask = (1 << bitOffset) ^ 0xFF

	def readInput(self, destBuf, toOffset):
		if self.hal[self.halName]:
			destBuf[toOffset] |= self.setMask
		else:
			destBuf[toOffset] &= self.clrMask

	def writeOutput(self, srcBuf, fromOffset):
		self.hal[self.halName] = (srcBuf[fromOffset] >> self.bitOffset) & 1

class SigU8(Sig):
	width = 8

	def readInput(self, destBuf, toOffset):
		destBuf[toOffset] = self.hal[self.halName] & 0xFF

	def writeOutput(self, srcBuf, fromOffset):
		self.hal[self.halName] = srcBuf[fromOffset] & 0xFF

class SigU16(Sig):
	width = 16

	def readInput(self, destBuf, toOffset):
		word = self.hal[self.halName] & 0xFFFF
		destBuf[toOffset] = (word >> 8) & 0xFF
		destBuf[toOffset + 1] = word & 0xFF

	def writeOutput(self, srcBuf, fromOffset):
		word = ((srcBuf[fromOffset] << 8) |
			srcBuf[fromOffset + 1])
		self.hal[self.halName] = word & 0xFFFF

class SigS16(Sig):
	width = 16

	def readInput(self, destBuf, toOffset):
		word = self.hal[self.halName] & 0xFFFF
		destBuf[toOffset] = (word >> 8) & 0xFF
		destBuf[toOffset + 1] = word & 0xFF

	def writeOutput(self, srcBuf, fromOffset):
		word = ((srcBuf[fromOffset] << 8) |
			srcBuf[fromOffset + 1])
		self.hal[self.halName] = wordToSignedPyInt(word)

class SigU31(Sig):
	width = 32 # U31 memory width is 32 bit

	def readInput(self, destBuf, toOffset):
		dword = self.hal[self.halName] & 0x7FFFFFFF
		destBuf[toOffset] = (dword >> 24) & 0xFF
		destBuf[toOffset + 1] = (dword >> 16) & 0xFF
		destBuf[toOffset + 2] = (dword >> 8) & 0xFF
		destBuf[toOffset + 3] = dword & 0xFF

	def writeOutput(self, srcBuf, fromOffset):
		dword = ((srcBuf[fromOffset] << 24) |
			 (srcBuf[fromOffset + 1] << 16) |
			 (srcBuf[fromOffset + 2] << 8) |
			 srcBuf[fromOffset + 3])
		self.hal[self.halName] = dword & 0x7FFFFFFF

class SigS32(Sig):
	width = 32

	def readInput(self, destBuf, toOffset):
		dword = self.hal[self.halName] & 0xFFFFFFFF
		destBuf[toOffset] = (dword >> 24) & 0xFF
		destBuf[toOffset + 1] = (dword >> 16) & 0xFF
		destBuf[toOffset + 2] = (dword >> 8) & 0xFF
		destBuf[toOffset + 3] = dword & 0xFF

	def writeOutput(self, srcBuf, fromOffset):
		dword = ((srcBuf[fromOffset] << 24) |
			 (srcBuf[fromOffset + 1] << 16) |
			 (srcBuf[fromOffset + 2] << 8) |
			 srcBuf[fromOffset + 3])
		self.hal[self.halName] = dwordToSignedPyInt(dword)

class SigFloat(Sig):
	width = 32

	def readInput(self, destBuf, toOffset):
		dword = pyFloatToDWord(self.hal[self.halName])
		destBuf[toOffset] = (dword >> 24) & 0xFF
		destBuf[toOffset + 1] = (dword >> 16) & 0xFF
		destBuf[toOffset + 2] = (dword >> 8) & 0xFF
		destBuf[toOffset + 3] = dword & 0xFF

	def writeOutput(self, srcBuf, fromOffset):
		dword = ((srcBuf[fromOffset] << 24) |
			 (srcBuf[fromOffset + 1] << 16) |
			 (srcBuf[fromOffset + 2] << 8) |
			 srcBuf[fromOffset + 3])
		self.hal[self.halName] = dwordToPyFloat(dword)

class HardwareInterface_LinuxCNC(AbstractHardwareInterface): #+cdef
	name		= "LinuxCNC"
	description	= "LinuxCNC hardware support.\nhttp://linuxcnc.org/"

	paramDescs = [
		HwParamDesc_int("inputSize",
				description="Input area size",
				defaultValue=32,
				mandatory=True),
		HwParamDesc_int("outputSize",
				description="Output area size",
				defaultValue=32,
				mandatory=True),
	]

	def __init__(self, sim, parameters={}):
		AbstractHardwareInterface.__init__(self,
						   sim=sim,
						   parameters=parameters)
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

		printInfo("Mapped AWL/STL input area:  P#E %d.0 BYTE %d" % (
			  self.inputAddressBase, self.inputSize))
		printInfo("Mapped AWL/STL output area:  P#A %d.0 BYTE %d" % (
			  self.outputAddressBase, self.outputSize))

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
		tab = []
		addr2sig = {}

		def isActive(name):
			activeName = "%s.active" % name
			try:
				return self.halComponent[activeName]
			except AttributeError:
				printWarning("Pin '%s' cannot be used without restart. "
					     "Please restart LinuxCNC." % name)
				return False

		def add(sig):
			tab.append(sig)
			if not isinstance(sig, SigBit):
				addr2sig[sig.address] = sig
			printInfo("Active HAL pin: %s" % str(sig))

		for address in range(addressBase, addressBase + size):
			offset = address - addressBase
			for bitNr in range(8):
				if isActive("%s.bit.%d.%d" % (baseName, address, bitNr)):
					add(SigBit(self.halComponent,
						   "%s.bit.%d.%d" % (baseName, address, bitNr),
						   address, offset, bitNr))
			if isActive("%s.u8.%d" % (baseName, address)):
				add(SigU8(self.halComponent,
					  "%s.u8.%d" % (baseName, address),
					  address, offset))
			if address % 2:
				continue
			if size - offset < 2:
				continue
			if isActive("%s.u16.%d" % (baseName, address)):
				add(SigU16(self.halComponent,
					   "%s.u16.%d" % (baseName, address),
					   address, offset))
			if isActive("%s.s16.%d" % (baseName, address)):
				add(SigS16(self.halComponent,
					   "%s.s16.%d" % (baseName, address),
					   address, offset))
			if size - offset < 4:
				continue
			if isActive("%s.u31.%d" % (baseName, address)):
				add(SigU31(self.halComponent,
					   "%s.u31.%d" % (baseName, address),
					   address, offset))
			if isActive("%s.s32.%d" % (baseName, address)):
				add(SigS32(self.halComponent,
					   "%s.s32.%d" % (baseName, address),
					   address, offset))
			if isActive("%s.float.%d" % (baseName, address)):
				add(SigFloat(self.halComponent,
					     "%s.float.%d" % (baseName, address),
					     address, offset))
		return tab, addr2sig

	def __tryBuildConfig(self):
		if not self.halComponent["config.ready"]:
			return False

		self.__activeInputs, self.__activeInputsAddr2Sig = self.__buildTable(
			"input",
			self.inputAddressBase,
			self.inputSize)

		self.__activeOutputs, self.__activeOutputsAddr2Sig = self.__buildTable(
			"output",
			self.outputAddressBase,
			self.outputSize)

		self.__configDone = True
		printInfo("HAL configuration done")
		return True

	def readInputs(self): #+cdef
		if not self.__configDone:
			if not self.__tryBuildConfig():
				return

		data = bytearray(self.inputSize)
		for sig in self.__activeInputs:
			sig.readInput(data, sig.offset)
		self.sim.cpu.storeInputRange(self.inputAddressBase, data)

	def writeOutputs(self): #+cdef
		if not self.__configDone:
			return

		data = self.sim.cpu.fetchOutputRange(self.outputAddressBase,
						     self.outputSize)
		for sig in self.__activeOutputs:
			sig.writeOutput(data, sig.offset)

	def directReadInput(self, accessWidth, accessOffset): #@nocy
#@cy	cdef bytearray directReadInput(self, uint32_t accessWidth, uint32_t accessOffset):
		if not self.__configDone:
			if not self.__tryBuildConfig():
				return bytearray()

		try:
			sig = self.__activeInputsAddr2Sig[accessOffset]
		except KeyError as e:
			return bytearray()
		if accessWidth != sig.width:
			self.raiseException("Directly accessing input at I %d.0 "
				"with width %d bit, but only %d bit wide "
				"accesses are supported." % (
				accessOffset, accessWidth, sig.width))

		data = bytearray(accessWidth // 8)
		sig.readInput(data, 0)
		return data

	def directWriteOutput(self, accessWidth, accessOffset, data): #@nocy
#@cy	cdef ExBool_t directWriteOutput(self, uint32_t accessWidth, uint32_t accessOffset, bytearray data) except ExBool_val:
		if not self.__configDone:
			if not self.__tryBuildConfig():
				return False

		try:
			sig = self.__activeOutputsAddr2Sig[accessOffset]
		except KeyError as e:
			return False
		if accessWidth != sig.width:
			self.raiseException("Directly accessing output at Q %d.0 "
				"with width %d bit, but only %d bit wide "
				"accesses are supported." % (
				accessOffset, accessWidth, sig.width))

		sig.writeOutput(data, 0)
		return True

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

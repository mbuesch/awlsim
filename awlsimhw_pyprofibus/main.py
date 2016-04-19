# -*- coding: utf-8 -*-
#
# AWL simulator - PyProfibus hardware interface
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
from awlsim.core.util import *


class HardwareInterface(AbstractHardwareInterface):
	name = "PyProfibus"

	# Hardware-specific parameters
	paramDescs = [
		HwParamDesc_str("phyType",
				defaultValue = "serial",
				description = "CP PHY type"),
		HwParamDesc_str("dev",
				defaultValue = "/dev/ttyS0",
				description = "Serial device node."),
		HwParamDesc_int("debug",
				minValue = 0,
				description = "Debug level."),
		HwParamDesc_int("baud",
				defaultValue = 19200,
				minValue = 9600, maxValue = 12000000,
				description = "The PROFIBUS baud rate."),
		HwParamDesc_int("masterClass",
				defaultValue = 1,
				minValue = 1, maxValue = 2,
				description = "The DP-Master class."),
		HwParamDesc_int("masterAddr",
				defaultValue = 1,
				minValue = 0, maxValue = 126,
				description = "The DP-Address of the master."),
	]

	def __init__(self, sim, parameters={}):
		AbstractHardwareInterface.__init__(self,
						   sim = sim,
						   parameters = parameters)

	def __setupSlaves(self):
		#TODO: Rewrite. Must be configurable.
		et200s = self.pyprofibus.DpSlaveDesc(identNumber = 0x806A,
						     slaveAddr = 8,
						     inputAddressRangeSize = 1,
						     outputAddressRangeSize = 2)
		for elem in (self.pyprofibus.DpCfgDataElement(0),
			     self.pyprofibus.DpCfgDataElement(0x20),
			     self.pyprofibus.DpCfgDataElement(0x20),
			     self.pyprofibus.DpCfgDataElement(0x10)):
			et200s.chkCfgTelegram.addCfgDataElement(elem)
		et200s.setPrmTelegram.addUserPrmData([0x11 | 0x40])
		et200s.setSyncMode(True)
		et200s.setFreezeMode(True)
		et200s.setGroupMask(1)
		et200s.setWatchdog(5000)
		self.master.addSlave(et200s)

	def __cleanup(self):
		if self.master:
			self.master.destroy()
		self.master = None
		self.phy = None
		self.cachedInputs = []

	def doStartup(self):
		# Import the PROFIBUS hardware access modules
		# and keep references to it.
		try:
			import pyprofibus
			import pyprofibus.phy_serial
			self.pyprofibus = pyprofibus
		except (ImportError, RuntimeError) as e:
			self.raiseException("Failed to import PROFIBUS protocol stack "
				"module 'pyprofibus':\n%s" % str(e))

		# Initialize the DPM
		self.phy = None
		self.master = None
		try:
			debug = self.getParamValueByName("debug")
			dev = self.getParamValueByName("dev")
			phyType = self.getParamValueByName("phyType")

			if phyType.lower() == "serial":
				baud = self.getParamValueByName("baud")
				self.phy = self.pyprofibus.phy_serial.CpPhySerial(
						debug = (debug >= 2),
						port = dev)
				self.phy.setConfig(baudrate = baud)
			else:
				self.raiseException("Invalid phyType parameter value")

			if self.getParamValueByName("masterClass") == 1:
				DPM_cls = self.pyprofibus.DPM1
			else:
				DPM_cls = self.pyprofibus.DPM2
			masterAddr = self.getParamValueByName("masterAddr")
			self.master = DPM_cls(phy = self.phy,
					      masterAddr = masterAddr,
					      debug = (debug >= 1))

			self.__setupSlaves()
			self.master.initialize()

			self.slaveList = self.master.getSlaveList()
			self.cachedInputs = [None] * len(self.slaveList)

		except self.pyprofibus.PhyError as e:
			self.raiseException("Profibus-PHY error: %s" % str(e))
			self.__cleanup()
		except self.pyprofibus.DpError as e:
			self.raiseException("Profibus-DP error: %s" % str(e))
			self.__cleanup()
		except self.pyprofibus.FdlError as e:
			self.raiseException("Profibus-FDL error: %s" % str(e))
			self.__cleanup()

	def doShutdown(self):
		self.__cleanup()

	def readInputs(self):
		address = self.inputAddressBase
		for slave in self.slaveList:
			# Get the cached slave-data
			inData = self.cachedInputs.pop(0)
			if not inData:
				continue
			if len(inData) != slave.inputAddressRangeSize:
				self.raiseException("Input data from slave '%s' has "
					"invalid length %d (expected %d)" %\
					(str(slave), len(inData),
					 slave.inputAddressRangeSize))
			self.sim.cpu.storeInputRange(address, inData)
			# Adjust the address base for the next slave.
			address += slave.inputAddressRangeSize
		assert(not self.cachedInputs)

	def writeOutputs(self):
		try:
			address = self.outputAddressBase
			for slave in self.slaveList:
				# Get the output data from the CPU
				outData = self.sim.cpu.fetchOutputRange(address,
						slave.outputAddressRangeSize)
				# Send it to the slave and request the input data.
				inData = self.master.dataExchange(slave.slaveAddr,
								  outData)
				# Cache the input data for the readInputs() call.
				self.cachedInputs.append(inData)
				# Adjust the address base for the next slave.
				address += slave.outputAddressRangeSize
		except self.pyprofibus.ProfibusError as e:
			self.raiseException("Hardware error: %s" % str(e))

	def directReadInput(self, accessWidth, accessOffset):
		return None#TODO

	def directWriteOutput(self, accessWidth, accessOffset, data):
		return False#TODO

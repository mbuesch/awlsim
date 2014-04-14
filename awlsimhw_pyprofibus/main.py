# -*- coding: utf-8 -*-
#
# AWL simulator - PyProfibus hardware interface
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


class HardwareInterface(AbstractHardwareInterface):
	name = "PyProfibus"

	# Hardware-specific parameters
	paramDescs = [
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
		HwParamDesc_int("spiDev",
				minValue = 0,
				description = "The SPI device number."),
		HwParamDesc_int("spiChip",
				minValue = 0,
				description = "The SPI device chip-select number."),
	]

	def __init__(self, sim, parameters={}):
		AbstractHardwareInterface.__init__(self,
						   sim = sim,
						   parameters = parameters)

	def __setupSlaves(self):
		#TODO: Rewrite. Must be configurable.
		et200s = self.DPM.DpSlaveDesc(identNumber = 0x806A,
					      slaveAddr = 8,
					      inputAddressRangeSize = 1,
					      outputAddressRangeSize = 2)
		for elem in (self.DP.DpCfgDataElement(0),
			     self.DP.DpCfgDataElement(0x20),
			     self.DP.DpCfgDataElement(0x20),
			     self.DP.DpCfgDataElement(0x10)):
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
			import pyprofibus.dp_master
			import pyprofibus.dp
			import pyprofibus.fdl
			import pyprofibus.phy
			self.DPM = pyprofibus.dp_master
			self.DP = pyprofibus.dp
			self.FDL = pyprofibus.fdl
			self.PHY = pyprofibus.phy
		except (ImportError, RuntimeError) as e:
			self.raiseException("Failed to import PROFIBUS protocol stack "
				"module 'pyprofibus':\n%s" % str(e))

		# Initialize the DPM
		self.phy = None
		self.master = None
		try:
			self.phy = self.PHY.CpPhy(device = self.getParam("spiDev"),
						  chipselect = self.getParam("spiChip"),
						  debug = True if (self.getParam("debug") >= 2) else False)
			self.phy.profibusSetPhyConfig(baudrate = self.getParam("baud"))
			if self.getParam("masterClass") == 1:
				DPM_cls = self.DPM.DPM1
			else:
				DPM_cls = self.DPM.DPM2
			self.master = DPM_cls(phy = self.phy,
					      masterAddr = self.getParam("masterAddr"),
					      debug = True if (self.getParam("debug") >= 1) else False)
			self.__setupSlaves()
			self.master.initialize()
			self.slaveList = self.master.getSlaveList()
			self.cachedInputs = [None] * len(self.slaveList)
		except self.PHY.PhyError as e:
			self.raiseException("PHY error: %s" % str(e))
			self.__cleanup()
		except self.DP.DpError as e:
			self.raiseException("Profibus-DP error: %s" % str(e))
			self.__cleanup()
		except self.FDL.FdlError as e:
			self.raiseException("Fieldbug Data Link error: %s" % str(e))
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
		except (self.PHY.PhyError, self.DP.DpError, self.FDL.FdlError) as e:
			self.raiseException("Hardware error: %s" % str(e))

	def directReadInput(self, accessWidth, accessOffset):
		return None#TODO

	def directWriteOutput(self, accessWidth, accessOffset, data):
		return False#TODO

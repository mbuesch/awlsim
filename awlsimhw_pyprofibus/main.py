# -*- coding: utf-8 -*-
#
# AWL simulator - PyProfibus hardware interface
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

#from awlsimhw_pyprofibus.main cimport * #@cy

from awlsim.core.hardware_params import *
from awlsim.core.hardware import * #+cimport
from awlsim.core.operators import * #+cimport
from awlsim.core.offset import * #+cimport
from awlsim.core.cpu import * #+cimport


class HardwareInterface_PyProfibus(AbstractHardwareInterface): #+cdef
	name = "PyProfibus"

	# Hardware-specific parameters
	paramDescs = [
		HwParamDesc_str("config",
				defaultValue = "awlsimhw_pyprofibus.conf",
				description = "Awlsim pyprofibus module config file."),
	]

	def __init__(self, sim, parameters={}):
		AbstractHardwareInterface.__init__(self,
						   sim = sim,
						   parameters = parameters)

	def __setupSlaves(self):
		setPrmReq = self.pyprofibus.dp.DpTelegram_SetPrm_Req
		dp1PrmMask = bytearray((setPrmReq.DPV1PRM0_FAILSAFE,
					setPrmReq.DPV1PRM1_REDCFG,
					0x00))
		dp1PrmSet  = bytearray((setPrmReq.DPV1PRM0_FAILSAFE,
					setPrmReq.DPV1PRM1_REDCFG,
					0x00))

		for slaveConf in self.__conf.slaveConfs:
			desc = self.pyprofibus.DpSlaveDesc(
				identNumber = slaveConf.gsd.getIdentNumber(),
				slaveAddr = slaveConf.addr)
			desc.setCfgDataElements(slaveConf.gsd.getCfgDataElements())
			if slaveConf.gsd.isDPV1():
				desc.setUserPrmData(slaveConf.gsd.getUserPrmData(
						dp1PrmMask = dp1PrmMask,
						dp1PrmSet = dp1PrmSet))
			else:
				desc.setUserPrmData(slaveConf.gsd.getUserPrmData())
			desc.setSyncMode(bool(slaveConf.syncMode))
			desc.setFreezeMode(bool(slaveConf.freezeMode))
			desc.setGroupMask(int(slaveConf.groupMask))
			desc.setWatchdog(int(slaveConf.watchdogMs))
			desc._awlsimSlaveConf = slaveConf
			self.master.addSlave(desc)

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
			import pyprofibus.phy_serial, pyprofibus.phy_dummy
			self.pyprofibus = pyprofibus
		except (ImportError, RuntimeError) as e:
			self.raiseException("Failed to import PROFIBUS protocol stack "
				"module 'pyprofibus':\n%s" % str(e))

		# Initialize the DPM
		self.phy = None
		self.master = None
		try:
			self.__conf = self.pyprofibus.PbConf.fromFile(
					self.getParamValueByName("config"))

			phyType = self.__conf.phyType.lower().strip()
			if phyType == "serial":
				self.phy = self.pyprofibus.phy_serial.CpPhySerial(
						debug = (self.__conf.debug >= 2),
						port = self.__conf.phyDev)
			elif phyType == "dummy_slave":
				self.phy = self.pyprofibus.phy_dummy.CpPhyDummySlave(
						debug = (self.__conf.debug >= 2))
			else:
				self.raiseException("Invalid phyType parameter value")
			self.phy.setConfig(baudrate = self.__conf.phyBaud)

			if self.__conf.dpMasterClass == 1:
				DPM_cls = self.pyprofibus.DPM1
			else:
				DPM_cls = self.pyprofibus.DPM2
			self.master = DPM_cls(phy = self.phy,
					      masterAddr = self.__conf.dpMasterAddr,
					      debug = (self.__conf.debug >= 1))

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
		except self.pyprofibus.conf.PbConfError as e:
			self.raiseException("Profibus configuration error: %s" % str(e))
			self.__cleanup()

	def doShutdown(self):
		self.__cleanup()

	def readInputs(self): #+cdef
		address = self.inputAddressBase
		for slave in self.slaveList:
			# Get the cached slave-data
			if not self.cachedInputs:
				break
			inputSize = slave._awlsimSlaveConf.inputSize
			inData = self.cachedInputs.pop(0)
			if not inData:
				continue
			inData = bytearray(inData)
			if len(inData) > inputSize:
				inData = inData[0:inputSize]
			if len(inData) < inputSize:
				inData += b'\0' * (inputSize - len(inData))
			self.sim.cpu.storeInputRange(address, inData)
			# Adjust the address base for the next slave.
			address += inputSize
		assert(not self.cachedInputs)

	def writeOutputs(self): #+cdef
		try:
			address = self.outputAddressBase
			for slave in self.slaveList:
				# Get the output data from the CPU
				outputSize = slave._awlsimSlaveConf.outputSize
				outData = self.sim.cpu.fetchOutputRange(address,
						outputSize)
				# Send it to the slave and request the input data.
				inData = self.master.runSlave(slave, outData)
				# Cache the input data for the readInputs() call.
				self.cachedInputs.append(inData)
				# Adjust the address base for the next slave.
				address += outputSize
		except self.pyprofibus.ProfibusError as e:
			self.raiseException("Hardware error: %s" % str(e))

	def directReadInput(self, accessWidth, accessOffset): #@nocy
#@cy	cdef bytearray directReadInput(self, uint32_t accessWidth, uint32_t accessOffset):
		return bytearray()#TODO

	def directWriteOutput(self, accessWidth, accessOffset, data): #@nocy
#@cy	cdef ExBool_t directWriteOutput(self, uint32_t accessWidth, uint32_t accessOffset, bytearray data) except ExBool_val:
		return False#TODO

# Module entry point
HardwareInterface = HardwareInterface_PyProfibus

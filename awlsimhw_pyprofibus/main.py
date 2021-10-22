# -*- coding: utf-8 -*-
#
# AWL simulator - PyProfibus hardware interface
#
# Copyright 2013-2021 Michael Buesch <m@bues.ch>
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

#from awlsimhw_pyprofibus.main cimport * #@cy

from awlsim.core.hardware_params import *
from awlsim.core.hardware import * #+cimport
from awlsim.core.operators import * #+cimport
from awlsim.core.offset import * #+cimport
from awlsim.core.cpu import * #+cimport


class HardwareInterface_PyProfibus(AbstractHardwareInterface): #+cdef
	name		= "PyProfibus"
	description	= "PROFIBUS-DP support with PyProfibus.\n"\
			  "https://bues.ch/a/profibus"

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
			slaveDesc = slaveConf.makeDpSlaveDesc()
			if slaveConf.gsd.isDPV1():
				slaveDesc.setUserPrmData(slaveConf.gsd.getUserPrmData(
						dp1PrmMask=dp1PrmMask,
						dp1PrmSet=dp1PrmSet))
			self.master.addSlave(slaveDesc)

	def __cleanup(self):
		if self.master:
			self.master.destroy()
		self.master = None
		self.cachedInputs = [None] * (0x7F + 1)

	def doStartup(self):
		# Import the PROFIBUS hardware access modules
		# and keep references to it.
		try:
			import pyprofibus
			self.pyprofibus = pyprofibus
		except (ImportError, RuntimeError) as e: #@nocov
			self.raiseException("Failed to import PROFIBUS protocol stack "
				"module 'pyprofibus':\n%s" % str(e))

		# Initialize the DPM
		self.master = None
		try:
			self.__conf = self.pyprofibus.PbConf.fromFile(
					self.getParamValueByName("config"))
			self.master = self.__conf.makeDPM()
			self.__setupSlaves()
			self.master.initialize()

			self.slaveList = self.master.getSlaveList()
			self.cachedInputs = [None] * (0x7F + 1)

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
			inData = self.cachedInputs[slave.slaveAddr]
			if inData is None:
				continue
			self.cachedInputs[slave.slaveAddr] = None
			outputSize = slave.slaveConf.outputSize
			assert len(inData) == outputSize
			self.sim.cpu.storeInputRange(address, bytearray(inData))
			# Adjust the address base for the next slave.
			address += outputSize

	def writeOutputs(self): #+cdef
		try:
			address = self.outputAddressBase
			for slave in self.slaveList:
				# Get the output data from the CPU
				inputSize = slave.slaveConf.inputSize
				outData = self.sim.cpu.fetchOutputRange(address, inputSize)
				# Write the output data to the pyprofibus subsystem.
				slave.setMasterOutData(outData)
				# Adjust the address base for the next slave.
				address += inputSize
			# Run the pyprofibus master state machine.
			slave = self.master.run()
			if slave:
				# Get the input data from the pyprofibus subsystem.
				inData = slave.getMasterInData()
				# Cache the input data for the readInputs() call.
				self.cachedInputs[slave.slaveAddr] = inData
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

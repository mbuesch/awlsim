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

import re

if isPy2Compat:
	from ConfigParser import SafeConfigParser as _ConfigParser
	from ConfigParser import Error as _ConfigParserError
else:
	from configparser import ConfigParser as _ConfigParser
	from configparser import Error as _ConfigParserError


class HardwareInterface(AbstractHardwareInterface):
	name = "PyProfibus"

	# Hardware-specific parameters
	paramDescs = [
		HwParamDesc_str("config",
				defaultValue = "awlsimhw_pyprofibus.conf",
				description = "Awlsim pyprofibus module config file."),
	]

	class _SlaveConf(object):
		addr = None
		gsd = None
		sync_mode = None
		freeze_mode = None
		group_mask = None
		watchdog_ms = None
		input_size = None
		output_size = None

	def __init__(self, sim, parameters={}):
		AbstractHardwareInterface.__init__(self,
						   sim = sim,
						   parameters = parameters)

	__reSlave = re.compile(r'^SLAVE_(\d+)$')
	__reMod = re.compile(r'^module_(\d+)$')

	def __parseConfig(self, filename):
		try:
			text = awlFileRead(filename, encoding="UTF-8")
			p = _ConfigParser()
			p.readfp(StringIO(text), filename)

			self.__debug = p.getint("PROFIBUS", "debug",
						fallback = 0)

			self.__phyType = p.get("PHY", "type",
					       fallback = "serial")
			self.__phyDev = p.get("PHY", "dev",
					      fallback = "/dev/ttyS0")
			self.__phyBaud = p.getint("PHY", "baud",
						  fallback = 19200)

			self.__dpMasterClass = p.getint("DP", "master_class",
							fallback = 1)
			if self.__dpMasterClass not in {1, 2}:
				raise ValueError("Invalid master_class")
			self.__dpMasterAddr = p.getint("DP", "master_addr",
						       fallback = 0x02)
			if self.__dpMasterAddr < 0 or self.__dpMasterAddr > 127:
				raise ValueError("Invalid master_addr")

			self.__slaveConfs = []
			for section in p.sections():
				m = self.__reSlave.match(section)
				if not m:
					continue
				s = self._SlaveConf()
				s.addr = p.getint(section, "addr")
				s.gsd = self.pyprofibus.gsd.interp.GsdInterp.fromFile(
					p.get(section, "gsd"))
				s.sync_mode = p.getboolean(section, "sync_mode",
							   fallback = False)
				s.freeze_mode = p.getboolean(section, "freeze_mode",
							     fallback = False)
				s.group_mask = p.getboolean(section, "group_mask",
							    fallback = 1)
				if s.group_mask < 0 or s.group_mask > 0xFF:
					raise ValueError("Invalid group_mask")
				s.watchdog_ms = p.getint(section, "watchdog_ms",
							 fallback = 5000)
				if s.watchdog_ms < 0 or s.watchdog_ms > 255 * 255:
					raise ValueError("Invalid watchdog_ms")
				s.input_size = p.getint(section, "input_size")
				if s.input_size < 0 or s.input_size > 246:
					raise ValueError("Invalid input_size")
				s.output_size = p.getint(section, "output_size")
				if s.output_size < 0 or s.output_size > 246:
					raise ValueError("Invalid output_size")

				mods = [ o for o in p.options(section)
					 if self.__reMod.match(o) ]
				mods.sort(key = lambda o: self.__reMod.match(o).group(1))
				for option in mods:
					s.gsd.setConfiguredModule(p.get(section, option))

				self.__slaveConfs.append(s)

		except (_ConfigParserError, AwlParserError, ValueError) as e:
			self.raiseException("Profibus config file parse "
				"error:\n%s" % str(e))
		except self.pyprofibus.gsd.parser.GsdError as e:
			self.raiseException("Failed to parse GSD file:\n%s" % str(e))

	def __setupSlaves(self):
		setPrmReq = self.pyprofibus.dp.DpTelegram_SetPrm_Req
		dp1PrmMask = bytearray((setPrmReq.DPV1PRM0_FAILSAFE,
					0x00,
					0x00))
		dp1PrmSet  = bytearray((setPrmReq.DPV1PRM0_FAILSAFE,
					0x00,
					0x00))

		for slaveConf in self.__slaveConfs:
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
			desc.setSyncMode(bool(slaveConf.sync_mode))
			desc.setFreezeMode(bool(slaveConf.freeze_mode))
			desc.setGroupMask(int(slaveConf.group_mask))
			desc.setWatchdog(int(slaveConf.watchdog_ms))
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
			import pyprofibus.phy_serial
			import pyprofibus.gsd
			import pyprofibus.gsd.interp
			self.pyprofibus = pyprofibus
		except (ImportError, RuntimeError) as e:
			self.raiseException("Failed to import PROFIBUS protocol stack "
				"module 'pyprofibus':\n%s" % str(e))

		# Initialize the DPM
		self.phy = None
		self.master = None
		try:
			self.__parseConfig(self.getParamValueByName("config"))

			if self.__phyType.lower() == "serial":
				self.phy = self.pyprofibus.phy_serial.CpPhySerial(
						debug = (self.__debug >= 2),
						port = self.__phyDev)
				self.phy.setConfig(baudrate = self.__phyBaud)
			else:
				self.raiseException("Invalid phyType parameter value")

			if self.__dpMasterClass == 1:
				DPM_cls = self.pyprofibus.DPM1
			else:
				DPM_cls = self.pyprofibus.DPM2
			self.master = DPM_cls(phy = self.phy,
					      masterAddr = self.__dpMasterAddr,
					      debug = (self.__debug >= 1))

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
			if not self.cachedInputs:
				break
			inputSize = slave._awlsimSlaveConf.input_size
			inData = self.cachedInputs.pop(0)
			if not inData:
				continue
			if len(inData) > inputSize:
				inData = inData[0:inputSize]
			if len(inData) < inputSize:
				inData += b'\0' * (inputSize - len(inData))
			self.sim.cpu.storeInputRange(address, inData)
			# Adjust the address base for the next slave.
			address += inputSize
		assert(not self.cachedInputs)

	def writeOutputs(self):
		try:
			address = self.outputAddressBase
			for slave in self.slaveList:
				# Get the output data from the CPU
				outputSize = slave._awlsimSlaveConf.output_size
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

	def directReadInput(self, accessWidth, accessOffset):
		return None#TODO

	def directWriteOutput(self, accessWidth, accessOffset, data):
		return False#TODO

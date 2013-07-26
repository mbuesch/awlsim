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

from awlsim.hardware import *
from awlsim.util import *

try:
	import pyprofibus.dp_master as DPM
	import pyprofibus.dp as DP
	import pyprofibus.fdl as FDL
	import pyprofibus.phy as PHY
except (ImportError, RuntimeError) as e:
	raise AwlSimError("Failed to import PROFIBUS protocol stack "
		"module 'pyprofibus':\n%s" % str(e))


class HardwareInterface(AbstractHardwareInterface):
	name = "PyProfibus"

	def __init__(self, sim, parameters={}):
		AbstractHardwareInterface.__init__(self,
						   sim = sim,
						   parameters = parameters)
		self.__parseParameters()

	def __parseParameters(self):
		self.param_debug = self.getParam_int("debug", minValue = 0)
		self.param_masterClass = self.getParam_int("masterClass",
					defaultValue = 1,
					minValue = 1, maxValue = 2)
		self.param_masterAddr = self.getParam_int("masterAddr",
					defaultValue = 1,
					minValue = 0, maxValue = 126)
		self.param_spiDev = self.getParam_int("spiDev", minValue = 0)
		self.param_spiChip = self.getParam_int("spiChip", minValue = 0)

	def __setupSlaves(self):
		#TODO: Rewrite. Must be configurable.
		et200s = DPM.DpSlaveDesc(identNumber = 0x806A,
					 slaveAddr = 8)
		for elem in (DP.DpCfgDataElement(0),
			     DP.DpCfgDataElement(0x20),
			     DP.DpCfgDataElement(0x20),
			     DP.DpCfgDataElement(0x10)):
			et200s.chkCfgTelegram.addCfgDataElement(elem)
		et200s.setPrmTelegram.addUserPrmData([0x11 | 0x40])
		et200s.setSyncMode(True)
		et200s.setFreezeMode(True)
		et200s.setGroupMask(1)
		et200s.setWatchdog(300)
		self.master.addSlave(et200s)

	def __cleanup(self):
		if self.master:
			self.master.destroy()
		self.master = None
		self.phy = None

	def doStartup(self):
		self.phy = None
		self.master = None
		try:
			self.phy = PHY.CpPhy(device = self.param_spiDev,
					     chipselect = self.param_spiChip,
					     debug = True if (self.param_debug >= 2) else False)
			if self.param_masterClass == 1:
				DPM_cls = DPM.DPM1
			else:
				DPM_cls = DPM.DPM2
			self.master = DPM_cls(phy = self.phy,
					      masterAddr = self.param_masterAddr,
					      debug = True if (self.param_debug >= 1) else False)
			self.__setupSlaves()
			self.master.initialize()
		except PHY.PhyError as e:
			self.raiseException("PHY error: %s" % str(e))
			self.__cleanup()
		except DP.DpError as e:
			self.raiseException("Profibus-DP error: %s" % str(e))
			self.__cleanup()
		except FDL.FdlError as e:
			self.raiseException("Fieldbug Data Link error: %s" % str(e))
			self.__cleanup()

	def doShutdown(self):
		self.__cleanup()

	def readInputs(self):
		pass#TODO

	def writeOutputs(self):
		pass#TODO

	def directReadInput(self, accessWidth, accessOffset):
		return None#TODO

	def directWriteOutput(self, accessWidth, accessOffset, data):
		return False#TODO

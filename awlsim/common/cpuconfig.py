# -*- coding: utf-8 -*-
#
# AWL simulator - CPU core configuration
#
# Copyright 2012-2017 Michael Buesch <m@bues.ch>
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

from awlsim.common.enumeration import *
from awlsim.common.exceptions import *


__all__ = [ "S7CPUConfig", ]


class S7CPUConfig(object):
	"""STEP 7 CPU core configuration"""

	# Mnemonic identifiers
	# Note: These numbers are .awlpro file ABI.
	EnumGen.start
	MNEMONICS_AUTO		= EnumGen.item
	MNEMONICS_EN		= EnumGen.item
	MNEMONICS_DE		= EnumGen.item
	EnumGen.end

	DEFAULT_MNEMONICS	= MNEMONICS_AUTO
	DEFAULT_CLOCKMEM	= -1

	def __init__(self, cpu=None):
		self.cpu = None
		self.setConfiguredMnemonics(self.DEFAULT_MNEMONICS)
		self.setClockMemByte(self.DEFAULT_CLOCKMEM)
		self.cpu = cpu

	def assignFrom(self, otherCpuConfig):
		self.setConfiguredMnemonics(otherCpuConfig.getConfiguredMnemonics())
		self.setClockMemByte(otherCpuConfig.clockMemByte)

	def setConfiguredMnemonics(self, mnemonics):
		if mnemonics not in (self.MNEMONICS_AUTO,
				     self.MNEMONICS_EN,
				     self.MNEMONICS_DE):
			raise AwlSimError("Invalid mnemonics configuration: %d" % mnemonics)
		self.__configuredMnemonics = mnemonics
		self.setDetectedMnemonics(self.MNEMONICS_AUTO)

	def setDetectedMnemonics(self, mnemonics):
		self.__detectedMnemonics = mnemonics

	def getConfiguredMnemonics(self):
		return self.__configuredMnemonics

	def getMnemonics(self):
		if self.__configuredMnemonics == self.MNEMONICS_AUTO:
			return self.__detectedMnemonics
		return self.__configuredMnemonics

	def setClockMemByte(self, byteAddress):
		self.clockMemByte = byteAddress
		if self.cpu:
			self.cpu.initClockMemState()

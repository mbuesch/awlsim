# -*- coding: utf-8 -*-
#
# AWL simulator - CPU
#
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
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

from awlsim.core.util import *


class S7CPUSpecs(object):
	"STEP 7 CPU Specifications"

	EnumGen.start
	MNEMONICS_AUTO		= EnumGen.item
	MNEMONICS_EN		= EnumGen.item
	MNEMONICS_DE		= EnumGen.item
	EnumGen.end

	def __init__(self, cpu=None):
		self.cpu = None
		self.setConfiguredMnemonics(self.MNEMONICS_AUTO)
		self.setNrAccus(2)
		self.setNrTimers(2048)
		self.setNrCounters(2048)
		self.setNrFlags(8192)
		self.setNrInputs(8192)
		self.setNrOutputs(8192)
		self.setNrLocalbytes(1024)
		self.cpu = cpu

	def assignFrom(self, otherCpuSpecs):
		self.setConfiguredMnemonics(otherCpuSpecs.getConfiguredMnemonics())
		self.setNrAccus(otherCpuSpecs.nrAccus)
		self.setNrTimers(otherCpuSpecs.nrTimers)
		self.setNrCounters(otherCpuSpecs.nrCounters)
		self.setNrFlags(otherCpuSpecs.nrFlags)
		self.setNrInputs(otherCpuSpecs.nrInputs)
		self.setNrOutputs(otherCpuSpecs.nrOutputs)
		self.setNrLocalbytes(otherCpuSpecs.nrLocalbytes)

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

	def setNrAccus(self, count):
		if count not in (2, 4):
			raise AwlSimError("Invalid number of accus")
		self.nrAccus = count
		if self.cpu:
			self.cpu.reallocate()

	def setNrTimers(self, count):
		self.nrTimers = count
		if self.cpu:
			self.cpu.reallocate()

	def setNrCounters(self, count):
		self.nrCounters = count
		if self.cpu:
			self.cpu.reallocate()

	def setNrFlags(self, count):
		self.nrFlags = count
		if self.cpu:
			self.cpu.reallocate()

	def setNrInputs(self, count):
		self.nrInputs = count
		if self.cpu:
			self.cpu.reallocate()

	def setNrOutputs(self, count):
		self.nrOutputs = count
		if self.cpu:
			self.cpu.reallocate()

	def setNrLocalbytes(self, count):
		self.nrLocalbytes = count
		if self.cpu:
			self.cpu.reallocate()

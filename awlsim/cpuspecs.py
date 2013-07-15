# -*- coding: utf-8 -*-
#
# AWL simulator - CPU
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from awlsim.util import *


class S7CPUSpecs(object):
	"STEP 7 CPU Specifications"

	enum.start
	MNEMONICS_AUTO		= enum.item
	MNEMONICS_EN		= enum.item
	MNEMONICS_DE		= enum.item
	enum.end

	def __init__(self, cpu):
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

	def setConfiguredMnemonics(self, mnemonics):
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

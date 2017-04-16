# -*- coding: utf-8 -*-
#
# AWL simulator - CPU core feature specification
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


__all__ = [ "S7CPUSpecs", ]


class S7CPUSpecs(object):
	"""STEP 7 CPU core specifications"""

	def __init__(self, cpu=None):
		self.cpu = None
		self.setNrAccus(2)
		self.setNrTimers(2048)
		self.setNrCounters(2048)
		self.setNrFlags(8192)
		self.setNrInputs(8192)
		self.setNrOutputs(8192)
		self.setNrLocalbytes(2048)
		self.cpu = cpu

	def assignFrom(self, otherCpuSpecs):
		self.setNrAccus(otherCpuSpecs.nrAccus)
		self.setNrTimers(otherCpuSpecs.nrTimers)
		self.setNrCounters(otherCpuSpecs.nrCounters)
		self.setNrFlags(otherCpuSpecs.nrFlags)
		self.setNrInputs(otherCpuSpecs.nrInputs)
		self.setNrOutputs(otherCpuSpecs.nrOutputs)
		self.setNrLocalbytes(otherCpuSpecs.nrLocalbytes)

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

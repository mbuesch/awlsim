# -*- coding: utf-8 -*-
#
# AWL simulator
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

from awlsim.cpu import *
from awlsim.util import *


VERSION_MAJOR = 0
VERSION_MINOR = 13


class AwlSim(object):
	def __init__(self):
		self.cpu = S7CPU(self)

	def __handleSimException(self, e):
		if not e.getCpu():
			# The CPU reference is not set, yet.
			# Set it to the current CPU.
			e.setCpu(self.cpu)
		raise e

	def load(self, parseTree):
		try:
			self.cpu.load(parseTree)
			self.cpu.startup()
		except AwlSimError as e:
			self.__handleSimException(e)

	def getCPU(self):
		return self.cpu

	def runCycle(self):
		try:
			self.cpu.runCycle()
		except AwlSimError as e:
			self.__handleSimException(e)

	def __repr__(self):
		return str(self.cpu)

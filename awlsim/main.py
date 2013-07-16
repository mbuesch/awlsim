# -*- coding: utf-8 -*-
#
# AWL simulator
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from awlsim.cpu import *
from awlsim.util import *


VERSION_MAJOR = 0
VERSION_MINOR = 12


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

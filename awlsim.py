# -*- coding: utf-8 -*-
#
# AWL simulator
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from awlcpu import *
from util import *


VERSION_MAJOR = 0
VERSION_MINOR = 6


class AwlSim(object):
	def __init__(self):
		self.cpu = S7CPU(self)

	def load(self, parseTree):
		self.cpu.load(parseTree)
		self.cpu.startup()

	def getCPU(self):
		return self.cpu

	def runCycle(self):
		ex = None
		try:
			self.cpu.runCycle()
		except AwlSimError as e:
			ex = e
		if ex:
			raise AwlSimError("ERROR at AWL line %d: %s\n\n%s" %\
				(self.cpu.getCurrentInsn().getLineNr(),
				 str(ex), str(self.cpu)))

	def __repr__(self):
		return str(self.cpu)

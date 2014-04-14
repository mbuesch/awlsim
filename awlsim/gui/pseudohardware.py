# -*- coding: utf-8 -*-
#
# AWL simulator - GUI pseudo hardware interface
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

from awlsim.gui.util import *


class GuiPseudoHardwareInterface(AbstractHardwareInterface):
	"""Input/output to the CPU is handled by this pseudo
	hardware interface."""

	name = "GUI"

	def __init__(self, sim, cpuWidget):
		AbstractHardwareInterface.__init__(self, sim = sim)
		self.cpuWidget = cpuWidget
		self.cpu = cpuWidget.sim.getCPU()

		self.__nextUpdate = 0.0

	def readInputs(self):
		# Read the "hardware inputs" a.k.a. GUI buttons.
		# This is done by processing the queued store-requests.
		for storeRequest in self.cpuWidget.getQueuedStoreRequests():
			try:
				self.cpu.store(storeRequest.operator,
					       storeRequest.value)
			except AwlSimError as e:
				if storeRequest.failureCallback:
					storeRequest.failureCallback()

	def writeOutputs(self):
		# Write the "hardware outputs" a.k.a. GUI display elements.
		# This is only done one in a while for performance reasons.
		if self.cpu.now >= self.__nextUpdate:
			self.__nextUpdate = self.cpu.now + 0.15
			self.cpuWidget.update()

	def directReadInput(self, accessWidth, accessOffset):
		#TODO: Read input widgets. As workaround we just read the current CPU value.
		return self.sim.cpu.fetch(AwlOperator(AwlOperator.MEM_E,
						      accessWidth,
						      AwlOffset(accessOffset)))

	def directWriteOutput(self, accessWidth, accessOffset, data):
		#TODO: Trigger output widgets update.
		return True

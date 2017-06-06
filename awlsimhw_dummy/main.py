# -*- coding: utf-8 -*-
#
# AWL simulator - Dummy hardware interface
#
# Copyright 2013-2017 Michael Buesch <m@bues.ch>
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

from awlsim.common.util import *
from awlsim.common.exceptions import *

#from awlsimhw_dummy.main cimport * #@cy

from awlsim.core.hardware_params import *
from awlsim.core.hardware import * #+cimport
from awlsim.core.operators import * #+cimport
from awlsim.core.offset import * #+cimport
from awlsim.core.cpu import * #+cimport


class HardwareInterface_Dummy(AbstractHardwareInterface): #+cdef
	name = "dummy"

	def __init__(self, sim, parameters={}):
		AbstractHardwareInterface.__init__(self,
						   sim = sim,
						   parameters = parameters)

	def doStartup(self):
		pass # Do nothing

	def doShutdown(self):
		pass # Do nothing

	def readInputs(self): #+cdef
		pass # Do nothing

	def writeOutputs(self): #+cdef
		pass # Do nothing

	def directReadInput(self, accessWidth, accessOffset): #@nocy
#@cy	cdef bytearray directReadInput(self, uint32_t accessWidth, uint32_t accessOffset):
		if accessOffset < self.inputAddressBase:
			return bytearray()
		# Just read the current value from the CPU and return it.
		try:
			return self.sim.cpu.fetchInputRange(accessOffset, accessWidth // 8)
		except AwlSimError as e:
			# We may be out of process image range. Just return 0.
			return bytearray( (0,) * (accessWidth // 8) )

	def directWriteOutput(self, accessWidth, accessOffset, data): #@nocy
#@cy	cdef ExBool_t directWriteOutput(self, uint32_t accessWidth, uint32_t accessOffset, bytearray data) except ExBool_val:
		if accessOffset < self.outputAddressBase:
			return False
		# Just pretend we wrote it somewhere.
		return True

# Module entry point
HardwareInterface = HardwareInterface_Dummy

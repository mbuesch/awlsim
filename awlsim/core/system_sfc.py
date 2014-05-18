# -*- coding: utf-8 -*-
#
# AWL simulator - SFCs
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

from awlsim.core.systemblocks import *
from awlsim.core.util import *


class SFCm1(SFC):
	"""SFC -1: __NOP"""

	def __init__(self, cpu):
		SFC.__init__(self, cpu, -1)

	def run(self):
		pass # No operation

class SFCm2(SFC):
	"""SFC -2: __REBOOT"""

	def __init__(self, cpu):
		SFC.__init__(self, cpu, -2)

		self.interface.addField_IN(
			BlockInterfaceField(name = "REBOOT_TYPE",
					    dataType = AwlDataType.makeByName("INT"))
		)

	def run(self):
		rebootType = wordToSignedPyInt(self.fetchInterfaceFieldByName("REBOOT_TYPE"))
		if rebootType == 1:
			raise MaintenanceRequest(MaintenanceRequest.TYPE_SOFTREBOOT,
						 "SFC -2 soft reboot request")
		else:
			raise AwlSimError("SFC -2: Unknown REBOOT_TYPE %d" % rebootType)

class SFCm3(SFC):
	"""SFC -3: __SHUTDOWN"""

	def __init__(self, cpu):
		SFC.__init__(self, cpu, -3)

		self.interface.addField_IN(
			BlockInterfaceField(name = "SHUTDOWN_TYPE",
					    dataType = AwlDataType.makeByName("INT"))
		)

	def run(self):
		shutdownType = wordToSignedPyInt(self.fetchInterfaceFieldByName("SHUTDOWN_TYPE"))
		if shutdownType == 1:
			raise MaintenanceRequest(MaintenanceRequest.TYPE_SHUTDOWN,
						 "SFC -3 shutdown request")
		else:
			raise AwlSimError("SFC -3: Unknown SHUTDOWN_TYPE %d" % shutdownType)

class SFC64(SFC):
	"""SFC 64: TIME_TCK"""

	def __init__(self, cpu):
		SFC.__init__(self, cpu, 64)

		self.interface.addField_OUT(
			BlockInterfaceField(name = "RET_VAL",
					    dataType = AwlDataType.makeByName("TIME"))
		)

	def run(self):
		# Return a 31-bit millisecond representation of "now".
		self.storeInterfaceFieldByName("RET_VAL",
			int(self.cpu.now * 1000) & 0x7FFFFFFF)

SFC_table = {
	-1	: SFCm1,
	-2	: SFCm2,
	-3	: SFCm3,

	64	: SFC64,
}

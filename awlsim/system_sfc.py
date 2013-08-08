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

from awlsim.systemblocks import *
from awlsim.util import *


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
			BlockInterface.Field(name = "REBOOT_TYPE",
					     dataType = AwlDataType.makeByName("INT"))
		)

	def run(self):
		pass#TODO REBOOT_TYPE
		raise SoftRebootRequest("SFC -2 soft reboot request")

class SFC64(SFC):
	def __init__(self, cpu):
		SFC.__init__(self, cpu, 64)

	def run(self):
		pass#TODO

SFC_table = {
	-1	: SFCm1,
	-2	: SFCm2,

	64	: SFC64,
}

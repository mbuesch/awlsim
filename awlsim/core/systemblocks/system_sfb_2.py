# -*- coding: utf-8 -*-
#
# AWL simulator - SFBs
#
# Copyright 2014 Michael Buesch <m@bues.ch>
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

from awlsim.core.systemblocks.systemblocks import *
from awlsim.core.util import *


class SFB2(SFB):
	name = (2, "CTUD", "IEC 1131-3 up/down counter")

	interfaceFields = {
		BlockInterfaceField.FTYPE_IN	: (
			BlockInterfaceField(name = "CU",
					    dataType = AwlDataType.makeByName("BOOL")),
			BlockInterfaceField(name = "CD",
					    dataType = AwlDataType.makeByName("BOOL")),
			BlockInterfaceField(name = "R",
					    dataType = AwlDataType.makeByName("BOOL")),
			BlockInterfaceField(name = "LOAD",
					    dataType = AwlDataType.makeByName("BOOL")),
			BlockInterfaceField(name = "PV",
					    dataType = AwlDataType.makeByName("INT")),
		),
		BlockInterfaceField.FTYPE_OUT	: (
			BlockInterfaceField(name = "QU",
					    dataType = AwlDataType.makeByName("BOOL")),
			BlockInterfaceField(name = "QD",
					    dataType = AwlDataType.makeByName("BOOL")),
			BlockInterfaceField(name = "CV",
					    dataType = AwlDataType.makeByName("INT")),
		),
		BlockInterfaceField.FTYPE_STAT	: (
			BlockInterfaceField(name = "CUO",
					    dataType = AwlDataType.makeByName("BOOL")),
			BlockInterfaceField(name = "CDO",
					    dataType = AwlDataType.makeByName("BOOL")),
		),
	}

	def run(self):
		pass#TODO
		raise AwlSimError("SFB 2 \"CTUD\" not implemented, yet.")

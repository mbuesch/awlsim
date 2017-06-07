# -*- coding: utf-8 -*-
#
# AWL simulator - SFCs
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

from awlsim.common.datatypehelpers import * #+cimport
from awlsim.common.exceptions import *

from awlsim.core.systemblocks.systemblocks import * #+cimport
from awlsim.core.blockinterface import *
from awlsim.core.datatypes import *
from awlsim.core.util import *


class SFCm3(SFC): #+cdef
	name = (-3, "__SHUTDOWN", None)

	interfaceFields = {
		BlockInterfaceField.FTYPE_IN	: (
			BlockInterfaceField(name="SHUTDOWN_TYPE", dataType="INT"),
		),
	}

	def run(self): #+cpdef
		shutdownType = wordToSignedPyInt(self.fetchInterfaceFieldByName("SHUTDOWN_TYPE"))
		if shutdownType == 1:
			raise MaintenanceRequest(MaintenanceRequest.TYPE_SHUTDOWN,
						 "SFC -3 shutdown request")
		elif shutdownType == 2:
			raise MaintenanceRequest(MaintenanceRequest.TYPE_STOP,
						 "SFC -3 stop request")
		else:
			raise AwlSimError("SFC -3: Unknown SHUTDOWN_TYPE %d" % shutdownType)

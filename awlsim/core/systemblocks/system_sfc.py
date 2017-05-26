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

from awlsim.core.systemblocks.system_sfc_m4 import * #+cimport
from awlsim.core.systemblocks.system_sfc_m3 import * #+cimport
from awlsim.core.systemblocks.system_sfc_m2 import * #+cimport
from awlsim.core.systemblocks.system_sfc_m1 import * #+cimport
from awlsim.core.systemblocks.system_sfc_21 import * #+cimport
from awlsim.core.systemblocks.system_sfc_46 import * #+cimport
from awlsim.core.systemblocks.system_sfc_47 import * #+cimport
from awlsim.core.systemblocks.system_sfc_64 import * #+cimport

__all__ = [
	"_SFC_table",
]

_SFC_table = { #+cdef-dict
	-4	: SFCm4,	# __CLKRST
	-3	: SFCm3,	# __SHUTDOWN
	-2	: SFCm2,	# __REBOOT
	-1	: SFCm1,	# __SFC_NOP

	21	: SFC21,	# FILL
	46	: SFC46,	# STP
	47	: SFC47,	# WAIT
	64	: SFC64,	# TIME_TCK
}

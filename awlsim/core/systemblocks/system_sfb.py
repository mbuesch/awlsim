# -*- coding: utf-8 -*-
#
# AWL simulator - SFBs
#
# Copyright 2012-2014 Michael Buesch <m@bues.ch>
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

from awlsim.core.systemblocks.system_sfb_m1 import *
from awlsim.core.systemblocks.system_sfb_0 import *
from awlsim.core.systemblocks.system_sfb_1 import *
from awlsim.core.systemblocks.system_sfb_2 import *
from awlsim.core.systemblocks.system_sfb_3 import *
from awlsim.core.systemblocks.system_sfb_4 import *
from awlsim.core.systemblocks.system_sfb_5 import *


SFB_table = {
	-1	: SFBm1,	# __NOP
	0	: SFB0,		# CTU
	1	: SFB1,		# CTD
	2	: SFB2,		# CTUD
	3	: SFB3,		# TP
	4	: SFB4,		# TON
	5	: SFB5,		# TOF
}

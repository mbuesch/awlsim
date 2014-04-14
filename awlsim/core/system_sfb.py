# -*- coding: utf-8 -*-
#
# AWL simulator - SFBs
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


class SFBm1(SFB):
	"""SFB -1: __NOP"""

	def __init__(self, cpu):
		SFB.__init__(self, cpu, -1)

	def run(self):
		pass # No operation

SFB_table = {
	-1	: SFBm1,
}

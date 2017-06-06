# -*- coding: utf-8 -*-
#
# AWL simulator - System error codes
#
# Copyright 2016 Michael Buesch <m@bues.ch>
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

from awlsim.common.exceptions import *


class SystemErrCode(object):
	"""Error codes used in system blocks RET_VALs.
	"""

	# Error code bases
	E_INTERNAL	= 0x807F # Internal error
	E_ANYSYNT	= 0x8001 # Invalid syntax code in ANY
	E_RLEN		= 0x8022 # Area length error on read access
	E_WLEN		= 0x8023 # Area length error on write access
	E_RAREA		= 0x8024 # Area error on read access
	E_WAREA		= 0x8025 # Area error on write access
	E_TNOTEXIST	= 0x8026 # Timer does not exist
	E_ZNOTEXIST	= 0x8027 # Counter does not exist
	E_RALIGN	= 0x8028 # Alignment error on read access
	E_WALIGN	= 0x8029 # Alignment error on write access
	E_WPGDB		= 0x8030 # Global DB is write protected
	E_WPIDB		= 0x8031 # Instance DB is write protected
	E_DBINVALID	= 0x8032 # DB number is too big
	E_FCINVALID	= 0x8034 # FC number is too big
	E_FBINVALID	= 0x8035 # FB number is too big
	E_DBNOTEXIST	= 0x803A # DB number is not loaded
	E_FCNOTEXIST	= 0x803C # FC number is not loaded
	E_FBNOTEXIST	= 0x803E # FB number is not loaded
	E_PAE		= 0x8042 # Peripheral input read error
	E_PAA		= 0x8043 # Peripheral output write error
	E_RPARM		= 0x8044 # Read access to parameter failed
	E_WPARM		= 0x8045 # Write access to parameter failed


	@classmethod
	def make(cls, baseCode, parameterNr = 0):
		"""baseCode -> The error code base.
		parameterNr -> The number of the parameter that caused
		the error. Starting at 1.
		"""
		return (baseCode & 0xF0FF) | ((parameterNr << 8) & 0x0F00)

# -*- coding: utf-8 -*-
#
# AWL simulator - SFBs
#
# Copyright 2014-2015 Michael Buesch <m@bues.ch>
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

from awlsim.core.systemblocks.systemblocks import *
from awlsim.core.util import *


class SFB5(SFB):
	name = (5, "TOF", "IEC 1131-3 delayed reset")

	interfaceFields = {
		BlockInterfaceField.FTYPE_IN	: (
			BlockInterfaceField(name = "IN",
					    dataType = AwlDataType.makeByName("BOOL")),
			BlockInterfaceField(name = "PT",
					    dataType = AwlDataType.makeByName("TIME")),
		),
		BlockInterfaceField.FTYPE_OUT	: (
			BlockInterfaceField(name = "Q",
					    dataType = AwlDataType.makeByName("BOOL")),
			BlockInterfaceField(name = "ET",
					    dataType = AwlDataType.makeByName("TIME")),
		),
		BlockInterfaceField.FTYPE_STAT	: (
			BlockInterfaceField(name = "STATE",
					    dataType = AwlDataType.makeByName("BYTE")),
			BlockInterfaceField(name = "STIME",
					    dataType = AwlDataType.makeByName("TIME")),
			BlockInterfaceField(name = "ATIME",
					    dataType = AwlDataType.makeByName("TIME")),
		),
	}

	# STATE bits
	STATE_PREV_IN		= 1 << 0
	STATE_DELAYING		= 1 << 1

	def run(self):
		s = self.cpu.statusWord
		s.BIE = 1

		PT = dwordToSignedPyInt(self.fetchInterfaceFieldByName("PT"))
		if PT <= 0:
			# Invalid PT. Abort and reset state.
			# A PT of zero is used to reset the timer.
			if PT == 0:
				# S7 resets IN here, for whatever weird reason.
				self.storeInterfaceFieldByName("IN", 0)
			else:
				# Negative PT. This is an error.
				s.BIE = 0
			self.storeInterfaceFieldByName("Q", 0)
			self.storeInterfaceFieldByName("ET", 0)
			self.storeInterfaceFieldByName("STATE", 0)
			return

		# Get the current time, as S7-time value (31-bit milliseconds)
		ATIME = self.cpu.now_TIME

		STATE = self.fetchInterfaceFieldByName("STATE")
		IN = self.fetchInterfaceFieldByName("IN")
		if IN:
			# IN is 1.
			# This sets Q=1 and interrupts any running state.
			STATE &= ~self.STATE_DELAYING
			STATE |= self.STATE_PREV_IN
			self.storeInterfaceFieldByName("STATE", STATE)
			self.storeInterfaceFieldByName("ET", 0)
			self.storeInterfaceFieldByName("Q", 1)
		else:
			if STATE & self.STATE_PREV_IN:
				# Negative edge on IN.
				# This starts the delay. Q will stay 1.
				self.storeInterfaceFieldByName("STIME", ATIME)
				STATE |= self.STATE_DELAYING
			STATE &= ~self.STATE_PREV_IN
			self.storeInterfaceFieldByName("STATE", STATE)
		if STATE & self.STATE_DELAYING:
			# The delay is running.
			STIME = self.fetchInterfaceFieldByName("STIME")
			self.storeInterfaceFieldByName("ATIME", ATIME)
			ET = (ATIME - STIME) & 0x7FFFFFFF
			if ET >= PT:
				# Time elapsed. Reset Q.
				ET = PT
				self.storeInterfaceFieldByName("Q", 0)
				STATE &= ~self.STATE_DELAYING
				self.storeInterfaceFieldByName("STATE", STATE)
			else:
				self.storeInterfaceFieldByName("Q", 1)
			self.storeInterfaceFieldByName("ET", ET)

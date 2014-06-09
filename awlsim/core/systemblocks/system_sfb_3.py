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


class SFB3(SFB):
	name = (3, "TP", "IEC 1131-3 timed pulse")

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
	STATE_RUNNING		= 1 << 0
	STATE_FINISHED		= 1 << 1

	def run(self):
		PT = dwordToSignedPyInt(self.fetchInterfaceFieldByName("PT"))
		if PT <= 0:
			# Invalid PT. Abort and reset state.
			# A PT of zero is used to reset the timer.
			if PT == 0:
				# S7 resets IN here, for whatever weird reason.
				self.storeInterfaceFieldByName("IN", 0)
			self.storeInterfaceFieldByName("Q", 0)
			self.storeInterfaceFieldByName("ET", 0)
			self.storeInterfaceFieldByName("STATE", 0)
			return

		# Get the current time, as S7-time value (31-bit milliseconds)
		ATIME = int(self.cpu.now * 1000.0) & 0x7FFFFFFF

		STATE = self.fetchInterfaceFieldByName("STATE")
		IN = self.fetchInterfaceFieldByName("IN")
		if IN and not (STATE & (self.STATE_RUNNING | self.STATE_FINISHED)):
			# IN is true and we are not running, yet.
			# Start the timer.
			self.storeInterfaceFieldByName("STIME", ATIME)
			STATE |= self.STATE_RUNNING
			self.storeInterfaceFieldByName("STATE", STATE)
		if STATE & self.STATE_RUNNING:
			# The timer is running.
			STIME = self.fetchInterfaceFieldByName("STIME")
			self.storeInterfaceFieldByName("ATIME", ATIME)
			ET = (ATIME - STIME) & 0x7FFFFFFF
			if ET >= PT:
				# Time elapsed.
				ET = PT
				self.storeInterfaceFieldByName("Q", 0)
				STATE &= ~self.STATE_RUNNING
				STATE |= self.STATE_FINISHED
				self.storeInterfaceFieldByName("STATE", STATE)
			else:
				self.storeInterfaceFieldByName("Q", 1)
			self.storeInterfaceFieldByName("ET", ET)
		if not IN and (STATE & self.STATE_FINISHED):
			# IN is false and we are finished.
			# Shut down the timer.
			STATE &= ~self.STATE_FINISHED
			self.storeInterfaceFieldByName("STATE", STATE)
			self.storeInterfaceFieldByName("ET", 0)

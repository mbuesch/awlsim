# -*- coding: utf-8 -*-
#
# AWL simulator - PLC core server memory area helpers
#
# Copyright 2013 Michael Buesch <m@bues.ch>
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

from awlsim.util import *


class MemoryArea(object):
	enum.start
	TYPE_E		= enum.item # input memory
	TYPE_A		= enum.item # output memory
	TYPE_M		= enum.item # flags memory
	TYPE_L		= enum.item # localdata memory
	TYPE_DB		= enum.item # DB memory
	TYPE_T		= enum.item # timer
	TYPE_Z		= enum.item # counter
	TYPE_STW	= enum.item # status word
	enum.end

	def __init__(self, memType, flags, index, start, length):
		self.memType = memType
		self.flags = flags
		self.index = index
		self.start = start
		self.length = length

class MemoryAreaData(object):
	def __init__(self, memType, flags, index, start, data):
		self.memType = memType
		self.flags = flags
		self.index = index
		self.start = start
		self.data = data

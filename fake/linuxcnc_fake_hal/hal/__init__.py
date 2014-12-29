# -*- coding: utf-8 -*-
#
# LinuxCNC fake Python HAL module for unit testing
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


HAL_BIT		= 1
HAL_FLOAT	= 2
HAL_S32		= 3
HAL_U32		= 4

HAL_IN		= 16
HAL_OUT		= 32
HAL_IO		= HAL_IN | HAL_OUT

HAL_RO		= 64
HAL_RW		= 192


class component(object):
	def __init__(self, name):
		pass

	def newpin(self, p, t, d):
		pass

	def newparam(self, p, t, d):
		pass

	def ready(self):
		pass

	def __getitem__(self, k):
		return 0

	def __setitem__(self, k, v):
		pass

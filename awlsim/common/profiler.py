# -*- coding: utf-8 -*-
#
# AWL simulator - Profiler support
#
# Copyright 2012-2019 Michael Buesch <m@bues.ch>
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
#from awlsim.common.cython_support cimport * #@cy
from awlsim.common.compat import *

from awlsim.common.exceptions import *
from awlsim.common.util import *


__all__ = [
	"Profiler",
]


class Profiler(object):
	__slots__ = (
		"__profileModule",
		"__pstatsModule",
		"__profiler",
		"__enableCount",
	)

	def __init__(self):
		try:
			import cProfile as profileModule
		except ImportError:
			profileModule = None
		self.__profileModule = profileModule
		try:
			import pstats as pstatsModule
		except ImportError:
			pstatsModule = None
		self.__pstatsModule = pstatsModule

		if not self.__profileModule or\
		   not self.__pstatsModule:
			raise AwlSimError("Failed to load cProfile/pstats modules. "
				"Cannot enable profiling.")

		self.__profiler = self.__profileModule.Profile()
		self.__enableCount = 0

	def start(self):
		if self.__enableCount <= 0:
			self.__profiler.enable()
		self.__enableCount += 1

	def stop(self):
		self.__enableCount = max(self.__enableCount - 1, 0)
		if self.__enableCount <= 0:
			self.__profiler.disable()

	def getResult(self):
		sio = StringIO()
		ps = self.__pstatsModule.Stats(self.__profiler,
					       stream=sio)
		ps.sort_stats("time")
		ps.print_stats()
		return sio.getvalue()

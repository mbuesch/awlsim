# -*- coding: utf-8 -*-
#
# AWL simulator - instructions
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

from awlsim.common.exceptions import *

from awlsim.core.instructions.main import * #+cimport
from awlsim.core.operatortypes import * #+cimport
from awlsim.core.operators import * #+cimport

import time


class AwlInsn_SLEEP(AwlInsn): #+cdef

	__slots__ = ()

	def __init__(self, cpu, rawInsn=None, **kwargs):
		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_SLEEP, rawInsn, **kwargs)
		self.assertOpCount(1)

	def run(self): #+cdef
		sleepMsecs = self.cpu.fetch(self.op0, self._widths_scalar)
		sleepSecs = sleepMsecs / 1000.0

		if sleepSecs >= self.cpu.cycleTimeLimit:
			raise AwlSimError("__SLEEP time exceed cycle time limit")

		self.cpu.updateTimestamp()
		start = self.cpu.now
		while 1:
			self.cpu.updateTimestamp()
			slept = self.cpu.now - start
			remaining = sleepSecs - slept
			if remaining <= 0.0:
				break
			if remaining >= 0.1:
				self.cpu.requestScreenUpdate()
				time.sleep(0.05)

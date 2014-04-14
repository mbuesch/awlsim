# -*- coding: utf-8 -*-
#
# AWL simulator - instructions
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

from awlsim.core.instructions.main import *

import time


class AwlInsn_SLEEP(AwlInsn):
	def __init__(self, cpu, rawInsn):
		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_SLEEP, rawInsn)
		self.assertOpCount(1)

	def run(self):
		msecs = self.cpu.fetch(self.ops[0])

		if float(msecs) / 1000 >= self.cpu.cycleTimeLimit:
			raise AwlSimError("__SLEEP time exceed cycle time limit")

		while msecs > 0:
			m = min(50, msecs)
			time.sleep(float(m) / 1000)
			self.cpu.updateTimestamp()
			self.cpu.requestScreenUpdate()
			msecs -= m

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


class AwlInsn_FEATURE(AwlInsn):
	def __init__(self, cpu, rawInsn):
		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_FEATURE, rawInsn)
		self.assertOpCount((1, 2))

	def run(self):
		target = self.cpu.fetch(self.ops[0])
		value = None
		if len(self.ops) >= 2:
			value = self.cpu.fetch(self.ops[1])

		if target == 0:
			# Set/get the number of accumulator registers.
			if value is not None:
				self.cpu.specs.setNrAccus(value)
			self.cpu.accu1.set(self.cpu.specs.nrAccus)
		elif target == 1:
			# Set/get the enable-status of OB-temp writing.
			if value is not None:
				self.cpu.enableObTempPresets(value)
			self.cpu.accu1.set(int(self.cpu.obTempPresetsEnabled()))
		else:
			raise AwlSimError("Unsupported __FEATURE target %d" % target)

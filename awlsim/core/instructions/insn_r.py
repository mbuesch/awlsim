# -*- coding: utf-8 -*-
#
# AWL simulator - instructions
#
# Copyright 2012-2014 Michael Buesch <m@bues.ch>
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

from awlsim.core.instructions.main import * #@nocy
from awlsim.core.operators import *
#from awlsim.core.instructions.main cimport * #@cy


class AwlInsn_R(AwlInsn): #+cdef

	__slots__ = ()

	def __init__(self, cpu, rawInsn=None, **kwargs):
		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_R, rawInsn, **kwargs)
		self.assertOpCount(1)

	def run(self):
#@cy		cdef S7StatusWord s

		s, oper = self.cpu.statusWord,\
			self.ops[0].resolve(True)
		if oper.type == AwlOperator.MEM_Z:
			if s.VKE:
				self.cpu.getCounter(oper.value.byteOffset).reset()
			s.OR, s.NER = 0, 0
		elif oper.type == AwlOperator.MEM_T:
			if s.VKE:
				self.cpu.getTimer(oper.value.byteOffset).reset()
			s.OR, s.NER = 0, 0
		else:
			if s.VKE and (not self.cpu.mcrActive or self.cpu.mcrIsOn()):
				self.cpu.store(oper, 0, {1,})
			s.OR, s.STA, s.NER = 0, s.VKE, 0

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


class AwlInsn_INLINE_AWL(AwlInsn): #+cdef
	"""Inline-AWL pseudo-instruction.
	This instructions carries plain AWL source text."""

	__slots__ = (
		"awlCodeStr",
	)

	def __init__(self, cpu, awlCodeStr, **kwargs):
		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_INLINE_AWL, **kwargs)
		self.awlCodeStr = awlCodeStr

	def run(self): #+cdef
		# This pseudo-instruction can't be executed.
		raise AwlSimBug("Tried to execute AwlInsn_INLINE_AWL.")

	def getStr(self, *args, **kwargs):
		ret = []
		if self.commentStr:
			ret.append("// %s" % self.commentStr)
		if self.hasLabel():
			ret.append("%s: NOP 0;" % self.getLabel())
		ret.append(self.awlCodeStr)
		return "\n".join(ret)

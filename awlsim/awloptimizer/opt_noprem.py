# -*- coding: utf-8 -*-
#
# AWL simulator - AWL optimizer - Remove NOPs
#
# Copyright 2017 Michael Buesch <m@bues.ch>
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

from awlsim.awloptimizer.base import *

from awlsim.core.instructions.all_insns import * #+cimport


__all__ = [
	"AwlOptimizer_NopRemove",
]


class AwlOptimizer_NopRemove(AwlOptimizer_Base):
	"""AWL/STL optimizer: Remove NOP instructions
	"""

	NAME		= "noprem"
	LONGNAME	= "Remove superfluous NOP instructions"
	DESC		= "Removes almost all NOP instructions from the program."

	def __init__(self, optimizer):
		AwlOptimizer_Base.__init__(self, optimizer)

	def run(self, insns):
		newInsns = []
		for i, insn in enumerate(insns):
			if isinstance(insn, AwlInsn_NOP):
				if insn.labelStr:
					if i < len(insns) - 1:
						# Move the label to the next insn
						nextInsn = insns[i + 1]
						if nextInsn.labelStr:
							# Rename all references to insn.labelStr
							# to nextInsn.labelStr
							pass#TODO
						else:
							# Assign the label to the next insn.
							nextInsn.labelStr = insn.labelStr
							# Remove the NOP
							continue
					else:
						# This NOP is the last insn.
						# Keep it.
						pass
				else:
					# This is just a plain NOP.
					# Remove it.
					continue
			newInsns.append(insn)
		return newInsns

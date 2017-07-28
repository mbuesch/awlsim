# -*- coding: utf-8 -*-
#
# AWL simulator - AWL optimizer - Remove BIE forwards
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

from awlsim.common.util import *

from awlsim.awloptimizer.awloptimizer_base import *

from awlsim.core.operatortypes import * #+cimport
from awlsim.core.instructions.all_insns import * #+cimport


__all__ = [
	"AwlOptimizer_BIEForward",
]


class AwlOptimizer_BIEForward(AwlOptimizer_Base):
	"""AWL/STL optimizer: Remove BIE forwards
	This optimizes the instruction sequence:
		SET
		SPBxB xxx
		xxx: U BIE
	This optimizer depends on a preceding NOP removal run.
	"""

	def __init__(self, optimizer):
		AwlOptimizer_Base.__init__(self, optimizer)

	def run(self, insns):
		newInsns = []
		skip = 0
		for i, insn in enumerate(insns):
			if skip:
				skip -= 1
				continue

			if i <= len(insns) - 3 and\
			   isinstance(insns[i], AwlInsn_SET) and\
			   (isinstance(insns[i + 1], AwlInsn_SPBB) or\
			    isinstance(insns[i + 1], AwlInsn_SPBNB)) and\
			   isinstance(insns[i + 2], AwlInsn_U):

				SET_insn = insns[i]
				SPBxB_insn = insns[i + 1]
				U_insn = insns[i + 2]

				if len(U_insn.ops) == 1 and\
				   U_insn.ops[0].operType == AwlOperatorTypes.MEM_STW and\
				   U_insn.ops[0].offset == make_AwlOffset(0, 8) and\
				   len(SPBxB_insn.ops) == 1 and\
				   SPBxB_insn.ops[0].operType == AwlOperatorTypes.LBL_REF:

					jmpTarget = SPBxB_insn.ops[0].immediateStr
					foundInsns = self._findInsnsByLabel(insns, jmpTarget)

					if len(foundInsns.jmpSourceInsns) == 1 and\
					   getany(foundInsns.jmpSourceInsns) is SPBxB_insn and\
					   len(foundInsns.jmpTargetInsns) == 1 and\
					   getany(foundInsns.jmpTargetInsns) is U_insn:

						newInsns.append(insns[i]) # AwlInsn_SET
						skip = 2
						continue
			newInsns.append(insn)
		return newInsns
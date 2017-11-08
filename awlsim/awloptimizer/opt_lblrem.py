# -*- coding: utf-8 -*-
#
# AWL simulator - AWL optimizer - Remove unused labels
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

from awlsim.core.operatortypes import * #+cimport


__all__ = [
	"AwlOptimizer_LabelRemove",
]


class AwlOptimizer_LabelRemove(AwlOptimizer_Base):
	"""AWL/STL optimizer: Remove unused labels
	"""

	NAME		= "lblrem"
	LONGNAME	= "Remove unused labels"
	DESC		= "Remove labels that are not referenced by any instruction."
	STAGES		= frozenset((AwlOptimizer_Base.STAGE3, ))
	BEFORE		= frozenset()
	AFTER		= frozenset()

	def __init__(self, optimizer):
		AwlOptimizer_Base.__init__(self, optimizer)

	def run(self, insns):
		# Build a set of labels that actually are referenced.
		usedLabels = set()
		for insn in insns:
			for oper in insn.ops:
				if oper.operType == AwlOperatorTypes.LBL_REF:
					usedLabels.add(oper.immediateStr)

		# Remove unreferenced labels.
		for insn in insns:
			if insn.hasLabel() and\
			   insn.getLabel() not in usedLabels:
				insn.setLabel(None)

		return insns

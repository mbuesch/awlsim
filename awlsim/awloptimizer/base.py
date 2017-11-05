# -*- coding: utf-8 -*-
#
# AWL simulator - AWL optimizer base class
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

from awlsim.common.enumeration import *

from awlsim.core.operatortypes import * #+cimport


__all__ = [
	"AwlOptimizer_Base",
]


class AwlOptimizer_Base(object):
	"""AWL/STL optimizer base class
	"""

	EnumGen.start
	STAGE1	= EnumGen.item
	STAGE2	= EnumGen.item
	STAGE3	= EnumGen.item
	EnumGen.end

	# The optimization pass name.
	NAME		= "<none>"
	LONGNAME	= ""
	# The optimization pass description string.
	DESC		= ""
	# The stage(s) this optimization is supposed to run in.
	STAGES		= frozenset((STAGE1, ))
	# Dependency lists.
	BEFORE		= frozenset()
	AFTER		= frozenset()

	def __init__(self, optimizer):
		self.optimizer = optimizer

	def run(self, insns):
		"""Run the optimizer on the supplied list of instructions.
		Returns the optimized list of instructions.
		Override this method.
		"""
		raise NotImplementedError

	class __FindResult(object):
		def __init__(self, jmpSourceInsns=None, jmpTargetInsns=None):
			"""jmpSourceInsns: Set of found jump instructions.
			jmpTargetInsns: Set of found jump target instructions.
			"""
			self.jmpSourceInsns = jmpSourceInsns or set()
			self.jmpTargetInsns = jmpTargetInsns or set()

	def _findInsnsByLabel(self, insns, labelStr):
		"""Find instructions by label.
		insns: The list of instructions to search.
		labelStr: The label string to look for.
		"""
		res = self.__FindResult()
		for insn in insns:
			# Check if this instruction is the jump target.
			if insn.labelStr == labelStr:
				res.jmpTargetInsns.add(insn)
			# Check if this instruction is the jump source.
			if len(insn.ops) == 1 and\
			   insn.ops[0].operType == AwlOperatorTypes.LBL_REF and\
			   insn.ops[0].immediateStr == labelStr:
				res.jmpSourceInsns.add(insn)
		return res

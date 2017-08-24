# -*- coding: utf-8 -*-
#
# AWL simulator - AWL optimizer
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

from awlsim.common.exceptions import *
from awlsim.common.util import *

from awlsim.awloptimizer.base import *
from awlsim.awloptimizer.opt_bieforward import *
from awlsim.awloptimizer.opt_labelremove import *
from awlsim.awloptimizer.opt_nop import *

import functools


__all__ = [
	"AwlOptimizer",
]


class AwlOptimizer(object):
	"""AWL/STL program optimizer.
	"""

	ALL_OPTIMIZERS = (
		AwlOptimizer_BIEForward,
		AwlOptimizer_LabelRemove,
		AwlOptimizer_NopRemove,
	)

	class AllOptsEnabled(object):
		def __contains__(self, other):
			return True

	def __init__(self, enabledOpts=AllOptsEnabled()):
		self.enabledOpts = enabledOpts
		self.infoStr = ""

	def __sortOptimizerClasses(self, optClasses):
		def cmpFunc(optClass0, optClass1):
			if optClass0.NAME == optClass1.NAME:
				return 0
			before = (optClass0.NAME in optClass1.AFTER or\
				  optClass1.NAME in optClass0.BEFORE)
			after = (optClass1.NAME in optClass0.AFTER or\
				 optClass0.NAME in optClass1.BEFORE)
			if before and after:
				raise AwlSimError("AwlOptimizer: Ambiguous "
					"dependency between '%s' and '%s'." % (
					optClass0.NAME, optClass1.NAME))
			if before:
				return -1 # optClass0 before optClass1
			if after:
				return 1 # optClass1 before optClass0
			return 0
		return sorted(optClasses,
			      key=functools.cmp_to_key(cmpFunc))

	def __getOptimizerClasses(self, currentStage):
		optClasses = [ optClass for optClass in self.ALL_OPTIMIZERS\
			       if (currentStage in optClass.STAGES and\
				   optClass.NAME in self.enabledOpts) ]
		return self.__sortOptimizerClasses(optClasses)

	def __runOptimizers(self, currentStage, insns):
		printDebug("AwlOptimizer: Running STAGE %d%s..." % (
			(currentStage + 1),
			(" for '%s'" % self.infoStr) if self.infoStr else ""))
		for optClass in self.__getOptimizerClasses(currentStage):
			printDebug("AwlOptimizer: Running optimizer '%s'..." % (
				optClass.NAME))
			insns = optClass(optimizer=self).run(insns=insns)
		return insns

	def __optimize_Stage1(self, insns):
		return self.__runOptimizers(AwlOptimizer_Base.STAGE1, insns)

	def __optimize_Stage2(self, insns):
		return self.__runOptimizers(AwlOptimizer_Base.STAGE2, insns)

	def __optimize_Stage3(self, insns):
		return self.__runOptimizers(AwlOptimizer_Base.STAGE3, insns)

	def optimizeInsns(self, insns, infoStr=""):
		"""Optimize a list of AwlInsn_xxx instances.
		insns: The list of instructions to optimize.
		Returns the optimized list of instructions.
		"""
		self.infoStr = infoStr
		insns = self.__optimize_Stage1(insns)
		insns = self.__optimize_Stage2(insns)
		insns = self.__optimize_Stage3(insns)
		return insns

	def getEnableStr(self):
		return ", ".join(
			optClass.NAME for optClass in self.ALL_OPTIMIZERS
			if optClass.NAME in self.enabledOpts)

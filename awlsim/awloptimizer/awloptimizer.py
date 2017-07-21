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


__all__ = [
	"AwlOptimizer",
]


class AwlOptimizer(object):
	"""AWL/STL program optimizer.
	"""

	def __init__(self):
		pass

	def optimizeInsns(self, insns):
		"""Optimize a list of AwlInsn_xxx instances.
		insns: The list of instructions to optimize.
		Returns the optimized list of instructions.
		"""
		pass#TODO
		return insns

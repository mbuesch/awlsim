# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - Comment element
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

from awlsim.fupcompiler.elem import *


class FupCompiler_ElemComment(FupCompiler_Elem):
	"""FUP compiler - Comment element.
	"""

	ELEM_NAME = "COMMENT"

	@classmethod
	def parse(cls, grid, x, y, subType, content):
		return FupCompiler_ElemComment(grid=grid,
					       x=x, y=y,
					       content=content)

	def __init__(self, grid, x, y, content, **kwargs):
		FupCompiler_Elem.__init__(self, grid=grid, x=x, y=y,
					  elemType=FupCompiler_Elem.TYPE_COMMENT,
					  subType=None, content=content,
					  **kwargs)

	def _doCompile(self):
		return []

# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - Grid
#
# Copyright 2016 Michael Buesch <m@bues.ch>
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

from awlsim.common.xmlfactory import *

from awlsim.fupcompiler.fupcompiler_elem import *


class FupCompiler_GridFactory(XmlFactory):
	def parser_open(self):
		XmlFactory.parser_open(self)

	def parser_beginTag(self, tag):
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		XmlFactory.parser_endTag(self, tag)

class FupCompiler_Grid(object):
	factory = FupCompiler_GridFactory

	def __init__(self, compiler):
		self.compiler = compiler	# FupCompiler
		self.wires = set()		# FupCompiler_Wire
		self.elems = set()		# FupCompiler_Elem

# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - Connection
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

from awlsim.fupcompiler.fupcompiler_base import *


class FupCompiler_ConnFactory(XmlFactory):
	def parser_open(self, tag=None):
		self.inConn = False
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		if not self.inConn:
			if tag.name == "connection":
				self.inConn = True
				pos = tag.getAttrInt("pos")
				dirIn = tag.getAttrInt("dir_in")
				dirOut = tag.getAttrInt("dir_out")
				wireId = tag.getAttrInt("wire")
				conn = FupCompiler_Conn(self.elem,
					pos, dirIn, dirOut, wireId)
				if not self.elem.addConn(conn):
					raise self.Error("Invalid connection")
				return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if self.inConn:
			if tag.name == "connection":
				self.inConn = False
				return
		else:
			if tag.name == "connections":
				self.parser_finish()
				return
		XmlFactory.parser_endTag(self, tag)

class FupCompiler_Conn(FupCompiler_BaseObj):
	factory = FupCompiler_ConnFactory

	def __init__(self, elem, pos, dirIn, dirOut, wireId):
		FupCompiler_BaseObj.__init__(self)
		self.elem = elem		# FupCompiler_Elem
		self.pos = pos			# Position index
		self.dirIn = bool(dirIn)	# Input
		self.dirOut = bool(dirOut)	# Output
		self.wireId = wireId		# Wire ID number

		self.wire = None

	def getConnected(self):
		"""Get all other connections that are connected
		via self.wire to this connection.
		This excludes self.
		"""
		for conn in self.wire.connections:
			if conn is not self:
				yield conn

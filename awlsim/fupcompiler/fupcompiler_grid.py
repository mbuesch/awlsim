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

from awlsim.fupcompiler.fupcompiler_base import *
from awlsim.fupcompiler.fupcompiler_conn import *
from awlsim.fupcompiler.fupcompiler_wire import *
from awlsim.fupcompiler.fupcompiler_elem import *


class FupCompiler_GridFactory(XmlFactory):
	def parser_open(self, tag=None):
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		if tag.name == "wires":
			self.parser_switchTo(FupCompiler_Wire.factory(grid=self.grid))
			return
		if tag.name == "elements":
			self.parser_switchTo(FupCompiler_Elem.factory(grid=self.grid))
			return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if tag.name == "grid":
			self.parser_finish()
			return
		XmlFactory.parser_endTag(self, tag)

class FupCompiler_Grid(FupCompiler_BaseObj):
	factory = FupCompiler_GridFactory

	def __init__(self, compiler):
		FupCompiler_BaseObj.__init__(self)
		self.compiler = compiler	# FupCompiler
		self.wires = {}			# FupCompiler_Wire
		self.elems = set()		# FupCompiler_Elem

	def addWire(self, wire):
		if wire.idNum in self.wires:
			return False
		self.wires[wire.idNum] = wire
		return True

	def getWire(self, wireId):
		try:
			if wireId >= 0:
				return self.wires[wireId]
		except KeyError:
			pass
		return None

	def addElem(self, elem):
		self.elems.add(elem)

	def compile(self):
		"""Compile this FUP grid to AWL.
		Returns a list of instructions.
		"""
		if self.compileState == self.COMPILE_DONE:
			return []
		self.compileState = self.COMPILE_RUNNING
		insns = []

		# Resolve all wire-IDs
		for wire in dictValues(self.wires):
			wire.connections = set()
		for elem in self.elems:
			for conn in elem.connections:
				if conn.wireId == -1:
					raise AwlSimError("FUP: Unconnected pin found "
						"in FUP element.")
				wire = self.getWire(conn.wireId)
				if not wire:
					raise AwlSimError("FUP: Wire with ID %d "
						"does not exist" % (conn.wireId))
				wire.connections.add(conn)
				conn.wire = wire
		for wire in dictValues(self.wires):
			if len(wire.connections) == 0:
				raise AwlSimError("FUP: Found unconnected wire %s" % (
					str(wire)))
			if len(wire.connections) == 1:
				raise AwlSimError("FUP: Found dangling wire "
					"%s with only one connection" % (
					str(wire)))

		# Find all assignment operators and walk the logic chain upwards.
		for elem in FupCompiler_Elem.sorted(self.elems):
			if elem.elemType == elem.TYPE_OPERAND and\
			   elem.subType == elem.SUBTYPE_ASSIGN:
				insns.extend(elem.compile())

		# Check if all elements have been compiled.
		for elem in self.elems:
			if elem.compileState != elem.COMPILE_DONE:
				raise AwlSimError("FUP: Found dangling element "
					"'%s'. Please make sure all connections of "
					"this element are connected." % (
					str(elem)))

		self.compileState = self.COMPILE_DONE
		return insns

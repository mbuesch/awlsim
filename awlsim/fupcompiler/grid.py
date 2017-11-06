# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - Grid
#
# Copyright 2016-2017 Michael Buesch <m@bues.ch>
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

from awlsim.awloptimizer.awloptimizer import *

from awlsim.fupcompiler.base import *
from awlsim.fupcompiler.conn import *
from awlsim.fupcompiler.wire import *
from awlsim.fupcompiler.elem import *
from awlsim.fupcompiler.elemcomment import *


class FupCompiler_GridFactory(XmlFactory):
	def parser_open(self, tag=None):
		assert(tag)
		uuid = tag.getAttr("uuid", None)
		self.grid.uuid = uuid
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		if tag.name == "optimizers":
			optSettCont = self.grid.optimizerSettingsContainer
			optSettCont.clear()
			self.parser_switchTo(optSettCont.factory(settingsContainer=optSettCont))
			return
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
	factory			= FupCompiler_GridFactory
	noPreprocessing		= True

	def __init__(self, compiler, uuid=None):
		FupCompiler_BaseObj.__init__(self, uuid=uuid)
		self.compiler = compiler	# FupCompiler
		self.wires = {}			# FupCompiler_Wire
		self.elems = set()		# FupCompiler_Elem
		self.optimizerSettingsContainer = AwlOptimizerSettingsContainer()

	def newWire(self, virtual=False):
		newWireId = 0
		if self.wires:
			newWireId = max(dictKeys(self.wires)) + 1
		wire = FupCompiler_Wire(self, newWireId, virtual)
		self.addWire(wire)
		return wire

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

		from awlsim.fupcompiler.elemoper import FupCompiler_ElemOper

		# Resolve all wire-IDs
		for wire in dictValues(self.wires):
			wire.clearConnections()
		for elem in self.elems:
			for conn in elem.connections:
				if conn.wireId == conn.WIREID_NONE and not conn.isOptional:
					raise FupGridError("Unconnected pin%s found "
						"in FUP element %s." % (
						(" \"%s\"" % conn.text) if conn.text else "",
						str(elem)),
						self)
				if conn.wireId == conn.WIREID_NONE:
					conn.wire = None
				else:
					wire = self.getWire(conn.wireId)
					if not wire:
						raise FupGridError("Wire with ID %d "
							"does not exist, but %s "
							"references it." % (
							conn.wireId, str(elem)),
							self)
					wire.addConn(conn)
					conn.wire = wire
		for wire in dictValues(self.wires):
			if len(wire.connections) == 0:
				raise FupGridError("Found unconnected wire %s" % (
					str(wire)),
					self)
			if len(wire.connections) == 1:
				raise FupGridError("Found dangling wire "
					"%s with only one connection" % (
					str(wire)),
					self)

		def checkAllElemStates(checkState):
			# Check if all elements have been processed.
			for elem in self.elems:
				if elem.compileState != checkState and\
				   not isinstance(elem, FupCompiler_ElemComment):
					raise FupGridError("Found dangling element "
						"'%s'. Please make sure all connections of "
						"this element are connected." % (
						str(elem)),
						self)

		# Preprocess all elements.
		# Find all assignment operators and walk the logic chain upwards.
		for elem in FupCompiler_Elem.sorted(self.elems):
			if elem.isCompileEntryPoint and elem.needPreprocess:
				elem.preprocess()

		# Check if all elements have been preprocessed.
		checkAllElemStates(FupCompiler_Elem.COMPILE_PREPROCESSED)

		# Check if inverted connections are only used on supported elements.
		for elem in FupCompiler_Elem.sorted(self.elems):
			for conn in elem.connections:
				if conn.inverted and\
				   conn.connType != conn.TYPE_VKE:
					raise FupGridError("An inverted connection "
						"is only allowed for VKE based (boolean) "
						"connections. The connection '%s' in "
						"element '%s' is not supported." % (
						str(conn), str(elem)),
						self)

		# Compile all elements.
		# Find all assignment operators and walk the logic chain upwards.
		for elem in FupCompiler_Elem.sorted(self.elems):
			if elem.isCompileEntryPoint and elem.needCompile:
				insns.extend(elem.compile())

		# Check if all elements have been compiled.
		checkAllElemStates(FupCompiler_Elem.COMPILE_DONE)

		self.compileState = self.COMPILE_DONE
		return insns

	def __repr__(self):
		return "FupCompiler_Grid(compiler)"

	def __str__(self):
		return "FUP-grid"

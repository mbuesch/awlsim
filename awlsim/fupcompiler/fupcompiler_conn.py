# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - Connection
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
				text = tag.getAttr("text", "")
				conn = FupCompiler_Conn(self.elem,
					pos, dirIn, dirOut, wireId, text)
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

	# Connection types
	EnumGen.start
	TYPE_UNKNOWN	= EnumGen.item
	TYPE_VKE	= EnumGen.item # Bit operation
	TYPE_ACCU	= EnumGen.item # Byte/word/dword operation
	EnumGen.end

	# Wire-ID used for unconnected connections
	WIREID_NONE	= -1

	def __init__(self, elem, pos, dirIn, dirOut, wireId, text):
		FupCompiler_BaseObj.__init__(self)
		self.elem = elem		# FupCompiler_Elem
		self.pos = pos			# Position index
		self.dirIn = bool(dirIn)	# Input
		self.dirOut = bool(dirOut)	# Output
		self.wireId = wireId		# Wire ID number
		self.text = text or ""		# Connection text (optional)

		self.wire = None

	@property
	def isOptional(self):
		"""Returns True, if this connection is optional.
		An optional connection does not have to be connected.
		"""
		return self.elem.connIsOptional(self)

	@property
	def connType(self):
		"""Get the connection type.
		This returns whether this connection is VKE based (TYPE_VKE)
		or accu based (TYPE_ACCU).
		If the type is unknown TYPE_UNKNOWN is returned.
		"""
		return self.elem.getConnType(self)

	@property
	def isConnected(self):
		"""Returns True, if this connection is connected to a wire.
		"""
		return self.wire is not None

	def getConnected(self, getOutputs=False, getInputs=False):
		"""Get all other connections that are connected
		via self.wire to this connection.
		This excludes self.
		If 'getOutputs' is True, connections with dirOut=True are returned.
		If 'getInputs' is True, connections with dirIn=True are returned.
		"""
		if self.wire:
			for conn in self.wire.connections:
				if conn is not self and\
				   ((conn.dirOut and getOutputs) or\
				    (conn.dirIn and getInputs)):
					yield conn

	def getConnectedElems(self, viaOut=False, viaIn=False):
		"""Get all elements that are connected to this connection.
		If 'viaOut' is True, elements connected to the wire via OUT
		connection are returned.
		If 'viaIn' is True, elements connected to the wire via OUT
		connection are returned.
		If neither 'viaOut' nor 'viaIn' is True, no element is returned.
		The element that belongs to 'self' is not returned.
		"""
		for conn in self.getConnected(getOutputs=viaOut, getInputs=viaIn):
			yield conn.elem

	def getConnectedElem(self, viaOut=False, viaIn=False):
		"""Get the single element that is connected to this connection.
		If 'viaOut' is True, elements connected to the wire via OUT
		connection are returned.
		If 'viaIn' is True, elements connected to the wire via OUT
		connection are returned.
		If neither 'viaOut' nor 'viaIn' is True, None is returned.
		If there is no matching element or more that one matching
		element, an exception is raised.
		"""
		if not viaOut and not viaIn:
			return None
		viaText = "%s%s%s" % (
			"IN" if viaIn else "",
			"/" if viaIn and viaOut else "",
			"OUT" if viaOut else "")
		connections = list(self.getConnected(getOutputs=viaOut, getInputs=viaIn))
		if len(connections) > 0:
			if len(connections) > 1:
				raise AwlSimError("The connection%s of element '%s' does "
					"only support a single %s-wire, "
					"but has %d %s-connections." % (
					(" \"%s\"" % self.text) if self.text else "",
					str(self.elem),
					viaText,
					len(connections),
					viaText))
			return connections[0].elem
		raise AwlSimError("The connection%s of element '%s' does "
			"does not have a valid %s-connected element." % (
			(" \"%s\"" % self.text) if self.text else "",
			str(self.elem), viaText))

# -*- coding: utf-8 -*-
#
# AWL simulator - FUP - Connection classes
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

from awlsim.gui.fup.fup_base import *
from awlsim.gui.fup.fup_wire import *


class FupConn_factory(XmlFactory):
	def parser_open(self, tag=None):
		self.inConn = False
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		if not self.inConn and self.elem:
			if tag.name == "connection":
				self.inConn = True
				pos = tag.getAttrInt("pos")
				dirIn = tag.getAttrInt("dir_in")
				dirOut = tag.getAttrInt("dir_out")
				wireId = tag.getAttrInt("wire")
				if pos < 0 or pos > 0xFFFF:
					raise self.Error("Invalid <connection> pos.")
				wire = self.elem.grid.getWireById(wireId)
				try:
					if dirIn and not dirOut:
						self.elem.inputs.extend(
							[None] * (pos + 1 - len(self.elem.inputs)))
						conn = FupConnIn(elem=self.elem, pos=pos, wire=wire)
						if wire:
							wire.connect(conn)
						self.elem.inputs[pos] = conn
						return
					elif dirOut and not dirIn:
						self.elem.outputs.extend(
							[None] * (pos + 1 - len(self.elem.outputs)))
						conn = FupConnOut(elem=self.elem, pos=pos, wire=wire)
						if wire:
							wire.connect(conn)
						self.elem.outputs[pos] = conn
						return
				except ValueError:
					raise self.Error("Invalid <connection>")
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

	def composer_getTags(self):
		return [
			self.Tag(name="connection",
				attrs={
					"dir_in" : str(int(self.conn.IN)),
					"dir_out" : str(int(self.conn.OUT)),
					"pos" : str(self.conn.pos),
					"wire" : str(-1) if self.conn.wire is None
						 else str(self.conn.wire.idNum),
				}),
		]

class FupConn(FupBaseClass):
	"""FUP/FBD element connection base class"""

	factory = FupConn_factory

	IN = False
	OUT = False

	CONN_OFFS = 4

	def __init__(self, elem, pos=0, wire=None):
		FupBaseClass.__init__(self)
		self.elem = elem	# The FupElem this connection belongs to
		self.pos = pos		# The y position (top is 0)
		self.wire = wire	# The FupWire this connection is connected to (if any).

	@property
	def relPixCoords(self):
		"""Get the (x, y) pixel coordinates of this connection
		relative to the element's root.
		Raises IndexError, if this does not belong to an element.
		"""
		elem = self.elem
		if elem:
			return elem.getConnRelPixCoords(self)
		raise IndexError

	@property
	def pixCoords(self):
		"""Get the absolute (x, y) pixel coordinates of this connection.
		Raises IndexError, if this does not belong to an element.
		"""
		elem = self.elem
		if elem:
			xAbs, yAbs = elem.pixCoords
			xRel, yRel = self.relPixCoords
			return xAbs + xRel, yAbs + yRel
		raise IndexError

	@property
	def isConnected(self):
		"""Returns True, if this connection is connected to a wire.
		"""
		return self.wire is not None

	def canConnectTo(self, other):
		"""Check if this connection can connect to another connection.
		"""
		if self.wire is not None and other.wire is not None:
			return False
		return (self is not other) and\
		       (self.elem is not None and other.elem is not None) and\
		       (self.elem is not other.elem) and\
		       ((self.IN and other.OUT) or\
			(self.OUT and other.IN))

	def connectTo(self, other):
		"""Connect this connection to another.
		Raises ValueError, if the connection cannot be done.
		"""
		if not self.canConnectTo(other):
			raise ValueError
		wire = self.wire or other.wire
		if not wire:
			# Create a new wire
			wire = FupWire(self.elem.grid)
		wire.connect(self)
		wire.connect(other)

	def disconnect(self):
		"""Break the current connection, if any.
		Returns True, if there was a connection.
		"""
		if self.wire:
			self.wire.disconnect(self)
			return True
		return False

class FupConnIn(FupConn):
	"""FUP/FBD element input connection"""
	IN = True

class FupConnOut(FupConn):
	"""FUP/FBD element output connection"""
	OUT = True

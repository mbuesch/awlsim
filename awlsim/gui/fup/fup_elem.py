# -*- coding: utf-8 -*-
#
# AWL simulator - FUP - Element classes
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

from awlsim.gui.util import *
from awlsim.gui.fup.fup_base import *
from awlsim.gui.fup.fup_conn import *


class FupElem_factory(XmlFactory):
	def parser_open(self, tag=None):
		self.inElem = False
		self.elem = None
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		if self.inElem:
			if tag.name == "connections":
				self.parser_switchTo(FupConn.factory(elem=self.elem))
				return
		else:
			if tag.name == "element":
				self.inElem = True
				elemType = tag.getAttr("type")
				x = tag.getAttrInt("x")
				y = tag.getAttrInt("y")
				if elemType == "boolean":
					from awlsim.gui.fup.fup_elembool import\
						FupElem_AND, FupElem_OR, FupElem_XOR
					subType = tag.getAttr("subtype")
					elemClass = {
						FupElem_AND.OP_SYM_NAME	: FupElem_AND,
						FupElem_OR.OP_SYM_NAME	: FupElem_OR,
						FupElem_XOR.OP_SYM_NAME	: FupElem_XOR,
					}.get(subType)
					if elemClass:
						self.elem = elemClass(
							x=x, y=y, nrInputs=0)
						self.elem.grid = self.grid
						return
				elif elemType == "operand":
					from awlsim.gui.fup.fup_elemoperand import\
						FupElem_LOAD, FupElem_ASSIGN
					subType = tag.getAttr("subtype")
					content = tag.getAttr("content", "")
					elemClass = {
						FupElem_LOAD.OP_SYM_NAME : FupElem_LOAD,
						FupElem_ASSIGN.OP_SYM_NAME : FupElem_ASSIGN,
					}.get(subType)
					if elemClass:
						self.elem = elemClass(x=x, y=y,
							contentText=content)
						self.elem.grid = self.grid
						return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if self.inElem:
			if tag.name == "element":
				if self.elem:
					# Insert the element into the grid.
					if not all(self.elem.inputs) or\
					   not all(self.elem.outputs):
						raise self.Error("<element> connections "
							"are incomplete.")
					if not self.grid.placeElem(self.elem):
						raise self.Error("<element> caused "
							"a grid collision.")
				self.inElem = False
				self.elem = None
				return
		else:
			if tag.name == "elements":
				self.parser_finish()
				return
		XmlFactory.parser_endTag(self, tag)

class FupElem(FupBaseClass):
	"""FUP/FBD element base class"""

	# Element symbol
	OP_SYM		= ""
	OP_SYM_NAME	= ""	# XML ABI name

	factory = FupElem_factory

	# Element areas
	EnumGen.start
	AREA_NONE	= EnumGen.item
	AREA_BODY	= EnumGen.item
	AREA_INPUT	= EnumGen.item
	AREA_OUTPUT	= EnumGen.item
	EnumGen.end

	def __init__(self, x, y):
		FupBaseClass.__init__(self)
		self.x = x		# X position as grid coordinates
		self.y = y		# Y position as grid coordinates
		self.grid = None

		self.inputs = []	# The input FupConn-ections
		self.outputs = []	# The output FupConn-ections

		self.expanded = False	# Content view expansion active

		lineWidth = 2
		self._noPen = QPen(Qt.NoPen)
		self._noPen.setWidth(0)
		self._outlinePen = QPen(QColor("#000000"))
		self._outlinePen.setWidth(lineWidth)
		self._outlineSelPen = QPen(QColor("#0000FF"))
		self._outlineSelPen.setWidth(lineWidth)
		self._connPen = QPen(QColor("#000000"))
		self._connPen.setWidth(lineWidth)
		self._connOpenPen = QPen(QColor("#DF6060"))
		self._connOpenPen.setWidth(lineWidth)
		self._bgBrush = QBrush(QColor("#FFFFFF"))
		self._bgSelBrush = QBrush(QColor("#BBBBBB"))
		self._textPen = QPen(QColor("#000000"))
		self._textPen.setWidth(0)

	def matchCloseConns(self, otherElem):
		"""Get a set of (selfConn, otherConn) pairs of connections
		that are close and could possibly be connected easily.
		"""
		selfConns, otherConns = (), ()

		# Check if self and otherElem overlap in Y direction.
		if self is not otherElem and\
		   otherElem.y <= self.y + self.height - 1 and\
		   otherElem.y + otherElem.height - 1 >= self.y:
			# otherElem is an operand within the y-range of this elem.

			if otherElem.x + otherElem.width - 1 == self.x - 1:
				# otherElem is located to the left
				# hand side (= input side) of this elem.
				selfConns = self.inputs
				otherConns = otherElem.outputs
			elif otherElem.x == self.x + self.width:
				# otherElem is located to the right
				# hand side (= output side) of this elem
				selfConns = self.outputs
				otherConns = otherElem.inputs

		connPairs = set()
		for selfConn in selfConns:
			for otherConn in otherConns:
				if selfConn.isConnected or\
				   otherConn.isConnected:
					# Already connected.
					continue
				selfX, selfY = selfConn.coords
				otherX, otherY = otherConn.coords
				if selfY == otherY:
					# These connections are at the same Y position.
					# Got a pair.
					connPairs.add( (selfConn, otherConn) )
		return connPairs

	def establishAutoConns(self):
		"""Automatically establish connections to close elements.
		"""
		connected = False
		for elem in self.grid.elems:
			for match in self.matchCloseConns(elem) or ():
				selfConn, otherConn = match
				try:
					selfConn.connectTo(otherConn)
				except ValueError:
					pass
				else:
					connected = True
		return connected

	def isConnectedTo(self, otherElem):
		"""Returns 1, if any output it connected to the other elements input.
		Returns -1, if any input it connected to the other elements output.
		Returns 0 otherwise.
		"""
		if any(conn.wire is not None and\
		       conn.wire in (c.wire for c in otherElem.outputs)
		       for conn in self.inputs):
			return -1
		if any(conn.wire is not None and\
		       conn.wire in (c.wire for c in otherElem.inputs)
		       for conn in self.outputs):
			return 1
		return 0

	def getRelatedElems(self):
		"""Get all elements that are "related" to the specified elements.
		Related elements are closely bound elements.
		"""
		if not self.grid:
			return []
		return { elem for elem in self.grid.elems
			 if self.isRelatedElem(elem) }

	def isRelatedElem(self, otherElem):
		"""Returns True, if the other element is related to self.
		May be overridden in a subclass.
		The default implementation always returns True, if the other element
		is a close operand.
		"""
		from awlsim.gui.fup.fup_elemoperand import FupElem_OPERAND
		if isinstance(otherElem, FupElem_OPERAND):
			if otherElem.y >= self.y and\
			   otherElem.y < self.y + self.height:
				isConnected = self.isConnectedTo(otherElem)
				if isConnected > 0:
					if otherElem.x == self.x + 1:
						return True
				elif isConnected < 0:
					if otherElem.x == self.x - 1:
						return True
		return False

	def breakConnections(self, breakInputs=True, breakOutputs=True):
		"""Disconnect all connections.
		"""
		if breakInputs:
			for conn in self.inputs:
				conn.disconnect()
		if breakOutputs:
			for conn in self.outputs:
				conn.disconnect()

	def getInput(self, index):
		try:
			return self.inputs[index]
		except IndexError:
			return None

	def getOutput(self, index):
		try:
			return self.outputs[index]
		except IndexError:
			return None

	def addConn(self, conn):
		"""Add a connection to the end of the connection list.
		"""
		if conn:
			if conn.IN:
				conn.elem = self
				self.inputs.append(conn)
				return True
			elif conn.OUT:
				conn.elem = self
				self.outputs.append(conn)
				return True
		return False

	def removeConn(self, conn):
		"""Remove a connection from the connection list.
		"""
		if conn:
			if conn.IN:
				if len(self.inputs) > 1:
					conn.elem = None
					self.inputs.remove(conn)
					return True
			elif conn.OUT:
				if len(self.outputs) > 1:
					conn.elem = None
					self.outputs.remove(conn)
					return True
		return False

	def getAreaViaPixCoord(self, pixelX, pixelY):
		"""Get (AREA_xxx, area_index) via pixel coordinates
		relative to the element.
		"""
		return self.AREA_BODY, 0

	def getConnViaPixCoord(self, pixelX, pixelY):
		"""Get a connection via pixel coordinates
		relative to the element.
		"""
		area, idx = self.getAreaViaPixCoord(pixelX, pixelY)
		if area == self.AREA_INPUT:
			return self.inputs[idx]
		elif area == self.AREA_OUTPUT:
			return self.outputs[idx]
		return None

	@property
	def pixCoords(self):
		"""Get the (x, y) positions of this element as absolute pixel coordinates.
		"""
		grid = self.grid
		if grid:
			return self.x * grid.cellPixWidth,\
			       self.y * grid.cellPixHeight
		return 0

	def getConnRelCoords(self, conn):
		"""Get the (x, y) grid coordinates of a connection
		relative to the element's root.
		Raises IndexError, if there is no such connection.
		"""
		raise IndexError

	def getConnRelPixCoords(self, conn):
		"""Get the (x, y) pixel coordinates of a connection
		relative to the element's root.
		Raises IndexError, if there is no such connection.
		"""
		if self.grid:
			# Get the grid coordinated. (This might raise IndexError)
			x, y = self.getConnRelCoords(conn)
			# Convert to pixels
			cellPixHeight = self.grid.cellPixHeight
			cellPixWidth = self.grid.cellPixWidth
			if conn.IN:
				xPix = (x * cellPixWidth) + FupConn.CONN_OFFS
				yPix = (y * cellPixHeight) + (cellPixHeight // 2)
				return xPix, yPix
			elif conn.OUT:
				xPix = (x * cellPixWidth) + cellPixWidth - FupConn.CONN_OFFS
				yPix = (y * cellPixHeight) + (cellPixHeight // 2)
				return xPix, yPix
		raise IndexError

	def isInGridRect(self, gridX0, gridY0, gridX1, gridY1):
		"""Returns true, if this element is placed under
		the specified grid rectangle.
		"""
		x0, y0 = min(gridX0, gridX1), min(gridY0, gridY1)
		x1, y1 = max(gridX0, gridX1), max(gridY0, gridY1)
		return self.x >= x0 and self.y >= y0 and\
		       self.x + self.width - 1 <= x1 and self.y + self.height - 1 <= y1

	@property
	def height(self):
		"""The element height, in grid coordinates.
		"""
		return 1

	@property
	def width(self):
		"""The element width, in grid coordinates.
		"""
		return 1

	@property
	def _xpadding(self):
		"""The horizontal pixel padding for the element body.
		"""
		if self.grid:
			return self.grid.cellPixWidth // 6
		return 0

	@property
	def _ypadding(self):
		"""The vertical pixel padding for the element body.
		"""
		if self.grid:
			return self.grid.cellPixHeight // 8
		return 0

	@property
	def selected(self):
		"""Returns True, if this element is selected.
		"""
		return self in self.grid.selectedElems

	def remove(self):
		"""Remove this element from the grid.
		"""
		if self.grid:
			self.grid.removeElem(self)

	def draw(self, painter):
		"""Draw this element.
		"""
		pass

	def prepareContextMenu(self, menu, area=None, conn=None):
		"""Add element specific context menu entries.
		"""
		pass

	def expand(self, expand=True):
		"""Expand this element to fully show it, if expand=True.
		Returns True, if the expansion state changed.
		"""
		return False

	def edit(self, parentWidget):
		"""Edit the element's contents.
		Returns True, if a repaint is required.
		"""
		return False

	def __repr__(self):
		return "FupElem(%d, %d)" % (self.x, self.y)

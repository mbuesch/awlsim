# -*- coding: utf-8 -*-
#
# AWL simulator - FUP - Element classes
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

from awlsim.gui.util import *
from awlsim.gui.fup.fup_base import *
from awlsim.gui.fup.fup_conn import *


class FupElem_factory(XmlFactory):
	def parser_open(self):
		self.inElem = False
		self.elem = None
		XmlFactory.parser_open(self)

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
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if self.inElem:
			if tag.name == "element":
				if self.elem:
					# Insert the element into the grid.
					if not self.elem.inputs:
						raise self.Error("<element> does "
							"not have any inputs.")
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

	def getConnRelPixCoords(self, conn):
		"""Get the (x, y) pixel coordinates of a connection
		relative to the element's root.
		Raises IndexError, if there is no such connection.
		"""
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
		return 1

	@property
	def width(self):
		return 1

	@property
	def selected(self):
		return self in self.grid.selectedElems

	def remove(self):
		if self.grid:
			self.grid.removeElem(self)

	def draw(self, painter):
		pass

	def prepareContextMenu(self, menu):
		pass

	def __repr__(self):
		return "FupElem(%d, %d)" % (self.x, self.y)

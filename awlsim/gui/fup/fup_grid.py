# -*- coding: utf-8 -*-
#
# AWL simulator - FUP - Grid classes
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
from awlsim.gui.fup.fup_elem import *
from awlsim.gui.fup.fup_elembool import *
from awlsim.gui.fup.fup_elemoperand import *


class FupGrid_factory(XmlFactory):
	def parser_open(self, tag=None):
		self.grid.clear()

		if tag:
			width = tag.getAttrInt("width")
			height = tag.getAttrInt("height")
			self.grid.resize(width, height)

		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		if tag.name == "wires":
			self.parser_switchTo(FupWire.factory(grid=self.grid))
			return
		if tag.name == "elements":
			self.parser_switchTo(FupElem.factory(grid=self.grid))
			return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if tag.name == "grid":
			self.grid.removeOrphanWires()
			self.parser_finish()
			return
		XmlFactory.parser_endTag(self, tag)

	def composer_getTags(self):
		wireTags = []
		for wire in sorted(self.grid.wires, key=lambda w: w.idNum):
			wireTags.extend(wire.factory(wire=wire).composer_getTags())
		elemTags = []
		for elem in self.grid.elems:
			elemTags.extend(elem.factory(elem=elem).composer_getTags())
		return [
			self.Tag(name="grid",
				tags=[
					self.Tag(name="wires",
						 tags=wireTags),
					self.Tag(name="elements",
						 tags=elemTags),
				],
				attrs={
					"width" : str(self.grid.width),
					"height" : str(self.grid.height),
				}),
		]

class FupGrid(object):
	"""FUP/FBD element grid"""

	factory = FupGrid_factory

	def __init__(self, drawWidget, width, height):
		self.__drawWidget = drawWidget
		self.width = width
		self.height = height

		self.elems = []		# The FupElem_xxx()s in this grid
		self.wires = set()	# The FupConnIn/Out()s in this grid

		self.selectedElems = set()
		self.expandedElems = set()

	def clear(self):
		for wire in self.wires:
			wire.disconnectAll()
		self.wires.clear()
		self.elems = []
		self.selectedElems.clear()

	def resize(self, width, height):
		"""Resize the grid.
		Returns True, if the resize was successfull.
		"""
		#TODO check if the size is possible
		self.width = width
		self.height = height
		return True

	def getUnusedWireIdNum(self):
		"""Get an unused wire idNum.
		"""
		if self.wires:
			return max(w.idNum for w in self.wires) + 1
		return 0

	def addWire(self, wire):
		"""Add a wire to the grid.
		Does nothing, if the wire does exist already.
		"""
		self.wires.add(wire)

	def removeWire(self, wire):
		"""Remove a wire to the grid.
		Does nothing, if the wire does not exist.
		"""
		with contextlib.suppress(KeyError):
			self.wires.remove(wire)

	def getWireById(self, wireIdNum):
		"""Get a wire by its idNum.
		"""
		if wireIdNum >= 0:
			for wire in self.wires:
				if wire.idNum == wireIdNum:
					return wire
		return None

	def removeOrphanWires(self):
		"""Remove all unconnected wires.
		"""
		newWiresSet = set()
		while self.wires:
			wire = self.wires.pop()
			if wire.connections:
				newWiresSet.add(wire)
		self.wires = newWiresSet

	def renumberWires(self):
		"""Re-assign all wire idNums.
		"""
		for i, wire in enumerate(self.wires):
			wire.idNum = i

	@property
	def cellPixWidth(self):
		if self.__drawWidget:
			return self.__drawWidget.cellPixWidth
		return 0

	@property
	def cellPixHeight(self):
		if self.__drawWidget:
			return self.__drawWidget.cellPixHeight
		return 0

	def __haveCollision(self, x, y, height, excludeElems=set()):
		if x < 0 or x >= self.width or\
		   y < 0 or y >= self.height:
			# Position is not on grid.
			return True
		for yy in range(y, y + height):
			elem = self.getElemAt(x, yy)
			if elem in excludeElems:
				continue # Element is ignored.
			if elem:
				return True # Collision with other element.
		return False

	def placeElem(self, elem):
		# Check if we have a collision.
		if self.__haveCollision(elem.x, elem.y, elem.height):
			return False
		# Add the element.
		self.elems.append(elem)
		elem.grid = self
		return True

	def removeElem(self, elem):
		with contextlib.suppress(ValueError):
			self.elems.remove(elem)
		elem.breakConnections()
		with contextlib.suppress(ValueError):
			self.selectedElems.remove(elem)

	def moveElemTo(self, elem, toX, toY,
		       relativeCoords=False,
		       checkOnly=False,
		       excludeCheckElems=set()):
		"""Move elem to position (toX, toY).
		If relativeCoords=True, the (toX, toY) coodinates are relative
		to the current position.
		If checkOnly=True, the actual move is not performed.
		All elements included in excludeCheckElems are excluded from
		the collision check.
		"""
		if relativeCoords:
			toX, toY = elem.x + toX, elem.y + toY
		if toX == elem.x and toY == elem.y:
			return True # No move needed
		# Check collision
		excludeElems = excludeCheckElems.copy()
		excludeElems.add(elem) # Can't collide with ourselves.
		if self.__haveCollision(toX, toY, elem.height,
					excludeElems=excludeElems):
			return False # Collision. Cannot move.
		# Move the element.
		if not checkOnly:
			elem.x = toX
			elem.y = toY
		return True

	def getElemAt(self, x, y):
		for elem in self.elems:
			ex, ey = elem.x, elem.y
			ew, eh = elem.width, elem.height
			if x >= ex and x < ex + ew and\
			   y >= ey and y < ey + eh:
				return elem
		return None

	def haveElemAt(self, x, y):
		return self.getElemAt(x, y) is not None

	def getElemsInRect(self, x0, y0, x1, y1):
		"""Get all elements placed within the given grid rectangle.
		"""
		return (elem for elem in self.elems
			if elem.isInGridRect(x0, y0, x1, y1))

	def selectElem(self, elem):
		if elem:
			self.selectedElems.add(elem)

	def selectElemAt(self, x, y):
		elem = self.getElemAt(x, y)
		if elem:
			self.selectElem(elem)
		else:
			self.deselectAll()

	def selectElemsInRect(self, x0, y0, x1, y1, clear=False):
		"""Select all elements within the given grid rectangle.
		"""
		if clear:
			self.deselectAll()
		for elem in self.getElemsInRect(x0, y0, x1, y1):
			self.selectElem(elem)

	def deselectElem(self, elem):
		with contextlib.suppress(KeyError):
			self.selectedElems.remove(elem)

	def deselectElemAt(self, x, y):
		elem = self.getElemAt(x, y)
		if elem:
			self.deselectElem(elem)

	def deselectAll(self):
		self.selectedElems.clear()

	def expandElem(self, elem, expand=True):
		ok = False
		if elem and expand and not elem in self.expandedElems:
			ok = elem.expand(expand)
			if ok:
				self.expandedElems.add(elem)
		if elem and not expand and elem in self.expandedElems:
			ok = elem.expand(expand)
			if ok:
				self.expandedElems.remove(elem)
		return ok

	def unexpandAllElems(self):
		if self.expandedElems:
			for elem in self.expandedElems.copy():
				self.expandElem(elem, False)
			return True
		return False

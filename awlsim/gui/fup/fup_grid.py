# -*- coding: utf-8 -*-
#
# AWL simulator - FUP - Grid classes
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

from awlsim.gui.geo2d import *
from awlsim.gui.fup.fup_base import *
from awlsim.gui.fup.fup_wire import *
from awlsim.gui.fup.fup_elem import *
from awlsim.gui.fup.fup_elembool import *
from awlsim.gui.fup.fup_elemoperand import *
from awlsim.gui.fup.fup_elemmove import *


class FupGrid_factory(XmlFactory):
	def parser_open(self, tag=None):
		self.grid.clear()

		if tag:
			width = tag.getAttrInt("width")
			height = tag.getAttrInt("height")
			uuid = tag.getAttr("uuid", None)
			self.grid.resize(width, height)
			self.grid.uuid = uuid

		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		if tag.name == "wires":
			self.parser_switchTo(FupWire.factory(grid=self.grid))
			return
		if tag.name == "elements":
			self.parser_switchTo(FupElem.factory(grid=self.grid))
			return
		if tag.name == "optimizers":
			optType = tag.getAttr("type")
			if optType == "awl":
				optSettingsCont = self.grid.optSettingsCont
				self.parser_switchTo(optSettingsCont.factory(
					settingsContainer=optSettingsCont))
				return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if tag.name == "grid":
			self.grid.removeOrphanWires()
			self.parser_finish()
			return
		XmlFactory.parser_endTag(self, tag)

	def composer_getTags(self):
		grid = self.grid
		childTags = []

		optSettingsCont = grid.optSettingsCont
		childTags.extend(
			optSettingsCont.factory(
				settingsContainer=optSettingsCont).composer_getTags())

		wireTags = []
		grid.renumberWires()
		for wire in sorted(grid.wires, key=lambda w: w.idNum):
			wireTags.extend(wire.factory(wire=wire).composer_getTags())
		childTags.append(self.Tag(name="wires",
					  tags=wireTags))

		elemTags = []
		for elem in grid.elems:
			elemTags.extend(elem.factory(elem=elem).composer_getTags())
		childTags.append(self.Tag(name="elements",
					  tags=elemTags))

		return [
			self.Tag(name="grid",
				tags=childTags,
				attrs={
					"width" : str(grid.width),
					"height" : str(grid.height),
					"uuid" : str(grid.uuid),
				}),
		]

class FupGrid(FupBaseClass):
	"""FUP/FBD element grid.
	"""

	factory = FupGrid_factory

	# Resize event callback.
	# If this is a callable, it it called with (width, height) on resize events.
	resizeEvent = None

	class CollLines(object):
		"""Collision cache line descriptor.
		This is used for describing drawn wires and
		detecting collisions among them.
		"""

		def __init__(self, lineSegments, wire=None, elem=None):
			"""lineSeg => Tuple of LineSeg2D() line segments.
			wire => FupWire() that this line belongs to, if any.
			elem => FupElem() that this line belongs to, if any.
			"""
			self.lineSegments = lineSegments
			self.wire = wire
			self.elem = elem

		def dup(self):
			"""Make a shallow copy of this Line.
			"""
			return self.__class__(self.lineSegments,
					      self.wire,
					      self.elem)

	def __init__(self, drawWidget, width, height, uuid=None):
		"""drawWidget => FupDrawWidget() instance.
		width => The grid width.
		height => The grid height.
		"""
		FupBaseClass.__init__(self, uuid=uuid)

		self.__drawWidget = drawWidget
		self.width = width
		self.height = height

		self.elems = []			# The FupElem_xxx()s in this grid
		self.wires = set()		# The FupConnIn/Out()s in this grid

		self.selectedElems = set()	# Set of selected elements in this grid
		self.expandedElems = set()	# Set of expanded elements in this grid
		self.clickedElem = None		# The recently clicked element in this grid
		self.clickedConn = None		# The recently clicked connection in this grid
		self.clickedArea = None		# The recently clicked area in this grid

		self.optSettingsCont = AwlOptimizerSettingsContainer()

		self.collisionCacheClear()

	def getFont(self, size=8, bold=False):
		return self.__drawWidget.getFont(size=size, bold=bold)

	@property
	def zoom(self):
		return self.__drawWidget.zoom

	def clear(self):
		for wire in self.wires:
			wire.disconnectAll()
		self.wires.clear()
		self.elems = []
		self.selectedElems.clear()
		self.collisionCacheClear()

	def collisionCacheClear(self):
		"""Clear the collision cache of drawn lines.
		"""
		# __collCacheLines is a list of FupGrid.CollLines() instances.
		self.__collCacheLines = []

	def collisionCacheAdd(self, line):
		"""Add a line entry to the collision cache.
		line => A FupGrid.CollLines() instance
		"""
		assert(isinstance(line, self.CollLines))
		self.__collCacheLines.append(line)

	def resize(self, width, height):
		"""Resize the grid.
		Returns True, if the resize was successfull.
		"""
		if width != self.width or height != self.height:
			if self.elems:
				minWidth = max(e.x + e.width for e in self.elems)
				minHeight = max(e.y + e.height for e in self.elems)
			else:
				minWidth = minHeight = 0
			if width >= minWidth and height >= minHeight:
				self.width = width
				self.height = height
				if callable(self.resizeEvent):
					self.resizeEvent(width, height)
				return True
		return False

	@property
	def interfDef(self):
		"""Get the block interface definition (AwlInterfDef() instance).
		"""
		return self.__drawWidget.interfDef

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
		# Remove CollLines()s that belong to 'wire' from the collision cache.
		self.__collCacheLines = [ line for line in self.__collCacheLines
					  if line.wire is None or\
					     line.wire is not wire ]

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
		for i, wire in enumerate(sorted(self.wires,
						key=lambda w: w.idNum)):
			wire.idNum = i

	def checkWireLine(self, painter, excludeWires, lineSeg):
		"""Checks if a wire line would be drawable and does not collide
		with another wire line.
		excludeWires => Iterable if FupWire()s to exclude from the check.
		lineSeg => The LineSeg2D() that should be drawn.
		Returns a set of colliding self.CollLines() instances.
		"""
		collisions = set()
		for line in self.__collCacheLines:
			if line.wire in excludeWires:
				continue
			for otherLineSeg in line.lineSegments:
				inter = lineSeg.intersection(otherLineSeg)
				if inter:
					# We have a collision.
					collisions.add(line.dup())
		return collisions

	def drawWireLine(self, painter, wire, lineSeg):
		"""Draw a wire line on 'painter'.
		wire => The FupWire() this line segment belongs to.
		lineSeg => The LineSeg2D() that describes the line to draw.
		"""
		if not lineSeg:
			return # Zero length line
		painter.drawLine(lineSeg.pointA.xInt, lineSeg.pointA.yInt,
				 lineSeg.pointB.xInt, lineSeg.pointB.yInt)
		self.collisionCacheAdd(self.CollLines((lineSeg,), wire=wire))

	def checkWireCollisions(self):
		"""Mark all wires as must-check-collisions.
		The collision check will be done at the next wire re-draw.
		"""
		for wire in self.wires:
			wire.checkCollisions()

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

	def __haveCollision(self, x, y, height, width, excludeElems=set()):
		if x < 0 or x >= self.width or\
		   y < 0 or y >= self.height:
			# Position is not on grid.
			return True
		for xx in range(x, x + width):
			for yy in range(y, y + height):
				elem = self.getElemAt(xx, yy)
				if elem in excludeElems:
					continue # Element is ignored.
				if elem:
					return True # Collision with other element.
		return False

	def canPlaceElem(self, elem):
		"""Check it we could place the element,
		but do not actually insert it into the grid.
		"""
		return not self.__haveCollision(elem.x, elem.y,
						elem.height, elem.width)

	def placeElem(self, elem):
		"""Insert an element into the grid.
		Returns False, if it was not possible to place the element.
		"""
		# Check if we have a collision.
		if not self.canPlaceElem(elem):
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
		# Remove CollLines()s that belong to 'elem' from the collision cache.
		self.__collCacheLines = [ line for line in self.__collCacheLines
					  if line.elem is None or\
					     line.elem is not elem ]

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
		if self.__haveCollision(toX, toY,
					elem.height, elem.width,
					excludeElems=excludeElems):
			return False # Collision. Cannot move.
		# Move the element.
		if not checkOnly:
			elem.x = toX
			elem.y = toY
			elem.checkWireCollisions()
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

	def expandElem(self, elem, expand=True, area=None):
		ok = False
		if elem and expand and not elem in self.expandedElems:
			ok = elem.expand(expand, area)
			if ok:
				self.expandedElems.add(elem)
		if elem and not expand and elem in self.expandedElems:
			ok = elem.expand(expand, area)
			if ok:
				self.expandedElems.remove(elem)
		return ok

	def unexpandAllElems(self):
		if self.expandedElems:
			for elem in self.expandedElems.copy():
				self.expandElem(elem, False)
			return True
		return False

class FupGridStub(object):
	"""FupGrid stub to get FupElem_factory working.
	"""

	def __init__(self):
		self.elements = []

	def getWireById(self, wireIdNum):
		if wireIdNum < 0:
			return None
		raise AwlSimError("FupGridStub: "
			"wireId=%d not allowed here." % (
			wireIdNum))

	def placeElem(self, elem):
		self.elements.append(elem)
		return True

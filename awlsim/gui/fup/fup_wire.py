# -*- coding: utf-8 -*-
#
# AWL simulator - FUP - Wire classes
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
#from awlsim.common.cython_support cimport * #@cy
from awlsim.common.compat import *

from awlsim.common.xmlfactory import *

from awlsim.gui.geo2d import *
from awlsim.gui.util import *
from awlsim.gui.fup.fup_base import *


class FupWire_factory(XmlFactory):
	def parser_open(self, tag=None):
		self.inWire = False
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		if not self.inWire:
			if tag.name == "wire":
				self.inWire = True
				idNum = tag.getAttrInt("id")
				uuid = tag.getAttr("uuid", None)
				if idNum in (w.idNum for w in self.grid.wires):
					raise self.Error("<wire id=%d> does "
						"already exist." % idNum)
				# Create wire and add it to the grid.
				FupWire(grid=self.grid, idNum=idNum, uuid=uuid)
				return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if self.inWire:
			if tag.name == "wire":
				self.inWire = False
				return
		else:
			if tag.name == "wires":
				self.parser_finish()
				return
		XmlFactory.parser_endTag(self, tag)

	def composer_getTags(self):
		return [
			self.Tag(name="wire",
				attrs={
					"id" : str(self.wire.idNum),
					"uuid" : str(self.wire.uuid),
				}),
		]

class FupWire(FupBaseClass):
	"""FUP/FBD wire connecting two FupConn connections."""

	factory = FupWire_factory

	BRANCH_DIA = 4
	MAX_CHANNEL_COLS = 8 # Max number of grid columns to search for a free vertical wire channel

	def __init__(self, grid, idNum=None, uuid=None):
		FupBaseClass.__init__(self, uuid=uuid)

		self.grid = grid
		if grid:
			self.connections = set() # The connections this wire is connected to
			self.outConn = None	 # The out-connection this is connected to

			if idNum is None:
				idNum = grid.getUnusedWireIdNum()
			self.idNum = idNum		# The ID number of this wire
			grid.addWire(self)

			self.__wirePen = QPen(QColor("#000000"))
			self.__wirePen.setWidth(2)
			self.__wireCollidingPen = QPen(QColor("#C02020"))
			self.__wireCollidingPen.setWidth(2)
			self.__wireBranchPen = QPen(QColor("#000000"))
			self.__wireBranchPen.setWidth(1)
			self.__wireBranchBrush = QBrush(QColor("#000000"))

			self.checkCollisions()

	def __invalidateAll(self):
		"""Other wires' channel choice depends on this wire. Re-route all.
		"""
		if self.grid:
			self.grid.checkWireCollisions()
		self.checkCollisions()

	def checkCollisions(self):
		"""Mark the wire as must-check-collisions.
		The collision check will be done at the next re-draw.
		"""
		self.__checkCollisions = True
		self.__hasCollision = False
		self.__channelX = None

	@staticmethod
	def __goesDown(yAbs0, inCoords):
		return sum(y for x, y in inCoords) / len(inCoords) >= yAbs0

	def __channelCandidates(self, xAbs0, inCoords):
		"""Get a list of candidate X coordinates for the vertical
		wire channel, ordered by preference.
		"""
		cellPixWidth = self.grid.cellPixWidth
		x0 = (xAbs0 // cellPixWidth) * cellPixWidth + cellPixWidth
		maxX = max([x0] + [ xAbs1 for xAbs1, yAbs1 in inCoords ])
		minInX = min([ xAbs1 for xAbs1, yAbs1 in inCoords ] or [x0])
		if all(yAbs1 == self.outConn.pixCoords[1]
		       for xAbs1, yAbs1 in inCoords):
			# Straight wire. There is no vertical segment to move.
			return [x0]
		# Stagger the channels of all outputs of the same element, so that
		# the vertical segments do not cross the horizontal stubs of the
		# neighbouring outputs: Wires going down: upper outputs use the
		# rightmost channels. Wires going up: lower outputs do.
		# Shifts are to the right only.
		step = max(2, cellPixWidth // self.MAX_CHANNEL_COLS)
		base = 0
		elem = self.outConn.elem
		if elem is not None and inCoords:
			yAbs0 = self.outConn.pixCoords[1]
			goesDown = self.__goesDown(yAbs0, inCoords)
			base = 0
			for other in elem.outputs:
				wire = other.wire if other is not None else None
				if wire is None or wire is self or wire.outConn is not other:
					continue
				otherY = other.pixCoords[1]
				otherCoords = [ c.pixCoords for c in wire.connections
						if c is not other ]
				if not otherCoords or\
				   wire.__goesDown(otherY, otherCoords) != goesDown:
					continue
				if (goesDown and otherY > yAbs0) or\
				   (not goesDown and otherY < yAbs0):
					base += 1
			base *= step
		shifts = (base, base + step, base + 2 * step)
		candidates = []
		col = 0
		while col < self.MAX_CHANNEL_COLS and\
		      (col == 0 or x0 + col * cellPixWidth <= maxX):
			for s in shifts:
				x = x0 + col * cellPixWidth + s
				if x >= xAbs0:
					candidates.append(x)
			col += 1
		# Never put the channel behind the nearest input.
		# That would make the wire run backwards.
		fitting = [ x for x in candidates if x <= minInX ]
		return fitting or [x0]

	def connect(self, conn):
		"""Add a connection to this wire.
		"""
		if conn in self.connections:
			return
		if conn.OUT and\
		   self.outConn is not None and\
		   self.outConn is not conn:
			# We already have an output connection.
			raise ValueError
		self.connections.add(conn)
		conn.wire = self
		if conn.OUT:
			self.outConn = conn
		self.__invalidateAll()

	def disconnectAll(self):
		"""Disconenct all connections.
		"""
		for conn in self.connections:
			conn.wire = None
		self.connections.clear()
		self.outConn = None
		self.grid.removeWire(self)
		self.__invalidateAll()

	def disconnect(self, conn):
		"""Disconnect a connection from this wire.
		"""
		conn.wire = None
		self.connections.remove(conn)
		if self.outConn is conn:
			# Only inputs left. Remove them all.
			self.disconnectAll()
		if len(self.connections) == 1:
			# Only one connection left. Remove that, too.
			self.disconnectAll()
		if not self.connections and not self.outConn:
			self.grid.removeWire(self)
		self.__invalidateAll()

	class DrawInfo(object):
		usesDirect = False

		def __init__(self, segments, segDirect):
			self.segments = segments	# Regular segments (list)
			self.segDirect = segDirect	# Direct connection segment

		@property
		def allRegularSegments(self):
			return self.segments

	class StartIntersections(object):
		posCount = 0
		negCount = 0
		horizCount = 0

	def draw(self, painter):
		if self.outConn is None:
			return # Only inputs. Do not draw.
		grid = self.grid

		# Branch circles diameter
		branchR, branchD = self.BRANCH_DIA // 2, self.BRANCH_DIA
		painter.setBrush(self.__wireBranchBrush)

		# Calculate the coordinates of all wire lines.
		cellPixWidth = self.grid.cellPixWidth
		xAbs0, yAbs0 = self.outConn.pixCoords
		inConns = [ c for c in self.connections if c is not self.outConn ]
		assert(all(c.IN for c in inConns))
		inCoords = [ c.pixCoords for c in inConns ]

		def buildLines(x):
			"""Construct the wire from out to all ins
			with the vertical channel at X coordinate 'x'.
			"""
			segStart = LineSeg2D.fromCoords(xAbs0, yAbs0, x, yAbs0)
			wireLines = []
			for xAbs1, yAbs1 in inCoords:
				seg0 = LineSeg2D.fromCoords(x, yAbs0, x, yAbs1)
				seg1 = LineSeg2D.fromCoords(x, yAbs1, xAbs1, yAbs1)
				segDirect = LineSeg2D.fromCoords(x, yAbs0, xAbs1, yAbs1)
				wireLines.append(self.DrawInfo((seg0, seg1), segDirect))
			return segStart, wireLines

		# Check for wire collisions, if requested.
		# Collision avoidance: Try several candidate X positions for the
		# vertical channel and use the first one without collisions.
		# The result is stored for future re-draws.
		if self.__checkCollisions:
			excludeWires = {self}
			self.__channelX = None
			for x in self.__channelCandidates(xAbs0, inCoords):
				segStart, wireLines = buildLines(x)
				if not any(grid.checkWireLine(painter, excludeWires, seg)
					   for seg in [segStart] + [
						seg for drawInfo in wireLines
						for seg in drawInfo.segments ]
					   if seg):
					self.__channelX = x
					break
			self.__hasCollision = self.__channelX is None
			if self.__hasCollision:
				self.__channelX = self.__channelCandidates(
					xAbs0, inCoords)[0]
			self.__checkCollisions = False
		x = self.__channelX
		segStart, wireLines = buildLines(x)

		def drawBranch(x, y):
			painter.setPen(self.__wireBranchPen)
			painter.drawEllipse(x - branchR, y - branchR,
					    branchD, branchD)

		def drawSeg(seg, pen=self.__wirePen):
			painter.setPen(pen)
			grid.drawWireLine(painter, self, seg)

		# Draw wire from output to all inputs
		drawSeg(segStart)
		for drawInfo in wireLines:
			if self.__hasCollision:
				drawSeg(drawInfo.segDirect,
					pen=self.__wireCollidingPen)
				drawInfo.usesDirect = True
			else:
				for seg in drawInfo.segments:
					drawSeg(seg)

		# Draw the branch circles
		startIntersections = self.StartIntersections()
		for drawInfo in wireLines:
			if drawInfo.usesDirect:
				continue
			for seg in drawInfo.allRegularSegments:
				intersections = {}
				def addInter(interPoint, otherSeg):
					if interPoint == segStart.pointB:
						vectY = otherSeg.vect.y
						if vectY == 0:
							startIntersections.horizCount += 1
						elif vectY > 0:
							startIntersections.posCount += 1
						else:
							startIntersections.negCount += 1
					else:
						key = (interPoint.xInt, interPoint.yInt)
						intersections[key] = intersections.setdefault(key, 0) + 1

				for otherDrawInfo in wireLines:
					if otherDrawInfo is drawInfo or\
					   otherDrawInfo.usesDirect:
						continue
					for otherSeg in otherDrawInfo.allRegularSegments:
						inter = seg.intersection(otherSeg)
						if not inter.intersects:
							continue
						addInter(inter.pointA, otherSeg)
						if inter.pointA != inter.pointB:
							addInter(inter.pointB, otherSeg)

				for (x, y), count in dictItems(intersections):
					if count > 1:
						drawBranch(x, y)
		# If there are at least two line segments starting from segStart
		# pointing into opposite directions, draw the start branch.
		count = int(bool(startIntersections.posCount)) +\
			int(bool(startIntersections.negCount)) +\
			int(bool(startIntersections.horizCount))
		if count >= 2:
			drawBranch(segStart.pointB.x, segStart.pointB.y)

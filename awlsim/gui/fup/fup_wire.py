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

	def __init__(self, grid, idNum=None, uuid=None):
		FupBaseClass.__init__(self, uuid=uuid)
		self.grid = grid
		self.connections = set()	# The connections this wire is connected to
		self.outConn = None		# The out-connection this is connected to

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

	def checkCollisions(self):
		"""Mark the wire as must-check-collisions.
		The collision check will be done at the next re-draw.
		"""
		self.__checkCollisions = True
		self.__hasCollision = False

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
		self.checkCollisions()

	def disconnectAll(self):
		"""Disconenct all connections.
		"""
		for conn in self.connections:
			conn.wire = None
		self.connections.clear()
		self.outConn = None
		self.grid.removeWire(self)
		self.checkCollisions()

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
		self.checkCollisions()

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
		x = (xAbs0 // cellPixWidth) * cellPixWidth + cellPixWidth
		segStart = LineSeg2D.fromCoords(xAbs0, yAbs0, x, yAbs0)
		wireLines = [] # List of DrawInfo()s
		for inConn in self.connections:
			if inConn is self.outConn:
				continue
			assert(inConn.IN)

			# Construct line segments to draw the wire from out to in.

			xAbs1, yAbs1 = inConn.pixCoords

			seg0 = LineSeg2D.fromCoords(x, yAbs0, x, yAbs1)
			seg1 = LineSeg2D.fromCoords(x, yAbs1, xAbs1, yAbs1)
			segDirect = LineSeg2D.fromCoords(x, yAbs0, xAbs1, yAbs1)

			wireLines.append(self.DrawInfo((seg0, seg1), segDirect))

		def drawBranch(x, y):
			painter.setPen(self.__wireBranchPen)
			painter.drawEllipse(x - branchR, y - branchR,
					    branchD, branchD)

		def drawSeg(seg, pen=self.__wirePen):
			painter.setPen(pen)
			grid.drawWireLine(painter, self, seg)

		# Check for wire collisions, if requested.
		# Store the result for future re-draws.
		if self.__checkCollisions:
			hasCollision = 0
			excludeWires = {self}
			for drawInfo in wireLines:
				hasCollision |= int(any(
					grid.checkWireLine(painter, excludeWires, seg)
					for seg in drawInfo.segments
				))
			self.__hasCollision = bool(hasCollision)
			self.__checkCollisions = False

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

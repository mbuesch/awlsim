# -*- coding: utf-8 -*-
#
# AWL simulator - 2D geometry
#
# Copyright 2017 Michael Buesch <m@bues.ch>
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


class Base2D(object):
	EPSILON = 0.000001

	def __hash__(self):
		return id(self)

	def __eq__(self, other):
		return self is other

	def __ne__(self, other):
		return not self.__eq__(other)

class Point2D(Base2D):
	"""2D point.
	"""

	__slots__ = ( "x", "y", )

	def __init__(self, x=0, y=0):
		self.x = x
		self.y = y

	def __eq__(self, other):
		return other is not None and\
		       self.x == other.x and self.y == other.y

	def __repr__(self):
		return "Point2D(x=%f, y=%f)" % (self.x, self.y)

class Vect2D(Base2D):
	"""2D vector.
	"""

	__slots__ = ( "x", "y", )

	def __init__(self, x=0, y=0):
		self.x = x
		self.y = y

	def __eq__(self, other):
		return other is not None and\
		       self.x == other.x and self.y == other.y

	def __repr__(self):
		return "Vect2D(x=%f, y=%f)" % (self.x, self.y)

class Inter2D(Base2D):
	"""Intersection information for two 2D line segments.
	"""

	__slots__ = ( "point", "vect", "__intersects", )

	def __init__(self, point=None, vect=None, intersects=False):
		"""point => Intersection point, or None.
		vect => Intersection vector.
			None or Vect2D(0, 0), if the intersection is only in one point.
		intersects => True, if there is an intersection.
		"""
		self.point = point
		self.vect = vect or Vect2D()
		self.__intersects = intersects

	def __eq__(self, other):
		return other is not None and\
		       self.point == other.point and\
		       self.vect == other.vect and\
		       self.__intersects == other.__intersects

	@property
	def intersects(self):
		"""Returns True, if there is an intersection.
		"""
		return self.__intersects and\
		       self.point is not None

	@property
	def lineSeg(self):
		"""Get the line segment of the intersection.
		Returns None, if self.point is None.
		"""
		if self.point:
			return LineSeg2D(self.point,
					 Point2D(self.point.x + self.vect.x,
						 self.point.y + self.vect.y))
		return None

	def __repr__(self):
		return "Inter2D(point=%s, vect=%s, intersects=%s)" % (
			self.point, self.vect, self.__intersects)

class LineSeg2D(Base2D):
	"""Line segment in 2D space.
	"""

	__slots__ = ( "pointA", "pointB", )

	def __init__(self, pointA, pointB):
		self.pointA = pointA
		self.pointB = pointB

	def __eq__(self, other):
		return other is not None and\
		       self.pointA == other.pointA and\
		       self.pointB == other.pointB

	@property
	def isHorizontal(self):
		"""Returns True, if the line segment is parallel to the X axis.
		"""
		return self.pointA.y == self.pointB.y

	@property
	def isVertical(self):
		"""Returns True, if the line segment is parallel to the Y axis.
		"""
		return self.pointA.x == self.pointB.x

	@property
	def slope(self):
		"""Get the slope of the line segment.
		Raises ZeroDivisionError if the line segment is vertical.
		"""
		return float(self.pointB.y - self.pointA.y) / \
			    (self.pointB.x - self.pointA.x)

	@property
	def intercept(self):
		"""Get the Y value of the Y axis crossing of this line.
		Raises ZeroDivisionError if the line segment is vertical.
		"""
		return self.pointA.y - (self.pointA.x * self.slope)

	@property
	def vect(self):
		"""Get the line segment vector.
		"""
		return Vect2D(-self.pointA.x + self.pointB.x,
			      -self.pointA.y + self.pointB.y)

	@staticmethod
	def __inRect(x, y, diaPointA, diaPointB):
		"""Check if point (x,y) is within an axis-aligned rect
		with the diagonal (diaPointA,diaPointB).
		"""
		diaMinX, diaMaxX = min(diaPointA.x, diaPointB.x),\
				   max(diaPointA.x, diaPointB.x)
		diaMinY, diaMaxY = min(diaPointA.y, diaPointB.y),\
				   max(diaPointA.y, diaPointB.y)
		return (x >= diaMinX and x <= diaMaxX and\
			y >= diaMinY and y <= diaMaxY)

	def __intersectionAligned(self, other):
		"""Get the intersection (if any) of two aligned line segments.
		'self' and 'other' must be aligned in order for this to
		return correct results.
		"""
		for interPoint in (other.pointA, other.pointB):
			x, y = interPoint.x, interPoint.y
			if self.__inRect(x, y, self.pointA, self.pointB):
				if self.__inRect(self.pointA.x, self.pointA.y,
						 other.pointA, other.pointB):
					vect = Vect2D(self.pointA.x - x,
						      self.pointA.y - y)
				else:
					vect = Vect2D(self.pointB.x - x,
						      self.pointB.y - y)
				return Inter2D(point=Point2D(x, y),
					       vect=vect,
					       intersects=True)
		return Inter2D()

	def __intersectionVertical(self, other):
		"""Get the intersection of a vertical line segment 'self'
		and a non-vertical line segment 'other'.
		'self' must be vertical in order for this to
		return correct results.
		"""
		x = self.pointA.x
		y = (x - other.pointA.x) * other.slope + other.pointA.y
		return Inter2D(point=Point2D(x, y),
			       intersects=self.__inRect(
					x, y, self.pointA, self.pointB))

	def intersection(self, other):
		"""Get the intersection of this line segment
		with another line segment.
		Returns an Inter2D.
		"""
		try:
			selfVert, otherVert = self.isVertical, other.isVertical
			if selfVert and otherVert:
				# Both line segments are vertical.
				# If they are aligned, they might overlap.
				if self.pointA.x == other.pointA.x:
					return self.__intersectionAligned(other)
				return Inter2D()
			elif selfVert:
				# self is vertical. other is not vertical.
				return self.__intersectionVertical(other)
			elif otherVert:
				# self is not vertical. other is vertical.
				return other.__intersectionVertical(self)
			# Get the intersection of two arbitrary
			# non-vertical line segments.
			selfSlope, otherSlope = self.slope, other.slope
			selfInter, otherInter = self.intercept, other.intercept
			try:
				x = (otherInter - selfInter) / \
				    (selfSlope - otherSlope)
				y = selfSlope * x + selfInter
				assert(abs(y - (otherSlope * x + otherInter)) < self.EPSILON)
			except ZeroDivisionError:
				# The line segments are parallel.
				# If they have the same intercept they are aligned
				# and might overlap.
				if abs(selfInter - otherInter) < self.EPSILON:
					return self.__intersectionAligned(other)
				return Inter2D()
			return Inter2D(point=Point2D(x, y),
				       intersects=self.__inRect(
						x, y, self.pointA, self.pointB))
		except ZeroDivisionError:
			pass
		return Inter2D()

	def __repr__(self):
		return "LineSeg2D(pointA=%s, pointB=%s)" % (
			self.pointA, self.pointB)

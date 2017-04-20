from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim_tstlib import *

from awlsim.gui.geo2d import *


class Test_LineSeg2D(object):
	def test_point(self):
		p = Point2D()
		assert_eq(p.x, 0)
		assert_eq(p.y, 0)
		assert_eq(bool(p), False)

		p = Point2D(42, -42)
		assert_eq(p.x, 42)
		assert_eq(p.y, -42)
		assert_eq(p, Point2D(42, -42))
		assert_ne(p, Point2D(42, 42))
		assert_ne(p, Point2D(-42, -42))
		assert_eq(bool(p), True)

	def test_vect(self):
		v = Vect2D()
		assert_eq(v.x, 0)
		assert_eq(v.y, 0)
		assert_eq(bool(v), False)

		v = Vect2D(42, -42)
		assert_eq(v.x, 42)
		assert_eq(v.y, -42)
		assert_eq(v, Vect2D(42, -42))
		assert_ne(v, Vect2D(42, 42))
		assert_ne(v, Vect2D(-42, -42))
		assert_eq(bool(v), True)

	def test_lineseg(self):
		s = LineSeg2D.fromCoords(3, 4, 3, 4)
		assert_eq(s.pointA, Point2D(3, 4))
		assert_eq(s.pointB, Point2D(3, 4))
		assert_eq(bool(s), False)

		s = LineSeg2D.fromCoords(1, 2, 3, 4)
		assert_eq(s.pointA, Point2D(1, 2))
		assert_eq(s.pointB, Point2D(3, 4))
		assert_eq(bool(s), True)

		assert_eq(LineSeg2D.fromCoords(1, 2, 3, 4), LineSeg2D.fromCoords(1, 2, 3, 4))
		assert_ne(LineSeg2D.fromCoords(1, 2, 3, 4), LineSeg2D.fromCoords(-1, 2, 3, 4))
		assert_ne(LineSeg2D.fromCoords(1, 2, 3, 4), LineSeg2D.fromCoords(1, -2, 3, 4))
		assert_ne(LineSeg2D.fromCoords(1, 2, 3, 4), LineSeg2D.fromCoords(1, 2, -3, 4))
		assert_ne(LineSeg2D.fromCoords(1, 2, 3, 4), LineSeg2D.fromCoords(1, 2, 3, -4))
		assert_eq(bool(s), True)

	def test_intersection_base(self):
		inter = Inter2D()
		assert_eq(inter, Inter2D())
		assert_ne(inter, Inter2D(Point2D(1, 1)))
		assert_is(inter.intersects, False)
		assert_is(inter.point, None)
		assert_eq(inter.vect, Vect2D())
		assert_eq(bool(inter), False)

		inter = Inter2D(Point2D(42, -42), Vect2D(142, -142), False)
		assert_eq(inter, Inter2D(Point2D(42, -42), Vect2D(142, -142), False))
		assert_ne(inter, Inter2D(Point2D(42, -42), Vect2D(143, -142), False))
		assert_is(inter.intersects, False)
		assert_eq(inter.point, Point2D(42, -42))
		assert_eq(inter.vect, Vect2D(142, -142))
		assert_eq(bool(inter), False)

		inter = Inter2D(Point2D(42, -42), Vect2D(142, -142), True)
		assert_eq(inter, Inter2D(Point2D(42, -42), Vect2D(142, -142), True))
		assert_ne(inter, Inter2D(Point2D(42, -42), Vect2D(142, -142), False))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(42, -42))
		assert_eq(inter.vect, Vect2D(142, -142))
		assert_eq(bool(inter), True)

		inter = Inter2D(None, Vect2D(142, -142), True)
		assert_is(inter.intersects, False)
		assert_is(inter.point, None)
		assert_eq(inter.vect, Vect2D(142, -142))
		assert_eq(bool(inter), False)

	def test_intersection(self):
		# intersecting
		inter = LineSeg2D(Point2D(2, 7), Point2D(8, 1)).intersection(
			LineSeg2D(Point2D(9, 8), Point2D(3, 2)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(5, 4))
		assert_eq(inter.vect, Vect2D())
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(5, 4), Point2D(5, 4)))

		# not intersecting
		inter = LineSeg2D(Point2D(1, 1), Point2D(4, 5)).intersection(
			LineSeg2D(Point2D(6, 6), Point2D(8, 2)))
		assert_is(inter.intersects, False)
		assert_eq(inter.point, Point2D(5.5, 7))
		assert_eq(inter.vect, Vect2D())
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(5.5, 7), Point2D(5.5, 7)))

		# parallel, horizontal, not intersecting
		inter = LineSeg2D(Point2D(3, 2), Point2D(9, 2)).intersection(
			LineSeg2D(Point2D(5, 3), Point2D(14, 3)))
		assert_is(inter.intersects, False)
		assert_is_none(inter.point)
		assert_eq(inter.vect, Vect2D())
		assert_is_none(inter.lineSeg)

		# parallel, vertical, not intersecting
		inter = LineSeg2D(Point2D(3, 9), Point2D(3, 4)).intersection(
			LineSeg2D(Point2D(5, 2), Point2D(5, 5)))
		assert_is(inter.intersects, False)
		assert_is_none(inter.point)
		assert_eq(inter.vect, Vect2D())
		assert_is_none(inter.lineSeg)

		# parallel, horizontal, intersecting
		inter = LineSeg2D(Point2D(3, 2), Point2D(9, 2)).intersection(
			LineSeg2D(Point2D(5, 2), Point2D(14, 2)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(9, 2))
		assert_eq(inter.vect, Vect2D(-4, 0))
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(9, 2), Point2D(5, 2)))

		# parallel, horizontal, intersecting
		inter = LineSeg2D(Point2D(3, 2), Point2D(9, 2)).intersection(
			LineSeg2D(Point2D(14, 2), Point2D(5, 2)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(9, 2))
		assert_eq(inter.vect, Vect2D(-4, 0))
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(9, 2), Point2D(5, 2)))

		# parallel, horizontal, intersecting
		inter = LineSeg2D(Point2D(9, 2), Point2D(3, 2)).intersection(
			LineSeg2D(Point2D(14, 2), Point2D(5, 2)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(9, 2))
		assert_eq(inter.vect, Vect2D(-4, 0))
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(9, 2), Point2D(5, 2)))

		# parallel, horizontal, intersecting
		inter = LineSeg2D(Point2D(5, 2), Point2D(14, 2)).intersection(
			LineSeg2D(Point2D(3, 2), Point2D(9, 2)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(5, 2))
		assert_eq(inter.vect, Vect2D(4, 0))
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(5, 2), Point2D(9, 2)))

		# parallel, vertical, intersecting
		inter = LineSeg2D(Point2D(3, 9), Point2D(3, 4)).intersection(
			LineSeg2D(Point2D(3, 2), Point2D(3, 5)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(3, 4))
		assert_eq(inter.vect, Vect2D(0, 1))
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(3, 4), Point2D(3, 5)))

		# parallel, vertical, intersecting
		inter = LineSeg2D(Point2D(3, 2), Point2D(3, 5)).intersection(
			LineSeg2D(Point2D(3, 9), Point2D(3, 4)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(3, 5))
		assert_eq(inter.vect, Vect2D(0, -1))
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(3, 5), Point2D(3, 4)))

		# parallel, vertical, intersecting
		inter = LineSeg2D(Point2D(60, 30), Point2D(60, 90)).intersection(
			LineSeg2D(Point2D(60, 30), Point2D(60, 70)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(60, 30))
		assert_eq(inter.vect, Vect2D(0, 40))
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(60, 30), Point2D(60, 70)))

		# parallel, vertical, intersecting
		inter = LineSeg2D(Point2D(4, 8), Point2D(4, 2)).intersection(
			LineSeg2D(Point2D(4, 8), Point2D(4, 4)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(4, 8))
		assert_eq(inter.vect, Vect2D(0, -4))
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(4, 8), Point2D(4, 4)))

		# parallel, vertical, intersecting
		inter = LineSeg2D(Point2D(4, 8), Point2D(4, 2)).intersection(
			LineSeg2D(Point2D(4, 6), Point2D(4, 2)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(4, 2))
		assert_eq(inter.vect, Vect2D(0, 4))
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(4, 2), Point2D(4, 6)))

		# parallel, vertical, intersecting
		inter = LineSeg2D(Point2D(4, 8), Point2D(4, 2)).intersection(
			LineSeg2D(Point2D(4, 7), Point2D(4, 3)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(4, 7))
		assert_eq(inter.vect, Vect2D(0, -4))
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(4, 7), Point2D(4, 3)))

		# parallel, vertical, intersecting
		inter = LineSeg2D(Point2D(4, 8), Point2D(4, 4)).intersection(
			LineSeg2D(Point2D(4, 8), Point2D(4, 2)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(4, 8))
		assert_eq(inter.vect, Vect2D(0, -4))
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(4, 8), Point2D(4, 4)))

		# parallel, vertical, intersecting
		inter = LineSeg2D(Point2D(4, 6), Point2D(4, 2)).intersection(
			LineSeg2D(Point2D(4, 8), Point2D(4, 2)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(4, 6))
		assert_eq(inter.vect, Vect2D(0, -4))
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(4, 6), Point2D(4, 2)))

		# parallel, vertical, intersecting
		inter = LineSeg2D(Point2D(4, 7), Point2D(4, 3)).intersection(
			LineSeg2D(Point2D(4, 8), Point2D(4, 2)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(4, 7))
		assert_eq(inter.vect, Vect2D(0, -4))
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(4, 7), Point2D(4, 3)))

		# parallel, vertical, pointy intersection
		inter = LineSeg2D(Point2D(4, 1), Point2D(4, 5)).intersection(
			LineSeg2D(Point2D(4, 5), Point2D(4, 7)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(4, 5))
		assert_eq(inter.vect, Vect2D(0, 0))
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(4, 5), Point2D(4, 5)))

		# parallel, vertical, pointy intersection
		inter = LineSeg2D(Point2D(4, 5), Point2D(4, 1)).intersection(
			LineSeg2D(Point2D(4, 5), Point2D(4, 7)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(4, 5))
		assert_eq(inter.vect, Vect2D(0, 0))
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(4, 5), Point2D(4, 5)))

		# parallel, vertical, pointy intersection
		inter = LineSeg2D(Point2D(4, 5), Point2D(4, 1)).intersection(
			LineSeg2D(Point2D(4, 7), Point2D(4, 5)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(4, 5))
		assert_eq(inter.vect, Vect2D(0, 0))
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(4, 5), Point2D(4, 5)))

		# parallel, vertical, pointy intersection
		inter = LineSeg2D(Point2D(4, 1), Point2D(4, 5)).intersection(
			LineSeg2D(Point2D(4, 7), Point2D(4, 5)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(4, 5))
		assert_eq(inter.vect, Vect2D(0, 0))
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(4, 5), Point2D(4, 5)))

		# parallel, vertical, full intersection
		inter = LineSeg2D(Point2D(4, 1), Point2D(4, 7)).intersection(
			LineSeg2D(Point2D(4, 1), Point2D(4, 7)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(4, 1))
		assert_eq(inter.vect, Vect2D(0, 6))
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(4, 1), Point2D(4, 7)))

		# parallel, vertical, full intersection
		inter = LineSeg2D(Point2D(4, 7), Point2D(4, 1)).intersection(
			LineSeg2D(Point2D(4, 7), Point2D(4, 1)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(4, 7))
		assert_eq(inter.vect, Vect2D(0, -6))
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(4, 7), Point2D(4, 1)))

		# parallel, vertical, full intersection
		inter = LineSeg2D(Point2D(4, 1), Point2D(4, 7)).intersection(
			LineSeg2D(Point2D(4, 7), Point2D(4, 1)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(4, 1))
		assert_eq(inter.vect, Vect2D(0, 6))
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(4, 1), Point2D(4, 7)))

		# parallel, vertical, full intersection
		inter = LineSeg2D(Point2D(4, 7), Point2D(4, 1)).intersection(
			LineSeg2D(Point2D(4, 1), Point2D(4, 7)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(4, 7))
		assert_eq(inter.vect, Vect2D(0, -6))
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(4, 7), Point2D(4, 1)))

		# AB vertical, CD horizontal, intersecting
		inter = LineSeg2D(Point2D(4, 1), Point2D(4, 8)).intersection(
			LineSeg2D(Point2D(2, 5), Point2D(12, 5)))
		assert_is(inter.intersects, True)
		assert_eq(inter.point, Point2D(4, 5))
		assert_eq(inter.vect, Vect2D())
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(4, 5), Point2D(4, 5)))

		# AB vertical, CD horizontal, not intersecting
		inter = LineSeg2D(Point2D(x=180, y=130), Point2D(x=180, y=110)).intersection(
			LineSeg2D(Point2D(x=236, y=110), Point2D(x=240, y=110)))
		assert_is(inter.intersects, False)
		assert_eq(inter.point, Point2D(180, 110))
		assert_eq(inter.vect, Vect2D())
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(180, 110), Point2D(180, 110)))

		# AB horizontal, CD vertical, not intersecting
		inter = LineSeg2D(Point2D(9, 5), Point2D(4, 5)).intersection(
			LineSeg2D(Point2D(8, 6), Point2D(8, 11)))
		assert_is(inter.intersects, False)
		assert_eq(inter.point, Point2D(8, 5))
		assert_eq(inter.vect, Vect2D())
		assert_eq(inter.lineSeg, LineSeg2D(Point2D(8, 5), Point2D(8, 5)))

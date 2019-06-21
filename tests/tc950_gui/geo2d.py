from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim_tstlib import *
initTest(__file__)

from awlsim.gui.geo2d import *


class Test_LineSeg2D(TestCase):
	def test_point(self):
		p = Point2D()
		self.assertEqual(p.x, 0)
		self.assertEqual(p.y, 0)
		self.assertFalse(p)

		p = Point2D(42, -42)
		self.assertEqual(p.x, 42)
		self.assertEqual(p.y, -42)
		self.assertEqual(p, Point2D(42, -42))
		self.assertNotEqual(p, Point2D(42, 42))
		self.assertNotEqual(p, Point2D(-42, -42))
		self.assertTrue(p)

	def test_vect(self):
		v = Vect2D()
		self.assertEqual(v.x, 0)
		self.assertEqual(v.y, 0)
		self.assertFalse(v)

		v = Vect2D(42, -42)
		self.assertEqual(v.x, 42)
		self.assertEqual(v.y, -42)
		self.assertEqual(v, Vect2D(42, -42))
		self.assertNotEqual(v, Vect2D(42, 42))
		self.assertNotEqual(v, Vect2D(-42, -42))
		self.assertTrue(v)

	def test_lineseg(self):
		s = LineSeg2D.fromCoords(3, 4, 3, 4)
		self.assertEqual(s.pointA, Point2D(3, 4))
		self.assertEqual(s.pointB, Point2D(3, 4))
		self.assertFalse(s)

		s = LineSeg2D.fromCoords(1, 2, 3, 4)
		self.assertEqual(s.pointA, Point2D(1, 2))
		self.assertEqual(s.pointB, Point2D(3, 4))
		self.assertTrue(s)

		self.assertEqual(LineSeg2D.fromCoords(1, 2, 3, 4), LineSeg2D.fromCoords(1, 2, 3, 4))
		self.assertNotEqual(LineSeg2D.fromCoords(1, 2, 3, 4), LineSeg2D.fromCoords(-1, 2, 3, 4))
		self.assertNotEqual(LineSeg2D.fromCoords(1, 2, 3, 4), LineSeg2D.fromCoords(1, -2, 3, 4))
		self.assertNotEqual(LineSeg2D.fromCoords(1, 2, 3, 4), LineSeg2D.fromCoords(1, 2, -3, 4))
		self.assertNotEqual(LineSeg2D.fromCoords(1, 2, 3, 4), LineSeg2D.fromCoords(1, 2, 3, -4))
		self.assertTrue(s)

	def test_intersection_base(self):
		inter = Inter2D()
		self.assertEqual(inter, Inter2D())
		self.assertNotEqual(inter, Inter2D(Point2D(1, 1)))
		self.assertFalse(inter.intersects)
		self.assertIsNone(inter.point)
		self.assertEqual(inter.vect, Vect2D())
		self.assertFalse(inter)

		inter = Inter2D(Point2D(42, -42), Vect2D(142, -142), False)
		self.assertEqual(inter, Inter2D(Point2D(42, -42), Vect2D(142, -142), False))
		self.assertNotEqual(inter, Inter2D(Point2D(42, -42), Vect2D(143, -142), False))
		self.assertFalse(inter.intersects)
		self.assertEqual(inter.point, Point2D(42, -42))
		self.assertEqual(inter.vect, Vect2D(142, -142))
		self.assertFalse(inter)

		inter = Inter2D(Point2D(42, -42), Vect2D(142, -142), True)
		self.assertEqual(inter, Inter2D(Point2D(42, -42), Vect2D(142, -142), True))
		self.assertNotEqual(inter, Inter2D(Point2D(42, -42), Vect2D(142, -142), False))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(42, -42))
		self.assertEqual(inter.vect, Vect2D(142, -142))
		self.assertTrue(inter)

		inter = Inter2D(None, Vect2D(142, -142), True)
		self.assertFalse(inter.intersects)
		self.assertIsNone(inter.point)
		self.assertEqual(inter.vect, Vect2D(142, -142))
		self.assertFalse(inter)

	def test_intersection(self):
		# intersecting
		inter = LineSeg2D(Point2D(2, 7), Point2D(8, 1)).intersection(
			LineSeg2D(Point2D(9, 8), Point2D(3, 2)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(5, 4))
		self.assertEqual(inter.vect, Vect2D())
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(5, 4), Point2D(5, 4)))

		# not intersecting
		inter = LineSeg2D(Point2D(1, 1), Point2D(4, 5)).intersection(
			LineSeg2D(Point2D(6, 6), Point2D(8, 2)))
		self.assertFalse(inter.intersects)
		self.assertEqual(inter.point, Point2D(5.5, 7))
		self.assertEqual(inter.vect, Vect2D())
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(5.5, 7), Point2D(5.5, 7)))

		# parallel, horizontal, not intersecting
		inter = LineSeg2D(Point2D(3, 2), Point2D(9, 2)).intersection(
			LineSeg2D(Point2D(5, 3), Point2D(14, 3)))
		self.assertFalse(inter.intersects)
		self.assertIsNone(inter.point)
		self.assertEqual(inter.vect, Vect2D())
		self.assertIsNone(inter.lineSeg)

		# parallel, vertical, not intersecting
		inter = LineSeg2D(Point2D(3, 9), Point2D(3, 4)).intersection(
			LineSeg2D(Point2D(5, 2), Point2D(5, 5)))
		self.assertFalse(inter.intersects)
		self.assertIsNone(inter.point)
		self.assertEqual(inter.vect, Vect2D())
		self.assertIsNone(inter.lineSeg)

		# parallel, horizontal, intersecting
		inter = LineSeg2D(Point2D(3, 2), Point2D(9, 2)).intersection(
			LineSeg2D(Point2D(5, 2), Point2D(14, 2)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(9, 2))
		self.assertEqual(inter.vect, Vect2D(-4, 0))
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(9, 2), Point2D(5, 2)))

		# parallel, horizontal, intersecting
		inter = LineSeg2D(Point2D(3, 2), Point2D(9, 2)).intersection(
			LineSeg2D(Point2D(14, 2), Point2D(5, 2)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(9, 2))
		self.assertEqual(inter.vect, Vect2D(-4, 0))
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(9, 2), Point2D(5, 2)))

		# parallel, horizontal, intersecting
		inter = LineSeg2D(Point2D(9, 2), Point2D(3, 2)).intersection(
			LineSeg2D(Point2D(14, 2), Point2D(5, 2)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(9, 2))
		self.assertEqual(inter.vect, Vect2D(-4, 0))
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(9, 2), Point2D(5, 2)))

		# parallel, horizontal, intersecting
		inter = LineSeg2D(Point2D(5, 2), Point2D(14, 2)).intersection(
			LineSeg2D(Point2D(3, 2), Point2D(9, 2)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(5, 2))
		self.assertEqual(inter.vect, Vect2D(4, 0))
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(5, 2), Point2D(9, 2)))

		# parallel, vertical, intersecting
		inter = LineSeg2D(Point2D(3, 9), Point2D(3, 4)).intersection(
			LineSeg2D(Point2D(3, 2), Point2D(3, 5)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(3, 4))
		self.assertEqual(inter.vect, Vect2D(0, 1))
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(3, 4), Point2D(3, 5)))

		# parallel, vertical, intersecting
		inter = LineSeg2D(Point2D(3, 2), Point2D(3, 5)).intersection(
			LineSeg2D(Point2D(3, 9), Point2D(3, 4)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(3, 5))
		self.assertEqual(inter.vect, Vect2D(0, -1))
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(3, 5), Point2D(3, 4)))

		# parallel, vertical, intersecting
		inter = LineSeg2D(Point2D(60, 30), Point2D(60, 90)).intersection(
			LineSeg2D(Point2D(60, 30), Point2D(60, 70)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(60, 30))
		self.assertEqual(inter.vect, Vect2D(0, 40))
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(60, 30), Point2D(60, 70)))

		# parallel, vertical, intersecting
		inter = LineSeg2D(Point2D(4, 8), Point2D(4, 2)).intersection(
			LineSeg2D(Point2D(4, 8), Point2D(4, 4)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(4, 8))
		self.assertEqual(inter.vect, Vect2D(0, -4))
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(4, 8), Point2D(4, 4)))

		# parallel, vertical, intersecting
		inter = LineSeg2D(Point2D(4, 8), Point2D(4, 2)).intersection(
			LineSeg2D(Point2D(4, 6), Point2D(4, 2)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(4, 2))
		self.assertEqual(inter.vect, Vect2D(0, 4))
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(4, 2), Point2D(4, 6)))

		# parallel, vertical, intersecting
		inter = LineSeg2D(Point2D(4, 8), Point2D(4, 2)).intersection(
			LineSeg2D(Point2D(4, 7), Point2D(4, 3)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(4, 7))
		self.assertEqual(inter.vect, Vect2D(0, -4))
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(4, 7), Point2D(4, 3)))

		# parallel, vertical, intersecting
		inter = LineSeg2D(Point2D(4, 8), Point2D(4, 4)).intersection(
			LineSeg2D(Point2D(4, 8), Point2D(4, 2)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(4, 8))
		self.assertEqual(inter.vect, Vect2D(0, -4))
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(4, 8), Point2D(4, 4)))

		# parallel, vertical, intersecting
		inter = LineSeg2D(Point2D(4, 6), Point2D(4, 2)).intersection(
			LineSeg2D(Point2D(4, 8), Point2D(4, 2)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(4, 6))
		self.assertEqual(inter.vect, Vect2D(0, -4))
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(4, 6), Point2D(4, 2)))

		# parallel, vertical, intersecting
		inter = LineSeg2D(Point2D(4, 7), Point2D(4, 3)).intersection(
			LineSeg2D(Point2D(4, 8), Point2D(4, 2)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(4, 7))
		self.assertEqual(inter.vect, Vect2D(0, -4))
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(4, 7), Point2D(4, 3)))

		# parallel, vertical, pointy intersection
		inter = LineSeg2D(Point2D(4, 1), Point2D(4, 5)).intersection(
			LineSeg2D(Point2D(4, 5), Point2D(4, 7)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(4, 5))
		self.assertEqual(inter.vect, Vect2D(0, 0))
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(4, 5), Point2D(4, 5)))

		# parallel, vertical, pointy intersection
		inter = LineSeg2D(Point2D(4, 5), Point2D(4, 1)).intersection(
			LineSeg2D(Point2D(4, 5), Point2D(4, 7)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(4, 5))
		self.assertEqual(inter.vect, Vect2D(0, 0))
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(4, 5), Point2D(4, 5)))

		# parallel, vertical, pointy intersection
		inter = LineSeg2D(Point2D(4, 5), Point2D(4, 1)).intersection(
			LineSeg2D(Point2D(4, 7), Point2D(4, 5)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(4, 5))
		self.assertEqual(inter.vect, Vect2D(0, 0))
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(4, 5), Point2D(4, 5)))

		# parallel, vertical, pointy intersection
		inter = LineSeg2D(Point2D(4, 1), Point2D(4, 5)).intersection(
			LineSeg2D(Point2D(4, 7), Point2D(4, 5)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(4, 5))
		self.assertEqual(inter.vect, Vect2D(0, 0))
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(4, 5), Point2D(4, 5)))

		# parallel, vertical, full intersection
		inter = LineSeg2D(Point2D(4, 1), Point2D(4, 7)).intersection(
			LineSeg2D(Point2D(4, 1), Point2D(4, 7)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(4, 1))
		self.assertEqual(inter.vect, Vect2D(0, 6))
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(4, 1), Point2D(4, 7)))

		# parallel, vertical, full intersection
		inter = LineSeg2D(Point2D(4, 7), Point2D(4, 1)).intersection(
			LineSeg2D(Point2D(4, 7), Point2D(4, 1)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(4, 7))
		self.assertEqual(inter.vect, Vect2D(0, -6))
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(4, 7), Point2D(4, 1)))

		# parallel, vertical, full intersection
		inter = LineSeg2D(Point2D(4, 1), Point2D(4, 7)).intersection(
			LineSeg2D(Point2D(4, 7), Point2D(4, 1)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(4, 1))
		self.assertEqual(inter.vect, Vect2D(0, 6))
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(4, 1), Point2D(4, 7)))

		# parallel, vertical, full intersection
		inter = LineSeg2D(Point2D(4, 7), Point2D(4, 1)).intersection(
			LineSeg2D(Point2D(4, 1), Point2D(4, 7)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(4, 7))
		self.assertEqual(inter.vect, Vect2D(0, -6))
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(4, 7), Point2D(4, 1)))

		# AB vertical, CD horizontal, intersecting
		inter = LineSeg2D(Point2D(4, 1), Point2D(4, 8)).intersection(
			LineSeg2D(Point2D(2, 5), Point2D(12, 5)))
		self.assertTrue(inter.intersects)
		self.assertEqual(inter.point, Point2D(4, 5))
		self.assertEqual(inter.vect, Vect2D())
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(4, 5), Point2D(4, 5)))

		# AB vertical, CD horizontal, not intersecting
		inter = LineSeg2D(Point2D(x=180, y=130), Point2D(x=180, y=110)).intersection(
			LineSeg2D(Point2D(x=236, y=110), Point2D(x=240, y=110)))
		self.assertFalse(inter.intersects)
		self.assertEqual(inter.point, Point2D(180, 110))
		self.assertEqual(inter.vect, Vect2D())
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(180, 110), Point2D(180, 110)))

		# AB horizontal, CD vertical, not intersecting
		inter = LineSeg2D(Point2D(9, 5), Point2D(4, 5)).intersection(
			LineSeg2D(Point2D(8, 6), Point2D(8, 11)))
		self.assertFalse(inter.intersects)
		self.assertEqual(inter.point, Point2D(8, 5))
		self.assertEqual(inter.vect, Vect2D())
		self.assertEqual(inter.lineSeg, LineSeg2D(Point2D(8, 5), Point2D(8, 5)))

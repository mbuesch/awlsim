# -*- coding: utf-8 -*-
#
# AWL simulator - FUP - Wire classes
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


class FupWire_factory(XmlFactory):
	def parser_open(self, tag=None):
		self.inWire = False
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		if not self.inWire:
			if tag.name == "wire":
				self.inWire = True
				idNum = tag.getAttrInt("id")
				if idNum in (w.idNum for w in self.grid.wires):
					raise self.Error("<wire id=%d> does "
						"already exist." % idNum)
				# Create wire and add it to the grid.
				FupWire(grid=self.grid, idNum=idNum)
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
				}),
		]

class FupWire(FupBaseClass):
	"""FUP/FBD wire connecting two FupConn connections."""

	factory = FupWire_factory

	BRANCH_DIA = 4

	def __init__(self, grid, idNum=None):
		FupBaseClass.__init__(self)
		self.grid = grid
		self.connections = set()	# The connections this wire is connected to
		self.outConn = None		# The out-connection this is connected to

		if idNum is None:
			idNum = grid.getUnusedWireIdNum()
		self.idNum = idNum		# The ID number of this wire
		grid.addWire(self)

		self.__wirePen = QPen(QColor("#000000"))
		self.__wirePen.setWidth(2)
		self.__wireBranchPen = QPen(QColor("#000000"))
		self.__wireBranchPen.setWidth(1)
		self.__wireBranchBrush = QBrush(QColor("#000000"))

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

	def disconnectAll(self):
		"""Disconenct all connections.
		"""
		for conn in self.connections:
			conn.wire = None
		self.connections.clear()
		self.outConn = None
		self.grid.removeWire(self)

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

	def draw(self, painter):
		if self.outConn is None:
			return
		xAbs0, yAbs0 = self.outConn.pixCoords
		r, d = self.BRANCH_DIA // 2, self.BRANCH_DIA
		painter.setBrush(self.__wireBranchBrush)
		for conn in self.connections:
			xAbs1, yAbs1 = conn.pixCoords
			painter.setPen(self.__wirePen)
			painter.drawLine(xAbs0, yAbs0, xAbs0, yAbs1)
			painter.drawLine(xAbs0, yAbs1, xAbs1, yAbs1)
			painter.setPen(self.__wireBranchPen)
			painter.drawEllipse(xAbs0 - r, yAbs0 - r, d, d)
			painter.drawEllipse(xAbs1 - r, yAbs1 - r, d, d)

# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - Helper routines
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

from awlsim.fupcompiler.fupcompiler_elembool import *


__all__ = [
	"FupCompiler_Helpers",
]


class FupCompiler_Helpers(object):
	"""FUP compiler helper routines.
	"""

	@staticmethod
	def genIntermediateAND(parentElem, leftConn, rightConn):
		"""
		Transform this:
		  [x]-----------------------[rightConn]

		into this:           _____
		  [x]---------------|0 & 0|---[rightConn]
		  [leftConn]--------|1____|

		If leftConn is connected already (to y), the result will look like this:
		                     _____
		  [x]---------------|0 & 0|---[rightConn]
		  [leftConn]----+---|1____|
		                |
		                +----[y]

		x is at least one arbitrary connection.
		leftConn must be an output.
		rightConn must be an input.
		rightConn must be connected (to x).
		"""

		assert(leftConn.dirOut)
		assert(rightConn.dirIn)
		assert(rightConn.isConnected)

		# Get the left-handed wire or create one.
		if leftConn.isConnected:
			leftWire = leftConn.wire
		else:
			leftWire = parentElem.grid.newWire()
			leftWire.addConn(leftConn)

		# disconnect the right-handed connection from its wire.
		origWire = rightConn.wire
		origWire.removeConn(rightConn)

		# Create a new right-handed wire
		rightWire = parentElem.grid.newWire()
		rightWire.addConn(rightConn)

		# Create a virtual AND element to connect the elements.
		virtElemAnd = FupCompiler_ElemBoolAnd(grid=parentElem.grid,
						      x=parentElem.x, y=parentElem.y,
						      content=None,
						      virtual=True)
		virtElemAndIn0 = FupCompiler_Conn(elem=virtElemAnd,
						  pos=0,
						  dirIn=True, dirOut=False,
						  wireId=origWire.idNum,
						  text=None,
						  virtual=True)
		virtElemAnd.addConn(virtElemAndIn0)
		origWire.addConn(virtElemAndIn0)
		virtElemAndIn1 = FupCompiler_Conn(elem=virtElemAnd,
						  pos=1,
						  dirIn=True, dirOut=False,
						  wireId=leftWire.idNum,
						  text=None,
						  virtual=True)
		virtElemAnd.addConn(virtElemAndIn1)
		leftWire.addConn(virtElemAndIn1)
		virtElemAndOut = FupCompiler_Conn(elem=virtElemAnd,
						  pos=0,
						  dirIn=False, dirOut=True,
						  wireId=rightWire.idNum,
						  text=None,
						  virtual=True)
		virtElemAnd.addConn(virtElemAndOut)
		rightWire.addConn(virtElemAndOut)

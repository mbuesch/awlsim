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

from awlsim.fupcompiler.elembool import *


__all__ = [
	"FupCompiler_Helpers",
]


class FupCompiler_Helpers(object):
	"""FUP compiler helper routines.
	"""

	@staticmethod
	def genIntermediateBool(parentElem,
				elemsA, connNamesA,
				elemB, connNameB,
				boolElemClass):
		"""
		parentElem:	The parent FUP element for exception accounting, etc.
		elemsA:		A list of the left handed elements.
		connNamesA:	A list of the connection names of the left handed elements.
		elemB:		The right handed element.
		connNameB:	The connection name of the right handed element.
		boolElemClass:	The FUP element class used to create the virtual BOOL element.
		Returns:	None

		This function converts this:

		      left elem                           elemB
		     __________                         __________
		    | orig conn|-----(optional)--------|connNameB |
		    |(optional)|                       |          |
		    |__________|                       |__________|

		to this:

		       elemsA                             elemB
		     __________         virtual         __________
		    | connNameA|--+      BOOL       +--|connNameB |
		    |          |  |     _______     |  |          |
		    |__________|  +----|   &   |----+  |__________|
		     __________        |  >=1  |
		    | connNameA|-------|   x   |
		    |          |       |       |
		    |__________|  +----|       |
		     __________   |    |       |
		    | connNameA|--+    |       |
		    |          |       |       |
		    |__________|  +----|_______|
		                  |
		                  |
		      left elem   |
		     __________   |
		    | orig conn|--+
		    |(optional)|
		    |__________|
		"""

		if not elemsA or not elemB:
			return # We have nothing to do.

		assert(len(elemsA) == len(connNamesA))
		assert(issubclass(boolElemClass, FupCompiler_ElemBool))

		connB = elemB.getUniqueConnByText(connNameB, searchInputs=True)

		if len(elemsA) == 1 and not connB.isConnected:
			# Element B is not connected and we have only one element A.
			# This is a special case.
			# We don't need a virtual BOOL. We can just connect B to A.
			elemA = elemsA[0]
			connA = elemA.getUniqueConnByText(connNamesA[0], searchOutputs=True)
			connB.connectTo(connA)
			return

		# If element B is already connected to a wire, keep that wire
		# for later connection to the virtual BOOL.
		if connB.isConnected:
			origWireB = connB.wire
			origWireB.removeConn(connB)
		else:
			origWireB = None

		# Create a wire that connects the virtual BOOL's output
		# to the connB input.
		wireB = parentElem.grid.newWire(virtual=True)
		wireB.addConn(connB)

		# Create a virtual BOOL element to connect the elements.
		virtElemBool = boolElemClass(grid=parentElem.grid,
					     x=parentElem.x, y=parentElem.y,
					     content=None, virtual=True)

		# Add an output connection to the virtual BOOL
		# and connect it to wireB.
		virtElemOut = FupCompiler_Conn(elem=virtElemBool,
					       pos=0,
					       dirIn=False, dirOut=True,
					       wireId=wireB.idNum,
					       text=None,
					       virtual=True)
		virtElemBool.addConn(virtElemOut)
		wireB.addConn(virtElemOut)

		# Connect all output connections of the A elements to the
		# virtual BOOL.
		connPos = -1
		for connPos, elemA in enumerate(elemsA):
			connA = elemA.getUniqueConnByText(connNamesA[connPos],
							  searchOutputs=True)

			# Get A's wire, or create a new wire, if A is not connected.
			if connA.isConnected:
				wireA = connA.wire
			else:
				wireA = parentElem.grid.newWire(virtual=True)
				wireA.addConn(connA)

			# Create an input connection to the virtual BOOL
			# and connect A's wire to it.
			virtElemIn = FupCompiler_Conn(elem=virtElemBool,
						      pos=connPos,
						      dirIn=True, dirOut=False,
						      wireId=wireA.idNum,
						      text=None,
						      virtual=True)
			virtElemBool.addConn(virtElemIn)
			wireA.addConn(virtElemIn)

		# Connect the element that was originally connected to element B
		# to a virtual BOOL input.
		if origWireB:
			virtElemIn = FupCompiler_Conn(elem=virtElemBool,
						      pos=connPos + 1,
						      dirIn=True, dirOut=False,
						      wireId=origWireB.idNum,
						      text=None,
						      virtual=True)
			virtElemBool.addConn(virtElemIn)
			origWireB.addConn(virtElemIn)

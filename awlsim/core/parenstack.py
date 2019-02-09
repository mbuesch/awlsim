# -*- coding: utf-8 -*-
#
# AWL simulator - Parenthesis stack
#
# Copyright 2012-2018 Michael Buesch <m@bues.ch>
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

from awlsim.common.cpuspecs import * #+cimport
from awlsim.common.cpuconfig import *
from awlsim.common.exceptions import *
from awlsim.common.util import *

from awlsim.core.cpu import * #+cimport
from awlsim.core.statusword import * #+cimport

#from cpython.mem cimport PyMem_Malloc, PyMem_Free #@cy


class ParenStackElem(object):				#@nocy
	"Parenthesis stack (Klammerstack) element."	#@nocy
	__slots__ = (					#@nocy
		"insnType",				#@nocy
		"NER",					#@nocy
		"VKE",					#@nocy
		"OR",					#@nocy
	)						#@nocy

class ParenStack(object): #+cdef
	"""Parenthesis stack (Klammerstack).
	"""

	__slots__ = (
		"cpu",
		"maxNrElements",
		"nrElements",
		"elements",
	)

	def push(self, insnType, statusWord): #@nocy
#@cy	cdef push(self, uint8_t insnType, S7StatusWord statusWord):
		"""Push a new element onto the parenthesis stack.
		"""
#@cy		cdef ParenStackElem *pse

		if self.nrElements >= self.maxNrElements:
			raise AwlSimError("Parenthesis stack overflow")

		pse = ParenStackElem() #@nocy
#@cy		pse = &(self.elements[self.nrElements])

		pse.insnType = insnType
		pse.NER = statusWord.NER
		pse.VKE = statusWord.VKE
		pse.OR = statusWord.OR

		# Append the element to the stack.
		self.nrElements += 1
		self.elements.append(pse) #@nocy

	def pop(self): #@nocy
#@cy	cdef ParenStackElem pop(self):
		"""Pop the newest element off the parenthesis stack.
		"""
		if self.nrElements <= 0:
			raise AwlSimError("Parenthesis stack underflow")

		# Remove the element from the stack.
		self.nrElements -= 1

		return self.elements.pop() #@nocy
#@cy		return self.elements[self.nrElements]

	def __str__(self):
		mnemonics = self.cpu.getMnemonics()
		type2name = {
			S7CPUConfig.MNEMONICS_EN : AwlInsn.type2name_english,
			S7CPUConfig.MNEMONICS_DE : AwlInsn.type2name_german,
		}[mnemonics]
		return ", ".join(
			'(insn="%s" VKE=%s OR=%d)' % (
			type2name[self.elements[i].insnType],
			self.elements[i].VKE,
			self.elements[i].OR,
			) for i in range(self.nrElements)
		)

#@cy	def __dealloc__(self):
#@cy		PyMem_Free(self.elements)
#@cy		self.elements = NULL


def make_ParenStack(cpu): #@nocy
#cdef ParenStack make_ParenStack(S7CPU cpu): #@cy
#@cy	cdef ParenStack ps
	ps = ParenStack()
	ps.cpu = cpu
	ps.maxNrElements = cpu.specs.parenStackSize
	ps.nrElements = 0
	ps.elements = [] #@nocy
#@cy	ps.elements = <ParenStackElem *>PyMem_Malloc(ps.maxNrElements * sizeof(ParenStackElem))
#@cy	if ps.elements == NULL:
#@cy		raise AwlSimError("make_ParenStack: Out of memory")
	return ps

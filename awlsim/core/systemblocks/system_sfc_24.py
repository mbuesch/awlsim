# -*- coding: utf-8 -*-
#
# AWL simulator - SFCs
#
# Copyright 2016-2018 Michael Buesch <m@bues.ch>
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

from awlsim.common.exceptions import *
from awlsim.common.util import *

from awlsim.core.systemblocks.systemblocks import * #+cimport
from awlsim.core.blockinterface import *
from awlsim.core.datablocks import * #+cimport
from awlsim.core.memory import * #+cimport


class SFC24(SFC): #+cdef
	name = (24, "TEST_DB", "test data block")

	interfaceFields = {
		BlockInterfaceField.FTYPE_IN	: (
			BlockInterfaceField(name="DB_NUMBER", dataType="WORD"),
		),
		BlockInterfaceField.FTYPE_OUT	: (
			BlockInterfaceField(name="RET_VAL", dataType="INT"),
			BlockInterfaceField(name="DB_LENGTH", dataType="WORD"),
			BlockInterfaceField(name="WRITE_PROT", dataType="BOOL"),
		),
	}

	def run(self): #+cpdef
#@cy		cdef S7StatusWord s
#@cy		cdef uint32_t dbNr

		s = self.cpu.statusWord

		dbNr = AwlMemoryObject_asScalar(
			self.fetchInterfaceFieldByName("DB_NUMBER"))

		if dbNr == 0:
			# 0x80A1: DB_NUMBER is 0 or > max permissible.
			self.storeInterfaceFieldByName("RET_VAL",
				make_AwlMemoryObject_fromScalar(0x80A1, 16))
			self.storeInterfaceFieldByName("DB_LENGTH",
				make_AwlMemoryObject_fromScalar(0, 16))
			self.storeInterfaceFieldByName("WRITE_PROT",
				make_AwlMemoryObject_fromScalar(0, 1))
			s.BIE = 0
			return

		db = self.cpu.getDB(dbNr)
		if db is None or db.index != dbNr:
			# 0x80B1: DB with the specified number does not exist.
			self.storeInterfaceFieldByName("RET_VAL",
				make_AwlMemoryObject_fromScalar(0x80B1, 16))
			self.storeInterfaceFieldByName("DB_LENGTH",
				make_AwlMemoryObject_fromScalar(0, 16))
			self.storeInterfaceFieldByName("WRITE_PROT",
				make_AwlMemoryObject_fromScalar(0, 1))
			s.BIE = 0
			return

		dbLen = db.struct.getSize() & 0xFFFF
		writeProt = 0 if (db.permissions & db.PERM_WRITE) else 1

		self.storeInterfaceFieldByName("RET_VAL",
			make_AwlMemoryObject_fromScalar(0, 16))
		self.storeInterfaceFieldByName("DB_LENGTH",
			make_AwlMemoryObject_fromScalar(dbLen, 16))
		self.storeInterfaceFieldByName("WRITE_PROT",
			make_AwlMemoryObject_fromScalar(writeProt, 1))
		s.BIE = 1

# -*- coding: utf-8 -*-
#
# AWL simulator - SFCs
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

from awlsim.common.wordpacker import *
from awlsim.common.datatypehelpers import * #+cimport
from awlsim.common.exceptions import *

from awlsim.core.systemblocks.systemblocks import * #+cimport
from awlsim.core.systemblocks.error_codes import *
from awlsim.core.cpu import * #+cimport
from awlsim.core.offset import * #+cimport
from awlsim.core.operatortypes import * #+cimport
from awlsim.core.operators import * #+cimport
from awlsim.core.memory import * #+cimport
from awlsim.core.blockinterface import *
from awlsim.core.util import *


class SFC21(SFC): #+cdef
	name = (21, "FILL", "fill memory area")

	interfaceFields = {
		BlockInterfaceField.FTYPE_IN	: (
			BlockInterfaceField(name="BVAL", dataType="ANY"),
		),
		BlockInterfaceField.FTYPE_OUT	: (
			BlockInterfaceField(name="RET_VAL", dataType="INT"),
			BlockInterfaceField(name="BLK", dataType="ANY"),
		),
	}

	def __init__(self, *args, **kwargs):
		SFC.__init__(self, *args, **kwargs)

		from awlsim.core.datatypes import AwlDataType

		self.__typeWidths = AwlDataType.typeWidths

	def run(self): #+cpdef
#@cy		cdef S7CPU cpu
#@cy		cdef S7StatusWord s

		cpu = self.cpu
		s = cpu.statusWord

		# Get the inputs (BLK actually is declared as output though)
		BVAL = self.fetchInterfaceFieldByName("BVAL")
		BLK = self.fetchInterfaceFieldByName("BLK")

		# Check ANY pointer S7 magic.
		if BVAL[0] != ANYPointerConst.MAGIC:
			s.BIE = 0
			self.storeInterfaceFieldByName("RET_VAL",
				SystemErrCode.make(SystemErrCode.E_RAREA, 1))
			return
		if BLK[0] != ANYPointerConst.MAGIC:
			s.BIE = 0
			self.storeInterfaceFieldByName("RET_VAL",
				SystemErrCode.make(SystemErrCode.E_WAREA, 3))
			return

		# Get the repetition counts from the ANY pointers
		BVAL_repCount = WordPacker.fromBytes(BVAL, 16, 2)
		BLK_repCount = WordPacker.fromBytes(BLK, 16, 2)

		# Get the data types from the ANY pointers.
		try:
			BVAL_typeId = ANYPointerConst.typeCode2typeId[BVAL[1]]
			BVAL_typeWidth = self.__typeWidths[BVAL_typeId]
			if BVAL_typeWidth <= 0:
				raise KeyError
		except KeyError:
			self.storeInterfaceFieldByName("RET_VAL",
				SystemErrCode.make(SystemErrCode.E_RAREA, 1))
			s.BIE = 0
			return
		try:
			BLK_typeId = ANYPointerConst.typeCode2typeId[BLK[1]]
			BLK_typeWidth = self.__typeWidths[BLK_typeId]
			if BLK_typeWidth <= 0:
				raise KeyError
		except KeyError:
			self.storeInterfaceFieldByName("RET_VAL",
				SystemErrCode.make(SystemErrCode.E_WAREA, 3))
			s.BIE = 0
			return

		# Calculate the area sizes (in bytes)
		BVAL_len = BVAL_typeWidth * BVAL_repCount
		if BVAL_len % 8:
			self.storeInterfaceFieldByName("RET_VAL",
				SystemErrCode.make(SystemErrCode.E_RLEN, 1))
			s.BIE = 0
			return
		BVAL_len //= 8
		BLK_len = BLK_typeWidth * BLK_repCount
		if BLK_len % 8:
			self.storeInterfaceFieldByName("RET_VAL",
				SystemErrCode.make(SystemErrCode.E_WLEN, 3))
			s.BIE = 0
			return
		BLK_len //= 8

		# Get the pointer dwords from the ANY pointers
		BVAL_ptr = Pointer(WordPacker.fromBytes(BVAL, 32, 6))
		BVAL_ptrArea = BVAL_ptr.getArea()
		BLK_ptr = Pointer(WordPacker.fromBytes(BLK, 32, 6))
		BLK_ptrArea = BLK_ptr.getArea()

		if BVAL_ptrArea in {PointerConst.AREA_DB, PointerConst.AREA_DI}:
			# Get the DB number from BVAL ANY pointer
			BVAL_dbNr = WordPacker.fromBytes(BVAL, 16, 4)
			# Open the DB
			BVAL_ptr.setArea(PointerConst.AREA_DB)
			BVAL_ptrArea = BVAL_ptr.getArea()
			try:
				db = cpu.dbs[BVAL_dbNr]
				if (db.permissions & db.PERM_READ) == 0:
					raise KeyError
				cpu.openDB(BVAL_dbNr, False)
			except (AwlSimError, KeyError) as e:
				self.storeInterfaceFieldByName("RET_VAL",
					SystemErrCode.make(SystemErrCode.E_DBNOTEXIST, 1))
				s.BIE = 0
				return
		if BLK_ptrArea in {PointerConst.AREA_DB, PointerConst.AREA_DI}:
			# Get the DB number from BLK ANY pointer
			BLK_dbNr = WordPacker.fromBytes(BLK, 16, 4)
			# Open the DB (as DI)
			BLK_ptr.setArea(PointerConst.AREA_DI)
			BLK_ptrArea = BLK_ptr.getArea()
			try:
				db = cpu.dbs[BLK_dbNr]
				if (db.permissions & db.PERM_WRITE) == 0:
					raise KeyError
				cpu.openDB(BLK_dbNr, True)
			except (AwlSimError, KeyError) as e:
				self.storeInterfaceFieldByName("RET_VAL",
					SystemErrCode.make(SystemErrCode.E_DBNOTEXIST, 3))
				s.BIE = 0
				return

		# Copy the data.
		BVAL_begin = make_AwlOffset_fromPointerValue(BVAL_ptr.toPointerValue())
		BVAL_offset = BVAL_begin.dup()
		BVAL_end = BVAL_offset + make_AwlOffset(BVAL_len, 0)
		if BVAL_offset.bitOffset:
			# BVAL data is not byte aligned.
			self.storeInterfaceFieldByName("RET_VAL",
				SystemErrCode.make(SystemErrCode.E_RALIGN, 1))
			s.BIE = 0
			return
		BVAL_fetchOper = make_AwlOperator(
			AwlIndirectOpConst.area2optype_fetch[BVAL_ptrArea << PointerConst.AREA_SHIFT],
			8, BVAL_offset, None)
		BLK_offset = make_AwlOffset_fromPointerValue(BLK_ptr.toPointerValue())
		BLK_end = BLK_offset + make_AwlOffset(BLK_len, 0)
		if BLK_offset.bitOffset:
			# BLK data is not byte aligned.
			self.storeInterfaceFieldByName("RET_VAL",
				SystemErrCode.make(SystemErrCode.E_WALIGN, 3))
			s.BIE = 0
			return
		BLK_storeOper = make_AwlOperator(
			AwlIndirectOpConst.area2optype_fetch[BLK_ptrArea << PointerConst.AREA_SHIFT],
			8, BLK_offset, None)
		while BLK_offset.byteOffset < BLK_end.byteOffset:
			if BLK_offset.byteOffset + 4 <= BLK_end.byteOffset and\
			   BVAL_offset.byteOffset + 4 <= BVAL_end.byteOffset:
				# Copy one DWORD
				BVAL_fetchOper.width = BLK_storeOper.width = 32
			elif BLK_offset.byteOffset + 2 <= BLK_end.byteOffset and\
			     BVAL_offset.byteOffset + 2 <= BVAL_end.byteOffset:
				# Copy one WORD
				BVAL_fetchOper.width = BLK_storeOper.width = 16
			else:
				# Copy one BYTE
				BVAL_fetchOper.width = BLK_storeOper.width = 8
			# Fetch the data from BVAL
			try:
				data = cpu.fetch(BVAL_fetchOper,
						 AwlOperatorWidths.WIDTH_MASK_ALL)
			except AwlSimError:
				self.storeInterfaceFieldByName("RET_VAL",
					SystemErrCode.make(SystemErrCode.E_RAREA, 1))
				s.BIE = 0
				return
			# Store the data to BLK
			try:
				cpu.store(BLK_storeOper, data,
					  AwlOperatorWidths.WIDTH_MASK_ALL)
			except AwlSimError:
				self.storeInterfaceFieldByName("RET_VAL",
					SystemErrCode.make(SystemErrCode.E_WAREA, 3))
				s.BIE = 0
				return
			BVAL_offset.byteOffset += BVAL_fetchOper.width // 8
			if BVAL_offset.byteOffset >= BVAL_end.byteOffset:
				BVAL_offset.byteOffset = BVAL_begin.byteOffset
			BLK_offset.byteOffset += BLK_storeOper.width // 8

		# Everything is fine.
		self.storeInterfaceFieldByName("RET_VAL", 0)
		s.BIE = 1

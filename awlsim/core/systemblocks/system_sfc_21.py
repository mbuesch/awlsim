# -*- coding: utf-8 -*-
#
# AWL simulator - SFCs
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

from awlsim.core.systemblocks.systemblocks import *
from awlsim.core.util import *


class SFC21(SFC):
	name = (21, "FILL", "fill memory area")

	interfaceFields = {
		BlockInterfaceField.FTYPE_IN	: (
			BlockInterfaceField(name = "BVAL",
					    dataType = AwlDataType.makeByName("ANY")),
		),
		BlockInterfaceField.FTYPE_OUT	: (
			BlockInterfaceField(name = "RET_VAL",
					    dataType = AwlDataType.makeByName("INT")),
			BlockInterfaceField(name = "BLK",
					    dataType = AwlDataType.makeByName("ANY")),
		),
	}

	def run(self):
		cpu = self.cpu
		s = cpu.statusWord

		# Get the inputs (BLK actually is declared as output though)
		BVAL = self.fetchInterfaceFieldByName("BVAL")
		BLK = self.fetchInterfaceFieldByName("BLK")

		# Check ANY pointer S7 magic.
		if BVAL[0] != ANYPointer.MAGIC:
			s.BIE = 0
			self.storeInterfaceFieldByName("RET_VAL",
				SystemErrCode.make(SystemErrCode.E_RAREA, 1))
			return
		if BLK[0] != ANYPointer.MAGIC:
			s.BIE = 0
			self.storeInterfaceFieldByName("RET_VAL",
				SystemErrCode.make(SystemErrCode.E_WAREA, 3))
			return

		# Get the repetition counts from the ANY pointers
		BVAL_repCount = WordPacker.fromBytes(BVAL, 16, 2)
		BLK_repCount = WordPacker.fromBytes(BLK, 16, 2)

		# Get the data types from the ANY pointers.
		try:
			BVAL_typeId = ANYPointer.typeCode2typeId[BVAL[1]]
			BVAL_typeWidth = AwlDataType.typeWidths[BVAL_typeId]
			if BVAL_typeWidth <= 0:
				raise KeyError
		except KeyError:
			self.storeInterfaceFieldByName("RET_VAL",
				SystemErrCode.make(SystemErrCode.E_RAREA, 1))
			s.BIE = 0
			return
		try:
			BLK_typeId = ANYPointer.typeCode2typeId[BLK[1]]
			BLK_typeWidth = AwlDataType.typeWidths[BLK_typeId]
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

		if BVAL_ptrArea in {BVAL_ptr.AREA_DB, BVAL_ptr.AREA_DI}:
			# Get the DB number from BVAL ANY pointer
			BVAL_dbNr = WordPacker.fromBytes(BVAL, 16, 4)
			# Open the DB
			BVAL_ptr.setArea(BVAL_ptr.AREA_DB)
			BVAL_ptrArea = BVAL_ptr.getArea()
			try:
				if (cpu.dbs[BVAL_dbNr].permissions & DB.PERM_READ) == 0:
					raise KeyError
				cpu.run_AUF(AwlOperator(
					AwlOperator.BLKREF_DB, 16,
					AwlOffset(BVAL_dbNr)))
			except (AwlSimError, KeyError) as e:
				self.storeInterfaceFieldByName("RET_VAL",
					SystemErrCode.make(SystemErrCode.E_DBNOTEXIST, 1))
				s.BIE = 0
				return
		if BLK_ptrArea in {BLK_ptr.AREA_DB, BLK_ptr.AREA_DI}:
			# Get the DB number from BLK ANY pointer
			BLK_dbNr = WordPacker.fromBytes(BLK, 16, 4)
			# Open the DB (as DI)
			BLK_ptr.setArea(BLK_ptr.AREA_DI)
			BLK_ptrArea = BLK_ptr.getArea()
			try:
				cpu = self.cpu
				if (cpu.dbs[BLK_dbNr].permissions & DB.PERM_WRITE) == 0:
					raise KeyError
				cpu.run_AUF(AwlOperator(
					AwlOperator.BLKREF_DI, 16,
					AwlOffset(BLK_dbNr)))
			except (AwlSimError, KeyError) as e:
				self.storeInterfaceFieldByName("RET_VAL",
					SystemErrCode.make(SystemErrCode.E_DBNOTEXIST, 3))
				s.BIE = 0
				return

		# Copy the data.
		BVAL_begin = AwlOffset.fromPointerValue(BVAL_ptr.toPointerValue())
		BVAL_offset = BVAL_begin.dup()
		BVAL_end = BVAL_offset + AwlOffset(BVAL_len)
		if BVAL_offset.bitOffset:
			# BVAL data is not byte aligned.
			self.storeInterfaceFieldByName("RET_VAL",
				SystemErrCode.make(SystemErrCode.E_RALIGN, 1))
			s.BIE = 0
			return
		BVAL_fetchOper = AwlOperator(
			AwlIndirectOp.area2optype_fetch[BVAL_ptrArea << Pointer.AREA_SHIFT],
			8, BVAL_offset)
		BLK_offset = AwlOffset.fromPointerValue(BLK_ptr.toPointerValue())
		BLK_end = BLK_offset + AwlOffset(BLK_len)
		if BLK_offset.bitOffset:
			# BLK data is not byte aligned.
			self.storeInterfaceFieldByName("RET_VAL",
				SystemErrCode.make(SystemErrCode.E_WALIGN, 3))
			s.BIE = 0
			return
		BLK_storeOper = AwlOperator(
			AwlIndirectOp.area2optype_fetch[BLK_ptrArea << Pointer.AREA_SHIFT],
			8, BLK_offset)
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
				data = cpu.fetch(BVAL_fetchOper)
			except AwlSimError:
				self.storeInterfaceFieldByName("RET_VAL",
					SystemErrCode.make(SystemErrCode.E_RAREA, 1))
				s.BIE = 0
				return
			# Store the data to BLK
			try:
				cpu.store(BLK_storeOper, data)
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

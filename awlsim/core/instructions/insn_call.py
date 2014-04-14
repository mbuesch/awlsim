# -*- coding: utf-8 -*-
#
# AWL simulator - instructions
#
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
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
from awlsim.core.compat import *

from awlsim.core.instructions.main import *


class AwlInsn_AbstractCall(AwlInsn):
	def staticSanityChecks(self):
		if len(self.ops) == 1:
			# "CALL FC/SFC" or "UC/CC FC/SFC/FB/SFB"
			blockOper = self.ops[0]

			if blockOper.type == AwlOperator.BLKREF_FC:
				try:
					codeBlock = self.cpu.fcs[blockOper.value.byteOffset]
				except KeyError as e:
					raise AwlSimError("Called FC not found",
						rawInsn = self.rawInsn)
			elif blockOper.type == AwlOperator.BLKREF_SFC:
				try:
					codeBlock = self.cpu.sfcs[blockOper.value.byteOffset]
				except KeyError as e:
					raise AwlSimError("SFC %d not implemented, yet" %\
						blockOper.value.byteOffset,
						rawInsn = self.rawInsn)
			elif blockOper.type == AwlOperator.BLKREF_FB:
				if self.type == AwlInsn.TYPE_CALL:
					raise AwlSimError("Missing DB in function "
						"block call",
						rawInsn = self.rawInsn)
				try:
					codeBlock = self.cpu.fbs[blockOper.value.byteOffset]
				except KeyError as e:
					raise AwlSimError("Called FB not found",
						rawInsn = self.rawInsn)
			elif blockOper.type == AwlOperator.BLKREF_SFB:
				if self.type == AwlInsn.TYPE_CALL:
					raise AwlSimError("Missing DB in system function "
						"block call",
						rawInsn = self.rawInsn)
				try:
					codeBlock = self.cpu.sfbs[blockOper.value.byteOffset]
				except KeyError as e:
					raise AwlSimError("SFB %d not implemented, yet" %\
						blockOper.value.byteOffset,
						rawInsn = self.rawInsn)
			elif blockOper.type == AwlOperator.INDIRECT:
				# Indirect call. (like UC FC[MW 0])
				codeBlock = None
			else:
				raise AwlSimError("Invalid CALL operand",
					rawInsn = self.rawInsn)

			if self.type == AwlInsn.TYPE_CALL and\
			   codeBlock and\
			   codeBlock.interface.interfaceFieldCount != len(self.params):
				raise AwlSimError("Call interface mismatch. "
					"Passed %d parameters, but expected %d.\n"
					"====  The block interface is:\n%s\n====" %\
					(len(self.params), codeBlock.interface.interfaceFieldCount,
					 str(codeBlock.interface)),
					rawInsn = self.rawInsn)
		elif len(self.ops) == 2:
			# "CALL FB/SFB"
			blockOper = self.ops[0]
			dbOper = self.ops[1]

			if dbOper.type != AwlOperator.BLKREF_DB:
				raise AwlSimError("Second CALL operand is "
					"not a DB operand.",
					rawInsn = self.rawInsn)
			try:
				db = self.cpu.dbs[dbOper.value.byteOffset]
			except KeyError as e:
				raise AwlSimError("DB used in FB call not found",
					rawInsn = self.rawInsn)
			if not db.isInstanceDB():
				raise AwlSimError("DB %d is not an instance DB" %\
					dbOper.value.byteOffset,
					rawInsn = self.rawInsn)

			if blockOper.type == AwlOperator.BLKREF_FB:
				try:
					fb = self.cpu.fbs[blockOper.value.byteOffset]
				except KeyError as e:
					raise AwlSimError("Called FB not found",
						rawInsn = self.rawInsn)
				# TODO check if this is an FB-DB
				pass#TODO
			elif blockOper.type == AwlOperator.BLKREF_SFB:
				try:
					fb = self.cpu.sfbs[blockOper.value.byteOffset]
				except KeyError as e:
					raise AwlSimError("SFB %d not implemented, yet" %\
						blockOper.value.byteOffset,
						rawInsn = self.rawInsn)
				# TODO check if this is an SFB-DB
				pass#TODO
			elif blockOper.type == AwlOperator.BLKREF_FC or\
			     blockOper.type == AwlOperator.BLKREF_SFC:
				raise AwlSimError("Calling function, but "
					"a DB was specified.",
					rawInsn = self.rawInsn)
			else:
				raise AwlSimError("Invalid CALL operand",
					rawInsn = self.rawInsn)

			if db.codeBlock.index != fb.index:
				raise AwlSimError("DB %d is not an instance DB for FB %d" %\
					(dbOper.value.byteOffset,
					 blockOper.value.byteOffset),
					rawInsn = self.rawInsn)
		else:
			assert(0)

class AwlInsn_CALL(AwlInsn_AbstractCall):
	def __init__(self, cpu, rawInsn):
		AwlInsn_AbstractCall.__init__(self, cpu, AwlInsn.TYPE_CALL, rawInsn)
		self.assertOpCount((1,2))

		if len(self.ops) == 1:
			self.run = self.__run_CALL_FC
		else:
			self.run = self.__run_CALL_FB

	def __run_CALL_FC(self):
		self.cpu.run_CALL(self.ops[0], None, self.params, False)
		s = self.cpu.statusWord
		s.OS, s.OR, s.STA, s.NER = 0, 0, 1, 0

	def __run_CALL_FB(self):
		self.cpu.run_CALL(self.ops[0], self.ops[1], self.params, False)
		s = self.cpu.statusWord
		s.OS, s.OR, s.STA, s.NER = 0, 0, 1, 0

class AwlInsn_CC(AwlInsn_AbstractCall):
	def __init__(self, cpu, rawInsn):
		AwlInsn_AbstractCall.__init__(self, cpu, AwlInsn.TYPE_CC, rawInsn)
		self.assertOpCount(1)

	def run(self):
		s = self.cpu.statusWord
		if s.VKE:
			self.cpu.run_CALL(self.ops[0], None, (), True)
		s.OS, s.OR, s.STA, s.VKE, s.NER = 0, 0, 1, 1, 0

class AwlInsn_UC(AwlInsn_AbstractCall):
	def __init__(self, cpu, rawInsn):
		AwlInsn_AbstractCall.__init__(self, cpu, AwlInsn.TYPE_UC, rawInsn)
		self.assertOpCount(1)

	def run(self):
		self.cpu.run_CALL(self.ops[0], None, (), True)
		s = self.cpu.statusWord
		s.OS, s.OR, s.STA, s.NER = 0, 0, 1, 0

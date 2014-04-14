# -*- coding: utf-8 -*-
#
# AWL simulator - Exceptions
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

from awlsim.core.enumeration import *


class AwlSimError(Exception):
	def __init__(self, message, cpu=None,
		     rawInsn=None, insn=None, lineNr=None):
		Exception.__init__(self, message)
		self.cpu = cpu
		self.rawInsn = rawInsn
		self.insn = insn
		self.lineNr = lineNr

	def setCpu(self, cpu):
		self.cpu = cpu

	def getCpu(self):
		return self.cpu

	def setRawInsn(self, rawInsn):
		self.rawInsn = rawInsn

	def getRawInsn(self):
		return self.rawInsn

	def setInsn(self, insn):
		self.insn = insn

	def getInsn(self):
		return self.insn

	def setLineNr(self, lineNr):
		self.lineNr = lineNr

	# Try to get the AWL-code line number where the
	# exception occurred. Returns None on failure.
	def getLineNr(self):
		if self.lineNr is not None:
			return self.lineNr
		if self.rawInsn:
			return self.rawInsn.getLineNr()
		if self.insn:
			return self.insn.getLineNr()
		if self.cpu:
			curInsn = self.cpu.getCurrentInsn()
			if curInsn:
				return curInsn.getLineNr()
		return None

	def getLineNrStr(self, errorStr="<unknown>"):
		lineNr = self.getLineNr()
		if lineNr is not None:
			return "%d" % lineNr
		return errorStr

	def getFailingInsnStr(self, errorStr=""):
		if self.rawInsn:
			return str(self.rawInsn)
		if self.insn:
			return str(self.insn)
		if self.cpu:
			curInsn = self.cpu.getCurrentInsn()
			if curInsn:
				return str(curInsn)
		return errorStr

	def doGetReport(self, title):
		ret = [ "-- %s --\n" % title ]
		ret.append("ERROR at line %s:\n" % self.getLineNrStr())
		ret.append("  \n%s\n" % str(self))
		cpu = self.getCpu()
		if cpu:
			ret.append("\n%s\n" % str(cpu))
		return "".join(ret)

	def getReport(self):
		return self.doGetReport("AWL simulator error")

class AwlParserError(AwlSimError):
	def __init__(self, message, lineNr=None):
		AwlSimError.__init__(self,
				     message = message,
				     lineNr = lineNr)

	def getReport(self):
		return self.doGetReport("AWL parser error")

class AwlSimErrorText(AwlSimError):
	def __init__(self, errorText):
		AwlSimError.__init__(self, message = errorText)

	def getReport(self):
		return str(self)

class MaintenanceRequest(Exception):
	EnumGen.start
	# Soft-reboot request, handled by the simulator core.
	# On soft-reboot, the upstart-OBs are executed.
	# Memory is not cleared.
	TYPE_SOFTREBOOT		= EnumGen.item
	# Regular-shutdown request, handled by toplevel simulator.
	# This exception is handed up to the toplevel loop.
	TYPE_SHUTDOWN		= EnumGen.item
	EnumGen.end

	def __init__(self, requestType, message=""):
		Exception.__init__(self, message)
		self.requestType = requestType

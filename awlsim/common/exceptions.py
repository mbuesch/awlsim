# -*- coding: utf-8 -*-
#
# AWL simulator - Exceptions
#
# Copyright 2012-2016 Michael Buesch <m@bues.ch>
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

from awlsim.common.enumeration import *


__all__ = [
	"AwlSimError",
	"AwlParserError",
	"AwlSimBug",
	"FrozenAwlSimError",
	"MaintenanceRequest",
	"ExitCodes",
	"suppressAllExc",
]


class AwlSimError(Exception):
	"""Main AwlSim exception.
	"""

	EXC_TYPE = "AwlSimError"

	def __init__(self, message, cpu=None,
		     rawInsn=None, insn=None, lineNr=None,
		     sourceId=None, sourceName=None):
		super(AwlSimError, self).__init__(self, message)
		self.message = message
		self.cpu = cpu
		self.rawInsn = rawInsn
		self.failingInsnStr = None
		self.insn = insn
		self.lineNr = lineNr
		self.sourceId = sourceId
		self.sourceName = sourceName
		self.seenByUser = False

	def setCpu(self, cpu):
		self.cpu = cpu

	def getCpu(self):
		return self.cpu

	def setRawInsn(self, rawInsn):
		self.rawInsn = rawInsn

	def getRawInsn(self):
		if self.rawInsn:
			return self.rawInsn
		insn = self.getInsn()
		if insn:
			rawInsn = insn.getRawInsn()
			if rawInsn:
				return rawInsn
		return None

	def setInsn(self, insn):
		self.insn = insn

	def getInsn(self):
		if self.insn:
			return self.insn
		cpu = self.getCpu()
		if cpu:
			curInsn = cpu.getCurrentInsn()
			if curInsn:
				return curInsn
		return None

	def setSourceId(self, sourceId):
		self.sourceId = sourceId

	def getSourceId(self):
		if self.sourceId is not None:
			return self.sourceId
		rawInsn = self.getRawInsn()
		if rawInsn:
			sourceId = rawInsn.getSourceId()
			if sourceId:
				return sourceId
		insn = self.getInsn()
		if insn:
			sourceId = insn.getSourceId()
			if sourceId:
				return sourceId
		cpu = self.getCpu()
		if cpu:
			curInsn = cpu.getCurrentInsn()
			if curInsn:
				sourceId = curInsn.getSourceId()
				if sourceId:
					return sourceId
		return None

	def setSourceName(self, sourceName):
		self.sourceName = sourceName

	def getSourceName(self):
		return self.sourceName

	def setLineNr(self, lineNr):
		self.lineNr = lineNr

	# Try to get the AWL-code line number where the
	# exception occurred. Returns None on failure.
	def getLineNr(self):
		if self.lineNr is not None:
			return self.lineNr
		rawInsn = self.getRawInsn()
		if rawInsn:
			lineNr = rawInsn.getLineNr()
			if lineNr is not None:
				return lineNr
		insn = self.getInsn()
		if insn:
			lineNr = insn.getLineNr()
			if lineNr is not None:
				return lineNr
		cpu = self.getCpu()
		if cpu:
			curInsn = cpu.getCurrentInsn()
			if curInsn:
				lineNr = curInsn.getLineNr()
				if lineNr is not None:
					return lineNr
		return None

	def getLineNrStr(self, errorStr="<unknown>"):
		lineNr = self.getLineNr()
		if lineNr is not None:
			return "%d" % lineNr
		return errorStr

	def setFailingInsnStr(self, string):
		self.failingInsnStr = string

	def getFailingInsnStr(self, errorStr=""):
		if self.failingInsnStr is not None:
			return self.failingInsnStr
		rawInsn = self.getRawInsn()
		if rawInsn:
			return str(rawInsn)
		insn = self.getInsn()
		if insn:
			return str(insn)
		cpu = self.getCpu()
		if cpu:
			curInsn = cpu.getCurrentInsn()
			if curInsn:
				return str(curInsn)
		return errorStr

	def doGetReport(self, title, verbose=True):
		sourceName = self.getSourceName()
		if sourceName:
			sourceName = "source '%s' " % sourceName
		else:
			sourceName = ""
		ret = [ "%s:\n\n" % title ]
		fileStr = ""
		if sourceName:
			fileStr = " in %s" % sourceName
		lineStr = ""
		if self.getLineNr() is not None:
			lineStr = " at line %d" % self.getLineNr()
		if fileStr or lineStr:
			ret.append("Error%s%s:\n" % (fileStr, lineStr))
		insnStr = self.getFailingInsnStr()
		if insnStr:
			ret.append("  %s\n" % insnStr)
		ret.append("\n  %s\n" % self.message)
		if verbose:
			cpu = self.getCpu()
			if cpu:
				ret.append("\n%s\n" % str(cpu))
		return "".join(ret)

	def getReport(self, verbose=True):
		return self.doGetReport("Awlsim error", verbose)

	def getSeenByUser(self):
		return self.seenByUser

	def setSeenByUser(self, seen=True):
		self.seenByUser = seen

	def __repr__(self):
		return self.getReport()

	__str__ = __repr__

class AwlParserError(AwlSimError):
	"""Parser specific exception.
	"""

	EXC_TYPE = "AwlParserError"

	def __init__(self, message, lineNr=None):
		AwlSimError.__init__(self,
				     message = message,
				     lineNr = lineNr)

	def getReport(self, verbose=True):
		return self.doGetReport("AWL parser error", verbose)

class AwlSimBug(AwlSimError):
	"""AwlSim bug exception.
	This will be raised in situations that represent an actual code bug.
	"""

	EXC_TYPE = "AwlSimBug"

	def __init__(self, message, *args, **kwargs):
		message = "AWLSIM BUG: %s\n"\
			"This bug should be reported to the awlsim developers." %\
			str(message)
		AwlSimError.__init__(self, message, *args, **kwargs)

class FrozenAwlSimError(AwlSimError):
	"""A frozen AwlSim exception.
	The report will be frozen and not be generated from scratch.
	"""

	EXC_TYPE = "FrozenAwlSimError"

	def __init__(self, excType, errorText, verboseErrorText=None):
		AwlSimError.__init__(self, message = errorText)
		self.EXC_TYPE = excType
		self.verboseErrorText = verboseErrorText or errorText

	def getReport(self, verbose=True):
		if verbose:
			return self.verboseErrorText
		return self.message

class MaintenanceRequest(Exception):
	EnumGen.start
	# Soft-reboot request, handled by the simulator core.
	# On soft-reboot, the upstart-OBs are executed.
	# Memory is not cleared.
	TYPE_SOFTREBOOT		= EnumGen.item
	# Regular-shutdown request, handled by toplevel simulator.
	# This exception is handed up to the toplevel loop.
	TYPE_SHUTDOWN		= EnumGen.item
	# CPU-STOP request, handled by toplevel simulator.
	# This exception is handed up to the toplevel loop.
	TYPE_STOP		= EnumGen.item
	# CPU-STOP due to runtime timeout.
	# This exception is handed up to the toplevel loop.
	TYPE_RTTIMEOUT		= EnumGen.item
	EnumGen.end

	def __init__(self, requestType, message=""):
		super(MaintenanceRequest, self).__init__(self, message)
		self.requestType = requestType
		self.message = message

	def __repr__(self):
		return self.message

class ExitCodes(object):
	"""Awlsim program exit codes."""

	EnumGen.start
	# Success.
	EXIT_OK			= EnumGen.itemAt(0)
	# Command line option error.
	EXIT_ERR_CMDLINE	= EnumGen.itemAt(10)
	# Python interpreter error.
	EXIT_ERR_INTERP		= EnumGen.itemAt(20)
	# AwlSimError.
	EXIT_ERR_SIM		= EnumGen.itemAt(30)
	# I/O error.
	EXIT_ERR_IO		= EnumGen.itemAt(40)
	# Other error.
	EXIT_ERR_OTHER		= EnumGen.itemAt(100)
	EnumGen.end

class __suppressAllExc(object):
	"""Context manager to suppress almost all exceptions.
	Only really fatal coding exceptions will be re-raised.
	The usage is similar to that of contextlib.suppress().
	"""

	import re as _re

	def __enter__(self):
		pass

	def __exit__(self, exctype, excinst, exctb):
		if exctype is None:
			return False # no exception
		if issubclass(exctype, (SyntaxError, NameError, AttributeError)):
			return False # raise fatal exception
		if issubclass(exctype, ValueError):
			re, text = self._re, str(excinst)
			if re.match(r'.*takes exactly \d+ argument \(\d+ given\).*', text) or\
			   re.match(r'.*missing \d+ required positional argument.*', text) or\
			   re.match(r'.*takes \d+ positional argument but \d+ were given.*', text):
				return False # raise fatal exception
		return True # suppress exception
suppressAllExc = __suppressAllExc()

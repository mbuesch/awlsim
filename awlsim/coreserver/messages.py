# -*- coding: utf-8 -*-
#
# AWL simulator - PLC core server messages
#
# Copyright 2013-2020 Michael Buesch <m@bues.ch>
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
from awlsim.common.project import *
from awlsim.common.hwmod import *
from awlsim.common.datatypehelpers import * #+cimport
from awlsim.common.blockinfo import *
from awlsim.common.net import *
from awlsim.common.sources import *
from awlsim.common.exceptions import *
from awlsim.common.monotonic import * #+cimport

from awlsim.coreserver.memarea import *

from awlsim.library.libselection import *

import struct
import socket
import errno


class TransferError(Exception):
	EnumGen.start
	REASON_UNKNOWN		= EnumGen.item
	REASON_BLOCKING		= EnumGen.item
	REASON_REMOTEDIED	= EnumGen.item
	EnumGen.end

	def __init__(self, text, parentException=None, reason=None):
		if not text and parentException:
			text = str(parentException)
		_errno = excErrno(parentException)
		if _errno == -1:
			_errno = errno.ECONNREFUSED
		if reason is None:
			if parentException:
				# Try to find out whether this was an exception due
				# to blocking IO (on a nonblocking socket).
				# This varies between Python versions, argh.
				if (isinstance(parentException, socket.timeout) or
				    isinstance(parentException, BlockingIOError) or
				    _errno == errno.EAGAIN or
				    _errno == errno.EWOULDBLOCK or
				    _errno == errno.EINTR):
					reason = self.REASON_BLOCKING
				else:
					reason = self.REASON_UNKNOWN
			else:
				reason = self.REASON_UNKNOWN
		super(TransferError, self).__init__(text)
		self.parent = parentException
		self.reason = reason
		self.errno = _errno

class AwlSimMessage(object):
	# Header format:
	#	Magic		(16 bit)
	#	Message ID	(16 bit)
	#	Flags		(16 bit)
	#	Sequence count	(16 bit)
	#	Reply to ID	(16 bit)
	#	Reply to seq	(16 bit)
	#	reserved	(32 bit)
	#	reserved	(32 bit)
	#	reserved	(32 bit)
	#	reserved	(32 bit)
	#	Payload length	(32 bit)
	#	Payload		(optional)
	hdrStruct = struct.Struct(str(">HHHHHHIIIII"))

	HDR_MAGIC		= 0x5719
	HDR_LENGTH		= hdrStruct.size

	HDR_FLAG_REPLY		= 1 << 0

	# Message IDs:
	EnumGen.start
	# Basic functionality
	MSG_ID_REPLY		= EnumGen.itemAt(0x0000) # Generic status reply
	MSG_ID_EXCEPTION	= EnumGen.item
	MSG_ID_MAINTREQ		= EnumGen.item
	MSG_ID_PING		= EnumGen.item
	MSG_ID_PONG		= EnumGen.item
	MSG_ID_RESET		= EnumGen.item
	MSG_ID_SHUTDOWN		= EnumGen.item
	# Program sources and blocks
	MSG_ID_GET_AWLSRC	= EnumGen.itemAt(0x0100)
	MSG_ID_AWLSRC		= EnumGen.item
	MSG_ID_GET_FUPSRC	= EnumGen.item
	MSG_ID_FUPSRC		= EnumGen.item
	MSG_ID_GET_KOPSRC	= EnumGen.item
	MSG_ID_KOPSRC		= EnumGen.item
	MSG_ID_GET_SYMTABSRC	= EnumGen.item
	MSG_ID_SYMTABSRC	= EnumGen.item
	MSG_ID_GET_LIBSEL	= EnumGen.item # not implemented
	MSG_ID_LIBSEL		= EnumGen.item
	MSG_ID_GET_HWMOD	= EnumGen.item # not implemented
	MSG_ID_HWMOD		= EnumGen.item
	# Remove content
	MSG_ID_REMOVESRC	= EnumGen.itemAt(0x0200)
	MSG_ID_REMOVEBLK	= EnumGen.item
	# Build control
	MSG_ID_BUILD		= EnumGen.itemAt(0x0300)
	# Fetch program info
	MSG_ID_GET_IDENTS	= EnumGen.itemAt(0x0400)
	MSG_ID_IDENTS		= EnumGen.item
	MSG_ID_GET_BLOCKINFO	= EnumGen.item
	MSG_ID_BLOCKINFO	= EnumGen.item
	# Configuration
	MSG_ID_GET_OPT		= EnumGen.itemAt(0x0500)
	MSG_ID_OPT		= EnumGen.item
	MSG_ID_GET_CPUSPECS	= EnumGen.item
	MSG_ID_CPUSPECS		= EnumGen.item
	MSG_ID_GET_CPUCONF	= EnumGen.item
	MSG_ID_CPUCONF		= EnumGen.item
	# State
	MSG_ID_GET_RUNSTATE	= EnumGen.itemAt(0x0600)
	MSG_ID_RUNSTATE		= EnumGen.item
	MSG_ID_GET_CPUDUMP	= EnumGen.item
	MSG_ID_CPUDUMP		= EnumGen.item
	MSG_ID_GET_CPUSTATS	= EnumGen.item
	MSG_ID_CPUSTATS		= EnumGen.item
	MSG_ID_REQ_MEMORY	= EnumGen.item
	MSG_ID_MEMORY		= EnumGen.item
	MSG_ID_INSNSTATE_CONFIG	= EnumGen.item
	MSG_ID_INSNSTATE	= EnumGen.item
	MSG_ID_MEAS_CONFIG	= EnumGen.item
	MSG_ID_MEAS		= EnumGen.item
	EnumGen.end

	_bytesLenStruct = struct.Struct(str(">I"))

	def setReplyTo(self, otherMsg):
		if otherMsg:
			self.replyToId = otherMsg.msgId
			self.replyToSeq = otherMsg.seq
			self.hdrFlags |= self.HDR_FLAG_REPLY
		else:
			self.replyToId = 0
			self.replyToSeq = 0
			self.hdrFlags &= ~self.HDR_FLAG_REPLY

	def isReplyTo(self, otherMsg):
		if otherMsg:
			return (((self.hdrFlags & self.HDR_FLAG_REPLY) != 0) and
				(self.replyToId == otherMsg.msgId) and
				(self.replyToSeq == otherMsg.seq))
		return False

	@classmethod
	def packString(cls, string):
		try:
			if not string:
				string = ""
			return cls.packBytes(string.encode("utf-8", "strict"))
		except UnicodeError as e:
			raise ValueError

	@classmethod
	def packBytes(cls, _bytes):
		try:
			if not _bytes:
				_bytes = b""
			if len(_bytes) > 0xFFFFFFFF:
				raise ValueError
			return cls._bytesLenStruct.pack(len(_bytes)) + _bytes
		except struct.error as e:
			raise ValueError

	@classmethod
	def unpackString(cls, data, offset = 0):
		try:
			_bytes, count = cls.unpackBytes(data, offset)
			return (_bytes.decode("utf-8", "strict"), count)
		except UnicodeError as e:
			raise ValueError

	@classmethod
	def unpackBytes(cls, data, offset = 0):
		try:
			(length, ) = cls._bytesLenStruct.unpack_from(data, offset)
			_bytes = data[offset + cls._bytesLenStruct.size :
				      offset + cls._bytesLenStruct.size + length]
			if len(_bytes) != length:
				raise ValueError
			return (_bytes, cls._bytesLenStruct.size + length)
		except struct.error as e:
			raise ValueError

	# Default values for instance attributes:
	msgId = None	# MSG_ID_...
	seq = 0		# Sequence number.
	hdrFlags = 0	# HDR_FLAG_...
	replyToId = 0	# Reply to msgId
	replyToSeq = 0	# Reply to seq

	def toBytes(self, payloadLength=0):
		return self.hdrStruct.pack(self.HDR_MAGIC,
					   self.msgId,
					   self.hdrFlags,
					   self.seq,
					   self.replyToId,
					   self.replyToSeq,
					   0, # reserved
					   0, # reserved
					   0, # reserved
					   0, # reserved
					   payloadLength)

	@classmethod
	def fromBytes(cls, payload):
		return cls()

class AwlSimMessage_REPLY(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_REPLY

	EnumGen.start
	STAT_OK		= EnumGen.item
	STAT_FAIL	= EnumGen.item
	EnumGen.end

	plStruct = struct.Struct(str(">HHHHHHHH"))

	@classmethod
	def make(cls, replyToMsg, status):
		msg = cls(status)
		msg.setReplyTo(replyToMsg)
		return msg

	def __init__(self, status):
		self.status = status

	def toBytes(self):
		pl = self.plStruct.pack(self.status, 0, 0, 0,
					0, 0, 0, 0)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			status, _, _, _,\
			_, _, _, _ =\
				cls.plStruct.unpack(payload)
		except struct.error as e:
			raise TransferError("REPLY: Invalid data format")
		return cls(status)

class AwlSimMessage_PING(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_PING

class AwlSimMessage_PONG(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_PONG

class AwlSimMessage_RESET(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_RESET

	# Payload struct:
	#	reserved		(32 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)

	plStruct = struct.Struct(str(">IIIIIIII"))

	def __init__(self):
		pass

	def toBytes(self):
		pl = self.plStruct.pack(0, 0, 0, 0, 0, 0, 0, 0)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			_, _, _, _, _, _, _, _ =\
				cls.plStruct.unpack(payload)
		except struct.error as e:
			raise TransferError("RESET: Invalid data format")
		return cls()

class AwlSimMessage_SHUTDOWN(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_SHUTDOWN

	EnumGen.start
	SHUTDOWN_CORE		= EnumGen.item
	SHUTDOWN_SYSTEM_HALT	= EnumGen.item
	SHUTDOWN_SYSTEM_REBOOT	= EnumGen.item
	EnumGen.end

	SHUTDOWN_MAGIC = 0x7B8F

	# Payload struct:
	#	magic number		(16 bit)
	#	shutdownType		(16 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)

	plStruct = struct.Struct(str(">HHIIIIIII"))

	def __init__(self, shutdownType):
		self.shutdownType = shutdownType & 0xFFFF

	def toBytes(self):
		pl = self.plStruct.pack(self.SHUTDOWN_MAGIC,
					self.shutdownType,
					0, 0, 0, 0, 0, 0, 0)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			magic, shutdownType, _, _, _, _, _, _, _ =\
				cls.plStruct.unpack(payload)
			if magic != cls.SHUTDOWN_MAGIC:
				raise TransferError("SHUTDOWN: Incorrect magic number")
		except struct.error as e:
			raise TransferError("SHUTDOWN: Invalid data format")
		return cls(shutdownType)

class AwlSimMessage_RUNSTATE(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_RUNSTATE

	EnumGen.start
	STATE_STOP	= EnumGen.item
	STATE_RUN	= EnumGen.item
	EnumGen.end

	# Payload struct:
	#	runState		(16 bit)
	#	reserved		(16 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)

	plStruct = struct.Struct(str(">HHIIIIIII"))

	def __init__(self, runState):
		self.runState = runState

	def toBytes(self):
		pl = self.plStruct.pack(self.runState,
					0, 0, 0, 0, 0, 0, 0, 0)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			runState, _, _, _, _, _, _, _, _ =\
				cls.plStruct.unpack(payload)
		except struct.error as e:
			raise TransferError("RUNSTATE: Invalid data format")
		return cls(runState)

class AwlSimMessage_GET_RUNSTATE(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_GET_RUNSTATE

class AwlSimMessage_EXCEPTION(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_EXCEPTION

	# Payload struct:
	#	flags			(32 bit)
	#	lineNr			(32 bit)
	#	coordinate X		(32 bit)
	#	coordinate Y		(32 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)
	#	reserved		(32 bit)
	#	exception type		(string)
	#	sourceName		(string)
	#	sourceId		(bytes)
	#	failing insn string	(string)
	#	message			(string)
	#	verboseMsg		(string)
	#	element UUID		(string)
	plStruct = struct.Struct(str(">IIIIIIIIII"))

	def __init__(self, exception):
		self.exception = exception

	def toBytes(self):
		try:
			e = self.exception
			lineNr = e.getLineNr()
			lineNr = 0xFFFFFFFF if lineNr is None else lineNr
			coordinates = e.getCoordinates()
			x = clamp(coordinates[0], -1, 0x7FFFFFFF) & 0xFFFFFFFF
			y = clamp(coordinates[1], -1, 0x7FFFFFFF) & 0xFFFFFFFF
			pl = self.plStruct.pack(0, lineNr, x, y, 0, 0, 0, 0, 0, 0) +\
			     self.packString(e.EXC_TYPE) +\
			     self.packString(e.getSourceName() or "") +\
			     self.packBytes(e.getSourceId() or "") +\
			     self.packString(e.getFailingInsnStr()) +\
			     self.packString(e.getReport(verbose = False)) +\
			     self.packString(e.getReport(verbose = True)) +\
			     self.packString(e.getElemUUID())
			return AwlSimMessage.toBytes(self, len(pl)) + pl
		except ValueError:
			raise TransferError("EXCEPTION: Encoding error")

	@classmethod
	def fromBytes(cls, payload):
		try:
			offset = 0
			flags, lineNr, x, y, _, _, _, _, _, _ =\
				cls.plStruct.unpack_from(payload, offset)
			offset += cls.plStruct.size
			excType, count = cls.unpackString(payload, offset)
			offset += count
			sourceName, count = cls.unpackString(payload, offset)
			offset += count
			sourceId, count = cls.unpackBytes(payload, offset)
			offset += count
			failingInsnStr, count = cls.unpackString(payload, offset)
			offset += count
			text, count = cls.unpackString(payload, offset)
			offset += count
			verboseText, count = cls.unpackString(payload, offset)
			offset += count
			if len(payload) > offset:
				elemUUID, count = cls.unpackString(payload, offset)
			else:
				elemUUID = None
		except ValueError:
			raise TransferError("EXCEPTION: Encoding error")
		coordinates = (
			-1 if x == 0xFFFFFFFF else x,
			-1 if y == 0xFFFFFFFF else y,
		)
		e = FrozenAwlSimError(excType=excType,
				      errorText=text,
				      verboseErrorText=verboseText)
		e.setLineNr(lineNr if lineNr < 0xFFFFFFFF else None)
		e.setSourceName(sourceName)
		e.setSourceId(sourceId)
		e.setFailingInsnStr(failingInsnStr)
		e.setCoordinates(coordinates)
		e.setElemUUID(elemUUID)
		return cls(e)

class _AwlSimMessage_GET_source(AwlSimMessage):
	msgId = None

	# Payload struct:
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	identHash (bytes)
	plStruct = struct.Struct(str(">IIIIIIII"))

	def __init__(self, identHash):
		self.identHash = identHash

	def toBytes(self):
		pl = self.plStruct.pack(0, 0, 0, 0, 0, 0, 0, 0) +\
			self.packBytes(self.identHash)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			offset = 0
			_, _, _, _, _, _, _, _ =\
				cls.plStruct.unpack_from(payload, offset)
			offset += cls.plStruct.size
			identHash, count = cls.unpackBytes(payload, offset)
		except (ValueError, struct.error, AwlSimError) as e:
			raise TransferError("GET_source: Invalid data format")
		return cls(identHash = identHash)

class _AwlSimMessage_source(AwlSimMessage):
	sourceClass = None

	# Payload struct:
	#	flags (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	sourceName (string)
	#	sourceBytes (bytes)
	plStruct = struct.Struct(str(">IIIIIIII"))

	FLAG_ENABLED	= 1 << 0
	FLAG_VOLATILE	= 1 << 1

	def __init__(self, source):
		if not source:
			source = self.sourceClass()
		# If the source it file-backed, integrate it.
		# Otherwise the source data will not be sent.
		if source.isFileBacked():
			source = source.dup()
			source.forceNonFileBacked(source.name)
		else:
			source = source.dup()
		self.source = source

	def toBytes(self):
		try:
			flags = 0
			if self.source.enabled:
				flags |= self.FLAG_ENABLED
			if self.source.volatile:
				flags |= self.FLAG_VOLATILE
			pl = self.plStruct.pack(flags, 0, 0, 0, 0, 0, 0, 0) +\
				self.packString(self.source.name) +\
				self.packBytes(self.source.sourceBytes)
			return AwlSimMessage.toBytes(self, len(pl)) + pl
		except ValueError:
			raise TransferError("SOURCE: Data format error")

	@classmethod
	def fromBytes(cls, payload):
		try:
			offset = 0
			flags, _, _, _, _, _, _, _ =\
				cls.plStruct.unpack_from(payload, offset)
			offset += cls.plStruct.size
			name, cnt = cls.unpackString(payload, offset)
			offset += cnt
			sourceBytes, cnt = cls.unpackBytes(payload, offset)
		except (ValueError, struct.error) as e:
			raise TransferError("SOURCE: Data format error")
		return cls(cls.sourceClass(name=name,
					   enabled=(flags & cls.FLAG_ENABLED),
					   volatile=(flags & cls.FLAG_VOLATILE),
					   sourceBytes=sourceBytes))

class AwlSimMessage_GET_SYMTABSRC(_AwlSimMessage_GET_source):
	msgId = AwlSimMessage.MSG_ID_GET_SYMTABSRC

class AwlSimMessage_SYMTABSRC(_AwlSimMessage_source):
	msgId = AwlSimMessage.MSG_ID_SYMTABSRC
	sourceClass = SymTabSource

class AwlSimMessage_GET_AWLSRC(_AwlSimMessage_GET_source):
	msgId = AwlSimMessage.MSG_ID_GET_AWLSRC

class AwlSimMessage_AWLSRC(_AwlSimMessage_source):
	msgId = AwlSimMessage.MSG_ID_AWLSRC
	sourceClass = AwlSource

class AwlSimMessage_GET_FUPSRC(_AwlSimMessage_GET_source):
	msgId = AwlSimMessage.MSG_ID_GET_FUPSRC

class AwlSimMessage_FUPSRC(_AwlSimMessage_source):
	msgId = AwlSimMessage.MSG_ID_FUPSRC
	sourceClass = FupSource

class AwlSimMessage_GET_KOPSRC(_AwlSimMessage_GET_source):
	msgId = AwlSimMessage.MSG_ID_GET_KOPSRC

class AwlSimMessage_KOPSRC(_AwlSimMessage_source):
	msgId = AwlSimMessage.MSG_ID_KOPSRC
	sourceClass = KopSource

class AwlSimMessage_HWMOD(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_HWMOD

	# Payload header struct:
	#	number of parameters (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	module name (string)
	plHdrStruct = struct.Struct(str(">IIII"))

	# Payload param struct:
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	parameter name (string)
	#	parameter value (string)
	plParamStruct = struct.Struct(str(">IIII"))

	# hwmodDesc -> HwmodDescriptor instance
	def __init__(self, hwmodDesc):
		self.hwmodDesc = hwmodDesc

	def toBytes(self):
		payload = b""
		try:
			params = tuple(dictItems(self.hwmodDesc.getParameters()))
			payload += self.plHdrStruct.pack(len(params), 0, 0, 0)
			payload += self.packString(self.hwmodDesc.getModuleName())
			for pname, pval in params:
				payload += self.plParamStruct.pack(0, 0, 0, 0)
				payload += self.packString(pname)
				payload += self.packString(pval)
			return AwlSimMessage.toBytes(self, len(payload)) + payload
		except (ValueError) as e:
			raise TransferError("LOAD_HW: Invalid data format")

	@classmethod
	def fromBytes(cls, payload):
		paramDict = {}
		offset = 0
		try:
			nrParams, _, _, _ = cls.plHdrStruct.unpack_from(payload, offset)
			offset += cls.plHdrStruct.size
			name, count = cls.unpackString(payload, offset)
			offset += count
			for i in range(nrParams):
				if offset >= len(payload):
					break
				_, _, _, _ = cls.plParamStruct.unpack_from(payload, offset)
				offset += cls.plParamStruct.size
				pname, count = cls.unpackString(payload, offset)
				offset += count
				pval, count = cls.unpackString(payload, offset)
				offset += count
				paramDict[pname] = pval
		except (ValueError) as e:
			raise TransferError("LOAD_HW: Invalid data format")
		return cls(HwmodDescriptor(name, paramDict))

class AwlSimMessage_LIBSEL(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_LIBSEL

	plStruct = struct.Struct(str(">HHiiI"))

	def __init__(self, libSelection):
		self.libSelection = libSelection

	# Pack a library selection.
	# May raise ValueError or struct.error
	@classmethod
	def packLibSelection(cls, libSel):
		payload = [ cls.packString(libSel.getLibName()), ]
		payload.append(cls.plStruct.pack(0,
						 libSel.getEntryType(),
						 libSel.getEntryIndex(),
						 libSel.getEffectiveEntryIndex(),
						 0))
		return b''.join(payload)

	# Unpack a library selection.
	# May raise ValueError, struct.error or AwlSimError
	@classmethod
	def unpackLibSelection(cls, payload, offset = 0):
		libName, count = cls.unpackString(payload, offset)
		offset += count
		_, eType, eIndex, effIndex, _ =\
			cls.plStruct.unpack_from(payload, offset)
		offset += cls.plStruct.size
		return (AwlLibEntrySelection(
				libName = libName,
				entryType = eType,
				entryIndex = eIndex,
				effectiveEntryIndex = effIndex),
			offset)

	def toBytes(self):
		try:
			payload = self.packLibSelection(self.libSelection)
			return AwlSimMessage.toBytes(self, len(payload)) + payload
		except (ValueError, struct.error) as e:
			raise TransferError("LOAD_LIB: Invalid data format")

	@classmethod
	def fromBytes(cls, payload):
		try:
			libSelection, offset = cls.unpackLibSelection(payload)
		except (ValueError, struct.error, AwlSimError) as e:
			raise TransferError("LOAD_LIB: Invalid data format")
		return cls(libSelection = libSelection)

class AwlSimMessage_BUILD(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_BUILD

	plStruct = struct.Struct(str(">8I"))

	def toBytes(self):
		try:
			pl = self.plStruct.pack(0, 0, 0, 0, 0, 0, 0, 0)
			return AwlSimMessage.toBytes(self, len(pl)) + pl
		except (ValueError, struct.error) as e:
			raise TransferError("BUILD: Invalid data format")

	@classmethod
	def fromBytes(cls, payload):
		try:
			pass
		except (ValueError, struct.error) as e:
			raise TransferError("BUILD: Invalid data format")
		return cls()

class AwlSimMessage_GET_OPT(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_GET_OPT

	def __init__(self, name):
		self.name = name

	def toBytes(self):
		try:
			payload = self.packString(self.name)
		except ValueError as e:
			raise TransferError("GET_OPT: Invalid data format")
		return AwlSimMessage.toBytes(self, len(payload)) + payload

	@classmethod
	def fromBytes(cls, payload):
		try:
			name, count = cls.unpackString(payload, 0)
		except ValueError as e:
			raise TransferError("GET_OPT: Invalid data format")
		return cls(name=name)

class AwlSimMessage_OPT(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_OPT

	def __init__(self, name, value):
		self.name = name
		self.value = value

	def getStrValue(self):
		return self.value

	def getIntValue(self):
		try:
			return int(self.value)
		except ValueError as e:
			raise AwlSimError("OPT: Value is not an integer")

	def getBoolValue(self):
		try:
			return bool(self.getIntValue())
		except ValueError as e:
			raise AwlSimError("OPT: Value is not a boolean")

	def getFloatValue(self):
		try:
			return float(self.value)
		except ValueError as e:
			raise AwlSimError("OPT: Value is not a float")

	def toBytes(self):
		try:
			payload = self.packString(self.name)
			payload += self.packString(self.value)
		except ValueError as e:
			raise TransferError("OPT: Invalid data format")
		return AwlSimMessage.toBytes(self, len(payload)) + payload

	@classmethod
	def fromBytes(cls, payload):
		try:
			offset = 0
			name, count = cls.unpackString(payload, offset)
			offset += count
			value, count = cls.unpackString(payload, offset)
			offset += count
		except ValueError as e:
			raise TransferError("OPT: Invalid data format")
		return cls(name = name, value = value)

class AwlSimMessage_GET_CPUDUMP(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_GET_CPUDUMP

class AwlSimMessage_CPUDUMP(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_CPUDUMP

	def __init__(self, dumpText):
		self.dumpText = dumpText

	def toBytes(self):
		try:
			pl = self.packString(self.dumpText)
			return AwlSimMessage.toBytes(self, len(pl)) + pl
		except UnicodeError:
			raise TransferError("CPUDUMP: Unicode error")

	@classmethod
	def fromBytes(cls, payload):
		try:
			dumpText, count = cls.unpackString(payload)
		except UnicodeError:
			raise TransferError("CPUDUMP: Unicode error")
		return cls(dumpText)

class AwlSimMessage_GET_CPUSTATS(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_GET_CPUSTATS

class AwlSimMessage_CPUSTATS(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_CPUSTATS

	# Payload struct:
	#	flags (32 bit)
	#	reserved (32 bit)
	#	uptime in milliseconds (64 bit)
	#	runtime in milliseconds (64 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	insnPerSecond *1 (32 bit)
	#	insnPerCycle *1000 (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	avgCycleTime in microseconds (32 bit)
	#	minCycleTime in microseconds (32 bit)
	#	maxCycleTime in microseconds (32 bit)
	#	padCycleTime in microseconds (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	plStruct = struct.Struct(str(">IIQQIIIIIIIIIIIIIIIIIIIIIIIIII"))

	FLG_RUN = 1 << 0

	def __init__(self,
		     running,
		     uptime,
		     runtime,
		     insnPerSecond,
		     insnPerCycle,
		     avgCycleTime,
		     minCycleTime,
		     maxCycleTime,
		     padCycleTime):
		self.running = bool(running)
		self.uptime = float(uptime)
		self.runtime = float(runtime)
		self.insnPerSecond = float(insnPerSecond)
		self.insnPerCycle = float(insnPerCycle)
		self.avgCycleTime = float(avgCycleTime)
		self.minCycleTime = float(minCycleTime)
		self.maxCycleTime = float(maxCycleTime)
		self.padCycleTime = float(padCycleTime)

	def toBytes(self):
		try:
			flags = self.FLG_RUN if self.running else 0
			pl = self.plStruct.pack(
				flags,
				0,
				clamp(int(round(self.uptime * 1000.0)),
				      0, 0xFFFFFFFFFFFFFFFF),
				clamp(int(round(self.runtime * 1000.0)),
				      0, 0xFFFFFFFFFFFFFFFF),
				0, 0, 0, 0,
				clamp(int(round(self.insnPerSecond)),
				      0, 0xFFFFFFFF),
				clamp(int(round(self.insnPerCycle * 1000.0)),
				      0, 0xFFFFFFFF),
				0, 0, 0, 0,
				clamp(int(round(self.avgCycleTime * 1000000.0)),
				      0, 0xFFFFFFFF),
				clamp(int(round(self.minCycleTime * 1000000.0)),
				      0, 0xFFFFFFFF),
				clamp(int(round(self.maxCycleTime * 1000000.0)),
				      0, 0xFFFFFFFF),
				clamp(int(round(self.padCycleTime * 1000000.0)),
				      0, 0xFFFFFFFF),
				0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
			)
			return AwlSimMessage.toBytes(self, len(pl)) + pl
		except ValueError:
			raise TransferError("CPUSTATS: Data format error")

	@classmethod
	def fromBytes(cls, payload):
		try:
			flags, _,\
			uptime, runtime,\
			_, _, _, _,\
			insnPerSecond, insnPerCycle,\
			_, _, _, _,\
			avgCycleTime, minCycleTime, maxCycleTime, padCycleTime,\
			_, _, _, _, _, _, _, _, _, _, _, _ =\
				cls.plStruct.unpack_from(payload, 0)
		except (ValueError, struct.error) as e:
			raise TransferError("CPUSTATS: Data format error")
		return cls(running=bool(flags & cls.FLG_RUN),
			   uptime=(float(uptime) / 1000.0),
			   runtime=(float(runtime) / 1000.0),
			   insnPerSecond=(float(insnPerSecond)),
			   insnPerCycle=(float(insnPerCycle) / 1000.0),
			   avgCycleTime=(float(avgCycleTime) / 1000000.0),
			   minCycleTime=(float(minCycleTime) / 1000000.0),
			   maxCycleTime=(float(maxCycleTime) / 1000000.0),
			   padCycleTime=(float(padCycleTime) / 1000000.0))

class AwlSimMessage_MAINTREQ(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_MAINTREQ

	plStruct = struct.Struct(str(">HHIIIIIII"))

	def __init__(self, maintRequest):
		self.maintRequest = maintRequest

	def toBytes(self):
		pl = self.plStruct.pack(self.maintRequest.requestType,
					0, 0, 0, 0, 0, 0, 0, 0) +\
		     self.packString(str(self.maintRequest))
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			requestType, _, _, _, _, _, _, _, _ =\
				cls.plStruct.unpack_from(payload, 0)
			msg, count = cls.unpackString(payload, cls.plStruct.size)
		except (struct.error, ValueError) as e:
			raise TransferError("MAINTREQ: Invalid data format")
		return cls(MaintenanceRequest(requestType, msg))

class AwlSimMessage_GET_CPUSPECS(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_GET_CPUSPECS

class AwlSimMessage_CPUSPECS(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_CPUSPECS

	plStruct = struct.Struct(str(">32I"))

	def __init__(self, cpuspecs):
		self.cpuspecs = cpuspecs

	def toBytes(self):
		pl = self.plStruct.pack(self.cpuspecs.nrAccus,
					self.cpuspecs.nrTimers,
					self.cpuspecs.nrCounters,
					self.cpuspecs.nrFlags,
					self.cpuspecs.nrInputs,
					self.cpuspecs.nrOutputs,
					self.cpuspecs.nrLocalbytes,
					self.cpuspecs.parenStackSize,
					self.cpuspecs.callStackSize,
					*( (0,) * 23 ) # padding
		)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			data = cls.plStruct.unpack(payload)
			(nrAccus, nrTimers,
			 nrCounters, nrFlags, nrInputs,
			 nrOutputs, nrLocalbytes,
			 parenStackSize, callStackSize) = data[:9]
		except struct.error as e:
			raise TransferError("CPUSPECS: Invalid data format")
		cpuspecs = S7CPUSpecs()
		cpuspecs.setNrAccus(nrAccus)
		cpuspecs.setNrTimers(nrTimers)
		cpuspecs.setNrCounters(nrCounters)
		cpuspecs.setNrFlags(nrFlags)
		cpuspecs.setNrInputs(nrInputs)
		cpuspecs.setNrOutputs(nrOutputs)
		cpuspecs.setNrLocalbytes(nrLocalbytes)
		cpuspecs.setParenStackSize(parenStackSize)
		cpuspecs.setCallStackSize(callStackSize)
		return cls(cpuspecs)

class AwlSimMessage_GET_CPUCONF(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_GET_CPUCONF

class AwlSimMessage_CPUCONF(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_CPUCONF

	plStruct = struct.Struct(str(">32I"))

	def __init__(self, cpuconf):
		self.cpuconf = cpuconf

	def toBytes(self):
		pl = self.plStruct.pack(self.cpuconf.getConfiguredMnemonics(),
					self.cpuconf.clockMemByte & 0xFFFFFFFF,
					self.cpuconf.cycleTimeLimitUs & 0xFFFFFFFF,
					(self.cpuconf.runTimeLimitUs >> 32) & 0xFFFFFFFF,
					self.cpuconf.runTimeLimitUs & 0xFFFFFFFF,
					1 if self.cpuconf.extInsnsEn else 0,
					1 if self.cpuconf.obStartinfoEn else 0,
					self.cpuconf.cycleTimeTargetUs & 0xFFFFFFFF,
					*( (0,) * 24 ) # padding
		)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			data = cls.plStruct.unpack(payload)
			(mnemonics,
			 clockMemByte,
			 cycleTimeLimitUs,
			 runTimeLimitUsHigh, runTimeLimitUsLow,
			 extInsnsEn,
			 obStartinfoEn,
			 cycleTimeTargetUs,
			) = data[:8]
		except struct.error as e:
			raise TransferError("CPUCONF: Invalid data format")
		cpuconf = S7CPUConfig()
		cpuconf.setConfiguredMnemonics(mnemonics)
		cpuconf.setClockMemByte(-1 if clockMemByte > 0xFFFF else clockMemByte)
		cpuconf.setCycleTimeLimitUs(cycleTimeLimitUs)
		cpuconf.setCycleTimeTargetUs(cycleTimeTargetUs)
		cpuconf.setRunTimeLimitUs(qwordToSignedPyInt((runTimeLimitUsHigh << 32) |
							     runTimeLimitUsLow))
		cpuconf.setExtInsnsEn(True if (extInsnsEn & 1) else False)
		cpuconf.setOBStartinfoEn(True if (obStartinfoEn & 1) else False)
		return cls(cpuconf)

class AwlSimMessage_REQ_MEMORY(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_REQ_MEMORY

	# Payload header struct:
	#	flags (32 bit)
	#	repetition period in nanoseconds (32 bit)
	#	number of memory areas (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	plHdrStruct = struct.Struct(str(">IiIIIIII"))

	# Payload memory area struct:
	#	memType (8 bit)
	#	flags (8 bit)
	#	index (16 bit)
	#	start (32 bit)
	#	length (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	plAreaStruct = struct.Struct(str(">BBHIIIIIII"))

	# Flags
	FLG_SYNC	= 1 << 0 # Synchronous. Returns a REPLY when finished.

	def __init__(self, flags, repetitionPeriod, memAreas):
		self.flags = flags
		self.repetitionPeriod = repetitionPeriod
		self.memAreas = memAreas

	def toBytes(self):
		repPeriodNs = int(round(self.repetitionPeriod * 1000000000.0))
		pl = self.plHdrStruct.pack(self.flags, repPeriodNs, len(self.memAreas),
					   0, 0, 0, 0, 0)
		for memArea in self.memAreas:
			pl += self.plAreaStruct.pack(memArea.memType,
						     memArea.flags,
						     memArea.index,
						     memArea.start,
						     memArea.length,
						     0, 0, 0, 0, 0)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			offset = 0
			flags, repPeriodNs, nrMemAreas, _, _, _, _, _ =\
				cls.plHdrStruct.unpack_from(payload, offset)
			offset += cls.plHdrStruct.size
			repetitionPeriod = float(repPeriodNs) / 1000000000.0
			memAreas = []
			for i in range(nrMemAreas):
				if offset >= len(payload):
					break
				memType, mFlags, index, start, length,\
				_, _, _, _, _ =\
					cls.plAreaStruct.unpack_from(payload, offset)
				offset += cls.plAreaStruct.size
				memAreas.append(MemoryArea(memType, mFlags, index, start, length))
		except struct.error as e:
			raise TransferError("REQ_MEMORY: Invalid data format")
		return cls(flags, repetitionPeriod, memAreas)

class AwlSimMessage_MEMORY(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_MEMORY

	# Payload header struct:
	#	flags (32 bit)
	#	number of memory areas (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	plHdrStruct = struct.Struct(str(">IIII"))

	# Payload memory area struct:
	#	memType (8 bit)
	#	flags (8 bit)
	#	index (16 bit)
	#	start (32 bit)
	#	specified length (32 bit)
	#	actual length (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	the actual binary data (variable length, padded to 32-bit boundary)
	plAreaStruct = struct.Struct(str(">BBHIIIII"))

	# Flags
	FLG_SYNC	= 1 << 0 # Synchronous. Returns a REPLY when finished.

	def __init__(self, flags, memAreas):
		self.flags = flags
		self.memAreas = memAreas

	def toBytes(self):
		pl = [ self.plHdrStruct.pack(self.flags, len(self.memAreas), 0, 0) ]
		for memArea in self.memAreas:
			actualLength = len(memArea.data)
			pl.append(self.plAreaStruct.pack(memArea.memType,
							 memArea.flags,
							 memArea.index,
							 memArea.start,
							 memArea.length,
							 actualLength,
							 0, 0))
			pl.append(bytes(memArea.data))
			# Pad to a 32-bit boundary
			pl.append(b'\x00' * (roundUp(actualLength, 4) - actualLength))
		pl = b''.join(pl)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			offset = 0
			flags, nrMemAreas, _, _ =\
				cls.plHdrStruct.unpack_from(payload, offset)
			offset += cls.plHdrStruct.size
			memAreas = []
			for i in range(nrMemAreas):
				if offset >= len(payload):
					break
				memType, mFlags, index, start, length, actualLength, _, _ =\
					cls.plAreaStruct.unpack_from(payload, offset)
				offset += cls.plAreaStruct.size
				data = payload[offset : offset + actualLength]
				offset += roundUp(actualLength, 4)
				if len(data) != actualLength:
					raise IndexError
				memAreas.append(MemoryArea(memType, mFlags, index,
							   start, length, data))
		except (struct.error, IndexError) as e:
			raise TransferError("MEMORY: Invalid data format")
		return cls(flags, memAreas)

class AwlSimMessage_INSNSTATE(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_INSNSTATE

	# Payload data struct:
	#	AWL line number (32 bit)
	#	Serial number. Reset to 0 on cycle exit. (32 bit)
	#	Flags (16 bit) (currently unused. Set to 0)
	#	CPU status word (16 bit)
	#	CPU ACCU 1 (32 bit)
	#	CPU ACCU 2 (32 bit)
	#	CPU ACCU 3 (32 bit)
	#	CPU ACCU 4 (32 bit)
	#	CPU AR 1 (32 bit)
	#	CPU AR 2 (32 bit)
	#	CPU DB register (16 bit)
	#	CPU DI register (16 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	user data (32 bit)
	#	Source ident hash bytes (variable length)
	plDataStruct = struct.Struct(str(">IIHHIIIIIIHHIIII"))

	def __init__(self, sourceId, lineNr, serial, flags,
		     stw, accu1, accu2, accu3, accu4, ar1, ar2, db, di,
		     userData):
		self.sourceId = sourceId
		self.lineNr = lineNr
		self.serial = serial
		self.flags = flags
		self.stw = stw
		self.accu1 = accu1
		self.accu2 = accu2
		self.accu3 = accu3
		self.accu4 = accu4
		self.ar1 = ar1
		self.ar2 = ar2
		self.db = db
		self.di = di
		self.userData = userData

	def toBytes(self):
		pl = self.plDataStruct.pack(
			self.lineNr, self.serial,
			self.flags, self.stw, self.accu1, self.accu2,
			self.accu3, self.accu4, self.ar1, self.ar2,
			self.db, self.di,
			0, 0, 0,
			self.userData)
		pl += self.packBytes(self.sourceId)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			lineNr, serial, flags, stw,\
			accu1, accu2, accu3, accu4,\
			ar1, ar2, db, di,\
			_, _, _,\
			userData =\
				cls.plDataStruct.unpack_from(payload, 0)
			sourceId, offset = cls.unpackBytes(payload, cls.plDataStruct.size)
		except (struct.error, IndexError) as e:
			raise TransferError("INSNSTATE: Invalid data format")
		return cls(sourceId, lineNr, serial, flags,
			   stw, accu1, accu2, accu3, accu4, ar1, ar2, db, di,
			   userData)

class AwlSimMessage_INSNSTATE_CONFIG(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_INSNSTATE_CONFIG

	# Payload data struct:
	#	Flags (32 bit)
	#	From AWL line (32 bit)
	#	To AWL line (32 bit)
	#	OB1 divider (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	user data (32 bit)
	#	AWL source ident hash bytes (variable length)
	plDataStruct = struct.Struct(str(">IIIIIIIIIIIIIIII"))

	# Flags:
	FLG_SYNC		= 1 << 0 # Synchronous status reply.
	FLG_CLEAR		= 1 << 1 # Clear current settings.
	FLG_SET			= 1 << 2 # Apply settings.

	def __init__(self, flags, sourceId, fromLine, toLine, ob1Div, userData):
		self.flags = flags & 0xFFFFFFFF
		self.sourceId = sourceId
		self.fromLine = fromLine & 0xFFFFFFFF
		self.toLine = toLine & 0xFFFFFFFF
		self.ob1Div = ob1Div & 0xFFFFFFFF
		self.userData = userData & 0xFFFFFFFF

	def toBytes(self):
		pl = self.plDataStruct.pack(
			self.flags, self.fromLine, self.toLine,
			self.ob1Div,
			0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
			self.userData)
		pl += self.packBytes(self.sourceId)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			flags, fromLine, toLine, ob1Div,\
			_, _, _, _, _, _, _, _, _, _, _,\
			userData =\
				cls.plDataStruct.unpack_from(payload, 0)
			sourceId, offset = cls.unpackBytes(payload, cls.plDataStruct.size)
		except (struct.error, IndexError) as e:
			raise TransferError("INSNSTATE_CONFIG: Invalid data format")
		return cls(flags, sourceId, fromLine, toLine, ob1Div, userData)

class AwlSimMessage_MEAS(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_MEAS

	# Payload data struct:
	#	Flags (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	measurement report data (string)
	plDataStruct = struct.Struct(str(">IIIIIIIIIIIIIIII"))

	# Flags:
	FLG_HAVEDATA		= 1 << 0
	FLG_FAIL		= 1 << 1

	def __init__(self, flags, reportStr):
		self.flags = flags & 0xFFFFFFFF
		self.reportStr = reportStr

	def toBytes(self):
		pl = self.plDataStruct.pack(self.flags,
			0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
		pl += self.packString(self.reportStr)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			offset = 0
			flags, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _ =\
				cls.plDataStruct.unpack_from(payload, offset)
			offset += cls.plDataStruct.size
			reportStr, offset = cls.unpackString(payload, offset)
		except (struct.error, IndexError) as e:
			raise TransferError("MEAS: Invalid data format")
		return cls(flags, reportStr)

class AwlSimMessage_MEAS_CONFIG(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_MEAS_CONFIG

	# Payload data struct:
	#	Flags (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	plDataStruct = struct.Struct(str(">IIIIIIIIIIIIIIII"))

	# Flags:
	FLG_ENABLE		= 1 << 0
	FLG_GETMEAS		= 1 << 1
	FLG_CSV			= 1 << 2

	def __init__(self, flags):
		self.flags = flags & 0xFFFFFFFF

	def toBytes(self):
		pl = self.plDataStruct.pack(
			self.flags,
			0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			flags, _, _, _,\
			_, _, _, _, _, _, _, _, _, _, _, _ =\
				cls.plDataStruct.unpack_from(payload, 0)
		except (struct.error, IndexError) as e:
			raise TransferError("MEAS_CONFIG: Invalid data format")
		return cls(flags)

class AwlSimMessage_REMOVESRC(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_REMOVESRC

	# Payload data struct:
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	Source ident hash (bytes)
	plHdrStruct = struct.Struct(str(">IIIIIIII"))

	def __init__(self, identHash):
		self.identHash = identHash

	def toBytes(self):
		payload = self.plHdrStruct.pack(0, 0, 0, 0, 0, 0, 0, 0)
		payload += self.packBytes(self.identHash)
		return AwlSimMessage.toBytes(self, len(payload)) + payload

	@classmethod
	def fromBytes(cls, payload):
		try:
			offset = 0
			_, _, _, _, _, _, _, _ =\
				cls.plHdrStruct.unpack_from(payload, offset)
			offset += cls.plHdrStruct.size
			identHash, count = cls.unpackBytes(payload, offset)
		except (ValueError, struct.error) as e:
			raise TransferError("REMOVESRC: Invalid data format")
		return cls(identHash)

class AwlSimMessage_REMOVEBLK(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_REMOVEBLK

	# Block info payload struct:
	#	BlockInfo.TYPE_... (32 bit)
	#	Block index (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	plStruct = struct.Struct(str(">IIIIIIIIIIIIIIII"))

	def __init__(self, blockInfo):
		self.blockInfo = blockInfo

	def toBytes(self):
		payload = self.plStruct.pack(
				self.blockInfo.blockIndex,
				self.blockInfo.blockType,
				0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
		return AwlSimMessage.toBytes(self, len(payload)) + payload

	@classmethod
	def fromBytes(cls, payload):
		try:
			blockIndex, blockType,\
			_, _, _, _, _, _, _, _, _, _, _, _, _, _ = \
				cls.plStruct.unpack_from(payload, 0)
			blockInfo = BlockInfo(
				blockType=blockType,
				blockIndex=blockIndex)
		except (ValueError, struct.error) as e:
			raise TransferError("REMOVEBLK: Invalid data format")
		return cls(blockInfo)

class AwlSimMessage_GET_IDENTS(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_GET_IDENTS

	# Get-flags. Specify what information to get.
	EnumGen.start
	GET_AWLSRCS		= EnumGen.bitmask # Get AwlSource()s (w/o data)
	GET_SYMTABSRCS		= EnumGen.bitmask # Get SymTabSource()s (w/o data)
	GET_HWMODS		= EnumGen.bitmask # Get HW modules
	GET_LIBSELS		= EnumGen.bitmask # Get AwlLibEntrySelection()s
	GET_FUPSRCS		= EnumGen.bitmask # Get FupSource()s (w/o data)
	GET_KOPSRCS		= EnumGen.bitmask # Get KopSource()s (w/o data)
	EnumGen.end

	# Payload header struct:
	#	Get-flags (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	plHdrStruct = struct.Struct(str(">IIIIIIII"))

	def __init__(self, getFlags):
		self.getFlags = getFlags

	def toBytes(self):
		payload = self.plHdrStruct.pack(self.getFlags, 0, 0, 0, 0, 0, 0, 0)
		return AwlSimMessage.toBytes(self, len(payload)) + payload

	@classmethod
	def fromBytes(cls, payload):
		try:
			getFlags, _, _, _, _, _, _, _ =\
				cls.plHdrStruct.unpack_from(payload, 0)
		except (ValueError, struct.error) as e:
			raise TransferError("GET_IDENTS: Invalid data format")
		return cls(getFlags)

class AwlSimMessage_IDENTS(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_IDENTS

	# Payload header struct:
	#	Number of AWL sources (32 bit)
	#	Number of symbol tables (32 bit)
	#	Number of hardware modules (32 bit)
	#	Number of library selections (32 bit)
	#	Number of FUP sources (32 bit)
	#	Number of KOP sources (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	plHdrStruct = struct.Struct(str(">16I"))

	# Payload module header struct:
	#	Number of parameters (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	plModStruct = struct.Struct(str(">4I"))

	# awlSources: List of AwlSource()s
	# symTabSources: List of SymTabSource()s
	# hwMods: List of HwmodDescriptor()s
	# libSelections: List of AwlLibEntrySelection()s
	def __init__(self, awlSources, symTabSources, hwMods, libSelections, fupSources, kopSources):
		self.awlSources = awlSources
		self.symTabSources = symTabSources
		self.hwMods = hwMods
		self.libSelections = libSelections
		self.fupSources = fupSources
		self.kopSources = kopSources

	def toBytes(self):
		payload = [ self.plHdrStruct.pack(len(self.awlSources),
						  len(self.symTabSources),
						  len(self.hwMods),
						  len(self.libSelections),
						  len(self.fupSources),
						  len(self.kopSources),
						  0, 0, 0, 0, 0,
						  0, 0, 0, 0, 0) ]
		def addSrcs(srcs):
			for src in srcs:
				payload.append(self.packString(src.name))
				payload.append(self.packString(src.filepath))
				payload.append(self.packBytes(src.identHash))
		addSrcs(self.awlSources)
		addSrcs(self.symTabSources)
		for hwmodDesc in self.hwMods:
			params = hwmodDesc.getParameters()
			payload.append(self.plModStruct.pack(len(params), 0, 0, 0))
			payload.append(self.packString(hwmodDesc.getModuleName()))
			for pName, pVal in dictItems(params):
				payload.append(self.packString(pName))
				payload.append(self.packString(pVal if isString(pVal) else ""))
		for libSel in self.libSelections:
			payload.append(AwlSimMessage_LIBSEL.packLibSelection(libSel))
		addSrcs(self.fupSources)
		addSrcs(self.kopSources)
		payload = b''.join(payload)
		return AwlSimMessage.toBytes(self, len(payload)) + payload

	@classmethod
	def fromBytes(cls, payload):
		try:
			awlSources = []
			symTabSources = []
			hwMods = []
			libSelections = []
			fupSources = []
			kopSources = []
			offset = 0
			nrAwl, nrSym, nrHw, nrLib, nrFup, nrKop,\
			_, _, _, _, _, _, _, _, _, _ = cls.plHdrStruct.unpack_from(
								payload, offset)
			offset += cls.plHdrStruct.size
			def unpackSrcs(srcClass, sourcesList, count, offset):
				for i in range(count):
					name, count = cls.unpackString(payload, offset)
					offset += count
					path, count = cls.unpackString(payload, offset)
					offset += count
					identHash, count = cls.unpackBytes(payload, offset)
					offset += count
					src = srcClass(name, path, None)
					src.identHash = identHash # Force hash
					sourcesList.append(src)
				return offset
			offset = unpackSrcs(AwlSource, awlSources, nrAwl, offset)
			offset = unpackSrcs(SymTabSource, symTabSources, nrSym, offset)
			for i in range(nrHw):
				nrParam, _, _, _ = cls.plModStruct.unpack_from(
						payload, offset)
				offset += cls.plModStruct.size
				modName, count = cls.unpackString(payload, offset)
				offset += count
				params = {}
				for i in range(nrParam):
					pName, count = cls.unpackString(payload, offset)
					offset += count
					pVal, count = cls.unpackString(payload, offset)
					offset += count
					params[pName] = pVal
				hwMods.append(HwmodDescriptor(modName, params))
			for i in range(nrLib):
				libSel, offset = AwlSimMessage_LIBSEL.unpackLibSelection(
						payload, offset)
				libSelections.append(libSel)
			offset = unpackSrcs(FupSource, fupSources, nrFup, offset)
			offset = unpackSrcs(KopSource, kopSources, nrKop, offset)
		except (ValueError, struct.error, AwlSimError) as e:
			raise TransferError("IDENTS: Invalid data format")
		return cls(awlSources = awlSources,
			   symTabSources = symTabSources,
			   hwMods = hwMods,
			   libSelections = libSelections,
			   fupSources = fupSources,
			   kopSources = kopSources)

class AwlSimMessage_GET_BLOCKINFO(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_GET_BLOCKINFO

	# Get-flags. Specify what information to get.
	EnumGen.start
	GET_OB_INFO		= EnumGen.bitmask # Get OB info
	GET_FC_INFO		= EnumGen.bitmask # Get FC info
	GET_FB_INFO		= EnumGen.bitmask # Get FB info
	GET_DB_INFO		= EnumGen.bitmask # Get DB info
	GET_UDT_INFO		= EnumGen.bitmask # Get UDT info
	EnumGen.end

	# Payload header struct:
	#	Get-flags (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	plHdrStruct = struct.Struct(str(">IIIIIIII"))

	def __init__(self, getFlags):
		self.getFlags = getFlags

	def toBytes(self):
		payload = self.plHdrStruct.pack(self.getFlags, 0, 0, 0, 0, 0, 0, 0)
		return AwlSimMessage.toBytes(self, len(payload)) + payload

	@classmethod
	def fromBytes(cls, payload):
		try:
			getFlags, _, _, _, _, _, _, _ =\
				cls.plHdrStruct.unpack_from(payload, 0)
		except (ValueError, struct.error) as e:
			raise TransferError("GET_BLOCKINFO: Invalid data format")
		return cls(getFlags)

class AwlSimMessage_BLOCKINFO(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_BLOCKINFO

	# Payload header struct:
	#	Number of block infos (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	plHdrStruct = struct.Struct(str(">IIII"))

	# Block info payload struct:
	#	BlockInfo.TYPE_... (32 bit)
	#	Block index (32 bit)
	#	reserved (32 bit)
	#	reserved (32 bit)
	#	ident hash bytes (length prefix, variable length)
	plBlockInfoStruct = struct.Struct(str(">IIII"))

	def __init__(self, blockInfos):
		self.blockInfos = blockInfos

	def toBytes(self):
		payload = [ self.plHdrStruct.pack(len(self.blockInfos), 0, 0, 0) ]
		for blockInfo in self.blockInfos:
			payload.append(self.plBlockInfoStruct.pack(
					blockInfo.blockIndex,
					blockInfo.blockType,
					0, 0))
			payload.append(self.packBytes(blockInfo.identHash))
		payload = b"".join(payload)
		return AwlSimMessage.toBytes(self, len(payload)) + payload

	@classmethod
	def fromBytes(cls, payload):
		try:
			blockInfos = []
			nrBlockInfos, _, _, _ = cls.plHdrStruct.unpack_from(payload, 0)
			offset = cls.plHdrStruct.size
			for i in range(nrBlockInfos):
				blockIndex, blockType, _, _ = \
					cls.plBlockInfoStruct.unpack_from(payload, offset)
				offset += cls.plBlockInfoStruct.size
				identHash, count = cls.unpackBytes(payload, offset)
				offset += count
				blockInfos.append(BlockInfo(
					blockType=blockType,
					blockIndex=blockIndex,
					identHash=identHash)
				)
		except (ValueError, struct.error) as e:
			raise TransferError("BLOCKINFO: Invalid data format")
		return cls(blockInfos = blockInfos)

class AwlSimMessageTransceiver(object):
	id2class = {
		AwlSimMessage.MSG_ID_REPLY		: AwlSimMessage_REPLY,
		AwlSimMessage.MSG_ID_EXCEPTION		: AwlSimMessage_EXCEPTION,
		AwlSimMessage.MSG_ID_MAINTREQ		: AwlSimMessage_MAINTREQ,
		AwlSimMessage.MSG_ID_PING		: AwlSimMessage_PING,
		AwlSimMessage.MSG_ID_PONG		: AwlSimMessage_PONG,
		AwlSimMessage.MSG_ID_RESET		: AwlSimMessage_RESET,
		AwlSimMessage.MSG_ID_SHUTDOWN		: AwlSimMessage_SHUTDOWN,
		AwlSimMessage.MSG_ID_GET_AWLSRC		: AwlSimMessage_GET_AWLSRC,
		AwlSimMessage.MSG_ID_AWLSRC		: AwlSimMessage_AWLSRC,
		AwlSimMessage.MSG_ID_GET_SYMTABSRC	: AwlSimMessage_GET_SYMTABSRC,
		AwlSimMessage.MSG_ID_SYMTABSRC		: AwlSimMessage_SYMTABSRC,
		AwlSimMessage.MSG_ID_HWMOD		: AwlSimMessage_HWMOD,
		AwlSimMessage.MSG_ID_LIBSEL		: AwlSimMessage_LIBSEL,
		AwlSimMessage.MSG_ID_GET_FUPSRC		: AwlSimMessage_GET_FUPSRC,
		AwlSimMessage.MSG_ID_FUPSRC		: AwlSimMessage_FUPSRC,
		AwlSimMessage.MSG_ID_GET_KOPSRC		: AwlSimMessage_GET_KOPSRC,
		AwlSimMessage.MSG_ID_KOPSRC		: AwlSimMessage_KOPSRC,
		AwlSimMessage.MSG_ID_BUILD		: AwlSimMessage_BUILD,
		AwlSimMessage.MSG_ID_REMOVESRC		: AwlSimMessage_REMOVESRC,
		AwlSimMessage.MSG_ID_REMOVEBLK		: AwlSimMessage_REMOVEBLK,
		AwlSimMessage.MSG_ID_GET_IDENTS		: AwlSimMessage_GET_IDENTS,
		AwlSimMessage.MSG_ID_IDENTS		: AwlSimMessage_IDENTS,
		AwlSimMessage.MSG_ID_GET_BLOCKINFO	: AwlSimMessage_GET_BLOCKINFO,
		AwlSimMessage.MSG_ID_BLOCKINFO		: AwlSimMessage_BLOCKINFO,
		AwlSimMessage.MSG_ID_GET_OPT		: AwlSimMessage_GET_OPT,
		AwlSimMessage.MSG_ID_OPT		: AwlSimMessage_OPT,
		AwlSimMessage.MSG_ID_GET_CPUSPECS	: AwlSimMessage_GET_CPUSPECS,
		AwlSimMessage.MSG_ID_CPUSPECS		: AwlSimMessage_CPUSPECS,
		AwlSimMessage.MSG_ID_GET_CPUCONF	: AwlSimMessage_GET_CPUCONF,
		AwlSimMessage.MSG_ID_CPUCONF		: AwlSimMessage_CPUCONF,
		AwlSimMessage.MSG_ID_GET_RUNSTATE	: AwlSimMessage_GET_RUNSTATE,
		AwlSimMessage.MSG_ID_RUNSTATE		: AwlSimMessage_RUNSTATE,
		AwlSimMessage.MSG_ID_GET_CPUDUMP	: AwlSimMessage_GET_CPUDUMP,
		AwlSimMessage.MSG_ID_CPUDUMP		: AwlSimMessage_CPUDUMP,
		AwlSimMessage.MSG_ID_REQ_MEMORY		: AwlSimMessage_REQ_MEMORY,
		AwlSimMessage.MSG_ID_MEMORY		: AwlSimMessage_MEMORY,
		AwlSimMessage.MSG_ID_GET_CPUSTATS	: AwlSimMessage_GET_CPUSTATS,
		AwlSimMessage.MSG_ID_CPUSTATS		: AwlSimMessage_CPUSTATS,
		AwlSimMessage.MSG_ID_INSNSTATE_CONFIG	: AwlSimMessage_INSNSTATE_CONFIG,
		AwlSimMessage.MSG_ID_INSNSTATE		: AwlSimMessage_INSNSTATE,
		AwlSimMessage.MSG_ID_MEAS_CONFIG	: AwlSimMessage_MEAS_CONFIG,
		AwlSimMessage.MSG_ID_MEAS		: AwlSimMessage_MEAS,
	}

	DEFAULT_TX_BUF_SIZE	= 1024 * 100
	DEFAULT_RX_BUF_SIZE	= 1024 * 100

	def __init__(self, sock, peerInfoString):
		self.sock = sock
		self.peerInfoString = peerInfoString
		self.__isTCP = sock.family in (socket.AF_INET, socket.AF_INET6) and\
			       sock.type == socket.SOCK_STREAM
		self.__haveCork = hasattr(socket, "TCP_CORK")
		self.__haveCork = False #XXX disabled

		self.__debugEnabled = Logging.getLogLevel() >= Logging.LOG_VERBOSE
		self.__debugTime = monotonic_time()
		self.__debugTx = 0
		self.__debugTxBlobs = 0
		self.__debugTxLen = 0
		self.__debugRx = 0
		self.__debugRxBlobs = 0
		self.__debugRxLen = 0

		# Transmit status
		self.txSeqCount = 0

		# Receive buffer
		self.__resetRxBuf()

		_SocketErrors = SocketErrors
		try:
			if isJython: #XXX Workaround
				self.sock.setblocking(True)
			self.__timeout = None
			self.sock.settimeout(self.__timeout)

			self.sock.setsockopt(socket.SOL_SOCKET,
					     socket.SO_OOBINLINE,
					     1)
			SO_PRIORITY = getattr(socket, "SO_PRIORITY",
					      12 if (osIsPosix and isPy2Compat) else None)
			if SO_PRIORITY is not None:
				self.sock.setsockopt(socket.SOL_SOCKET,
						     SO_PRIORITY,
						     6)
			self.setTxBufSize(self.DEFAULT_TX_BUF_SIZE)
			self.setRxBufSize(self.DEFAULT_RX_BUF_SIZE)
			if self.__isTCP:
				self.sock.setsockopt(socket.IPPROTO_TCP,
						     socket.TCP_NODELAY,
						     1)
		except _SocketErrors as e:
			self.shutdown()
			raise AwlSimError("Failed to initialize socket: %s" % str(e))

	def setTxBufSize(self, size):
		self.sock.setsockopt(socket.SOL_SOCKET,
				     socket.SO_SNDBUF,
				     size)

	def setRxBufSize(self, size):
		self.sock.setsockopt(socket.SOL_SOCKET,
				     socket.SO_RCVBUF,
				     size)

	def shutdown(self):
		if self.sock:
			with suppressAllExc:
				self.sock.setblocking(False)
			with suppressAllExc:
				if hasattr(self.sock, "shutdown"):
					self.sock.shutdown(socket.SHUT_RDWR)
			with suppressAllExc:
				self.sock.close()
			self.sock = None

	def txCork(self, cork = True):
		if self.__isTCP and self.__haveCork:
			self.sock.setsockopt(socket.IPPROTO_TCP,
					     socket.TCP_CORK,
					     1 if cork else 0)

	def __dump(self, prefix, timeDiff, nrMsg, nrBlobs, nrBytes):
		bytePerSec = nrBytes / timeDiff
		blobPerSec = nrBlobs / timeDiff
		msgPerSec = nrMsg / timeDiff
		printVerbose("%s:  %s msg/s  %s blobs/s  %s bytes/s" % (
			     prefix,
			     floatToHumanReadable(msgPerSec, binary=False),
			     floatToHumanReadable(blobPerSec, binary=False),
			     floatToHumanReadable(bytePerSec, binary=True)))

	def __dumpStats(self):
		now = monotonic_time()
		timeDiff = now - self.__debugTime
		if timeDiff >= 5.0:
			self.__debugTime = now
			self.__dump("TX", timeDiff, self.__debugTx,
				    self.__debugTxBlobs, self.__debugTxLen)
			self.__debugTx = self.__debugTxBlobs = self.__debugTxLen = 0
			self.__dump("RX", timeDiff, self.__debugRx,
				    self.__debugRxBlobs, self.__debugRxLen)
			self.__debugRx = self.__debugRxBlobs = self.__debugRxLen = 0

	def __accountTx(self, nrMsg, nrBlobs, dataLen):
		self.__debugTx += nrMsg
		self.__debugTxBlobs += nrBlobs
		self.__debugTxLen += dataLen
		self.__dumpStats()

	def __accountRx(self, nrMsg, nrBlobs, dataLen):
		self.__debugRx += nrMsg
		self.__debugRxBlobs += nrBlobs
		self.__debugRxLen += dataLen
		self.__dumpStats()

	def __setMsgTxSeq(self, msg):
		msg.seq = self.txSeqCount
		self.txSeqCount = (self.txSeqCount + 1) & 0xFFFF

	def send(self, msg, timeout=None):
		if timeout != self.__timeout:
			self.sock.settimeout(timeout)
			self.__timeout = timeout

		if not msg:
			return
		if isinstance(msg, list):
			dataList = []
			for oneMsg in msg:
				self.__setMsgTxSeq(oneMsg)
				dataList.append(oneMsg.toBytes())
			data = memoryview(b"".join(dataList))
			nrMsg = len(msg)
		else:
			self.__setMsgTxSeq(msg)
			data = memoryview(msg.toBytes())
			nrMsg = 1

		offset = 0
		dataLen = len(data)
		sock = self.sock
		_SocketErrors = SocketErrors
		while offset < dataLen:
			try:
				offset += sock.send(data[offset : ])
			except _SocketErrors as e:
				transferError = TransferError(None, e)
				if transferError.reason != TransferError.REASON_BLOCKING:
					raise transferError
		if self.__debugEnabled:
			self.__accountTx(nrMsg, 1, dataLen)

	def receive(self, timeout=0.0):
		if timeout != self.__timeout:
			self.sock.settimeout(timeout)
			self.__timeout = timeout

		_SocketErrors = SocketErrors
		hdrLen, rxByteCnt = AwlSimMessage.HDR_LENGTH, self.rxByteCnt
		if rxByteCnt < hdrLen:
			try:
				data = self.sock.recv(hdrLen - rxByteCnt)
			except _SocketErrors as e:
				transferError = TransferError(None, e)
				if transferError.reason == TransferError.REASON_BLOCKING:
					return None
				self.__resetRxBuf()
				raise transferError
			if not data:
				# The remote end closed the connection
				self.__resetRxBuf()
				raise TransferError(None, None,
						    TransferError.REASON_REMOTEDIED)
			self.rxBuffers.append(data)
			self.rxByteCnt = rxByteCnt = rxByteCnt + len(data)
			if rxByteCnt < hdrLen:
				return None
			try:
				magic, self.msgId, self.hdrFlags, self.seq,\
				self.replyToId, self.replyToSeq, _, _, _, _, self.payloadLen =\
					AwlSimMessage.hdrStruct.unpack(b"".join(self.rxBuffers))
				self.rxBuffers = [] # Discard raw header bytes.
			except struct.error as e:
				self.__resetRxBuf()
				raise AwlSimError("Received message with invalid "
					"header format.")
			if magic != AwlSimMessage.HDR_MAGIC:
				self.__resetRxBuf()
				raise AwlSimError("Received message with invalid "
					"magic value (was 0x%04X, expected 0x%04X)." %\
					(magic, AwlSimMessage.HDR_MAGIC))
			if self.payloadLen:
				return None
		msgLen = hdrLen + self.payloadLen
		if rxByteCnt < msgLen:
			try:
				data = self.sock.recv(msgLen - rxByteCnt)
			except _SocketErrors as e:
				transferError = TransferError(None, e)
				if transferError.reason == TransferError.REASON_BLOCKING:
					return None
				self.__resetRxBuf()
				raise transferError
			if not data:
				# The remote end closed the connection
				self.__resetRxBuf()
				raise TransferError(None, None,
						    TransferError.REASON_REMOTEDIED)
			self.rxBuffers.append(data)
			self.rxByteCnt = rxByteCnt = rxByteCnt + len(data)
			if rxByteCnt < msgLen:
				return None
		try:
			cls = self.id2class[self.msgId]
		except KeyError:
			self.__resetRxBuf()
			msgId = "No ID" if self.msgId is None else ("0x%04X" % self.msgId)
			raise AwlSimError("Received unknown message: %s" % msgId)
		msg = cls.fromBytes(b"".join(self.rxBuffers))
		msg.seq = self.seq
		msg.hdrFlags = self.hdrFlags
		msg.replyToId = self.replyToId
		msg.replyToSeq = self.replyToSeq
		self.__resetRxBuf()
		if self.__debugEnabled:
			self.__accountRx(1, 1, msgLen)
		return msg

	def __resetRxBuf(self):
		self.rxBuffers = []
		self.rxByteCnt = 0
		self.msgId = 0
		self.hdrFlags = 0
		self.seq = 0
		self.replyToId = 0
		self.replyToSeq = 0
		self.payloadLen = 0

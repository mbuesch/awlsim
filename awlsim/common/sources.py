# -*- coding: utf-8 -*-
#
# AWL simulator - source management
#
# Copyright 2014-2016 Michael Buesch <m@bues.ch>
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

from awlsim.common.refmanager import *
from awlsim.common.util import *

import base64, binascii
import hashlib


class GenericSource(object):
	SRCTYPE		= "<generic>"
	IDENT_HASH	= hashlib.sha256

	def __init__(self, name="", filepath="", sourceBytes=b""):
		self.name = name
		self.filepath = filepath
		self.sourceBytes = sourceBytes
		self.__identHash = None

	@property
	def name(self):
		return self.__name

	@name.setter
	def name(self, newName):
		self.__name = newName
		self.__identHash = None

	@property
	def filepath(self):
		return self.__filepath

	@filepath.setter
	def filepath(self, newFilepath):
		self.__filepath = newFilepath
		self.__identHash = None

	@property
	def sourceBytes(self):
		return self.__sourceBytes

	@sourceBytes.setter
	def sourceBytes(self, newSourceBytes):
		self.__sourceBytes = newSourceBytes
		self.__identHash = None

	@property
	def identHash(self):
		if not self.__identHash:
			# Calculate the ident hash
			h = self.IDENT_HASH(self.SRCTYPE.encode(
					"utf-8", "strict"))
			if self.name is not None:
				h.update(self.name.encode("utf-8", "ignore"))
			if self.filepath is not None:
				h.update(self.filepath.encode("utf-8", "ignore"))
			h.update(self.sourceBytes)
			self.__identHash = h.digest()
		return self.__identHash

	@identHash.setter
	def identHash(self, identHash):
		# Force the ident hash.
		self.__identHash = identHash

	@property
	def identHashStr(self):
		return bytesToHexStr(self.identHash)

	def dup(self):
		raise NotImplementedError

	def isFileBacked(self):
		return bool(self.filepath)

	def writeFileBacking(self):
		"Write the backing file, if any."
		if not self.isFileBacked():
			return
		awlFileWrite(self.filepath, self.sourceBytes, encoding="binary")

	def forceNonFileBacked(self, newName):
		"Convert this source to a non-file-backed source."
		if self.isFileBacked():
			self.filepath = ""
			self.name = newName

	def toBase64(self):
		return base64.b64encode(self.sourceBytes).decode("ascii")

	@classmethod
	def fromFile(cls, name, filepath):
		try:
			data = awlFileRead(filepath, encoding="binary")
		except AwlSimError as e:
			raise AwlSimError("Project: Could not read %s "
				"source file '%s':\n%s" %\
				(cls.SRCTYPE, filepath, str(e)))
		return cls(name, filepath, data)

	@classmethod
	def fromBase64(cls, name, b64):
		try:
			data = base64.b64decode(b64.encode("ascii"))
		except (TypeError, binascii.Error, UnicodeError) as e:
			raise AwlSimError("Project: %s source '%s' "
				"has invalid base64 encoding." %\
				(cls.SRCTYPE, name))
		return cls(name, None, data)

	def __eq__(self, other):
		return self.identHash == other.identHash

	def __ne__(self, other):
		return not self.__eq__(other)

	def __repr__(self):
		return "%s%s %s %s" % ("" if self.isFileBacked() else "project ",
				    self.SRCTYPE, self.name, self.identHashStr)

class AwlSource(GenericSource):
	SRCTYPE = "AWL/STL"

	def dup(self):
		return AwlSource(self.name, self.filepath,
				 self.sourceBytes[:])

class FupSource(GenericSource):
	SRCTYPE = "FUP/FBD"

	def dup(self):
		return FupSource(self.name, self.filepath,
				 self.sourceBytes[:])

class KopSource(GenericSource):
	SRCTYPE = "KOP/LAD"

	def dup(self):
		return KopSource(self.name, self.filepath,
				 self.sourceBytes[:])

class SymTabSource(GenericSource):
	SRCTYPE = "symbol table"

	def dup(self):
		return SymTabSource(self.name, self.filepath,
				    self.sourceBytes[:])

class SourceManager(ObjRefManager):
	"""Manages one source."""

	def __init__(self, source, container = None):
		"""source -> An AwlSource or SymTabSource instance.
		container -> A SourceContainer instance or None.
		"""
		super(SourceManager, self).__init__(
			name = lambda slf: "%s/%s" % (slf.source.name,
						      slf.source.identHashStr))
		self.source = source
		self.container = container
		if container:
			container.addManager(self)

	def allRefsDestroyed(self):
		"""Called, if all source references are destroyed.
		"""
		super(SourceManager, self).allRefsDestroyed()
		if self.container:
			self.container.removeManager(self)
		self.source = self.container = None

	def getBlocks(self):
		"""Get the compiled blocks that were created from the
		source managed here.
		"""
		return { ref.obj for ref in self.refs }

class SourceContainer(object):
	"""Container for source managers."""

	def __init__(self):
		self.__sourceManagers = []

	def addManager(self, sourceManager):
		"""Add a SourceManager instance to this container.
		"""
		self.__sourceManagers.append(sourceManager)
		sourceManager.container = self

	def removeManager(self, sourceManager):
		"""Remove a SourceManager instance from this container.
		"""
		try:
			self.__sourceManagers.remove(sourceManager)
		except ValueError as e:
			# The removed manager did not exist.
			# This might happen in rare conditions, for example if a
			# previous download/translation attempt failed.
			# Just ignore this.
			pass

	def removeByIdent(self, identHash):
		"""Remove a SourceManager by identHash.
		"""
		sourceManager = self.getSourceManagerByIdent(identHash)
		if sourceManager:
			self.removeManager(sourceManager)
			return True
		return False

	def clear(self):
		"""Remove all managers from the container.
		"""
		for sourceManager in self.__sourceManagers[:]:
			self.removeManager(sourceManager)

	def getSourceManagers(self):
		"""Return a list of source managers in this container.
		"""
		return self.__sourceManagers

	def getSources(self):
		"""Return a list of sources in this container.
		"""
		return [ m.source for m in self.getSourceManagers() ]

	def getSourceManagerByIdent(self, identHash):
		"""Get the source manager by source ident hash.
		Returns None, if no such source was found.
		"""
		for sourceManager in self.__sourceManagers:
			if sourceManager.source.identHash == identHash:
				return sourceManager
		return None

	def getSourceByIdent(self, identHash):
		"""Get the source by source ident hash.
		Returns None, if no such source was found.
		"""
		sourceManager = self.getSourceManagerByIdent(identHash)
		return sourceManager.source if sourceManager else None

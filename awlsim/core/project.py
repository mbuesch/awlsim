# -*- coding: utf-8 -*-
#
# AWL simulator - project
#
# Copyright 2014 Michael Buesch <m@bues.ch>
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

from awlsim.core.cpuspecs import *
from awlsim.core.util import *

import base64, binascii
import datetime
import os

if isPy2Compat:
	from ConfigParser import SafeConfigParser as _ConfigParser
	from ConfigParser import Error as _ConfigParserError
else:
	from configparser import ConfigParser as _ConfigParser
	from configparser import Error as _ConfigParserError


class GenericSource(object):
	SRCTYPE = "<generic>"

	def __init__(self, identifier, filepath="", sourceBytes=b""):
		assert(identifier)
		self.identifier = identifier
		self.filepath = filepath
		self.sourceBytes = sourceBytes

	def dup(self):
		raise NotImplementedError

	def isFileBacked(self):
		return bool(self.filepath)

	def toBase64(self):
		return base64.b64encode(self.sourceBytes).decode("ascii")

	@classmethod
	def fromFile(cls, identifier, filepath):
		try:
			data = awlFileRead(filepath, encoding="binary")
		except AwlSimError as e:
			raise AwlSimError("Project: Could not read %s "
				"source file '%s':\n%s" %\
				(cls.SRCTYPE, filepath, str(e)))
		return cls(identifier, filepath, data)

	@classmethod
	def fromBase64(cls, identifier, b64):
		try:
			data = base64.b64decode(b64, validate=True)
		except (TypeError, binascii.Error) as e:
			raise AwlSimError("Project: %s source '%s' "
				"has invalid base64 encoding." %\
				(cls.SRCTYPE, identifier))
		return cls(identifier, None, data)

	def __repr__(self):
		return "%s%s %s" % ("" if self.isFileBacked() else "project ",
				    self.SRCTYPE, self.identifier)

class AwlSource(GenericSource):
	SRCTYPE = "AWL/STL"

	def dup(self):
		return AwlSource(self.identifier, self.filepath,
				 self.sourceBytes[:])

class SymTabSource(GenericSource):
	SRCTYPE = "symbol table"

	def dup(self):
		return SymTabSource(self.identifier, self.filepath,
				    self.sourceBytes[:])

class Project(object):
	def __init__(self, projectFile, awlSources=[], symTabSources=[], cpuSpecs=None):
		self.projectFile = projectFile
		self.awlSources = awlSources
		self.symTabSources = symTabSources
		if not cpuSpecs:
			cpuSpecs = S7CPUSpecs()
		self.cpuSpecs = cpuSpecs

	@classmethod
	def dataIsProject(cls, data):
		magic = b"[AWLSIM_PROJECT]"
		if isIronPython and isinstance(data, str):
			try:
				"a".startswith(b"a") # Test for ipy byte conversion bug
			except TypeError:
				# XXX: Workaround for IronPython byte conversion bug
				printInfo("Applying workaround for IronPython byte conversion bug")
				magic = magic.decode("UTF-8")
		return data.lstrip().startswith(magic)

	@classmethod
	def fileIsProject(cls, filename):
		return cls.dataIsProject(awlFileRead(filename, encoding="binary"))

	@classmethod
	def fromText(cls, text, projectFile):
		if not cls.dataIsProject(text.encode("utf-8")):
			raise AwlSimError("Project file: The data is "\
				"not an awlsim project.")
		projectDir = os.path.dirname(projectFile)
		awlSources = []
		symTabSources = []
		cpuSpecs = S7CPUSpecs()
		try:
			p = _ConfigParser()
			p.readfp(StringIO(text), projectFile)
			version = p.getint("AWLSIM_PROJECT", "file_version")
			expectedVersion = 0
			if version != expectedVersion:
				raise AwlSimError("Project file: Unsupported version. "\
					"File version is %d, but expected %d." %\
					(version, expectedVersion))

			# CPU section
			for i in range(0xFFFF):
				option = "awl_file_%d" % i
				if not p.has_option("CPU", option):
					break
				path = p.get("CPU", option)
				src = AwlSource.fromFile(path, cls.__generic2path(path, projectDir))
				awlSources.append(src)
			for i in range(0xFFFF):
				option = "awl_%d" % i
				if not p.has_option("CPU", option):
					break
				awlBase64 = p.get("CPU", option)
				src = AwlSource.fromBase64("#%d" % i, awlBase64)
				awlSources.append(src)
			if p.has_option("CPU", "mnemonics"):
				mnemonics = p.getint("CPU", "mnemonics")
				cpuSpecs.setConfiguredMnemonics(mnemonics)
			if p.has_option("CPU", "nr_accus"):
				nrAccus = p.getint("CPU", "nr_accus")
				cpuSpecs.setNrAccus(nrAccus)

			# SYMBOLS section
			for i in range(0xFFFF):
				option = "sym_tab_file_%d" % i
				if not p.has_option("SYMBOLS", option):
					break
				path = p.get("SYMBOLS", option)
				src = SymTabSource.fromFile(path, cls.__generic2path(path, projectDir))
				symTabSources.append(src)
			for i in range(0xFFFF):
				option = "sym_tab_%d" % i
				if not p.has_option("SYMBOLS", option):
					break
				symTabBase64 = p.get("SYMBOLS", option)
				src = SymTabSource.fromBase64("#%d" % i, symTabBase64)
				symTabSources.append(src)

		except _ConfigParserError as e:
			raise AwlSimError("Project parser error: " + str(e))

		return cls(projectFile = projectFile,
			   awlSources = awlSources,
			   symTabSources = symTabSources,
			   cpuSpecs = cpuSpecs)

	@classmethod
	def fromFile(cls, filename):
		return cls.fromText(awlFileRead(filename, encoding="utf8"), filename)

	@classmethod
	def __path2generic(cls, path, relativeToDir):
		"""Generate an OS-independent string from a path."""
		if "\r" in path or "\n" in path:
			# The project file format cannot handle these
			raise AwlSimError("Project file: Path '%s' contains invalid "\
				"characters (line breaks)." % path)
		path = os.path.relpath(path, relativeToDir)
		if os.path.splitdrive(path)[0]:
			raise AwlSimError("Project file: Failed to strip drive letter. "\
				"Please make sure the project file, AWL code files and "\
				"symbol tables files all reside on the same drive.")
		path = path.replace(os.path.sep, "/")
		return path

	@classmethod
	def __generic2path(cls, path, relativeToDir):
		"""Generate a path from an OS-independent string."""
		path = path.replace("/", os.path.sep)
		path = os.path.join(relativeToDir, path)
		return path

	def toText(self, projectFile=None):
		if not projectFile:
			projectFile = self.projectFile
		projectDir = os.path.dirname(projectFile)

		lines = []
		lines.append("[AWLSIM_PROJECT]")
		lines.append("file_version=0")
		lines.append("date=%s" % str(datetime.datetime.utcnow()))
		lines.append("")

		lines.append("[CPU]")
		fileBackedSources = (src for src in self.awlSources if src.isFileBacked())
		embeddedSources = (src for src in self.awlSources if not src.isFileBacked())
		for i, awlSrc in enumerate(fileBackedSources):
			path = self.__path2generic(awlSrc.filepath, projectDir)
			lines.append("awl_file_%d=%s" % (i, path))
		for i, awlSrc in enumerate(embeddedSources):
			lines.append("awl_%d=%s" % (i, awlSrc.toBase64()))
		lines.append("mnemonics=%d" % self.cpuSpecs.getConfiguredMnemonics())
		lines.append("nr_accus=%d" % self.cpuSpecs.nrAccus)
		lines.append("")

		lines.append("[SYMBOLS]")
		fileBackedSources = (src for src in self.symTabSources if src.isFileBacked())
		embeddedSources = (src for src in self.symTabSources if not src.isFileBacked())
		for i, symSrc in enumerate(fileBackedSources):
			path = self.__path2generic(symSrc.filepath, projectDir)
			lines.append("sym_tab_file_%d=%s" % (i, path))
		for i, symSrc in enumerate(embeddedSources):
			lines.append("sym_tab_%d=%s" % (i, symSrc.toBase64()))

		return "\r\n".join(lines)

	def toFile(self, projectFile=None):
		if not projectFile:
			projectFile = self.projectFile
		if not projectFile:
			raise AwlSimError("Project file: Cannot generate project file. "
				"No file name specified.")
		text = self.toText(projectFile)
		awlFileWrite(projectFile, text, encoding="utf8")

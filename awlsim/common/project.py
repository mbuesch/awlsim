# -*- coding: utf-8 -*-
#
# AWL simulator - project
#
# Copyright 2014-2017 Michael Buesch <m@bues.ch>
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

from awlsim.common.xmlfactory import *
from awlsim.common.project_legacy import *
from awlsim.common.cpuspecs import * #+cimport
from awlsim.common.cpuconfig import *
from awlsim.common.sources import *
from awlsim.common.hwmod import *
from awlsim.common.util import *
from awlsim.common.exceptions import *
from awlsim.common.version import *

from awlsim.library.libselection import *

import datetime
import os
import sys


__all__ = [ "GuiSettings", "CoreLinkSettings", "HwmodSettings", "Project", ]


class GuiSettingsFactory(XmlFactory):
	def parser_open(self, tag=None):
		self.inEditor = False
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		guiSettings = self.guiSettings
		if not self.inEditor:
			if tag.name == "editor":
				autoIndent = tag.getAttrBool("autoindent", True)
				pasteAutoIndent = tag.getAttrBool("paste_autoindent", True)
				validation = tag.getAttrBool("validation", True)
				font = tag.getAttr("font", "")
				guiSettings.setEditorAutoIndentEn(autoIndent)
				guiSettings.setEditorPasteIndentEn(pasteAutoIndent)
				guiSettings.setEditorValidationEn(validation)
				if font:
					guiSettings.setEditorFont(font)
				self.inEditor = True
				return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if self.inEditor:
			if tag.name == "editor":
				self.inEditor = False
				return
		else:
			if tag.name == "gui":
				self.parser_finish()
				return
		XmlFactory.parser_endTag(self, tag)

	def composer_getTags(self):
		project, guiSettings = self.project, self.guiSettings

		childTags = []

		childTags.append(self.Tag(name="editor",
					  attrs={
			"autoindent"		: str(int(guiSettings.getEditorAutoIndentEn())),
			"paste_autoindent"	: str(int(guiSettings.getEditorPasteIndentEn())),
			"validation"		: str(int(guiSettings.getEditorValidationEn())),
			"font"			: str(guiSettings.getEditorFont()),
		}))

		tags = [
			self.Tag(name="gui",
				 comment="\nGraphical user interface configuration",
				 tags=childTags
			),
		]
		return tags

class CoreLinkSettingsFactory(XmlFactory):
	def parser_open(self, tag=None):
		self.inSpawnLocal = False
		self.inConnect = False
		self.inTunnel = False
		self.inSsh = False
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		linkSettings = self.linkSettings
		if self.inSpawnLocal:
			pass
		elif self.inConnect:
			pass
		elif self.inTunnel:
			if not self.inSsh:
				if tag.name == "ssh":
					user = tag.getAttr("user", CoreLinkSettings.DEFAULT_SSH_USER)
					port = tag.getAttrInt("port", CoreLinkSettings.DEFAULT_SSH_PORT)
					exe = tag.getAttr("executable", CoreLinkSettings.DEFAULT_SSH_EXE)
					linkSettings.setSSHUser(user)
					linkSettings.setSSHPort(port)
					linkSettings.setSSHExecutable(exe)
					self.inSsh = True
					return
		else:
			if tag.name == "spawn_local":
				enable = tag.getAttrBool("enable", True)
				portBegin = tag.getAttrInt("port_range_begin",
							   CoreLinkSettings.SPAWN_PORT_BASE)
				portEnd = tag.getAttrInt("port_range_end",
							 portBegin + CoreLinkSettings.SPAWN_PORT_NUM)
				interpreters = tag.getAttr("interpreters",
							   CoreLinkSettings.DEFAULT_INTERP)
				linkSettings.setSpawnLocalEn(enable)
				linkSettings.setSpawnLocalPortRange(range(portBegin, portEnd + 1))
				linkSettings.setSpawnLocalInterpreters(interpreters)
				self.inSpawnLocal = True
				return
			elif tag.name == "connect":
				host = tag.getAttr("host", CoreLinkSettings.DEFAULT_CONN_HOST)
				port = tag.getAttrInt("port", CoreLinkSettings.DEFAULT_CONN_PORT)
				timeout = tag.getAttrInt("timeout_ms", CoreLinkSettings.DEFAULT_CONN_TO)
				linkSettings.setConnectHost(host)
				linkSettings.setConnectPort(port)
				linkSettings.setConnectTimeoutMs(timeout)
				self.inConnect = True
				return
			elif tag.name == "tunnel":
				tunnelType = tag.getAttrInt("type", CoreLinkSettings.TUNNEL_NONE)
				localPort = tag.getAttrInt("local_port", CoreLinkSettings.TUNNEL_LOCPORT_AUTO)
				linkSettings.setTunnel(tunnelType)
				linkSettings.setTunnelLocalPort(localPort)
				self.inTunnel = True
				return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if self.inSpawnLocal:
			if tag.name == "spawn_local":
				self.inSpawnLocal = False
				return
		elif self.inConnect:
			if tag.name == "connect":
				self.inConnect = False
				return
		elif self.inTunnel:
			if self.inSsh:
				if tag.name == "ssh":
					self.inSsh = False
					return
			else:
				if tag.name == "tunnel":
					self.inTunnel = False
					return
		else:
			if tag.name == "core_link":
				self.parser_finish()
				return
		XmlFactory.parser_endTag(self, tag)

	def composer_getTags(self):
		project, linkSettings = self.project, self.linkSettings

		childTags = []

		childTags.append(self.Tag(name="spawn_local",
					  comment="\nLocally spawned core server",
					  attrs={
			"enable"		: str(int(linkSettings.getSpawnLocalEn())),
			"port_range_begin"	: str(int(linkSettings.getSpawnLocalPortRange()[0])),
			"port_range_end"	: str(int(linkSettings.getSpawnLocalPortRange()[-1])),
			"interpreters"		: str(linkSettings.getSpawnLocalInterpreters()),
		}))

		childTags.append(self.Tag(name="connect",
					  comment="\nRemote server connection",
					  attrs={
			"host"			: str(linkSettings.getConnectHost()),
			"port"			: str(int(linkSettings.getConnectPort())),
			"timeout_ms"		: str(int(linkSettings.getConnectTimeoutMs())),
		}))

		tunnelChildTags = [self.Tag(name="ssh",
					    attrs={
			"user"			: str(linkSettings.getSSHUser()),
			"port"			: str(int(linkSettings.getSSHPort())),
			"executable"		: str(linkSettings.getSSHExecutable()),
		})]
		childTags.append(self.Tag(name="tunnel",
					  comment="\nTransport tunnel",
					  tags=tunnelChildTags,
					  attrs={
			"type"			: str(int(linkSettings.getTunnel())),
			"local_port"		: str(int(linkSettings.getTunnelLocalPort())),
		}))

		tags = [
			self.Tag(name="core_link",
				 comment="\nCore server link configuration",
				 tags=childTags
			),
		]
		return tags

class HwmodSettingsFactory(XmlFactory):
	def parser_open(self, tag=None):
		hwmodSettings = self.hwmodSettings
		hwmodSettings.setLoadedModules([])
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		hwmodSettings = self.hwmodSettings
		if tag.name == "module":
			hwmodDesc = HwmodDescriptor("")
			self.parser_switchTo(hwmodDesc.factory(hwmodDesc=hwmodDesc))
			hwmodSettings.addLoadedModule(hwmodDesc)
			return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if tag.name == "hardware":
			self.parser_finish()
			return
		XmlFactory.parser_endTag(self, tag)

	def composer_getTags(self):
		project, hwmodSettings = self.project, self.hwmodSettings

		childTags = []

		loadedMods = sorted(hwmodSettings.getLoadedModules(),
				    key=lambda hwmodDesc: hwmodDesc.getModuleName())
		for hwmodDesc in loadedMods:
			childTags.extend(hwmodDesc.factory(
				hwmodDesc=hwmodDesc).composer_getTags())

		tags = [
			self.Tag(name="hardware",
				 comment="\nHardware modules configuration",
				 tags=childTags
			),
		]
		return tags

class ProjectFactory(XmlFactory):
	FILE_FORMAT_VERSION = 1

	def parser_open(self, tag=None):
		self.inProject = False
		self.inCpu = False
		self.inCpuSpecs = False
		self.inCpuConf = False
		self.inLangAwl = False
		self.inLangFup = False
		self.inLangKop = False
		self.inSyms = False
		self.inLibs = False
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		project = self.project
		if self.inProject:
			if self.inCpu:
				if tag.name == "specs":
					nrAccus = tag.getAttrInt("nr_accus",
							S7CPUSpecs.DEFAULT_NR_ACCUS)
					nrTimers = tag.getAttrInt("nr_timers",
							S7CPUSpecs.DEFAULT_NR_TIMERS)
					nrCounters = tag.getAttrInt("nr_counters",
							S7CPUSpecs.DEFAULT_NR_COUNTERS)
					nrFlags = tag.getAttrInt("nr_flags",
							S7CPUSpecs.DEFAULT_NR_FLAGS)
					nrInputs = tag.getAttrInt("nr_inputs",
							S7CPUSpecs.DEFAULT_NR_INPUTS)
					nrOutputs = tag.getAttrInt("nr_outputs",
							S7CPUSpecs.DEFAULT_NR_OUTPUTS)
					nrLocalbytes = tag.getAttrInt("nr_localbytes",
							S7CPUSpecs.DEFAULT_NR_LOCALBYTES)
					specs = project.getCpuSpecs()
					specs.setNrAccus(nrAccus)
					specs.setNrTimers(nrTimers)
					specs.setNrCounters(nrCounters)
					specs.setNrFlags(nrFlags)
					specs.setNrInputs(nrInputs)
					specs.setNrOutputs(nrOutputs)
					specs.setNrLocalbytes(nrLocalbytes)
					self.inCpuSpecs = True
					return
				elif tag.name == "config":
					clockMem = tag.getAttrInt("clock_memory_byte",
								  S7CPUConfig.DEFAULT_CLOCKMEM)
					obStartEn = tag.getAttrBool("ob_startinfo_enable", False)
					mnemonics = tag.getAttrInt("mnemonics",
								   S7CPUConfig.DEFAULT_MNEMONICS)
					extInsnsEn = tag.getAttrBool("ext_insns_enable", False)
					conf = project.getCpuConf()
					conf.setClockMemByte(clockMem)
					conf.setConfiguredMnemonics(mnemonics)
					project.setObTempPresetsEn(obStartEn)
					project.setExtInsnsEn(extInsnsEn)
					self.inCpuConf = True
					return
			elif self.inLangAwl:
				if tag.name == "source":
					source = AwlSource()
					self.parser_switchTo(source.factory(project=project,
									    source=source))
					project.addAwlSource(source)
					return
			elif self.inLangFup:
				if tag.name == "source":
					source = FupSource()
					self.parser_switchTo(source.factory(project=project,
									    source=source))
					project.addFupSource(source)
					return
			elif self.inLangKop:
				if tag.name == "source":
					source = KopSource()
					self.parser_switchTo(source.factory(project=project,
									    source=source))

					project.addKopSource(source)
					return
			elif self.inSyms:
				if tag.name == "source":
					source = SymTabSource()
					self.parser_switchTo(source.factory(project=project,
									    source=source))
					project.addSymTabSource(source)
					return
			elif self.inLibs:
				if tag.name == "lib_selection":
					libSel = AwlLibEntrySelection()
					self.parser_switchTo(libSel.factory(project=project,
									    libSel=libSel))
					project.addLibSelection(libSel)
					return
			else:
				if tag.name == "cpu":
					self.inCpu = True
					return
				elif tag.name == "language_awl":
					project.setAwlSources([])
					self.inLangAwl = True
					return
				elif tag.name == "language_fup":
					project.setFupSources([])
					self.inLangFup = True
					return
				elif tag.name == "language_kop":
					project.setKopSources([])
					self.inLangKop = True
					return
				elif tag.name == "symbols":
					project.setSymTabSources([])
					self.inSyms = True
					return
				elif tag.name == "libraries":
					project.setLibSelections([])
					self.inLibs = True
					return
				elif tag.name == "core_link":
					linkSettings = project.getCoreLinkSettings()
					self.parser_switchTo(linkSettings.factory(linkSettings=linkSettings))
					return
				elif tag.name == "hardware":
					hwmodSettings = project.getHwmodSettings()
					self.parser_switchTo(hwmodSettings.factory(hwmodSettings=hwmodSettings))
					return
				elif tag.name == "gui":
					guiSettings = project.getGuiSettings()
					self.parser_switchTo(guiSettings.factory(guiSettings=guiSettings))
					return
		else:
			if tag.name == "awlsim_project":
				version = tag.getAttrInt("format_version")
				if version != self.FILE_FORMAT_VERSION:
					raise self.Error("Unsupported .awlpro format version. "
						"Got %d, but expected %d." % (
						version, self.FILE_FORMAT_VERSION))
				createDate = tag.getAttr("date_create", None)
				modifyDate = tag.getAttr("date_modify", None)
				try:
					if createDate:
						createDate = datetime.datetime.strptime(
							createDate, project.DATETIME_FMT)
						project.setCreateDate(createDate)
				except (ValueError, TypeError) as e:
					pass
				try:
					if modifyDate:
						modifyDate = datetime.datetime.strptime(
							modifyDate, project.DATETIME_FMT)
						project.setModifyDate(modifyDate)
				except (ValueError, TypeError) as e:
					pass
				self.inProject = True
				return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if self.inProject:
			if self.inCpu:
				if self.inCpuSpecs:
					if tag.name == "specs":
						self.inCpuSpecs = False
						return
				elif self.inCpuConf:
					if tag.name == "config":
						self.inCpuConf = False
						return
				else:
					if tag.name == "cpu":
						self.inCpu = False
						return
			elif self.inLangAwl:
				if tag.name == "language_awl":
					self.inLangAwl = False
					return
			elif self.inLangFup:
				if tag.name == "language_fup":
					self.inLangFup = False
					return
			elif self.inLangKop:
				if tag.name == "language_kop":
					self.inLangKop = False
					return
			elif self.inSyms:
				if tag.name == "symbols":
					self.inSyms = False
					return
			elif self.inLibs:
				if tag.name == "libraries":
					self.inLibs = False
					return
			else:
				if tag.name == "awlsim_project":
					self.inProject = False
					self.parser_finish()
					return
		XmlFactory.parser_endTag(self, tag)

	def composer_getTags(self):
		project = self.project
		specs = project.getCpuSpecs()
		conf = project.getCpuConf()

		childTags = []

		cpuChildTags = [
			self.Tag(name="specs",
				 comment="\nCPU core feature specification",
				 attrs={
					"nr_accus"		: str(int(specs.nrAccus)),
					"nr_timers"		: str(int(specs.nrTimers)),
					"nr_counters"		: str(int(specs.nrCounters)),
					"nr_flags"		: str(int(specs.nrFlags)),
					"nr_inputs"		: str(int(specs.nrInputs)),
					"nr_outputs"		: str(int(specs.nrOutputs)),
					"nr_localbytes"		: str(int(specs.nrLocalbytes)),
				 }),
			self.Tag(name="config",
				 comment="\nCPU core configuration",
				 attrs={
					"ob_startinfo_enable"	: str(int(project.getObTempPresetsEn())),
					"ext_insns_enable"	: str(int(project.getExtInsnsEn())),
					"clock_memory_byte"	: str(int(conf.clockMemByte)),
					"mnemonics"		: str(int(conf.getConfiguredMnemonics())),
				 })
		]
		childTags.append(
			self.Tag(name="cpu",
				 comment="\nCPU core configuration",
				 tags=cpuChildTags
		))

		awlChildTags = []
		for awlSrc in project.getAwlSources():
			awlChildTags.extend(awlSrc.factory(project=project,
							   source=awlSrc).composer_getTags())
		childTags.append(
			self.Tag(name="language_awl",
				 comment="\nAWL/STL language configuration",
				 tags=awlChildTags
		))

		fupChildTags = []
		for fupSrc in project.getFupSources():
			fupChildTags.extend(fupSrc.factory(project=project,
							   source=fupSrc).composer_getTags())
		childTags.append(
			self.Tag(name="language_fup",
				 comment="\nFUP/FBD language configuration",
				 tags=fupChildTags
		))

		kopChildTags = []
		for kopSrc in project.getKopSources():
			kopChildTags.extend(kopSrc.factory(project=project,
							   source=kopSrc).composer_getTags())
		childTags.append(
			self.Tag(name="language_kop",
				 comment="\nKOP/LAD language configuration",
				 tags=kopChildTags
		))

		symsChildTags = []
		for symTabSrc in project.getSymTabSources():
			symsChildTags.extend(symTabSrc.factory(project=project,
							       source=symTabSrc).composer_getTags())
		childTags.append(
			self.Tag(name="symbols",
				 comment="\nSymbol table configuration",
				 tags=symsChildTags
		))

		libsChildTags = []
		for libSel in project.getLibSelections():
			libsChildTags.extend(libSel.factory(project=project,
							    libSel=libSel).composer_getTags())
		childTags.append(
			self.Tag(name="libraries",
				 comment="\nStandard library selections",
				 tags=libsChildTags
		))

		linkSettings = project.getCoreLinkSettings()
		childTags.extend(linkSettings.factory(project=project,
						      linkSettings=linkSettings).composer_getTags())

		hwmodSettings = project.getHwmodSettings()
		childTags.extend(hwmodSettings.factory(project=project,
						       hwmodSettings=hwmodSettings).composer_getTags())

		guiSettings = project.getGuiSettings()
		childTags.extend(guiSettings.factory(project=project,
						     guiSettings=guiSettings).composer_getTags())

		tags = [
			self.Tag(name="awlsim_project",
				 comment="Awlsim project file generated by awlsim-%s" % VERSION_STRING,
				 attrs={
					"format_version": str(self.FILE_FORMAT_VERSION),
					"date_create"	: str(project.getCreateDate().strftime(
							      project.DATETIME_FMT)),
					"date_modify"	: str(project.getModifyDate().strftime(
							      project.DATETIME_FMT)),
				 },
				 tags=childTags),
		]

		return tags

class GuiSettings(object):
	factory	= GuiSettingsFactory

	def __init__(self,
		     editorAutoIndentEn=True,
		     editorPasteIndentEn=True,
		     editorValidationEn=True,
		     editorFont=""):
		self.setEditorAutoIndentEn(editorAutoIndentEn)
		self.setEditorPasteIndentEn(editorPasteIndentEn)
		self.setEditorValidationEn(editorValidationEn)
		self.setEditorFont(editorFont)

	def setEditorAutoIndentEn(self, editorAutoIndentEn):
		self.editorAutoIndentEn = bool(editorAutoIndentEn)

	def getEditorAutoIndentEn(self):
		return self.editorAutoIndentEn

	def setEditorPasteIndentEn(self, editorPasteIndentEn):
		self.editorPasteIndentEn = bool(editorPasteIndentEn)

	def getEditorPasteIndentEn(self):
		return self.editorPasteIndentEn

	def setEditorValidationEn(self, editorValidationEn):
		self.editorValidationEn = bool(editorValidationEn)

	def getEditorValidationEn(self):
		return self.editorValidationEn

	def setEditorFont(self, editorFont):
		self.editorFont = editorFont

	def getEditorFont(self):
		return self.editorFont

class CoreLinkSettings(object):
	factory			= CoreLinkSettingsFactory

	DEFAULT_INTERPRETERS	= "pypy3; pypy; $CURRENT; python3; python2; python; py"
	DEFAULT_INTERP		= "$DEFAULT"

	SPAWN_PORT_BASE		= 4151 + 32
	SPAWN_PORT_NUM		= 4095

	DEFAULT_CONN_HOST	= "localhost"
	DEFAULT_CONN_PORT	= 4151
	DEFAULT_CONN_TO		= 3000

	TUNNEL_NONE		= 0
	TUNNEL_SSH		= 1

	TUNNEL_LOCPORT_AUTO	= -1

	DEFAULT_SSH_USER	= "pi"
	DEFAULT_SSH_PORT	= 22
	DEFAULT_SSH_EXE		= "ssh"

	def __init__(self,
		     spawnLocalEn=True,
		     spawnLocalPortRange=range(SPAWN_PORT_BASE,
					       SPAWN_PORT_BASE + SPAWN_PORT_NUM + 1),
		     spawnLocalInterpreters=DEFAULT_INTERP,
		     connectHost=DEFAULT_CONN_HOST,
		     connectPort=DEFAULT_CONN_PORT,
		     connectTimeoutMs=DEFAULT_CONN_TO,
		     tunnel=TUNNEL_NONE,
		     tunnelLocalPort=TUNNEL_LOCPORT_AUTO,
		     sshUser=DEFAULT_SSH_USER,
		     sshPort=DEFAULT_SSH_PORT,
		     sshExecutable=DEFAULT_SSH_EXE):
		self.setSpawnLocalEn(spawnLocalEn)
		self.setSpawnLocalPortRange(spawnLocalPortRange)
		self.setSpawnLocalInterpreters(spawnLocalInterpreters),
		self.setConnectHost(connectHost)
		self.setConnectPort(connectPort)
		self.setConnectTimeoutMs(connectTimeoutMs)
		self.setTunnel(tunnel)
		self.setTunnelLocalPort(tunnelLocalPort)
		self.setSSHUser(sshUser)
		self.setSSHPort(sshPort)
		self.setSSHExecutable(sshExecutable)

	def setSpawnLocalEn(self, spawnLocalEn):
		self.spawnLocalEn = bool(spawnLocalEn)

	def getSpawnLocalEn(self):
		return self.spawnLocalEn

	def setSpawnLocalPortRange(self, spawnLocalPortRange):
		self.spawnLocalPortRange = spawnLocalPortRange

	def getSpawnLocalPortRange(self):
		return self.spawnLocalPortRange

	def setSpawnLocalInterpreters(self, spawnLocalInterpreters):
		self.spawnLocalInterpreters = spawnLocalInterpreters

	def getSpawnLocalInterpreters(self):
		return self.spawnLocalInterpreters

	def __expandInterpStr(self, interpStr):
		ret = []
		for inter in interpStr.split(';'):
			if inter.strip() == "$DEFAULT":
				inter = self.__expandInterpStr(self.DEFAULT_INTERPRETERS)
			elif inter.strip() == "$CURRENT":
				inter = sys.executable
			ret.append(inter)
		return ";".join(ret)

	def getSpawnLocalInterpreterList(self, replace=True):
		interpStr = self.getSpawnLocalInterpreters()
		if replace:
			interpStr = self.__expandInterpStr(interpStr)
		return [ i.strip() for i in interpStr.split(';') ]

	def setConnectHost(self, connectHost):
		self.connectHost = connectHost

	def getConnectHost(self):
		return self.connectHost

	def setConnectPort(self, connectPort):
		self.connectPort = connectPort

	def getConnectPort(self):
		return self.connectPort

	def setConnectTimeoutMs(self, connectTimeoutMs):
		self.connectTimeoutMs = connectTimeoutMs

	def getConnectTimeoutMs(self):
		return self.connectTimeoutMs

	def setTunnel(self, tunnel):
		self.tunnel = tunnel

	def getTunnel(self):
		return self.tunnel

	def setTunnelLocalPort(self, tunnelLocalPort):
		self.tunnelLocalPort = tunnelLocalPort

	def getTunnelLocalPort(self):
		return self.tunnelLocalPort

	def setSSHUser(self, sshUser):
		self.sshUser = sshUser

	def getSSHUser(self):
		return self.sshUser

	def setSSHPort(self, sshPort):
		self.sshPort = sshPort

	def getSSHPort(self):
		return self.sshPort

	def setSSHExecutable(self, sshExecutable):
		self.sshExecutable = sshExecutable

	def getSSHExecutable(self):
		return self.sshExecutable

class HwmodSettings(object):
	factory	= HwmodSettingsFactory

	def __init__(self,
		     loadedModules=None):
		self.setLoadedModules(loadedModules)

	def setLoadedModules(self, loadedModules):
		self.loadedModules = loadedModules or []

	def addLoadedModule(self, modDesc):
		self.loadedModules.append(modDesc)

	def getLoadedModules(self):
		return self.loadedModules

class Project(object):
	"""Awlsim project.
	This is the in-memory representation of an .awlpro file.
	"""

	factory		= ProjectFactory

	ENCODING	= XmlFactory.XML_ENCODING
	DATETIME_FMT	= "%Y-%m-%d %H:%M:%S.%f"

	EnumGen.start
	TYPE_UNKNOWN	= EnumGen.item # unknown format
	TYPE_V0		= EnumGen.item # legacy INI-format
	TYPE_V1		= EnumGen.item # XML-format
	EnumGen.end

	def __init__(self, projectFile,
		     createDate=None,
		     modifyDate=None,
		     awlSources=None,
		     fupSources=None,
		     kopSources=None,
		     symTabSources=None,
		     libSelections=None,
		     cpuSpecs=None,
		     cpuConf=None,
		     obTempPresetsEn=False,
		     extInsnsEn=False,
		     guiSettings=None,
		     coreLinkSettings=None,
		     hwmodSettings=None):
		self.setProjectFile(projectFile)
		self.setCreateDate(createDate)
		self.setModifyDate(modifyDate)
		self.setAwlSources(awlSources)
		self.setFupSources(fupSources)
		self.setKopSources(kopSources)
		self.setSymTabSources(symTabSources)
		self.setLibSelections(libSelections)
		self.setCpuSpecs(cpuSpecs)
		self.setCpuConf(cpuConf)
		self.setObTempPresetsEn(obTempPresetsEn)
		self.setExtInsnsEn(extInsnsEn)
		self.setGuiSettings(guiSettings)
		self.setCoreLinkSettings(coreLinkSettings)
		self.setHwmodSettings(hwmodSettings)

	def clear(self):
		self.setProjectFile(None)
		self.setCreateDate(None)
		self.setModifyDate(None)
		self.setAwlSources(None)
		self.setFupSources(None)
		self.setKopSources(None)
		self.setSymTabSources(None)
		self.setLibSelections(None)
		self.setCpuSpecs(None)
		self.setObTempPresetsEn(False)
		self.setExtInsnsEn(False)
		self.setGuiSettings(None)
		self.setCoreLinkSettings(None)
		self.setHwmodSettings(None)

	def setProjectFile(self, filename):
		self.projectFile = filename

	def getProjectFile(self):
		return self.projectFile

	def setCreateDate(self, createDate):
		if createDate is None:
			createDate = datetime.datetime.utcnow()
		self.createDate = createDate

	def getCreateDate(self):
		return self.createDate

	def setModifyDate(self, modifyDate):
		if modifyDate is None:
			modifyDate = self.getCreateDate()
		if modifyDate is None:
			modifyDate = datetime.datetime.utcnow()
		self.modifyDate = modifyDate

	def getModifyDate(self):
		return self.modifyDate

	def setAwlSources(self, awlSources):
		self.awlSources = awlSources or []

	def addAwlSource(self, source):
		self.awlSources.append(source)

	def getAwlSources(self):
		return self.awlSources

	def setFupSources(self, fupSources):
		self.fupSources = fupSources or []

	def addFupSource(self, source):
		self.fupSources.append(source)

	def getFupSources(self):
		return self.fupSources

	def setKopSources(self, kopSources):
		self.kopSources = kopSources or []

	def addKopSource(self, source):
		self.kopSources.append(source)

	def getKopSources(self):
		return self.kopSources

	def setSymTabSources(self, symTabSources):
		self.symTabSources = symTabSources or []

	def addSymTabSource(self, source):
		self.symTabSources.append(source)

	def getSymTabSources(self):
		return self.symTabSources

	def setLibSelections(self, libSelections):
		self.libSelections = libSelections or []

	def addLibSelection(self, libSelection):
		self.libSelections.append(libSelection)

	def getLibSelections(self):
		return self.libSelections

	def setCpuSpecs(self, cpuSpecs):
		self.cpuSpecs = cpuSpecs or S7CPUSpecs()

	def getCpuSpecs(self):
		return self.cpuSpecs

	def setCpuConf(self, cpuConf):
		self.cpuConf = cpuConf or S7CPUConfig()

	def getCpuConf(self):
		return self.cpuConf

	def setObTempPresetsEn(self, obTempPresetsEn):
		self.obTempPresetsEn = bool(obTempPresetsEn)

	def getObTempPresetsEn(self):
		return self.obTempPresetsEn

	def setExtInsnsEn(self, extInsnsEn):
		self.extInsnsEn = bool(extInsnsEn)

	def getExtInsnsEn(self):
		return self.extInsnsEn

	def setGuiSettings(self, guiSettings):
		self.guiSettings = guiSettings or GuiSettings()

	def getGuiSettings(self):
		return self.guiSettings

	def setCoreLinkSettings(self, coreLinkSettings):
		self.coreLinkSettings = coreLinkSettings or CoreLinkSettings()

	def getCoreLinkSettings(self):
		return self.coreLinkSettings

	def setHwmodSettings(self, hwmodSettings):
		self.hwmodSettings = hwmodSettings or HwmodSettings()

	def getHwmodSettings(self):
		return self.hwmodSettings

	@classmethod
	def detectType(cls, dataBytes):
		try:
			dataText = dataBytes.decode(cls.ENCODING)
			dataLines = dataText.splitlines()
			magic_v0 = "[AWLSIM_PROJECT]"
			magic_v1 = "<awlsim_project"
			if dataText.lstrip().startswith(magic_v0):
				return cls.TYPE_V0
			if any(dataLine.startswith(magic_v1)
			       for dataLine in dataLines):
				return cls.TYPE_V1
		except UnicodeError as e:
			pass
		return cls.TYPE_UNKNOWN

	@classmethod
	def detectFileType(cls, filename):
		return cls.detectType(safeFileRead(filename))

	@classmethod
	def dataIsProject(cls, dataBytes):
		return cls.detectType(dataBytes) != cls.TYPE_UNKNOWN

	@classmethod
	def fileIsProject(cls, filename):
		return cls.detectFileType(filename) != cls.TYPE_UNKNOWN

	@classmethod
	def fromText(cls, text, projectFile):
		textBytes = text.encode(cls.ENCODING)
		projectType = cls.detectType(textBytes)
		if projectType == cls.TYPE_V0:
			return LegacyProjectParser.parse(cls, text, projectFile)
		if projectType != cls.TYPE_V1:
			raise AwlSimError("Project file: The data is "\
				"not an awlsim project.")

		project = cls(projectFile)
		project.projectDir = os.path.dirname(projectFile)

		try:
			factory = cls.factory(project=project)
			factory.parse(textBytes)
		except cls.factory.Error as e:
			raise AwlSimError("Project file: Failed to parse "
				"project XML data: %s" % str(e))

		project.projectDir = None
		return project

	@classmethod
	def fromFile(cls, filename):
		try:
			return cls.fromText(safeFileRead(filename).decode(cls.ENCODING), filename)
		except UnicodeError as e:
			raise AwlSimError("Project file: Failed to %s decode "
				"project file '%s': %s" % (
				cls.ENCODING, filename, str(e)))

	@classmethod
	def fromProjectOrRawAwlFile(cls, filename):
		"""Read a project (.awlpro) or raw AWL file (.awl)
		and return a Project()."""

		if Project.fileIsProject(filename):
			project = Project.fromFile(filename)
		else:
			# Make a fake project
			awlSrc = AwlSource.fromFile(name=filename,
						    filepath=filename,
						    compatReEncode=True)
			project = Project(projectFile = None,
					  awlSources = [ awlSrc, ])
		return project

	def toText(self, projectFile=None):
		if not projectFile:
			projectFile = self.projectFile
		self.projectDir = os.path.dirname(projectFile)

		self.setModifyDate(datetime.datetime.utcnow())

		try:
			factory = self.factory(project=self)
			xmlBytes = factory.compose(attrLineBreak=True)
			xmlText = xmlBytes.decode(factory.XML_ENCODING)
		except self.factory.Error as e:
			raise AwlSimError("Project file: Failed to compose XML: "
				"%s" % str(e))

		self.projectDir = None
		return xmlText

	def toFile(self, projectFile=None):
		if not projectFile:
			projectFile = self.projectFile
		if not projectFile:
			raise AwlSimError("Project file: Cannot generate project file. "
				"No file name specified.")
		text = self.toText(projectFile)
		try:
			data = text.encode(self.ENCODING)
		except UnicodeError as e:
			raise AwlSimError("Project file: Failed to %s encode "
				"project file '%s': %s" % (
				self.ENCODING, projectFile, str(e)))
		safeFileWrite(projectFile, data)
		for awlSrc in self.awlSources:
			awlSrc.writeFileBacking(compatReEncode=True)
		for symSrc in self.symTabSources:
			symSrc.writeFileBacking(compatReEncode=True)

	def __repr__(self):
		if self.projectFile:
			return 'Project("%s")' % self.projectFile
		return "Project(None)"

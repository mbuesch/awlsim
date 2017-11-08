# -*- coding: utf-8 -*-
#
# AWL simulator - AWL optimizer
#
# Copyright 2017 Michael Buesch <m@bues.ch>
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

from awlsim.common.exceptions import *
from awlsim.common.util import *
from awlsim.common.xmlfactory import *

from awlsim.awloptimizer.base import *
from awlsim.awloptimizer.opt_biefwd import *
from awlsim.awloptimizer.opt_lblrem import *
from awlsim.awloptimizer.opt_noprem import *

import functools


__all__ = [
	"AwlOptimizer",
	"AwlOptimizerSettings",
	"AwlOptimizerSettingsContainer",
]


class AwlOptimizer(object):
	"""AWL/STL program optimizer.
	"""

	ALL_OPTIMIZERS = (
		AwlOptimizer_BIEForward,
		AwlOptimizer_LabelRemove,
		AwlOptimizer_NopRemove,
	)

	def __init__(self, settingsContainer=None):
		self.settingsContainer = settingsContainer or AwlOptimizerSettingsContainer()
		self.infoStr = ""

	def __sortOptimizerClasses(self, optClasses):
		def cmpFunc(optClass0, optClass1):
			if optClass0.NAME == optClass1.NAME:
				return 0
			before = (optClass0.NAME in optClass1.AFTER or\
				  optClass1.NAME in optClass0.BEFORE)
			after = (optClass1.NAME in optClass0.AFTER or\
				 optClass0.NAME in optClass1.BEFORE)
			if before and after:
				raise AwlSimError("AwlOptimizer: Ambiguous "
					"dependency between '%s' and '%s'." % (
					optClass0.NAME, optClass1.NAME))
			if before:
				return -1 # optClass0 before optClass1
			if after:
				return 1 # optClass1 before optClass0
			return 0
		return sorted(optClasses,
			      key=functools.cmp_to_key(cmpFunc))

	def __getOptimizerClasses(self, currentStage):
		optClasses = [ optClass for optClass in self.ALL_OPTIMIZERS\
			       if (currentStage in optClass.STAGES and\
				   self.settingsContainer.isEnabled(optClass.NAME)) ]
		return self.__sortOptimizerClasses(optClasses)

	def __runOptimizers(self, currentStage, insns):
		printDebug("AwlOptimizer: Running STAGE %d%s..." % (
			(currentStage + 1),
			(" for '%s'" % self.infoStr) if self.infoStr else ""))
		for optClass in self.__getOptimizerClasses(currentStage):
			printDebug("AwlOptimizer: Running optimizer '%s'..." % (
				optClass.NAME))
			insns = optClass(optimizer=self).run(insns=insns)
		return insns

	def __optimize_Stage1(self, insns):
		return self.__runOptimizers(AwlOptimizer_Base.STAGE1, insns)

	def __optimize_Stage2(self, insns):
		return self.__runOptimizers(AwlOptimizer_Base.STAGE2, insns)

	def __optimize_Stage3(self, insns):
		return self.__runOptimizers(AwlOptimizer_Base.STAGE3, insns)

	def optimizeInsns(self, insns, infoStr=""):
		"""Optimize a list of AwlInsn_xxx instances.
		insns: The list of instructions to optimize.
		Returns the optimized list of instructions.
		"""
		if self.settingsContainer.globalEnable:
			self.infoStr = infoStr
			insns = self.__optimize_Stage1(insns)
			insns = self.__optimize_Stage2(insns)
			insns = self.__optimize_Stage3(insns)
		return insns

	def getEnableStr(self):
		return ", ".join(
			optClass.NAME for optClass in self.ALL_OPTIMIZERS
			if self.settingsContainer.isEnabled(optClass.NAME)
		)

class AwlOptimizerSettingsContainer_factory(XmlFactory):
	def parser_open(self, tag):
		assert(tag)
		container = self.settingsContainer

		self.inOptimizer = False
		self.settings = None

		globalEnable = tag.getAttrBool("enabled", True)
		allEnable = tag.getAttrBool("all", True)
		optType = tag.getAttr("type")
		if optType != "awl":
			raise self.Error("Unknown optimizer type '%s' "
				"settings found." % optType)

		container.clear()
		container.globalEnable = globalEnable
		container.allEnable = allEnable

		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		container = self.settingsContainer

		if tag.name == "optimizer":
			self.inOptimizer = True
			name = tag.getAttr("name")
			enabled = tag.getAttrBool("enabled", True)
			self.settings = AwlOptimizerSettings(
				name=name,
				enabled=enabled)
			return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		container = self.settingsContainer

		if self.inOptimizer:
			if tag.name == "optimizer":
				self.inOptimizer = False
				container.add(self.settings)
				return
		else:
			if tag.name == "optimizers":
				self.parser_finish()
				return
		XmlFactory.parser_endTag(self, tag)

	def composer_getTags(self):
		container = self.settingsContainer

		childTags = []
		for settings in sorted(dictValues(container.settingsDict),
				       key=lambda s: s.name):
			childTags.append(
				self.Tag(name="optimizer",
					 attrs={
						"name" : str(settings.name),
						"enabled" : "1" if settings.enabled else "0",
					 }
			))

		return [
			self.Tag(name="optimizers",
				attrs={
					"enabled" : "1" if container.globalEnable else "0",
					"all" : "1" if container.allEnable else "0",
					"type" : "awl",
				},
				tags=childTags
			)
		]

class AwlOptimizerSettings(object):
	"""Optimizer settings.
	"""

	__slots__ = (
		"name",
		"enabled",
	)

	def __init__(self, name, enabled=True):
		"""name: The optimizer run name.
		enabled: Optimizer run enable/disable.
		"""
		self.name = name
		self.enabled = enabled

	def dup(self):
		return self.__class__(name=str(self.name),
				      enabled=bool(self.enabled))

class AwlOptimizerSettingsContainer(object):
	factory = AwlOptimizerSettingsContainer_factory

	__slots__ = (
		"globalEnable",
		"allEnable",
		"settingsDict",
	)

	def __init__(self,
		     globalEnable=True,
		     allEnable=True,
		     settingsDict=None):
		self.globalEnable = globalEnable
		self.allEnable = allEnable
		self.settingsDict = settingsDict or {}

	def isEnabled(self, name):
		assert(isString(name))
		return self.globalEnable and\
		       (name in dictKeys(self.settingsDict) or\
			self.allEnable)

	def dup(self):
		settingsDict = {}
		for settings in dictValues(self.settingsDict):
			settingsDict[settings.name] = settings.dup()
		return self.__class__(globalEnable=bool(self.globalEnable),
				      allEnable=bool(self.allEnable),
				      settingsDict=settingsDict)

	def clear(self):
		self.globalEnable = True
		self.allEnable = True
		self.settingsDict.clear()

	def add(self, settings):
		if settings.name in self.settingsDict:
			return False
		self.settingsDict[settings.name] = settings
		return True

	def remove(self, settings):
		self.settingsDict.pop(settings.name, None)

	def __str__(self):
		return ", ".join(
			optClass.NAME for optClass in AwlOptimizer.ALL_OPTIMIZERS
			if self.isEnabled(optClass.NAME)
		)

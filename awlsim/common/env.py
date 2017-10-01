# -*- coding: utf-8 -*-
#
# AWL simulator - Environment variables
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

from awlsim.common.util import *
from awlsim.common.exceptions import *

import os


__all__ = [
	"AwlSimEnv",
]


class AwlSimEnv(object):
	"""Central environment variable handler.
	"""

	@classmethod
	def getEnv(cls):
		"""Get a copy of the environment dict.
		"""
		return dict(os.environ)

	@classmethod
	def clearLang(cls, env, lang="C"):
		"""Reset the language settings of an environment dict
		to some expected value and return the result.
		"""
		env = dict(env)
		env["LANG"] = lang
		for i in {"LANGUAGE", "LC_CTYPE", "LC_NUMERIC",
			  "LC_TIME", "LC_COLLATE", "LC_MONETARY",
			  "LC_MESSAGES", "LC_PAPER", "LC_NAME",
			  "LC_ADDRESS", "LC_TELEPHONE", "LC_MEASUREMENT",
			  "LC_IDENTIFICATION",}:
			env.pop(i, None)
		return env

	@classmethod
	def __getVar(cls, name, default=None):
		return cls.getEnv().get("AWLSIM_" + name, default)

	@classmethod
	def getProfileLevel(cls):
		"""Get AWLSIM_PROFILE.
		"""
		profileLevel = cls.__getVar("PROFILE", "0")
		try:
			profileLevel = int(profileLevel)
		except ValueError as e:
			profileLevel = 0
		return clamp(profileLevel, 0, 2)

	@classmethod
	def getGuiFramework(cls):
		"""Get AWLSIM_GUI.
		"""
		return cls.__getVar("GUI", "auto").lower()

	@classmethod
	def getAffinity(cls):
		"""Get AWLSIM_AFFINITY.
		Returns a list of host CPU indices or an empty list,
		if all host CPUs are allowed.
		"""
		affinityStr = cls.__getVar("AFFINITY", "")
		affinity = []
		try:
			for cpuIndex in affinityStr.split(","):
				cpuIndex = int(cpuIndex)
				if cpuIndex < 0:
					try:
						import multiprocessing
						cpuIndex = multiprocessing.cpu_count() + cpuIndex
					except ImportError as e:
						pass
				if cpuIndex < 0:
					cpuIndex = 0
				affinity.append(cpuIndex)
		except ValueError as e:
			affinity = []
		return affinity

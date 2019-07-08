# -*- coding: utf-8 -*-
#
# AWL simulator - Environment variables
#
# Copyright 2017-2019 Michael Buesch <m@bues.ch>
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

from awlsim.common.util import *
from awlsim.common.exceptions import *

import os
import gc


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
	def __getCpuCount(cls):
		try:
			import multiprocessing
			return multiprocessing.cpu_count()
		except ImportError as e:
			return 1

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
					cpuIndex = cls.__getCpuCount() + cpuIndex
				if cpuIndex < 0:
					cpuIndex = 0
				affinity.append(cpuIndex)
		except ValueError as e:
			affinity = []
		return sorted(set(affinity))

	SCHED_DEFAULT	= "default"	# Do not change the scheduling policy
	SCHED_NORMAL	= "normal"	# Use non-realtime scheduling policy
	SCHED_FIFO	= "fifo"	# Use SCHED_FIFO realtime scheduling policy
	SCHED_RR	= "rr"		# Use SCHED_RR realtime scheduling policy
	SCHED_DEADLINE	= "deadline"	# Use SCHED_DEADLINE realtime scheduling policy

	@classmethod
	def getSched(cls):
		"""Get AWLSIM_SCHED.
		Returns one of the SCHED_... constants.
		Returns None, if AWLSIM_SCHED has an invalid value.
		"""
		schedStr = cls.__getVar("SCHED", "").lower().strip()

		ifMulticore = False
		if schedStr.endswith("-if-multicore"):
			schedStr = schedStr[:-len("-if-multicore")]
			ifMulticore = True

		if schedStr == cls.SCHED_DEFAULT:
			return cls.SCHED_DEFAULT
		if schedStr == cls.SCHED_NORMAL or schedStr == "other":
			return cls.SCHED_NORMAL
		if schedStr == cls.SCHED_FIFO or schedStr == "realtime":
			if cls.__getCpuCount() <= 1 and ifMulticore:
				return cls.SCHED_NORMAL
			return cls.SCHED_FIFO
		if schedStr == cls.SCHED_RR:
			if cls.__getCpuCount() <= 1 and ifMulticore:
				return cls.SCHED_NORMAL
			return cls.SCHED_RR
		if schedStr == cls.SCHED_DEADLINE:
			if cls.__getCpuCount() <= 1 and ifMulticore:
				return cls.SCHED_NORMAL
			return cls.SCHED_DEADLINE
		return None

	@classmethod
	def getPrio(cls):
		"""Get AWLSIM_PRIO.
		Returns the scheduling priority as an integer or None.
		"""
		prioStr = cls.__getVar("PRIO", "").lower().strip()
		if prioStr != "default":
			try:
				return int(prioStr)
			except ValueError as e:
				pass
		return None

	MLOCK_OFF	= 0
	MLOCK_ALL	= 1
	MLOCK_FORCEALL	= 2

	@classmethod
	def getMLock(cls):
		"""Get AWLSIM_MLOCK.
		Returns one of the MLOCK_... constants.
		"""
		mlockStr = cls.__getVar("MLOCK", "").lower().strip()
		if not mlockStr:
			mlockStr = cls.MLOCK_OFF
		try:
			mlock = int(mlockStr)
			if mlock not in {cls.MLOCK_OFF,
					 cls.MLOCK_ALL,
					 cls.MLOCK_FORCEALL}:
				raise ValueError
		except ValueError as e:
			return cls.MLOCK_OFF
		return mlock

	GCMODE_RT	= "realtime"	# Manual GC, if realtime scheduling
	GCMODE_AUTO	= "auto"	# Automatic GC
	GCMODE_MANUAL	= "manual"	# Manual GC

	@classmethod
	def getGcMode(cls):
		"""Get AWLSIM_GCMODE.
		Returns one of the GCMODE_... constants.
		"""
		gcModeStr = cls.__getVar("GCMODE", "").lower().strip()
		if gcModeStr == cls.GCMODE_RT:
			return cls.GCMODE_RT
		if gcModeStr == cls.GCMODE_AUTO:
			return cls.GCMODE_AUTO
		if gcModeStr == cls.GCMODE_MANUAL:
			return cls.GCMODE_MANUAL
		return cls.GCMODE_RT

	@classmethod
	def getGcThreshold(cls, generation):
		"""Get AWLSIM_GCTHRES.
		AWLSIM_GCTHRES is a comma separated string with up to 3 integers.
		Each integer corresponding to the generation 0 to 2 thresholds.
		Returns the garbage collector threshold for the selected generation.
		"""
		thresStr = cls.__getVar("GCTHRES", "")
		thres = thresStr.split(",")
		assert(generation in (0, 1, 2))
		try:
			return clamp(int(thres[generation]),
				     0, 0x7FFFFFFF)
		except (ValueError, IndexError) as e:
			if generation == 0:
				gc_get_threshold = getattr(gc, "get_threshold", None)
				if gc_get_threshold:
					return gc_get_threshold()[0]
				return 700
			return 1

	@classmethod
	def getGcCycle(cls):
		"""Get AWLSIM_GCCYCLE.
		AWLSIM_GCCYCLE is the number of OB1 cycles it takes to trigger
		a manual garbage collection.
		Returns an integer.
		"""
		cycStr = cls.__getVar("GCCYCLE", "")
		try:
			return clamp(int(cycStr), 1, 0xFFFF)
		except ValueError as e:
			return 64

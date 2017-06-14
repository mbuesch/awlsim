# -*- coding: utf-8 -*-
#
# AWL simulator - labels
#
# Copyright 2012-2017 Michael Buesch <m@bues.ch>
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

from awlsim.common.sources import AwlSource
from awlsim.common.exceptions import *

from awlsim.core.operatortypes import * #+cimport
from awlsim.core.operators import * #+cimport
from awlsim.core.util import *


class AwlLabel(object):
	"""AWL label."""

	__slots__ = (
		"insn",
		"label",
	)

	def __init__(self, insn, label):
		self.insn = insn
		self.label = label

	def getLabelName(self):
		return self.label

	def getInsn(self):
		return self.insn

	@classmethod
	def resolveLabels(cls, insns):
		# Build the label table
		labels = []
		for i, insn in enumerate(insns):
			if not insn.hasLabel():
				continue
			insnLabel = insn.getLabel()
			for label in labels:
				if label.getLabelName() == insnLabel:
					raise AwlSimError("Duplicate label '%s' found. "
						"Label names have to be unique in a code block." %\
						insnLabel,
						insn = insn)
			labels.append(cls(insn, insnLabel))
		# Resolve label references
		for insn in insns:
			for op in insn.ops:
				if op.operType != AwlOperatorTypes.LBL_REF:
					continue
				labelIndex = cls.findInList(labels, op.immediateStr)
				if labelIndex is None:
					raise AwlSimError("Referenced label not found",
							  insn = insn)
				op.setLabelIndex(labelIndex)
		return labels

	@classmethod
	def findInList(cls, labelList, label):
		for i, lbl in enumerate(labelList):
			if lbl.getLabelName() == label:
				return i
		return None

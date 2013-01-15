# -*- coding: utf-8 -*-
#
# AWL simulator - labels
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from awlparser import *
from awloperators import *
from util import *


class AwlLabel(object):
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
			rawInsn = insn.getRawInsn()
			if not rawInsn.hasLabel():
				continue
			labels.append(AwlLabel(insn, rawInsn.getLabel()))
		# Resolve label references
		for insn in insns:
			for op in insn.ops:
				if op.type != AwlOperator.LBL_REF:
					continue
				labelIndex = AwlLabel.findInList(labels, op.label)
				if labelIndex is None:
					raise AwlSimError("line %d: Referenced label not found" %\
						insn.getLineNr())
				op.setLabelIndex(labelIndex)
		return labels

	@classmethod
	def findInList(cls, labelList, label):
		for i, lbl in enumerate(labelList):
			if lbl.getLabelName() == label:
				return i
		return None

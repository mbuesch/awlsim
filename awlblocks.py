# -*- coding: utf-8 -*-
#
# AWL simulator - blocks
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from awllabels import *
from util import *


class Block(object):
	def __init__(self, insns, index):
		self.insns = insns
		self.labels = None
		self.index = index
		if insns:
			self.labels = AwlLabel.resolveLabels(insns)

	def __repr__(self):
		return "Block %d" % self.index

class OB(Block):
	def __init__(self, insns, index):
		Block.__init__(self, insns, index)

	def __repr__(self):
		return "OB %d" % self.index

class FB(Block):
	def __init__(self, insns, index):
		Block.__init__(self, insns, index)

	def __repr__(self):
		return "FB %d" % self.index

class SFB(Block):
	def __init__(self, index):
		Block.__init__(self, None, index)

	def run(self, cpu, dbOper):
		pass # Reimplement this method

	def __repr__(self):
		return "SFB %d" % self.index

class FC(Block):
	def __init__(self, insns, index):
		Block.__init__(self, insns, index)

	def __repr__(self):
		return "FC %d" % self.index

class SFC(Block):
	def __init__(self, index):
		Block.__init__(self, None, index)

	def run(self, cpu):
		pass # Reimplement this method

	def __repr__(self):
		return "SFC %d" % self.index

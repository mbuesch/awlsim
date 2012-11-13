# -*- coding: utf-8 -*-
#
# AWL simulator - blocks
# Copyright 2012 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from awllabels import *
from util import *


class Block(object):
	def __init__(self, insns):
		self.insns = insns
		self.labels = None
		if insns:
			self.labels = AwlLabel.resolveLabels(insns)

class OB(Block):
	def __init__(self, insns):
		Block.__init__(self, insns)

class FB(Block):
	def __init__(self, insns):
		Block.__init__(self, insns)

class SFB(Block):
	def __init__(self):
		Block.__init__(self, None)

class FC(Block):
	def __init__(self, insns):
		Block.__init__(self, insns)

class SFC(Block):
	def __init__(self):
		Block.__init__(self, None)

# -*- coding: utf-8 -*-
#
# AWL simulator - blocks
# Copyright 2012 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from awldatablocks import *
from awllabels import *
from util import *


class Block(object):
	def __init__(self, insns, db):
		self.insns = insns
		self.labels = None
		if insns:
			self.labels = AwlLabel.resolveLabels(insns)
		self.db = db

class OB(Block):
	def __init__(self, insns, db):
		Block.__init__(self, insns, db)

class FB(Block):
	def __init__(self, insns, db):
		Block.__init__(self, insns, db)

class SFB(Block):
	def __init__(self, db):
		Block.__init__(self, None, db)

class FC(Block):
	def __init__(self, insns):
		Block.__init__(self, insns, None)

class SFC(Block):
	def __init__(self):
		Block.__init__(self, None, None)

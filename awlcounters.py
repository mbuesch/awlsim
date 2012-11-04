# -*- coding: utf-8 -*-
#
# AWL simulator - counters
# Copyright 2012 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from util import *


class Counter(object):
	def __init__(self, cpu, index):
		self.cpu = cpu
		self.index = index
		pass#TODO

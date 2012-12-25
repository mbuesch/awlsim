# -*- coding: utf-8 -*-
#
# AWL simulator - datablocks
# Copyright 2012 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from util import *


class DB(object):
	def __init__(self, index):
		self.index = index

	def fetch(self, operator):
		pass#TODO
		return 0

	def store(self, operator, value):
		pass#TODO

	def __repr__(self):
		return "DB %d" % self.index

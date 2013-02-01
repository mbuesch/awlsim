# -*- coding: utf-8 -*-
#
# AWL simulator - SFCs
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from awlblocks import *
from util import *


class SFC64(SFC):
	def __init__(self):
		SFC.__init__(self, 64)

	def run(self, cpu):
		pass#TODO

SFC_table = {
	64	: SFC64(),
}

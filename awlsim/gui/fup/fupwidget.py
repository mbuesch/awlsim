# -*- coding: utf-8 -*-
#
# AWL simulator - FUP widget
#
# Copyright 2016 Michael Buesch <m@bues.ch>
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

from awlsim.gui.fup.fupdrawwidget import *
from awlsim.gui.util import *


class FupWidget(QWidget):
	"""Main FUP/FBD widget."""

	def __init__(self, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout())

		self.draw = FupDrawWidget(self)
		self.drawScroll = QScrollArea(self)
		self.drawScroll.setWidget(self.draw)
		self.layout().addWidget(self.drawScroll, 0, 0)

	def getSource(self):
		#TODO
		return FupSource(name = "FUP")

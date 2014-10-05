# -*- coding: utf-8 -*-
#
# AWL simulator - GUI icons
#
# Copyright 2014 Michael Buesch <m@bues.ch>
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

from awlsim.gui.util import *

from awlsim.gui.icons.timer import *
from awlsim.gui.icons.counter import *
from awlsim.gui.icons.cpu import *
from awlsim.gui.icons.run import *
from awlsim.gui.icons.stop import *
from awlsim.gui.icons.datablock import *
from awlsim.gui.icons.inputs import *
from awlsim.gui.icons.outputs import *
from awlsim.gui.icons.flags import *
from awlsim.gui.icons.lcd import *
from awlsim.gui.icons.glasses import *
from awlsim.gui.icons.open import *
from awlsim.gui.icons.save import *
from awlsim.gui.icons.new import *

import base64


__icons = {
	"timer"		: icon_timer,
	"counter"	: icon_counter,
	"cpu"		: icon_cpu,
	"run"		: icon_run,
	"stop"		: icon_stop,
	"datablock"	: icon_datablock,
	"inputs"	: icon_inputs,
	"outputs"	: icon_outputs,
	"flags"		: icon_flags,
	"lcd"		: icon_lcd,
	"glasses"	: icon_glasses,
	"open"		: icon_open,
	"save"		: icon_save,
	"new"		: icon_new,
}

def getIcon(iconName):
	iconB64 = __icons[iconName]
	iconData = base64.b64decode(iconB64)
	img = QImage()
	img.loadFromData(iconData)
	pixmap = QPixmap()
	pixmap.convertFromImage(img)
	return QIcon(pixmap)

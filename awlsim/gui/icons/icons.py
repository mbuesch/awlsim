# -*- coding: utf-8 -*-
#
# AWL simulator - GUI icons
#
# Copyright 2014-2015 Michael Buesch <m@bues.ch>
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
from awlsim.gui.icons.stdlib import *
from awlsim.gui.icons.prefs import *
from awlsim.gui.icons.network import *
from awlsim.gui.icons.textsource import *
from awlsim.gui.icons.exit import *
from awlsim.gui.icons.undo import *
from awlsim.gui.icons.redo import *
from awlsim.gui.icons.browser import *
from awlsim.gui.icons.cut import *
from awlsim.gui.icons.copy import *
from awlsim.gui.icons.paste import *
from awlsim.gui.icons.download import *
from awlsim.gui.icons.download_one import *
from awlsim.gui.icons.warning import *
from awlsim.gui.icons.tag import *
from awlsim.gui.icons.hwmod import *
from awlsim.gui.icons.next import *
from awlsim.gui.icons.previous import *
from awlsim.gui.icons.doc_close import *
from awlsim.gui.icons.doc_edit import *
from awlsim.gui.icons.doc_export import *
from awlsim.gui.icons.doc_import import *
from awlsim.gui.icons.doc_new import *
from awlsim.gui.icons.tab_new import *
from awlsim.gui.icons.find import *
from awlsim.gui.icons.findreplace import *
from awlsim.gui.icons.plugin import *
from awlsim.gui.icons.fup import *
from awlsim.gui.icons.kop import *

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
	"stdlib"	: icon_stdlib,
	"prefs"		: icon_prefs,
	"network"	: icon_network,
	"textsource"	: icon_textsource,
	"exit"		: icon_exit,
	"undo"		: icon_undo,
	"redo"		: icon_redo,
	"browser"	: icon_browser,
	"cut"		: icon_cut,
	"copy"		: icon_copy,
	"paste"		: icon_paste,
	"download"	: icon_download,
	"download_one"	: icon_download_one,
	"warning"	: icon_warning,
	"tag"		: icon_tag,
	"hwmod"		: icon_hwmod,
	"next"		: icon_next,
	"previous"	: icon_previous,
	"doc_close"	: icon_doc_close,
	"doc_edit"	: icon_doc_edit,
	"doc_export"	: icon_doc_export,
	"doc_import"	: icon_doc_import,
	"doc_new"	: icon_doc_new,
	"tab_new"	: icon_tab_new,
	"find"		: icon_find,
	"findreplace"	: icon_findreplace,
	"plugin"	: icon_plugin,
	"fup"		: icon_fup,
	"kop"		: icon_kop,
}

def getIcon(iconName):
	global __icons

	try:
		icon = __icons[iconName]
	except KeyError:
		return QIcon()
	if isinstance(icon, QIcon):
		# The icon is already cached. Return it.
		return icon
	# Convert the icon.
	iconData = base64.b64decode(icon)
	img = QImage()
	img.loadFromData(iconData)
	pixmap = QPixmap()
	pixmap.convertFromImage(img)
	icon = QIcon(pixmap)
	# Add the icon to the cache.
	__icons[iconName] = icon
	return icon

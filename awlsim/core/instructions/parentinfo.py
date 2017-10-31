# -*- coding: utf-8 -*-
#
# AWL simulator - Instruction parent information
#
# Copyright 2017 Michael Buesch <m@bues.ch>
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

from awlsim.common.util import *
from awlsim.common.enumeration import *


__all__ = [
	"AwlInsnParentInfo",
]


class AwlInsnParentInfo(object):
	"""Instruction parent information.
	The compiler (AWL, FUP, KOP) may place information about the
	source of the instruction and its generation here.
	"""

	__slots__ = (
		"uuid",
		"rawInsn",
		"connType",
		"connIndex",
	)

	# Connection types
	EnumGen.start
	CONNTYPE_NONE	= EnumGen.item # Unknown or none
	CONNTYPE_IN	= EnumGen.item # Input connection
	CONNTYPE_OUT	= EnumGen.item # Output connection
	CONNTYPE_INOUT	= EnumGen.item # In/Out connection
	EnumGen.end

	def __init__(self,
		     uuid=None,
		     rawInsn=None,
		     connType=CONNTYPE_NONE,
		     connIndex=-1):
		"""Construct parent information.
		All information is optional.
		uuid: The UUID string of the parent object.
		rawInsn: A reference to the raw AWL instruction.
		connType: The "connection type" of the parent object this
		          instruction belongs to.
		connIndex: The "connection index" of the parent object this
		           instruction belongs to.
		"""
		self.uuid = uuid
		self.rawInsn = rawInsn
		self.connType = connType
		self.connIndex = connIndex

	def __bool__(self):
		return bool(self.uuid or\
			    self.rawInsn or\
			    self.connType != self.CONNTYPE_NONE or\
			    self.connIndex >= 0)

	__nonzero__ = __bool__ # Python 2 compat

	def __str__(self):
		fields = []
		if self.uuid:
			fields.append(shortUUID(self.uuid))
		if self.rawInsn:
			fields.append(str(self.rawInsn))
		if self.connType != self.CONNTYPE_NONE:
			connTypeStr = {
				self.CONNTYPE_IN	: "IN",
				self.CONNTYPE_OUT	: "OUT",
				self.CONNTYPE_INOUT	: "IN_OUT",
			}[self.connType]
			if self.connIndex >= 0:
				fields.append("%s-%d" % (connTypeStr,
							 self.connIndex))
			else:
				fields.append(connTypeStr)
		return "parent=(%s)" % ", ".join(fields)

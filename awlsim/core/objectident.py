# -*- coding: utf-8 -*-
#
# AWL simulator - Object identification
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

import hashlib
import binascii


class ObjIdent(object):
	IDENT_HASH		= "sha256"
	IDENT_HASH_INIT		= b""

	@classmethod
	def __hashFunc(cls, initData=b''):
		return hashlib.new(cls.IDENTHASH, initData)

	# Get the identification hash for this object.
	def getIdentHash(self):
		digest = self.__hashFunc(self.IDENT_HASH_INIT)
		for data in self.getIdentData():
			h = self.__hashFunc(digest)
			h.update(data)
			digest = h.digest()
		return binascii.b2a_hex(digest)

	# Get the data blobs used to identify the object.
	# Reimplement this in the subclass to provide the data.
	def getIdentData(self):
		# Return no data blobs by default.
		return []

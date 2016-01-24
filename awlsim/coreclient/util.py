# -*- coding: utf-8 -*-
#
# AWL simulator - Networking utils
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

from awlsim.common.exceptions import *


def parseNetAddress(addrStr):
	"""Parse a host:port networking address string.
	"""
	addrStr = addrStr.strip()
	if addrStr.startswith("["):
		end = addrStr.rfind("]")
		if end <= 0:
			raise AwlSimError("Invalid IPv6 address. "
				"Missing closing bracket ']'.")
		host = addrStr[1:end]
		portStr = addrStr[end+1:]
	else:
		end = addrStr.find(":")
		if end < 0:
			host = addrStr
			portStr = ""
		else:
			host = addrStr[:end]
			portStr = addrStr[end:]
	portStr = portStr.strip()
	if portStr:
		try:
			if not portStr.startswith(":"):
				raise ValueError
			port = int(portStr[1:])
			if port < 0 or port > 0xFFFF:
				raise ValueError
		except ValueError as e:
			raise AwlSimError("Invalid port number.")
	else:
		port = None
	return host, port

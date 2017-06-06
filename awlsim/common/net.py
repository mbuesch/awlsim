# -*- coding: utf-8 -*-
#
# AWL simulator - networking utility functions
#
# Copyright 2013-2016 Michael Buesch <m@bues.ch>
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
from awlsim.common.exceptions import *
import socket


__all__ = [
	"AF_UNIX",
	"SocketErrors",
	"netGetAddrInfo",
	"netPortIsUnused",
]


if hasattr(socket, "AF_UNIX"):
	AF_UNIX = socket.AF_UNIX
else:
	AF_UNIX = None

SocketErrors = (socket.error if hasattr(socket, "error") else OSError,
		BlockingIOError,
		ConnectionError)


def netGetAddrInfo(host, port, family = None):
	"""getaddrinfo() wrapper.
	"""
	socktype = socket.SOCK_STREAM
	if family in {None, socket.AF_UNSPEC}:
		# First try IPv4
		try:
			family, socktype, proto, canonname, sockaddr =\
				socket.getaddrinfo(host, port,
						   socket.AF_INET,
						   socktype)[0]
		except socket.gaierror as e:
			if e.errno == socket.EAI_ADDRFAMILY:
				# Also try IPv6
				family, socktype, proto, canonname, sockaddr =\
					socket.getaddrinfo(host, port,
							   socket.AF_INET6,
							   socktype)[0]
			else:
				raise e
	else:
		family, socktype, proto, canonname, sockaddr =\
			socket.getaddrinfo(host, port,
					   family,
					   socktype)[0]
	return (family, socktype, sockaddr)

def netPortIsUnused(host, port):
	"""Check if a port is not used.
	"""
	sock = None
	try:
		family, socktype, sockaddr = netGetAddrInfo(host, port)
		if family == AF_UNIX:
			if fileExists(sockaddr) == False:
				return True
			return False
		sock = socket.socket(family, socktype)
		sock.bind(sockaddr)
	except SocketErrors as e:
		return False
	finally:
		if sock:
			with suppressAllExc:
				sock.shutdown(socket.SHUT_RDWR)
			with suppressAllExc:
				sock.close()
	return True

# -*- coding: utf-8 -*-
#
# Raspberry Pi fake GPIO module for unit testing
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


BCM		= 11

LOW		= 0
HIGH		= 1

OUT		= 0
IN		= 1

PUD_OFF		= 0 + 20
PUD_DOWN	= 1 + 20
PUD_UP		= 2 + 20

__nrChannels = 28
__state = [ LOW, ] * __nrChannels
__directions = [ set(), ] * __nrChannels

def setwarnings(enabled):
	pass

def setmode(mode):
	assert(mode == BCM)

def setup(channel, direction, pull_up_down=PUD_OFF, initial=None):
	assert(pull_up_down in {PUD_OFF, PUD_DOWN, PUD_UP})
	assert(initial in {None, LOW, HIGH})
	assert(direction in {OUT, IN})
	assert(channel >= 0 and channel < __nrChannels)
	__directions[channel].add(direction)
	if direction == OUT:
		assert(pull_up_down == PUD_OFF)
		if initial is not None:
			__state[channel] = initial
	else:
		assert(initial == None)

def cleanup(channel = None):
	pass

def output(channels, values):
	assert(isinstance(channels, int) or\
	       isinstance(channels, list) or\
	       isinstance(channels, tuple))
	if isinstance(channels, int):
		channelsList = [ channels, ]
		assert(isinstance(values, int))
	else:
		channelsList = channels
		assert(isinstance(values, list) or\
		       isinstance(values, tuple))

	assert(isinstance(values, int) or\
	       isinstance(values, list) or\
	       isinstance(values, tuple))
	if isinstance(values, int):
		valuesList = [ values, ]
		assert(isinstance(channels, int))
	else:
		valuesList = values
		assert(isinstance(channels, list) or\
		       isinstance(channels, tuple))

	assert(len(channelsList) == len(valuesList))

	for i, channel in enumerate(channelsList):
		assert(isinstance(channel, int))
		assert(isinstance(valuesList[i], int) or\
		       isinstance(valuesList[i], bool))
		assert(channel >= 0 and channel < __nrChannels)
		assert(OUT in __directions[channel])
		__state[channel] = HIGH if valuesList[i] else LOW

def input(channel):
	assert(isinstance(channel, int))
	assert(channel >= 0 and channel < __nrChannels)
	assert(IN in __directions[channel])
	return __state[channel]

# -*- coding: utf-8 -*-
#
# AWL simulator - utility functions
#
# Copyright 2012-2015 Michael Buesch <m@bues.ch>
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

import sys


# Returns the index of a list element, or -1 if not found.
# If translate if not None, it should be a callable that translates
# a list entry. Arguments are index, entry.
def listIndex(_list, value, start=0, stop=-1, translate=None):
	if stop < 0:
		stop = len(_list)
	if translate:
		for i, ent in enumerate(_list[start:stop], start):
			if translate(i, ent) == value:
				return i
		return -1
	try:
		return _list.index(value, start, stop)
	except ValueError:
		return -1

# Convert an integer list to a human readable string.
# Example: [1, 2, 3]  ->  "1, 2 or 3"
def listToHumanStr(lst, lastSep="or"):
	if not lst:
		return ""
	lst = toList(lst)
	string = ", ".join(str(i) for i in lst)
	# Replace last comma with 'lastSep'
	string = string[::-1].replace(",", lastSep[::-1] + " ", 1)[::-1]
	return string

# Expand the elements of a list.
# 'expander' is the expansion callback. 'expander' takes
# one list element as argument. It returns a list.
def listExpand(lst, expander):
	ret = []
	for item in lst:
		ret.extend(expander(item))
	return ret

# Fully partition a string by separator 'sep'.
# Returns a list of strings:
# [ "first-element", sep, "second-element", sep, ... ]
# If 'keepEmpty' is True, empty elements are kept.
def strPartitionFull(string, sep, keepEmpty=True):
	first, ret = True, []
	for elem in string.split(sep):
		if not first:
			ret.append(sep)
		if elem or keepEmpty:
			ret.append(elem)
		first = False
	return ret

# Returns value, if value is a set.
# Returns a set with the elements of value, if value is a tuple.
# Returns a set with the elements of value, if value is a list.
# Otherwise returns a set with value as single element.
def toSet(value):
	if isinstance(value, set):
		return value
	if isinstance(value, list) or\
	   isinstance(value, tuple):
		return set(value)
	return { value, }

def pivotDict(inDict):
	outDict = {}
	for key, value in dictItems(inDict):
		if value in outDict:
			raise KeyError("Ambiguous key in pivot dict")
		outDict[value] = key
	return outDict

# Get "Greatest Common Divisor"
def math_gcd(*args):
	return reduce(compat_gcd, args)

# Get "Least Common Multiple"
def math_lcm(*args):
	return reduce(lambda x, y: x * y // math_gcd(x, y),
		      args)

#!/usr/bin/env python3
#
# I2C bus slave
# clock stretching workaround timer table generator
#
# Copyright (c) 2016 Michael Buesch <m@bues.ch>
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

import sys


I2CS_EXPECTED_KHZ	= int(sys.argv[1])
TIMER_KHZ		= 1000

scl_period_us = int(round(1000.0 / I2CS_EXPECTED_KHZ))
timer_period_us = int(round(1000.0 / TIMER_KHZ))

timer_ticks_per_scl = scl_period_us / timer_period_us


print("/* THIS IS AN AUTOMATICALLY GENERATED FILE */")
print("/* DO NOT EDIT */")
print("")
print("/*")
print(" * I2CS_EXPECTED_KHZ   = %d" % I2CS_EXPECTED_KHZ)
print(" * TIMER_KHZ           = %d" % TIMER_KHZ)
print(" * scl_period_us       = %d" % scl_period_us)
print(" * timer_period_us     = %d" % timer_period_us)
print(" * timer_ticks_per_scl = %.3f" % timer_ticks_per_scl)
print(" */")
print("")
print("#include \"util.h\"")
print("")
print("enum clkstretch_release_hint {")
print("\tCLKSTRETCH_RELEASE_UNSAFE, /* It's NOT safe to release SCL stretching. */")
print("\tCLKSTRETCH_RELEASE_SAFE, /* It's safe to release SCL stretching. */")
print("};")
print("")
print("static const enum clkstretch_release_hint __flash _used clkstretch_release_hint_table[] = {")
for timer_cnt in range(0xFF + 1):
	time_us = timer_period_us * timer_cnt
	modulo = time_us % scl_period_us
#	if modulo == scl_period_us // 4:# or\
#	   modulo == scl_period_us // 4 + 1:
	if modulo == 7:
		action = "SAFE"
	else:
		action = "UNSAFE"
	print("\tCLKSTRETCH_RELEASE_%s, /* %d us */" % (action, time_us));
print("};")

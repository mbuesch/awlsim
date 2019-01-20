#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# AWL simulator - Run random AWL program
#
# Copyright 2019 Michael Buesch <m@bues.ch>
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

import subprocess
import multiprocessing
import sys
import os
import getopt


basedir = os.path.dirname(os.path.abspath(__file__))
awlsim_base = os.path.join(basedir, "..")


class Error(Exception): pass

def error(msg):
	print(msg, file=sys.stderr)

def info(msg):
	print(msg, file=sys.stdout)

def process(seed):
	procGen = None
	procAwlsim = None
	try:
		info("Running with seed=%d ..." % seed)

		procGen = subprocess.Popen(
			[ sys.executable,
			  os.path.join(awlsim_base, "maintenance", "benchmark", "generate_benchmark.py"),
			  "--seed", str(seed), "--one-cycle" ],
			stdout=subprocess.PIPE,
			shell=False)
		procAwlsim = subprocess.Popen(
			[ sys.executable,
			  os.path.join(awlsim_base, "awlsim-test"),
			  "-D", "-L1", "-4", "-" ],
			stdin=procGen.stdout,
			stdout=subprocess.PIPE,
			shell=False)
		procGen.stdout.close()
		procAwlsim.communicate()
		procGen.terminate()
		procGen.wait()
		if procGen.returncode or procAwlsim.returncode:
			raise Error("Process exited with error.")
	except KeyboardInterrupt:
		raise Error("Aborted by user.")
	finally:
		for p in (procGen, procAwlsim):
			if p:
				p.terminate()
				p.wait()

def usage(f=sys.stdout):
	print("run-random.py [OPTIONS]", file=f)
	print("", file=f)
	print(" -j|--jobs JOBS       Number of parallel jobs. Default: Number of CPUs", file=f)
	print(" -f|--seed-from SEED  Start with seed from this value. Default: 0", file=f)
	print(" -t|--seed-to SEED    End with seed at this value.", file=f)
	print(" -s|--seed-step INC   Increment seed by this value. Default: 1", file=f)

def main():
	opt_jobs = None
	opt_rangeMin = 0
	opt_rangeMax = 0xFFFFFF
	opt_rangeStep = 1

	try:
		(opts, args) = getopt.getopt(sys.argv[1:],
			"hj:f:t:s:",
			[ "help", "jobs=", "seed-from=", "seed-to=", "seed-step=", ])
	except getopt.GetoptError as e:
		error(str(e))
	for (o, v) in opts:
		if o in ("-h", "--help"):
			usage()
			return 0
		if o in ("-j", "--jobs"):
			try:
				opt_jobs = int(v)
				if opt_jobs < 0:
					raise ValueError
				if opt_jobs == 0:
					opt_jobs = None
			except ValueError:
				error("Invalid -j|--jobs argument.")
				return 1
		if o in ("-f", "--seed-from"):
			try:
				opt_rangeMin = int(v)
				if opt_rangeMin < 0 or opt_rangeMin > 0xFFFFFFFF:
					raise ValueError
			except ValueError:
				error("Invalid -f|--seed-from argument.")
				return 1
		if o in ("-t", "--seed-to"):
			try:
				opt_rangeMax = int(v)
				if opt_rangeMax < 0 or opt_rangeMax > 0xFFFFFFFF:
					raise ValueError
			except ValueError:
				error("Invalid -t|--seed-to argument.")
				return 1
		if o in ("-s", "--seed-step"):
			try:
				opt_rangeStep = int(v)
			except ValueError:
				error("Invalid -s|--seed-step argument.")
				return 1

	try:
		seedRange = range(opt_rangeMin, opt_rangeMax + 1, opt_rangeStep)
		if opt_jobs == 1:
			for seed in seedRange:
				process(seed)
		else:
			with multiprocessing.Pool(opt_jobs) as pool:
				pool.map(process, seedRange)
	except KeyboardInterrupt:
		return 1
	except Exception as e:
		error(str(e))
		return 1
	return 0

if __name__ == "__main__":
	sys.exit(main())

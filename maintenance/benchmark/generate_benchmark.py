#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# AWL simulator - Generate instruction benchmark
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

import sys
import random
import getopt


insnCollection = (
	(
		( "U",		"BOOL"),
	), (
		( "UN",		"BOOL"),
	), (
		( "O",		"BOOL"),
	), (
		( "ON",		"BOOL"),
	), (
		( "X",		"BOOL"),
	), (
		( "XN",		"BOOL"),
	), (
		( "U",		"RANDOM_BOOL"),
	), (
		( "UN",		"RANDOM_BOOL"),
	), (
		( "O",		"RANDOM_BOOL"),
	), (
		( "ON",		"RANDOM_BOOL"),
	), (
		( "X",		"RANDOM_BOOL"),
	), (
		( "XN",		"RANDOM_BOOL"),
	), (
		( "U(",		""),
		( ")",		""),
	), (
		( "UN(",	""),
		( ")",		""),
	), (
		( "O(",		""),
		( ")",		""),
	), (
		( "ON(",	""),
		( ")",		""),
	), (
		( "X(",		""),
		( ")",		""),
	), (
		( "XN(",	""),
		( ")",		""),
	), (
		( "=",		"BOOL"),
	), (
		( "R",		"BOOL"),
	), (
		( "S",		"BOOL"),
	), (
		( "NOT",	""),
	), (
		( "SET",	""),
	), (
		( "CLR",	""),
	), (
		( "SAVE",	""),
	), (
		( "FN",		"BOOL"),
	), (
		( "FP",		"BOOL"),
	), (
		( "==I",	""),
	), (
		( "<>I",	""),
	), (
		( ">I",		""),
	), (
		( "<I",		""),
	), (
		( ">=I",	""),
	), (
		( "<=I",	""),
	), (
		( "==D",	""),
	), (
		( "<>D",	""),
	), (
		( ">D",		""),
	), (
		( "<D",		""),
	), (
		( ">=D",	""),
	), (
		( "<=D",	""),
	), (
		( "==R",	""),
	), (
		( "<>R",	""),
	), (
		( ">R",		""),
	), (
		( "<R",		""),
	), (
		( ">=R",	""),
	), (
		( "<=R",	""),
	), (
		( "L",		"0"),
		( "BTI",	""),
	), (
		( "ITB",	""),
	), (
		( "L",		"0"),
		( "BTD",	""),
	), (
		( "ITD",	""),
	), (
		( "DTB",	""),
	), (
		( "DTR",	""),
	), (
		( "INVI",	""),
	), (
		( "INVD",	""),
	), (
		( "NEGI",	""),
	), (
		( "NEGD",	""),
	), (
		( "NEGR",	""),
	), (
		( "TAW",	""),
	), (
		( "TAD",	""),
	), (
		( "RND",	""),
	), (
		( "TRUNC",	""),
	), (
		( "RND+",	""),
	), (
		( "RND-",	""),
	), (
		( "FR",		"COUNTER"),
	), (
		( "L",		"RANDOM_DWORD"),
	), (
		( "LC",		"WORD"),
	), (
		( "ZV",		"COUNTER"),
	), (
		( "ZR",		"COUNTER"),
	), (
		( "AUF",	"DB"),
	), (
		( "TDB",	""),
	), (
		( "SPA",	"LABEL"),
	), (
		( "L",		"0"),
		( "SPL",	"LABEL"),
	), (
		( "SPB",	"LABEL"),
	), (
		( "SPBN",	"LABEL"),
	), (
		( "SPBB",	"LABEL"),
	), (
		( "SPBNB",	"LABEL"),
	), (
		( "SPBI",	"LABEL"),
	), (
		( "SPBIN",	"LABEL"),
	), (
		( "SPO",	"LABEL"),
	), (
		( "SPS",	"LABEL"),
	), (
		( "SPZ",	"LABEL"),
	), (
		( "SPN",	"LABEL"),
	), (
		( "SPP",	"LABEL"),
	), (
		( "SPM",	"LABEL"),
	), (
		( "SPPZ",	"LABEL"),
	), (
		( "SPMZ",	"LABEL"),
	), (
		( "SPU",	"LABEL"),
	), (
		( "LOOP",	"LABEL"),
	), (
		( "+I",		""),
	), (
		( "-I",		""),
	), (
		( "*I",		""),
	), (
		( "/I",		""),
	), (
		( "+",		"0"),
	), (
		( "+D",		""),
	), (
		( "-D",		""),
	), (
		( "*D",		""),
	), (
		( "/D",		""),
	), (
		( "MOD",	""),
	), (
		( "+R",		""),
	), (
		( "-R",		""),
	), (
		( "*R",		""),
	), (
		( "/R",		""),
	), (
		( "ABS",	""),
	), (
		( "SQR",	""),
	), (
		( "SQRT",	""),
	), (
		( "EXP",	""),
	), (
		( "LN",		""),
	), (
		( "SIN",	""),
	), (
		( "COS",	""),
	), (
		( "TAN",	""),
	), (
		( "ASIN",	""),
	), (
		( "ACOS",	""),
	), (
		( "ATAN",	""),
	), (
		( "LAR1",	""),
	), (
		( "LAR2",	""),
	), (
		( "T",		"DWORD"),
	), (
		( "TAR",	""),
	), (
		( "TAR1",	""),
	), (
		( "TAR2",	""),
	), (
		( "MCR(",	""),
		( "MCRA",	""),
		( "MCRD",	""),
		( ")MCR",	""),
	), (
		( "SSI",	""),
	), (
		( "SSD",	""),
	), (
		( "SLW",	""),
	), (
		( "SRW",	""),
	), (
		( "SLD",	""),
	), (
		( "SRD",	""),
	), (
		( "RLD",	""),
	), (
		( "RRD",	""),
	), (
		( "RLDA",	""),
	), (
		( "RRDA",	""),
	), (
		( "L",		"0"),
		( "SI",		"TIMER"),
	), (
		( "L",		"0"),
		( "SV",		"TIMER"),
	), (
		( "L",		"0"),
		( "SE",		"TIMER"),
	), (
		( "L",		"0"),
		( "SS",		"TIMER"),
	), (
		( "L",		"0"),
		( "SA",		"TIMER"),
	), (
		( "UW",		""),
	), (
		( "OW",		""),
	), (
		( "XOW",	""),
	), (
		( "UD",		""),
	), (
		( "OD",		""),
	), (
		( "XOD",	""),
	), (
		( "TAK",	""),
	), (
		( "PUSH",	""),
	), (
		( "POP",	""),
	), (
		( "ENT",	""),
	), (
		( "LEAVE",	""),
	), (
		( "INC",	"0"),
	), (
		( "DEC",	"0"),
	), (
		( "+AR1",	""),
	), (
		( "+AR2",	""),
	), (
		( "BLD",	"0"),
	), (
		( "NOP",	"0"),
	), (
		( "CALL",	"FC 42"),
		( "CALL",	"FC 42"),
		( "CALL",	"FC 42"),
	), (
		( "CALL",	"FB 45, DB 45"),
		( "CALL",	"FB 45, DB 45"),
		( "CALL",	"FB 45, DB 45"),
	), (
		( "SET",	""),
	), (
		( "CC",		"FC 43"),
	), (
		( "UC",		"FC 44"),
	), (
		# Write some values to the HW module.
		( "L",		"MW 50"),
		( "+",		"1"),
		( "T",		"MW 50"),
		( "T",		"AW 0" )
	)
)

def out(data):
	print(data, end="\r\n")

def error(msg):
	print(msg, file=sys.stderr)
	sys.exit(1)

def usage(f=sys.stdout):
	print("generate_benchmark.py [OPTIONS]", file=f)
	print("", file=f)
	print(" -s|--seed SEED         Set the randomizer seed. Default: 42", file=f)
	print(" -i|--iterations COUNT  Set the number of iterations. Default: 10000", file=f)
	print(" -o|--one-cycle         Generate CALL SFC 46 at the end of OB 1.", file=f)

def getLabelName(index):
	if index < 0 or index >= 26 ** 4:
		raise ValueError("Label index out of range.")
	labelChars = [None] * 4
	for i in range(3, -1, -1):
		labelChars[i] = chr(ord("A") + (index % 26))
		index //= 26
	return "".join(labelChars)

def main():
	opt_nrIterations = 10000
	opt_rngSeed = 42
	opt_oneCycle = False

	try:
		(opts, args) = getopt.getopt(sys.argv[1:],
			"hs:i:o",
			[ "help", "seed=", "iterations=", "one-cycle", ])
	except getopt.GetoptError as e:
		error(str(e))
	for (o, v) in opts:
		if o in ("-h", "--help"):
			usage()
			return 0
		if o in ("-s", "--seed"):
			try:
				opt_rngSeed = int(v)
				if opt_rngSeed < 0 or opt_rngSeed > 0xFFFFFFFF:
					raise ValueError
			except ValueError:
				error("Invalid RNG seed.")
		if o in ("-i", "--iterations"):
			try:
				opt_nrIterations = int(v)
				if opt_nrIterations < 0:
					raise ValueError
			except ValueError:
				error("Invalid number of iterations.")
		if o in ("-o", "--one-cycle"):
			opt_oneCycle = True
	if args:
		usage(f=sys.stderr)
		return 1

	rng = random.Random()
	rng.seed(opt_rngSeed)

	labelIndex = 0
	out("//")
	out("//")
	out("// GENERATED by generate_benchmark.py")
	out("//")
	out("// iterations=%d" % opt_nrIterations)
	out("// seed=%d" % opt_rngSeed)
	out("//")
	out("//")
	out("")
	out("ORGANIZATION_BLOCK OB 1")
	out("BEGIN")
	for i in range(opt_nrIterations):
		for insn, args in rng.choice(insnCollection):
			prefixStr = suffixStr = None
			if args == "":
				argsStr = ""
			elif args == "BOOL":
				argsStr = "M 0.4"
			elif args == "WORD":
				argsStr = "MW 0"
			elif args == "DWORD":
				argsStr = "MD 0"
			elif args == "TIMER":
				argsStr = "T 42"
			elif args == "COUNTER":
				argsStr = "Z 42"
			elif args == "DB":
				argsStr = "DB 42"
			elif args == "LABEL":
				try:
					labelName = getLabelName(labelIndex)
				except ValueError as e:
					error("Failed to generate jump label: %s\n"
					      "The generated program is too big." % str(e))
				prefixStr = "\tL 0;\r\n\tCLR;"
				argsStr = labelName
				suffixStr = "%s:\tNOP 0;" % labelName
				labelIndex += 1
			elif args == "RANDOM_BOOL":
				argsStr = "TRUE" if rng.randint(0, 1) else "FALSE"
			elif args == "RANDOM_DWORD":
				argsStr = "DW#16#%08X" % rng.randint(0, 0xFFFFFFFF)
			else:
				argsStr = args
			if prefixStr:
				out(prefixStr)
			if argsStr:
				argsStr = " " + argsStr
			out("\t%s%s;" % (insn, argsStr))
			if suffixStr:
				out(suffixStr)
	if opt_oneCycle:
		out("\tCALL SFC 46 // STOP CPU")
	out("END_ORGANIZATION_BLOCK")

	out("\r\nDATA_BLOCK DB 42")
	out("\tSTRUCT")
	out("\t\tVAR : INT;")
	out("\tEND_STRUCT")
	out("BEGIN")
	out("END_DATA_BLOCK")

	out("\r\nFUNCTION FC 42 : VOID")
	out("BEGIN")
	out("\tBE;")
	out("END_FUNCTION")

	out("\r\nFUNCTION FC 43 : VOID")
	out("BEGIN")
	out("\tBEA")
	out("END_FUNCTION")

	out("\r\nFUNCTION FC 44 : VOID")
	out("BEGIN")
	out("\tSET;")
	out("\tBEB;")
	out("END_FUNCTION")

	out("\r\nFUNCTION_BLOCK FB 45")
	out("BEGIN")
	out("END_FUNCTION_BLOCK")

	out("\r\nDATA_BLOCK DB 45")
	out("\tFB 45")
	out("BEGIN")
	out("END_DATA_BLOCK")

if __name__ == "__main__":
	sys.exit(main())

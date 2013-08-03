#!/usr/bin/env python3

import sys
import os
import re
import shutil
import hashlib
from distutils.core import setup
from distutils.extension import Extension
from awlsim.version import VERSION_MAJOR, VERSION_MINOR


def pyCythonPatch(toFile, fromFile):
	print("cython-patch: patching file '%s' to '%s'" %\
	      (fromFile, toFile))
	tmpFile = toFile + ".TMP"
	infd = open(fromFile, "r")
	outfd = open(tmpFile, "w")
	for line in infd.readlines():
		line = re.sub(r'^from awlsim\.', "from awlsim_cython.", line)
		line = re.sub(r'^import awlsim\.', "import awlsim_cython.", line)
		outfd.write(line)
	infd.close()
	outfd.flush()
	outfd.close()
	try:
		toFileHash = hashlib.sha1(open(toFile, "rb").read()).hexdigest()
	except FileNotFoundError:
		pass
	else:
		newFileHash = hashlib.sha1(open(tmpFile, "rb").read()).hexdigest()
		if toFileHash == newFileHash:
			print("(already up to date)")
			return
	shutil.move(tmpFile, toFile)

def addCythonModules():
	global cmdclass
	global ext_modules

	modDir = "./awlsim/"
	buildDir = "./build/awlsim_cython_patched/"

	if not os.path.exists("./setup.py") or\
	   not os.path.exists(modDir) or\
	   not os.path.isdir(modDir):
		raise Exception("Wrong directory. "
			"Execute setup.py from within the awlsim directory.")

	os.makedirs(buildDir, 0o755, True)

	for dirpath, dirnames, filenames in os.walk(modDir):
		for filename in filenames:
			if filename.endswith(".py"):
				pyCythonPatch(buildDir + filename,
					      modDir + filename)
				basename = filename[:-3]
				ext_modules.append(
					Extension("awlsim_cython.%s" % basename,
						  ["%s/%s" % (buildDir, filename)])
				)
	cmdclass["build_ext"] = Cython_build_ext

cmdclass = {}
ext_modules = []
if 0:
	try:
		from Cython.Distutils import build_ext as Cython_build_ext
		if sys.version_info[0] >= 3:
			addCythonModules()
	except ImportError:
		pass

setup(	name		= "awlsim",
	version		= "%d.%d" % (VERSION_MAJOR, VERSION_MINOR),
	description	= "Step 7 AWL/STL/PLC simulator",
	author		= "Michael Buesch",
	author_email	= "m@bues.ch",
	url		= "http://bues.ch/cms/hacking/awlsim.html",
	packages	= [ "awlsim",
			    "awlsimhw_dummy",
			    "awlsimhw_linuxcnc",
			    "awlsimhw_pyprofibus", ],
	scripts		= [ "awlsimcli",
			    "awlsimgui",
			    "awlsim-linuxcnc-hal", ],
	cmdclass	= cmdclass,
	ext_modules	= ext_modules
)

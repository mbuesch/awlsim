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
		stripLine = line.strip()

		if not stripLine.endswith("#<no-cython-patch"):
			# Uncomment all lines starting with #>cython
			if stripLine.startswith("#>cython"):
				line = re.sub(r'#>cython\s*', "", line)

			# Comment all lines ending in #<no-cython
			if stripLine.endswith("#<no-cython"):
				line = "#" + line

			# Patch the import statements
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
	os.rename(tmpFile, toFile)

def addCythonModules(Cython_build_ext):
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
		p = dirpath.split("/")
		p = p[p.index("awlsim") + 1 : ]
		p = [ ent for ent in p if ent ]
		subpath = "/".join(p) # Path relative to modDir

		if subpath.startswith("gui"):
			continue
		for filename in filenames:
			if filename == "__init__.py":
				continue
			if filename.endswith(".py"):
				fromFile = dirpath + "/" + filename
				toDir = buildDir + "/" + subpath
				toFile = toDir + "/" + filename.replace(".py", ".pyx")

				os.makedirs(toDir, 0o755, True)
				pyCythonPatch(toFile, fromFile)

				modname = [ "awlsim_cython" ]
				if subpath:
					modname.extend(subpath.split("/"))
				modname.append(filename[:-3]) # Strip .py
				modname = ".".join(modname)

				ext_modules.append(
					Extension(modname, [toFile])
				)
	cmdclass["build_ext"] = Cython_build_ext

def tryBuildCythonModules():
	if sys.version_info[0] < 3:
		print("WARNING: Not building CYTHON modules for Python 2")
		return
	try:
		if int(os.getenv("NOCYTHON", "0")):
			print("Skipping build of CYTHON modules due to "
			      "NOCYTHON environment variable setting.")
			return
	except ValueError:
		pass
	if os.name != "posix":
		print("WARNING: Not building CYTHON modules on '%s' platform." %\
		      os.name)
		return
	try:
		from Cython.Distutils import build_ext as Cython_build_ext
		addCythonModules(Cython_build_ext)
	except ImportError as e:
		print("WARNING: Could not build the CYTHON modules: "
		      "%s" % str(e))
		print("--> Is Cython installed?")

cmdclass = {}
ext_modules = []
# Try to build the Cython modules. This might fail.
tryBuildCythonModules()

setup(	name		= "awlsim",
	version		= "%d.%d" % (VERSION_MAJOR, VERSION_MINOR),
	description	= "Step 7 AWL/STL/PLC simulator",
	author		= "Michael Buesch",
	author_email	= "m@bues.ch",
	url		= "http://bues.ch/cms/hacking/awlsim.html",
	packages	= [ "awlsim",
			    "awlsim/gui",
			    "awlsim/instructions",
			    "awlsimhw_dummy",
			    "awlsimhw_linuxcnc",
			    "awlsimhw_pyprofibus", ],
	scripts		= [ "awlsimcli",
			    "awlsimgui",
			    "awlsim-linuxcnc-hal", ],
	cmdclass	= cmdclass,
	ext_modules	= ext_modules
)

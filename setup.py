#!/usr/bin/env python3

from __future__ import print_function

import sys
import os
import re
from distutils.core import setup
from awlsim.common.version import VERSION_STRING
try:
	import py2exe
except ImportError as e:
	py2exe = None
try:
	if py2exe and "py2exe" in sys.argv:
		raise ImportError
	from cx_Freeze import setup, Executable
	cx_Freeze = True
except ImportError as e:
	cx_Freeze = False

sys.path.insert(0, "./maintenance")
import setup_cython


isWindows = os.name.lower() in {"nt", "ce"}


def getEnvInt(name, default = 0):
	try:
		return int(os.getenv(name, "%d" % default))
	except ValueError:
		return default

def getEnvBool(name, default = False):
	return bool(getEnvInt(name, 1 if default else 0))


fullBuild = getEnvBool("AWLSIM_FULL_BUILD")
buildCython = getEnvBool("AWLSIM_CYTHON", True)
setup_cython.parallelBuild = bool(getEnvInt("AWLSIM_CYTHON_PARALLEL", 1) == 1 or\
				  getEnvInt("AWLSIM_CYTHON_PARALLEL", 1) == sys.version_info[0])
setup_cython.profileEnabled = bool(getEnvInt("AWLSIM_PROFILE") > 0)


def pyCythonPatchLine(line, basicOnly=False):
	# Patch the import statements
	line = re.sub(r'^(\s*from awlsim[0-9a-zA-Z_]*)\.([0-9a-zA-Z_\.]+) import', r'\1_cython.\2 import', line)
	line = re.sub(r'^(\s*from awlsim[0-9a-zA-Z_]*)\.([0-9a-zA-Z_\.]+) cimport', r'\1_cython.\2 cimport', line)
	line = re.sub(r'^(\s*import awlsim[0-9a-zA-Z_]*)\.', r'\1_cython.', line)
	line = re.sub(r'^(\s*cimport awlsim[0-9a-zA-Z_]*)\.', r'\1_cython.', line)
	return line

setup_cython.pyCythonPatchLine = pyCythonPatchLine

cmdclass = {}

# Try to build the Cython modules. This might fail.
if buildCython:
	buildCython = setup_cython.cythonBuildPossible()
if buildCython:
	cmdclass["build_ext"] = setup_cython.CythonBuildExtension
	setup_cython.registerCythonModules()
else:
	print("Skipping build of CYTHON modules.")

ext_modules = setup_cython.ext_modules
extraKeywords = {}

# Workaround for mbcs codec bug in distutils
# http://bugs.python.org/issue10945
import codecs
try:
	codecs.lookup("mbcs")
except LookupError:
	codecs.register(lambda name: codecs.lookup("ascii") if name == "mbcs" else None)


# Create list of scripts. Depends on OS.
scripts = [ "awlsim-gui",
	    "awlsim-client",
	    "awlsim-server",
	    "awlsim-symtab",
	    "awlsim-proupgrade",
	    "awlsim-test", ]
if isWindows or fullBuild:
	scripts.append("awlsim-win.cmd")
if not isWindows or fullBuild:
	scripts.append("awlsim-linuxcnc-hal")
	scripts.append("pilc/pilc-hat-conf")


# Create freeze executable list.
guiBase = None
if isWindows:
	guiBase = "Win32GUI"
freezeExecutables = [ ("awlsim-gui", None, guiBase),
		      ("awlsim-client", None, None),
		      ("awlsim-server", None, None),
		      ("awlsim-symtab", None, None),
		      ("awlsim-proupgrade", None, None),
		      ("awlsim-test", None, None),
		      ("awlsim/coreserver/server.py", "awlsim-server-module", None), ]
if py2exe:
	extraKeywords["console"] = [ s for s, e, b in freezeExecutables ]
if cx_Freeze:
	executables = []
	for script, exe, base in freezeExecutables:
		if exe:
			if isWindows:
				exe += ".exe"
			executables.append(Executable(script = script,
						      targetName = exe,
						      base = base))
		else:
			executables.append(Executable(script = script,
						      base = base))
	extraKeywords["executables"] = executables
	extraKeywords["options"] = {
			"build_exe"     : {
				"packages"      : [ "awlsimhw_debug",
						    "awlsimhw_dummy",
						    "awlsim.library.iec", ],
			}
		}


setup(	name		= "awlsim",
	version		= VERSION_STRING,
	description	= "S7 AWL/STL Soft-PLC",
	license		= "GNU General Public License v2 or later",
	author		= "Michael Buesch",
	author_email	= "m@bues.ch",
	url		= "https://awlsim.de",
	packages	= [ "awlsim",
			    "awlsim_loader",
			    "awlsim/common",
			    "awlsim/core",
			    "awlsim/core/instructions",
			    "awlsim/core/systemblocks",
			    "awlsim/coreclient",
			    "awlsim/coreserver",
			    "awlsim/awlcompiler",
			    "awlsim/awloptimizer",
			    "awlsim/fupcompiler",
			    "awlsim/gui",
			    "awlsim/gui/fup",
			    "awlsim/gui/icons",
			    "awlsim/gui/interfedit",
			    "awlsim/library",
			    "awlsim/library/iec",
			    "awlsimhw_debug",
			    "awlsimhw_dummy",
			    "awlsimhw_linuxcnc",
			    "awlsimhw_pyprofibus",
			    "awlsimhw_rpigpio",
			    "libpilc", ],
	package_dir	= { "libpilc" : "pilc/libpilc", },
	scripts		= scripts,
	cmdclass	= cmdclass,
	ext_modules	= ext_modules,
	keywords	= [ "AWL", "STL", "SPS", "PLC", "Step 7",
			    "Siemens", "emulator", "simulator",
			    "PROFIBUS", "LinuxCNC", ],
	classifiers	= [
		"Development Status :: 4 - Beta",
		"Environment :: Console",
		"Environment :: Win32 (MS Windows)",
		"Environment :: X11 Applications",
		"Intended Audience :: Developers",
		"Intended Audience :: Education",
		"Intended Audience :: Information Technology",
		"Intended Audience :: Manufacturing",
		"Intended Audience :: Science/Research",
		"License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
		"Operating System :: Microsoft :: Windows",
		"Operating System :: POSIX",
		"Operating System :: POSIX :: Linux",
		"Programming Language :: Cython",
		"Programming Language :: Python",
		"Programming Language :: Python :: 2.7",
		"Programming Language :: Python :: 3",
		"Programming Language :: Python :: Implementation :: CPython",
		"Programming Language :: Python :: Implementation :: PyPy",
		"Programming Language :: Python :: Implementation :: Jython",
		"Programming Language :: Python :: Implementation :: IronPython",
		"Topic :: Education",
		"Topic :: Home Automation",
		"Topic :: Scientific/Engineering",
		"Topic :: Software Development",
		"Topic :: Software Development :: Interpreters",
		"Topic :: Software Development :: Embedded Systems",
		"Topic :: Software Development :: Testing",
		"Topic :: System :: Emulators",
	],
	long_description = open("README.md").read(),
	**extraKeywords
)

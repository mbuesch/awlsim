#!/usr/bin/env python3
#
# Awlsim setup.py Python build script.
#
# These environment variables affect the setup.py build:
#
#  AWLSIM_FULL_BUILD:
#	0 (default): Do not include scripts that are not necessary on this platform.
#	1:           Include all scripts; also those that aren't required on the platform.
#
#  AWLSIM_CYTHON_BUILD:
#	0 (default on non-Posix): Do not build any Cython modules.
#	1 (default on Posix):     Build Cython modules.
#
#  AWLSIM_CYTHON_PARALLEL:
#	0:           Do not use parallel compilation for Cython modules.
#	1 (default): Invoke multiple compilers in parallel (faster on multicore).
#
#  AWLSIM_PROFILE:
#	0 (default): Do not enable profiling support in compiled Cython modules.
#	1:           Enable profiling support in compiled Cython modules.
#
#  AWLSIM_DEBUG_BUILD:
#	0 (default): Do not enable debugging support in compiled Cython modules.
#	1:           Enable debugging support in compiled Cython modules.
#

from __future__ import division, absolute_import, print_function
# Avoid __future__.unicode_literals. It breaks on pypy2.

import sys, os
basedir = os.path.abspath(os.path.dirname(__file__))

# Add the basedir and basedir/misc to PYTHONPATH before
# we try to import awlsim.common.version and setup_cython.
for base in (os.getcwd(), basedir):
	sys.path.insert(0, os.path.join(base, "misc"))
	sys.path.insert(0, base)

import re
import warnings
from setuptools import setup
try:
	from cx_Freeze import setup, Executable
	cx_Freeze = True
except ImportError:
	cx_Freeze = False

from awlsim.common.version import VERSION_STRING
import setup_cython


isWindows = os.name.lower() in {"nt", "ce"}
isPosix = os.name.lower() == "posix"


def getEnvInt(name, default = 0):
	try:
		return int(os.getenv(name, "%d" % default))
	except ValueError:
		return default

def getEnvBool(name, default = False):
	return getEnvInt(name, 1 if default else 0) > 0


fullBuild = getEnvBool("AWLSIM_FULL_BUILD")
buildCython = getEnvBool("AWLSIM_CYTHON_BUILD", True if isPosix else False)
setup_cython.parallelBuild = getEnvBool("AWLSIM_CYTHON_PARALLEL", True)
setup_cython.profileEnabled = getEnvBool("AWLSIM_PROFILE")
setup_cython.debugEnabled = getEnvBool("AWLSIM_DEBUG_BUILD")


def pyCythonPatchLine(line):
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

# List of all hardware modules.
hwmodules = [
	"awlsimhw_debug",
	"awlsimhw_dummy",
	"awlsimhw_linuxcnc",
	"awlsimhw_pyprofibus",
	"awlsimhw_rpigpio",
	"awlsimhw_pixtend",
]

# Create freeze executable list.
if cx_Freeze:
	guiBase = "Win32GUI" if isWindows else None
	freezeExecutables = [
		("awlsim-gui", None, guiBase),
		("awlsim-client", None, None),
		("awlsim-server", None, None),
		("awlsim-symtab", None, None),
		("awlsim-proupgrade", None, None),
		("awlsim-test", None, None),
		("awlsim/coreserver/run.py", "awlsim-server-module", None),
	]
	executables = []
	for script, exe, base in freezeExecutables:
		if exe:
			if isWindows:
				exe += ".exe"
			executables.append(Executable(script=script,
						      targetName=exe,
						      base=base))
		else:
			executables.append(Executable(script=script,
						      base=base))
	extraKeywords["executables"] = executables
	extraKeywords["options"] = {
			"build_exe" : {
				"packages" : hwmodules + [ "awlsim.library.iec", ],
			}
		}

warnings.filterwarnings("ignore", r".*'python_requires'.*")
warnings.filterwarnings("ignore", r".*'long_description_content_type'.*")

with open(os.path.join(basedir, "README.md"), "rb") as fd:
	readmeText = fd.read().decode("UTF-8")

setup(	name		= "awlsim",
	version		= VERSION_STRING,
	description	= "S7 compatible Programmable Logic Controller PLC/SPS (AWL, STL, FUP, FBD)",
	license		= "GNU General Public License v2 or later",
	author		= "Michael Buesch",
	author_email	= "m@bues.ch",
	url		= "https://awlsim.de",
	python_requires = ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*",
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
			  ] + hwmodules,
	scripts		= scripts,
	cmdclass	= cmdclass,
	ext_modules	= ext_modules,
	keywords	= "AWL STL FUP FBD SPS PLC emulator simulator "
			  "Step-7 Siemens PROFIBUS "
			  "LinuxCNC PiXtend RaspberryPi",
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
		"Topic :: Education",
		"Topic :: Home Automation",
		"Topic :: Scientific/Engineering",
		"Topic :: Software Development",
		"Topic :: Software Development :: Interpreters",
		"Topic :: Software Development :: Embedded Systems",
		"Topic :: Software Development :: Testing",
		"Topic :: System :: Emulators",
	],
	long_description=readmeText,
	long_description_content_type="text/markdown",
	**extraKeywords
)

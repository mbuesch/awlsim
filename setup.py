#!/usr/bin/env python3

from __future__ import print_function

import sys
import os
import platform
import errno
import re
import shutil
import hashlib
from distutils.core import setup
from distutils.extension import Extension
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


def makedirs(path, mode=0o755):
	try:
		os.makedirs(path, mode)
	except OSError as e:
		if e.errno == errno.EEXIST:
			return
		raise

def hashFile(path):
	if sys.version_info[0] < 3:
		ExpectedException = IOError
	else:
		ExpectedException = FileNotFoundError
	try:
		return hashlib.sha1(open(path, "rb").read()).hexdigest()
	except ExpectedException as e:
		return None

def __fileopIfChanged(fromFile, toFile, fileop):
	toFileHash = hashFile(toFile)
	if toFileHash is not None:
		fromFileHash = hashFile(fromFile)
		if toFileHash == fromFileHash:
			return False
	makedirs(os.path.dirname(toFile))
	fileop(fromFile, toFile)
	return True

def copyIfChanged(fromFile, toFile):
	return __fileopIfChanged(fromFile, toFile, shutil.copy2)

def moveIfChanged(fromFile, toFile):
	return __fileopIfChanged(fromFile, toFile, os.rename)

def makeDummyFile(path):
	if os.path.isfile(path):
		return
	print("creating dummy file '%s'" % path)
	makedirs(os.path.dirname(path))
	fd = open(path, "w")
	fd.write("\n")
	fd.close()

def pyCythonPatch(fromFile, toFile, basicOnly=False):
	print("cython-patch: patching file '%s' to '%s'" %\
	      (fromFile, toFile))
	tmpFile = toFile + ".TMP"
	makedirs(os.path.dirname(tmpFile))
	infd = open(fromFile, "r")
	outfd = open(tmpFile, "w")
	for line in infd.readlines():
		stripLine = line.strip()

		if stripLine.endswith("#<no-cython-patch"):
			outfd.write(line)
			continue

		# Uncomment all lines containing #@cy
		if "#@cy" in stripLine:
			line = line.replace("#@cy", "")
			if line.startswith("#"):
				line = line[1:]
			if not line.endswith("\n"):
				line += "\n"

		# Sprinkle magic cdef, as requested by #+cdef
		if "#+cdef" in stripLine:
			if stripLine.startswith("class"):
				line = line.replace("class", "cdef class")
			else:
				line = line.replace("def", "cdef")

		# Comment all lines containing #@nocy
		if "#@nocy" in stripLine:
			line = "#" + line

		if not basicOnly:
			# Automagic types
			line = re.sub(r'\b_Bool\b', "unsigned char", line)
			line = re.sub(r'\bint8_t\b', "signed char", line)
			line = re.sub(r'\buint8_t\b', "unsigned char", line)
			line = re.sub(r'\bint16_t\b', "signed short", line)
			line = re.sub(r'\buint16_t\b', "unsigned short", line)
			line = re.sub(r'\bint32_t\b', "signed int", line)
			line = re.sub(r'\buint32_t\b', "unsigned int", line)
			line = re.sub(r'\bint64_t\b', "signed long long", line)
			line = re.sub(r'\buint64_t\b', "unsigned long long", line)

			# Remove compat stuff
			line = line.replace("absolute_import,", "")

		# Patch the import statements
		line = re.sub(r'^(\s*from awlsim[0-9a-zA-Z_]*)\.([0-9a-zA-Z_\.]+) import', r'\1_cython.\2 import', line)
		line = re.sub(r'^(\s*from awlsim[0-9a-zA-Z_]*)\.([0-9a-zA-Z_\.]+) cimport', r'\1_cython.\2 cimport', line)
		line = re.sub(r'^(\s*import awlsim[0-9a-zA-Z_]*)\.', r'\1_cython.', line)
		line = re.sub(r'^(\s*cimport awlsim[0-9a-zA-Z_]*)\.', r'\1_cython.', line)

		outfd.write(line)
	infd.close()
	outfd.flush()
	outfd.close()
	if not moveIfChanged(tmpFile, toFile):
		print("(already up to date)")
		os.unlink(tmpFile)

class CythonBuildUnit(object):
	def __init__(self, cyModName, baseName, fromPy, fromPxd, toDir, toPyx, toPxd):
		self.cyModName = cyModName
		self.baseName = baseName
		self.fromPy = fromPy
		self.fromPxd = fromPxd
		self.toDir = toDir
		self.toPyx = toPyx
		self.toPxd = toPxd

cythonBuildUnits = []

def patchCythonModules(buildDir):
	for unit in cythonBuildUnits:
		makedirs(unit.toDir)
		makeDummyFile(os.path.join(unit.toDir, "__init__.py"))
		if unit.baseName == "__init__":
			# Copy and patch the package __init__.py
			toPy = os.path.join(buildDir, *unit.cyModName.split(".")) + ".py"
			pyCythonPatch(unit.fromPy, toPy,
				      basicOnly=True)
		else:
			# Generate the .pyx
			pyCythonPatch(unit.fromPy, unit.toPyx)
		# Copy and patch the .pxd, if any
		if os.path.isfile(unit.fromPxd):
			pyCythonPatch(unit.fromPxd, unit.toPxd)

def registerCythonModule(baseDir, sourceModName):
	global ext_modules
	global cythonBuildUnits

	modDir = os.path.join(baseDir, sourceModName)
	# Make path to the cython patch-build-dir
	patchDir = os.path.join(baseDir, "build",
		"cython_patched.%s-%s-%d.%d" %\
		(platform.system().lower(),
		 platform.machine().lower(),
		 sys.version_info[0], sys.version_info[1]),
		"%s_cython" % sourceModName
	)

	if not os.path.exists(os.path.join(baseDir, "setup.py")) or\
	   not os.path.exists(modDir) or\
	   not os.path.isdir(modDir):
		raise Exception("Wrong directory. "
			"Execute setup.py from within the awlsim directory.")

	# Walk the "awlsim" module
	for dirpath, dirnames, filenames in os.walk(modDir):
		subpath = os.path.relpath(dirpath, modDir)
		if subpath == baseDir:
			subpath = ""

		if subpath.startswith("gui"):
			continue
		for filename in filenames:
			if not filename.endswith(".py"):
				continue
			baseName = filename[:-3] # Strip .py

			fromPy = os.path.join(dirpath, baseName + ".py")
			fromPxd = os.path.join(dirpath, baseName + ".pxd.in")
			toDir = os.path.join(patchDir, subpath)
			toPyx = os.path.join(toDir, baseName + ".pyx")
			toPxd = os.path.join(toDir, baseName + ".pxd")

			# Construct the new cython module name
			cyModName = [ "%s_cython" % sourceModName ]
			if subpath:
				cyModName.extend(subpath.split(os.sep))
			cyModName.append(baseName)
			cyModName = ".".join(cyModName)

			# Remember the filenames for the build
			unit = CythonBuildUnit(cyModName, baseName, fromPy, fromPxd,
					       toDir, toPyx, toPxd)
			cythonBuildUnits.append(unit)

			if baseName != "__init__":
				# Create a distutils Extension for the module
				ext_modules.append(
					Extension(cyModName, [toPyx])
				)

def registerCythonModules():
	baseDir = os.curdir # Base directory, where setup.py lives.

	for filename in os.listdir(baseDir):
		if filename == "awlsim" or\
		   filename.startswith("awlsimhw_"):
			registerCythonModule(baseDir, filename)

def tryBuildCythonModules():
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
	if "bdist_wininst" in sys.argv:
		print("WARNING: Omitting CYTHON modules while building "
		      "Windows installer.")
		return
	try:
		from Cython.Distutils import build_ext as Cython_build_ext
	except ImportError as e:
		print("WARNING: Could not build the CYTHON modules: "
		      "%s" % str(e))
		print("--> Is Cython installed?")
		return

	class MyCythonBuildExt(Cython_build_ext):
		def build_extension(self, ext):
			assert(not ext.name.endswith("__init__"))
			Cython_build_ext.build_extension(self, ext)

		def build_extensions(self):
			# First patch the files, the run the normal build
			patchCythonModules(self.build_lib)
			Cython_build_ext.build_extensions(self)

	cmdclass["build_ext"] = MyCythonBuildExt
	registerCythonModules()

cmdclass = {}
ext_modules = []
extraScripts = []
extraKeywords = {}
# Try to build the Cython modules. This might fail.
tryBuildCythonModules()

# Workaround for mbcs codec bug in distutils
# http://bugs.python.org/issue10945
import codecs
try:
	codecs.lookup("mbcs")
except LookupError:
	codecs.register(lambda name: codecs.lookup("ascii") if name == "mbcs" else None)

# Add win postinstall script
try:
	idx = sys.argv.index("bdist_wininst")
	if idx > 0:
		sys.argv.insert(idx + 1, "--install-script")
		sys.argv.insert(idx + 2, "awlsim-wininst-postinstall.py")
		extraScripts.append("awlsim-wininst-postinstall.py")
except ValueError:
	pass

freezeExecutables = [ ("awlsim-cli", None),
		      ("awlsim-gui", None),
		      ("awlsim-server", None),
		      ("awlsim-symtab", None),
		      ("awlsim/coreserver/server.py", "awlsim-server-module"), ]
if py2exe:
	extraKeywords["console"] = [ s for s, e in freezeExecutables ]
if cx_Freeze:
	executables = []
	for script, exe in freezeExecutables:
		if exe:
			if os.name.lower() in ("nt", "ce"):
				exe += ".exe"
			executables.append(Executable(script = script,
						      targetName = exe))
		else:
			executables.append(Executable(script = script))
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
	url		= "http://bues.ch/h/awlsim",
	packages	= [ "awlsim",
			    "awlsim/common",
			    "awlsim/core",
			    "awlsim/core/instructions",
			    "awlsim/core/systemblocks",
			    "awlsim/coreclient",
			    "awlsim/coreserver",
			    "awlsim/gui",
			    "awlsim/gui/icons",
			    "awlsim/library",
			    "awlsim/library/iec",
			    "awlsimhw_debug",
			    "awlsimhw_dummy",
			    "awlsimhw_linuxcnc",
			    "awlsimhw_pyprofibus", ],
	scripts		= [ "awlsim-cli",
			    "awlsim-gui",
			    "awlsim-server",
			    "awlsim-symtab",
			    "awlsim-linuxcnc-hal",
			    "awlsim-win.bat", ] + extraScripts,
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
	long_description = open("README.txt").read(),
	**extraKeywords
)

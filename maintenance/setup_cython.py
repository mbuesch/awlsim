#
#   Cython patcher
#   v1.6
#
#   Copyright (C) 2012-2017 Michael Buesch <m@bues.ch>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import print_function

import sys
import os
import platform
import errno
import shutil
import hashlib
import re


parallelBuild = False
profileEnabled = False
ext_modules = []
CythonBuildExtension = None


_Cython_Distutils_build_ext = None
_cythonPossible = None
_cythonBuildUnits = []


def makedirs(path, mode=0o755):
	try:
		os.makedirs(path, mode)
	except OSError as e:
		if e.errno == errno.EEXIST:
			return
		raise e

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

def pyCythonPatchLine(line, basicOnly=False):
	return line

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

		# Replace import by cimport as requested by #+cimport
		if "#+cimport" in stripLine:
			line = line.replace("#+cimport", "#")
			line = re.sub(r'\bimport\b', "cimport", line)

		# Convert None to NULL
		if "#@cy-NoneToNULL" in stripLine:
			line = line.replace("#@cy-NoneToNULL", "#")
			line = re.sub(r'\bNone\b', "NULL", line)

		# Uncomment all lines containing #@cy
		def uncomment(line, removeStr):
			line = line.replace(removeStr, "")
			if line.startswith("#"):
				line = line[1:]
			if not line.endswith("\n"):
				line += "\n"
			return line
		if "#@cy" in stripLine and\
		   not "#@cy2" in stripLine and\
		   not "#@cy3" in stripLine:
			line = uncomment(line, "#@cy")
		if sys.version_info[0] < 3:
			if "#@cy2" in stripLine:
				line = uncomment(line, "#@cy2")
		else:
			if "#@cy3" in stripLine:
				line = uncomment(line, "#@cy3")

		# Sprinkle magic cdef/cpdef, as requested by #+cdef/#+cpdef
		if "#+cdef-" in stripLine:
			# +cdef-foo-bar is the extended cdef patching.
			# It adds cdef and any additional characters to the
			# start of the line. Dashes are replaced with spaces.

			# Get the additional text
			idx = line.find("#+cdef-")
			cdefText = line[idx+2 : ]
			cdefText = cdefText.replace("-", " ").rstrip("\r\n")

			# Get the initial space length
			spaceCnt = 0
			while spaceCnt < len(line) and line[spaceCnt].isspace():
				spaceCnt += 1

			# Construct the new line
			line = line[ : spaceCnt] + cdefText + " " + line[spaceCnt : ]
		elif "#+cdef" in stripLine:
			# Simple cdef patching:
			# def -> cdef
			# class -> cdef class

			if stripLine.startswith("class"):
				line = re.sub(r'\bclass\b', "cdef class", line)
			else:
				line = re.sub(r'\bdef\b', "cdef", line)
		if "#+cpdef" in stripLine:
			# Simple cpdef patching:
			# def -> cpdef

			line = re.sub(r'\bdef\b', "cpdef", line)

		# Comment all lines containing #@nocy
		# or #@cyX for the not matching version.
		if "#@nocy" in stripLine:
			line = "#" + line
		if sys.version_info[0] < 3:
			if "#@cy3" in stripLine:
				line = "#" + line
		else:
			if "#@cy2" in stripLine:
				line = "#" + line

		if not basicOnly:
			# Automagic types
			line = re.sub(r'\b_Bool\b', "bint", line)
			line = re.sub(r'\bExBool_t\b', "signed char", line)
			line = re.sub(r'\bExBool_val\b', "-1", line)
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

		line = pyCythonPatchLine(line, basicOnly)

		outfd.write(line)
	infd.close()
	outfd.flush()
	outfd.close()
	if moveIfChanged(tmpFile, toFile):
		print("(updated)")
	else:
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

def patchCythonModules(buildDir):
	for unit in _cythonBuildUnits:
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
	global _cythonBuildUnits

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
			"Execute setup.py from within the main directory.")

	# Walk the module
	for dirpath, dirnames, filenames in os.walk(modDir):
		subpath = os.path.relpath(dirpath, modDir)
		if subpath == baseDir:
			subpath = ""

		dirpathList = dirpath.split(os.path.sep)

		if any(os.path.exists(os.path.sep.join(dirpathList[:i] + ["no_cython"]))
		       for i in range(len(dirpathList) + 1)):
			# no_cython file exists. -> skip
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
			_cythonBuildUnits.append(unit)

			if baseName != "__init__":
				# Create a distutils Extension for the module
				ext_modules.append(
					_Cython_Distutils_Extension(
						cyModName,
						[toPyx],
						cython_directives={
							"profile" : profileEnabled,
						}
					)
				)

def registerCythonModules():
	baseDir = os.curdir # Base directory, where setup.py lives.

	for filename in os.listdir(baseDir):
		if os.path.isdir(os.path.join(baseDir, filename)) and\
		   os.path.exists(os.path.join(baseDir, filename, "__init__.py")) and\
		   not os.path.exists(os.path.join(baseDir, filename, "no_cython")):
			registerCythonModule(baseDir, filename)

def cythonBuildPossible():
	global _cythonPossible

	if _cythonPossible is not None:
		return _cythonPossible

	_cythonPossible = False

	if os.name != "posix":
		print("WARNING: Not building CYTHON modules on '%s' platform." %\
		      os.name)
		return False
	if "bdist_wininst" in sys.argv:
		print("WARNING: Omitting CYTHON modules while building "
		      "Windows installer.")
		return False
	try:
		from Cython.Distutils import build_ext, Extension
		global _Cython_Distutils_build_ext
		global _Cython_Distutils_Extension
		_Cython_Distutils_build_ext = build_ext
		_Cython_Distutils_Extension = Extension
	except ImportError as e:
		print("WARNING: Could not build the CYTHON modules: "
		      "%s" % str(e))
		print("--> Is Cython installed?")
		return False

	_cythonPossible = True
	return True

if sys.version_info[0] < 3:
	# Cython2 build libraries need method pickling
	# for parallel build.
	def unpickle_method(fname, obj, cls):
		# Ignore MRO. We don't seem to inherit methods.
		return cls.__dict__[fname].__get__(obj, cls)
	def pickle_method(m):
		return unpickle_method, (m.im_func.__name__,
					 m.im_self,
					 m.im_class)
	import copy_reg, types
	copy_reg.pickle(types.MethodType, pickle_method, unpickle_method)

def cyBuildWrapper(arg):
	# This function does the same thing as the for-loop-body
	# inside of Cython's build_ext.build_extensions() method.
	# It is called via multiprocessing to build extensions
	# in parallel.
	# Note that this might break, if Cython's build_extensions()
	# is changed and stuff is added to its for loop. Meh.
	self, ext = arg
	ext.sources = self.cython_sources(ext.sources, ext)
	self.build_extension(ext)

if cythonBuildPossible():
	# Override Cython's build_ext class.
	class CythonBuildExtension(_Cython_Distutils_build_ext):
		def build_extension(self, ext):
			assert(not ext.name.endswith("__init__"))
			_Cython_Distutils_build_ext.build_extension(self, ext)

		def build_extensions(self):
			global parallelBuild

			# First patch the files, the run the build
			patchCythonModules(self.build_lib)

			if parallelBuild:
				# Run the parallel build, yay.
				try:
					self.check_extensions_list(self.extensions)
					from multiprocessing.pool import Pool
					Pool().map(cyBuildWrapper,
						   ((self, ext) for ext in self.extensions))
				except OSError as e:
					# This might happen in a restricted
					# environment like chroot.
					print("WARNING: Parallel build "
					      "disabled due to: %s" % str(e))
					parallelBuild = False
			if not parallelBuild:
				# Run the normal non-parallel build.
				_Cython_Distutils_build_ext.build_extensions(self)

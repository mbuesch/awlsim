#
#  Build Awlsim Cython test cases
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#

from __future__ import division, absolute_import, print_function
# Avoid __future__.unicode_literals. It breaks on pypy2.

import sys, os, re

basedir = os.path.abspath(os.path.dirname(__file__))

# Add the basedir and basedir/misc to PYTHONPATH before
# we try to import setup_cython.
for base in (os.getcwd(), basedir):
	sys.path.insert(0, os.path.join(base, "..", "misc"))
	sys.path.insert(0, base)
from setuptools import setup
import setup_cython


# Find the test case directories.
packages = []
for tc_dir in os.listdir(basedir):
	if not re.match(r"^tc\d\d\d_[\w\d_\-]+$", tc_dir):
		continue
	tc_dir = os.path.join(basedir, tc_dir)
	if not os.path.isdir(tc_dir):
		continue
	for dirpath, dirnames, filenames in os.walk(tc_dir):
		if "no_cython" in filenames:
			continue
		if not any(f.endswith(".py") and f != "__init__.py"
			   for f in filenames):
			continue
		packages.append(os.path.relpath(dirpath, basedir))
		# Generate an __init__.py, so that the directory
		# is a valid Python package.
		initpy = os.path.join(tc_dir, "__init__.py")
		if not os.path.exists(initpy):
			with open(initpy, "w") as fd:
				fd.write("# GENERATED dummy __init__.py file\n")
print("Discovered test case packages:", ", ".join(packages))


# Setup Cython build.

def pyCythonPatchLine(line):
	# Patch the import statements
	line = re.sub(r'^(\s*from awlsim[0-9a-zA-Z_]*)\.([0-9a-zA-Z_\.]+) import', r'\1_cython.\2 import', line)
	line = re.sub(r'^(\s*from awlsim[0-9a-zA-Z_]*)\.([0-9a-zA-Z_\.]+) cimport', r'\1_cython.\2 cimport', line)
	line = re.sub(r'^(\s*import awlsim[0-9a-zA-Z_]*)\.', r'\1_cython.', line)
	line = re.sub(r'^(\s*cimport awlsim[0-9a-zA-Z_]*)\.', r'\1_cython.', line)
	return line

os.environ["CFLAGS"] = os.environ["CXXFLAGS"] = "-O0"
os.environ["CPPFLAGS"] = ""
os.environ["LDFLAGS"] = ""
if not setup_cython.cythonBuildPossible():
	print("ERROR: Cannot build Cython modules.", file=sys.stderr)
	sys.exit(1)
cmdclass = {}
cmdclass["build_ext"] = setup_cython.CythonBuildExtension
setup_cython.setupFileName = os.path.basename(__file__)
setup_cython.parallelBuild = True
setup_cython.pyCythonPatchLine = pyCythonPatchLine
setup_cython.registerCythonModules()
ext_modules = setup_cython.ext_modules


# Create links to the awlsim packages.
awlsimBuildPatchDir = os.path.join("..", "build", setup_cython.patchDirName)
if not os.path.isdir(awlsimBuildPatchDir):
	print(("Awlsim build directory '%s' does not exist.\n"
	       "Has awlsim been built?") % awlsimBuildPatchDir,
	      file=sys.stderr)
	sys.exit(1)
for awlsimPack in os.listdir(awlsimBuildPatchDir):
	linkFrom = os.path.join("..", "..", awlsimBuildPatchDir, awlsimPack)
	linkToDir = os.path.join("build", setup_cython.patchDirName)
	linkTo = os.path.join(linkToDir, awlsimPack)
	if not os.path.lexists(linkTo):
		print("Linking awlsim package '%s' to '%s'" % (linkFrom, linkTo))
		os.makedirs(linkToDir, exist_ok=True)
		os.symlink(linkFrom, linkTo)


setup(	name		= "awlsim-cython-unittests",
	packages	= packages,
	cmdclass	= cmdclass,
	ext_modules	= ext_modules,
)

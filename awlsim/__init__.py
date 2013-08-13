import os
import sys

try:
	awlsim_useCython = bool(int(os.getenv("AWLSIMCYTHON", "0")))
except ValueError:
	awlsim_useCython = False

if awlsim_useCython:
	try:
		from awlsim_cython.util import *
		from awlsim_cython.version import *
		from awlsim_cython.main import *
		from awlsim_cython.parser import *
	except ImportError as e:
		sys.stderr.write("WARNING: Failed to import awlsim CYTHON core: "
				 "%s\n" % str(e))
		sys.stderr.write("--> Falling back to standard core...\n")
		sys.stderr.flush()
		awlsim_useCython = False

if not awlsim_useCython:
	from awlsim.util import *
	from awlsim.version import *
	from awlsim.main import *
	from awlsim.parser import *

#!/usr/bin/env python3

from distutils.core import setup
from awlsim.main import VERSION_MAJOR, VERSION_MINOR

setup(	name		= "awlsim",
	version		= "%d.%d" % (VERSION_MAJOR, VERSION_MINOR),
	description	= "Step 7 AWL/STL/PLC simulator",
	author		= "Michael Buesch",
	author_email	= "m@bues.ch",
	url		= "http://bues.ch/cms/hacking/awlsim.html",
	packages	= [ "awlsim", ],
	scripts		= [ "awlsimcli", "awlsimgui", ],
)

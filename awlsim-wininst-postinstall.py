#! python

import sys
import os

try:
	if sys.argv[1] == "-install":
		wrapper = os.path.join(sys.prefix, "Scripts", "awlsim-win.bat")
		for d in (get_special_folder_path("CSIDL_COMMON_STARTMENU"),
			  get_special_folder_path("CSIDL_STARTMENU")):
			if os.path.isdir(d):
				shortcut = os.path.join(d, "Awlsim.lnk")
				create_shortcut(wrapper, "Awlsim", shortcut)
				file_created(shortcut)
				break
except Exception as e:
	print(str(e))
	raise

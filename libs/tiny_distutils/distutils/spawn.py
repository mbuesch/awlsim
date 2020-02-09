__all__ = [ "find_executable", ]

import os
import os.path

def find_executable(executable, path=None):
	if executable:
		if executable.startswith(os.path.sep):
			if (os.access(executable, os.X_OK) and
			    not os.path.isdir(executable)):
				return executable
		else:
			if path is None:
				path = os.getenv("PATH", "")
			for p in path.split(":"):
				fullpath = os.path.join(p, executable)
				if (os.access(fullpath, os.X_OK) and
				    not os.path.isdir(fullpath)):
					return fullpath
	return None

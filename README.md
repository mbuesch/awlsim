# Awlsim - S7 compatible Programmable Logic Controller (PLC/SPS)

Awlsim is a free Step 7 compatible Programmable Logic Controller, that supports the automation languages AWL/STL and FUP/FBD. Awlsim itself is written in Python.

The latest version of Awlsim can be downloaded at the [official Awlsim site](https://awlsim.de).


## Awlsim - Programmable Logic Controller (PLC/SPS)

Awlsim is a free Step 7 compatible Programmable Logic Controller, that supports the automation languages AWL/STL and FUP/FBD. Awlsim itself is written in Python. The speed of execution ranges from several ten thousand AWL/STL instructions per second on slow embedded machines to a couple of million instructions per second on faster computers.

AWL/STL programs on PLCs are used for automation of industrial processes. However Awlsim is very flexible, so it can be used for other purposes beyond industrial applications, too. Awlsim aims to be compatible with the industry standard S7 software on the AWL/STL level.

Awlsim can emulate CPUs with two and four accumulator registers (S7-3xx and S7-4xx). Compatibility to S7 hardware is a task taken seriously by the Awlsim project. We want to be as close as possible to the real PLC hardware with our AWL/STL code execution. For this reason Awlsim ships an extensive selftest suite. Missing features and differences between Awlsim and Step 7 are documented in the [COMPATIBILITY documentation](COMPATIBILITY.html) and [TODO documentation](TODO.html) files.


## Quick start tutorial

See the [quick start tutorial](QUICK-START.html) for a simple example on how to use Awlsim in simulator mode. In simulator mode Awlsim can be run on any desktop PC. No special hardware is required.


## Example project

If you don't know where to start, you can find an example project in the `examples` directory as `EXAMPLE.awlpro`. You can easily run this example in simulation mode without the need for special hardware.


## Git repository

The latest development version of Awlsim can be fetched with git:

<pre>
git clone https://git.bues.ch/git/awlsim.git
cd awlsim
</pre>

After cloning the main repository the git submodules must also be fetched. The following helper script can be used:

<pre>
./maintenance/update-submodules
</pre>


## Dependencies

Awlsim depends on

* [Python](https://python.org) 3.4 or later or alternatively Python 2.7
* [PyQT 5](https://www.riverbankcomputing.com/software/pyqt/intro) or alternatively [PySide](https://wiki.qt.io/PySide)
* [CFFI](http://cffi.readthedocs.org/)

These packages can be installed with pip:

<pre>
pip3 install --upgrade PyQt5
pip3 install --upgrade cffi
</pre>

If building and using Awlsim with Cython acceleration is desired, Cython must also be installed:

<pre>
pip3 install --upgrade Cython
</pre>

On Windows all Awlsim dependencies can be installed by double clicking the shipped installer script: *maintenance\win-install-dependencies.cmd*

For Debian Linux users the script *maintenance/deb-dependencies-install.sh* installs all required and optional runtime and build dependencies.

## Directory structure

The Awlsim Git repository and source archive `awlsim-x.yz.tar.bz2` contain lots of files and directories. Here is an overview of the main files and directories and their purpose:

### Main executables
User interface executables. The main user executable is `awlsim-gui`.
<pre>
  awlsim-client             : Command line client tool.
  awlsim-gui                : Graphical user interface. This is the main user frontend.
  awlsim-linuxcnc-hal       : LinuxCNC HAL module executable.
  awlsim-proupgrade         : Command line tool to update .awlpro file formats.
  awlsim-server             : Command line server tool.
  awlsim-symtab             : Command line tool to parse symbol tables (.ASC).
  awlsim-test               : Command line tool for unit testing.
                              See tests/run.sh for execution of unit tests.
  awlsim-win.cmd            : Windows wrapper for awlsim-gui.
</pre>

### Documentation
These files and directories contain useful information about Awlsim.
<pre>
  doc/                      : Main documentation.
  doc/fup/                  : Awlsim FUP language and editor documentation.
  examples/                 : Various example projects and feature demonstrations.
  COMPATIBILITY.md|html     : S7 compatibility documentation.
  COPYING.txt               : Main license.
  DEVELOPMENT.md|html       : How to enhance and develop Awlsim.
  QUICK-START.md|html       : Quick start tutorial.
  README.md|html            : Main README document.
  TODO.md|html              : TODO list.
</pre>

### Main modules
The main modules implement most of Awlsim's functionality.
<pre>
  awlsim/                   : Main Awlsim Python-module directory. This is where the magic happens.
  awlsim/awlcompiler        : AWL compiler.
  awlsim/awloptimizer       : AWL optimizer.
  awlsim/common             : Common libraries, modules and helper functions.
  awlsim/core               : AWL interpreter core. This is where the AWL program is executed.
  awlsim/core/instructions  : Implementation of AWL instructions.
  awlsim/core/systemblocks  : Implementation of SFCs and SFBs.
  awlsim/coreclient         : Client library to connect to coreserver.
  awlsim/coreserver         : Server library to provide AWL interpreter core access via networking.
  awlsim/fupcompiler        : FUP compiler.
  awlsim/gui                : Graphical user interface implementation (Qt).
  awlsim/library            : AWL block (FC and FB) libraries.
  awlsim/library/iec        : Implementation of IEC FCs and FBs.
  awlsim_loader/            : Import wrapper for the main Awlsim Python-module.
                              This is used to automatically load Cython optimized modules.
  libs/                     : External libraries used for running or testing Awlsim.
  progs/                    : External programs used in Awlsim.
  submodules/               : Git submodules used for running Awlsim.
                              See  man git-submodule  for general help about Git submodules.
  submodules/pyprofibus/    : PROFIBUS-DP implementation.
  tests/                    : Unit test cases.
  tests/run.sh              : Main interface to run unit tests. Please see --help
</pre>

### Hardware support modules
The hardware modules are the glue between the Awlsim core and the real world. The hardware modules are invoked before and after running the user cycle (OB 1).
<pre>
  awlsimhw_debug/           : Hardware module for unit tests. Do not use in production.
  awlsimhw_dummy/           : Dummy no-operation hardware module for testing, debugging or simulation.
  awlsimhw_linuxcnc/        : LinuxCNC hardware support module.
  awlsimhw_pixtend/         : PiXtend hardware support module.
  awlsimhw_pyprofibus/      : PROFIBUS-DP hardware support module.
  awlsimhw_pyprofibus.conf  : Configuration file for awlsimhw_pyprofibus.
  awlsimhw_rpigpio/         : Raspberry Pi GPIO hardware support module.
</pre>

### Misc
<pre>
  awlsim-server.service.in  : Systemd unit template for awlsim-server.
  debian/                   : Debian packaging support.
  maintenance/              : Maintainer scripts.
  misc/                     : Miscellaneous scripts and files.
  pilc/                     : PiLC distribution build scripts.
  setup.py                  : Python package build script. This also builds the Cython modules.
</pre>


## FUP - Funktionsplan - Function block diagram

Awlsim supports programming in an S7-FUP like language. See [the FUP documentation](doc/fup/FUP.html) for more information about Awlsim's implementation of FUP.


## Building Awlsim

Awlsim can be run from the source directory in interpreted Python mode without building it. Just `cd` into the Awlsim source directory and execute the desired main executable (e.g. `./awlsim-gui` or `./awlsim-server` etc...).

The accelerated Cython libraries can be built with the standard Python `./setup.py build` command.

For convenience there also is a helper script `./maintenance/build.sh`, which will do everything right to build Awlsim. That can be used instead of calling setup.py directly.

There also is `./maintenance/build-noopt.sh`. That builds Cython modules without optimization. The build is much faster, but the resulting Cython libraries will be much slower. This is useful for development. Do not use this for production.


## Building Debian / Raspbian / PiLC .deb packages

Installing or upgrading Awlsim on a Debian based system is easy.
The `debuild` can be used to build the .deb packages. Just run the following commands to build all Awlsim .deb packages:

<pre>
cd path/to/awlsim                                 # Go to Awlsim source directory
sudo ./maintenance/deb-dependencies-install.sh    # This installs all dependencies
debuild -uc -us                                   # Build all Awlsim .deb packages
sudo ./maintenance/deb-install.sh ..              # Install or upgrade all Awlsim .deb packages
</pre>

The .deb files will be put into the parent directory of the Awlsim source directory.

If you get the following build failure during build:

`/usr/include/features.h:xxx:xx: fatal error: sys/cdefs.h: No such file or directory`

this can be fixed by re-installing the libc development package:

`sudo apt install --reinstall libc-dev`


## Development

Information about Awlsim development can be found in [the Awlsim development documentation](DEVELOPMENT.html).


## License / Copyright

Copyright (C) Michael Büsch / et al.

Awlsim is Open Source Free Software licensed under the GNU General Public License v2+. That means it's available in full source code and you are encouraged to improve it and contribute your changes back to the community. Awlsim is free of charge, too. 

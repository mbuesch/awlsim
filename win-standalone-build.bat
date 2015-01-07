@echo off

SET PATH=%PATH%;C:\WINDOWS;C:\WINDOWS\SYSTEM32;C:\PYTHON34;%ProgramFiles%\7-Zip

py -c "from awlsim.common.version import VERSION_STRING; print(VERSION_STRING)" > version.txt
set /p version= < version.txt
del version.txt

set distdir=awlsim-win-standalone-%version%
set zipfile=awlsim-win-standalone-%version%.zip
set bindir=%distdir%\awlsim-bin

rd /S /Q build 2>NUL
rd /S /Q %distdir% 2>NUL
del %zipfile% 2>NUL

echo Building standalone Windows executable for awlsim v%version%...
echo Please select:
echo   1)  Build 'cx_Freeze' based distribution (default)
echo   2)  Build 'py2exe' based distribution
set /p buildtype=Selection: 
if "%buildtype%" == "" goto build_cxfreeze
if "%buildtype%" == "1" goto build_cxfreeze
if "%buildtype%" == "2" goto build_py2exe
echo "Error: Invalid selection"
pause
exit


:build_cxfreeze
set buildtype=1
echo === Creating the cx_Freeze distribution
timeout /T 2 /NOBREAK >NUL
mkdir %distdir%
if ERRORLEVEL 1 goto error_prep
mkdir %bindir%
if ERRORLEVEL 1 goto error_prep
py setup.py build_exe ^
	--build-exe=%bindir% ^
	--optimize=2 ^
	--silent
if ERRORLEVEL 1 goto error_exe
goto copy_files


:build_py2exe
set buildtype=2
echo === Creating the py2exe distribution
timeout /T 2 /NOBREAK >NUL
mkdir %distdir%
if ERRORLEVEL 1 goto error_prep
mkdir %bindir%
if ERRORLEVEL 1 goto error_prep
py setup.py py2exe ^
	--dist-dir=%bindir% ^
	--optimize=2 ^
	--bundle-files=3 ^
	--ignores=win32api,win32con,readline,awlsim_cython ^
	--packages=awlsimhw_debug,awlsimhw_dummy,awlsim.library.iec ^
	--quiet
if ERRORLEVEL 1 goto error_exe
goto copy_files


:copy_files
echo === Copying additional files
copy examples\EXAMPLE.awlpro %distdir%\
if ERRORLEVEL 1 goto error_copy
copy README.txt %distdir%\
if ERRORLEVEL 1 goto error_copy
copy COMPATIBILITY.txt %distdir%\
if ERRORLEVEL 1 goto error_copy
copy TODO.txt %distdir%\
if ERRORLEVEL 1 goto error_copy
xcopy doc\foreign-licenses %distdir%\licenses\ /E
if ERRORLEVEL 1 goto error_copy
copy COPYING.txt %distdir%\licenses\AWLSIM-LICENSE.txt
if ERRORLEVEL 1 goto error_copy
if %buildtype% == 1 goto no_servermod_rename
move %bindir%\server.exe %bindir%\awlsim-server-module.exe
if ERRORLEVEL 1 goto error_copy
:no_servermod_rename


echo === Generating startup wrapper
set wrapper=%distdir%\awlsim.bat
echo @echo off> %wrapper%
if ERRORLEVEL 1 goto error_wrapper
echo start /Dawlsim-bin awlsim-gui.exe %%1>> %wrapper%
if ERRORLEVEL 1 goto error_wrapper


echo === Creating the distribution archive
7z a -tzip %zipfile% %distdir%
if ERRORLEVEL 1 goto error_zip


echo ---
echo finished
pause
exit




:error_prep
echo FAILED to prepare environment
goto error

:error_exe
echo FAILED to build exe
goto error

:error_copy
echo FAILED to copy files
goto error

:error_wrapper
echo FAILED to create wrapper
goto error

:error_zip
echo FAILED to create zip archive
goto error

:error
pause
exit

@echo off

SET PATH=%PATH%;C:\WINDOWS;C:\WINDOWS\SYSTEM32;C:\PYTHON34;%ProgramFiles%\7-Zip

py -c "from awlsim.core.version import VERSION_MAJOR, VERSION_MINOR; print('%%d.%%d' %% (VERSION_MAJOR, VERSION_MINOR))" > version.txt
set /p version= < version.txt

set distdir=awlsim-win-standalone-%version%
set zipfile=awlsim-win-standalone-%version%.zip

echo Building standalone Windows executable for awlsim v%version%...


rem ---
rem Create the py2exe distribution
rem ---
rd /s /q build 2>NUL
rd /s /q %distdir% 2>NUL
py setup.py py2exe ^
	--dist-dir=%distdir% ^
	--optimize=2 ^
	--bundle-files=3 ^
	--compressed ^
	--ignores=win32api,win32con,readline,awlsim_cython ^
	--packages=awlsimhw_debug,awlsimhw_dummy ^
	--quiet
if ERRORLEVEL 1 goto error_exe

rem ---
rem Copy additional files
rem ---
copy EXAMPLE.* %distdir%\
copy README.txt %distdir%\
copy COMPATIBILITY.txt %distdir%\
copy TODO.txt %distdir%\
xcopy doc\foreign-licenses %distdir%\licenses\ /E
copy COPYING.txt %distdir%\licenses\AWLSIM-LICENSE.txt

rem ---
rem Create the distribution archive
rem ---
del %zipfile% 2>NUL
7z a -tzip %zipfile% %distdir%
if ERRORLEVEL 1 goto error_zip


echo ---
echo finished
pause
exit


:error_exe
echo FAILED to build exe
goto error

:error_zip
echo FAILED to create zip archive
goto error

:error
pause
exit
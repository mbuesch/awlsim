@echo off

SET PATH=%PATH%;C:\WINDOWS;C:\WINDOWS\SYSTEM32;C:\PYTHON34;%ProgramFiles%\7-Zip

py -c "from awlsim.common.version import VERSION_MAJOR, VERSION_MINOR; print('%%d.%%d' %% (VERSION_MAJOR, VERSION_MINOR))" > version.txt
set /p version= < version.txt

set distdir=awlsim-win-standalone-%version%
set zipfile=awlsim-win-standalone-%version%.zip
set bindir=%distdir%\awlsim-bin

echo Building standalone Windows executable for awlsim v%version%...


rem ---
rem Create the cx_Freeze distribution
rem ---
rd /s /q build 2>NUL
rd /s /q %distdir% 2>NUL
mkdir %distdir%
mkdir %bindir%
py setup.py build_exe ^
	--build-exe %bindir% ^
	--optimize 2 ^
	--silent
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
move %bindir%\server.exe %bindir%\awlsim-server-module.exe

rem ---
rem Make startup wrapper
rem ---
set wrapper=%distdir%\awlsim.bat
echo @echo off> %wrapper%
echo start /Dawlsim-bin awlsim-gui.exe %%1>> %wrapper%

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

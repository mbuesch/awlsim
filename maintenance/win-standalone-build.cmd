@echo off
setlocal ENABLEDELAYEDEXPANSION

set project=awlsim

set PATH=%PATH%;C:\WINDOWS;C:\WINDOWS\SYSTEM32
for /D %%f in ( "C:\PYTHON*" ) do set PATH=!PATH!;%%f
for /D %%f in ( "%USERPROFILE%\AppData\Local\Programs\Python\Python*" ) do set PATH=!PATH!;%%f;%%f\Scripts
set PATH=%PATH%;%ProgramFiles%\7-Zip

cd ..
if ERRORLEVEL 1 goto error_basedir

py -c "from awlsim.common.version import VERSION_STRING; print(VERSION_STRING)" > version.txt
if ERRORLEVEL 1 goto error_version
set /p version= < version.txt
del version.txt

if "%PROCESSOR_ARCHITECTURE%" == "x86" (
	set winprefix=win32
) else (
	set winprefix=win64
)
set distdir=%project%-%winprefix%-standalone-%version%
set sfxfile=%project%-%winprefix%-%version%.package.exe
set bindirname=%project%-bin
set bindir=%distdir%\%bindirname%
set licensedirname=licenses
set licensedir=%distdir%\%licensedirname%


echo Building standalone Windows executable for %project% v%version%...
echo.

echo Please select GUI framework:
echo   1)  Build with PyQt5 (default)
echo   2)  Build with PySide4
set /p framework=Selection: 
if "%framework%" == "" goto framework_pyqt5
if "%framework%" == "1" goto framework_pyqt5
if "%framework%" == "2" goto framework_pyside4
echo "Error: Invalid selection"
goto error

:framework_pyqt5
echo Using PyQt5
set excludes=PySide
goto select_freezer

:framework_pyside4
echo Using PySide4
set excludes=PyQt5
goto select_freezer


:select_freezer
echo.
echo Please select freezer:
echo   1)  Build 'cx_Freeze' based distribution (default)
echo   2)  Build 'py2exe' based distribution
set /p buildtype=Selection: 
if "%buildtype%" == "" goto build_cxfreeze
if "%buildtype%" == "1" goto build_cxfreeze
if "%buildtype%" == "2" goto build_py2exe
echo "Error: Invalid selection"
goto error


:build_cxfreeze
set buildtype=1
echo === Creating the cx_Freeze distribution
call :prepare_env
py setup.py build_exe ^
	--build-exe=%bindir% ^
	--excludes=%excludes% ^
	--silent
if ERRORLEVEL 1 goto error_exe
goto copy_files


:build_py2exe
set buildtype=2
echo === Creating the py2exe distribution
call :prepare_env
py setup.py py2exe ^
	--dist-dir=%bindir% ^
	--bundle-files=3 ^
	--ignores=win32api,win32con,readline,awlsim_cython ^
	--excludes=%excludes% ^
	--packages=awlsimhw_debug,awlsimhw_dummy,awlsim.library.iec ^
	--quiet
if ERRORLEVEL 1 goto error_exe
goto copy_files


:copy_files
echo === Copying additional files
mkdir %licensedir%
if ERRORLEVEL 1 goto error_copy
copy examples\EXAMPLE.awlpro %distdir%\
if ERRORLEVEL 1 goto error_copy
copy README.* %distdir%\
if ERRORLEVEL 1 goto error_copy
copy COMPATIBILITY.* %distdir%\
if ERRORLEVEL 1 goto error_copy
copy TODO.* %distdir%\
if ERRORLEVEL 1 goto error_copy
copy QUICK-START.* %distdir%\
if ERRORLEVEL 1 goto error_copy
copy doc\foreign-licenses\*.txt %licensedir%\
if ERRORLEVEL 1 goto error_copy
xcopy /E /I doc\pic-quick-start %distdir%\doc\pic-quick-start
if ERRORLEVEL 1 goto error_copy
copy COPYING.txt %licensedir%\AWLSIM-LICENSE.txt
if ERRORLEVEL 1 goto error_copy
for /D %%f in ( "progs\putty\*" ) do (
	copy %%f\putty\PUTTY.EXE %bindir%\
	if ERRORLEVEL 1 goto error_copy
	copy %%f\putty\PLINK.EXE %bindir%\
	if ERRORLEVEL 1 goto error_copy
	copy %%f\LICENCE %licensedir%\PUTTY-LICENSE.txt
	if ERRORLEVEL 1 goto error_copy
)
if %buildtype% == 1 goto no_servermod_rename
move %bindir%\server.exe %bindir%\awlsim-server-module.exe
if ERRORLEVEL 1 goto error_copy
:no_servermod_rename


echo === Generating startup wrapper
set wrapper=%distdir%\%project%.cmd
echo @set PATH=%bindirname%;%%PATH%%> %wrapper%
echo @start %project%-bin\awlsim-gui.exe %%1 %%2 %%3 %%4 %%5 %%6 %%7 %%8 %%9>> %wrapper%
if ERRORLEVEL 1 goto error_wrapper


echo === Creating the distribution archive
7z a -mx=9 -sfx7z.sfx %sfxfile% %distdir%
if ERRORLEVEL 1 goto error_7z


echo ---
echo finished
pause
exit /B 0


:prepare_env
echo === Preparing distribution environment
rd /S /Q build 2>NUL
rd /S /Q %distdir% 2>NUL
del %sfxfile% 2>NUL
timeout /T 2 /NOBREAK >NUL
mkdir %distdir%
if ERRORLEVEL 1 goto error_prep
mkdir %bindir%
if ERRORLEVEL 1 goto error_prep
exit /B 0

:error_basedir
echo FAILED to CD to base directory
goto error

:error_version
echo FAILED to detect version
goto error

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

:error_7z
echo FAILED to create archive
goto error

:error
pause
exit 1

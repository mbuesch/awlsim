@echo off
setlocal ENABLEDELAYEDEXPANSION
set basedir=%~dp0
set awlsim_base=%basedir%\..


set PATH=%PATH%;C:\WINDOWS;C:\WINDOWS\SYSTEM32
for /D %%f in ( "C:\PYTHON*" ) do set PATH=!PATH!;%%f
for /D %%f in ( "%USERPROFILE%\AppData\Local\Programs\Python\Python*" ) do set PATH=!PATH!;%%f;%%f\Scripts


cd %awlsim_base%
if ERRORLEVEL 1 goto error_cd
set AWLSIM_CYTHON_BUILD=1
py -3 setup.py build
if ERRORLEVEL 1 goto error_build


echo ---
echo finished
pause
exit /B 0


:error_cd
echo FAILED to cd to base directory
goto error

:error_build
echo FAILED to build Awlsim
goto error

:error
pause
exit 1
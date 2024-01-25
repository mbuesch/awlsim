@echo off
setlocal ENABLEDELAYEDEXPANSION


set PATH=%PATH%;C:\WINDOWS;C:\WINDOWS\SYSTEM32
for /D %%f in ( "C:\PYTHON*" ) do set PATH=!PATH!;%%f
for /D %%f in ( "%USERPROFILE%\AppData\Local\Programs\Python\Python*" ) do set PATH=!PATH!;%%f;%%f\Scripts


call :install pip
if ERRORLEVEL 1 exit /B 1
call :install setuptools
if ERRORLEVEL 1 exit /B 1
call :install wheel
if ERRORLEVEL 1 exit /B 1
call :install pywin32
if ERRORLEVEL 1 exit /B 1
call :install Cython
if ERRORLEVEL 1 exit /B 1
call :install PyQt5_sip
if ERRORLEVEL 1 exit /B 1
call :install PyQt5
if ERRORLEVEL 1 exit /B 1
call :install cx_Freeze
if ERRORLEVEL 1 exit /B 1
call :install readme_renderer
if ERRORLEVEL 1 exit /B 1
call :install readme_renderer[md]
if ERRORLEVEL 1 exit /B 1

echo ---
echo finished successfully
pause
exit /B 0


:install
	echo Installing %1 ...
	python -m pip install --upgrade %1
	if ERRORLEVEL 1 (
		echo FAILED to install %1
		pause
		exit /B 1
	)
	exit /B 0

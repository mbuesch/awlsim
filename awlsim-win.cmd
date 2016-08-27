@echo off
setlocal ENABLEDELAYEDEXPANSION


set PYPROG=awlsim-gui
for /D %%f in ( "progs\putty\*" ) do set PATH=%%f\putty;!PATH!



set PATH=%PATH%;C:\WINDOWS;C:\WINDOWS\SYSTEM32
for /D %%f in ( "C:\PYTHON*" ) do set PATH=!PATH!;%%f

py -h >NUL 2>&1
if %ERRORLEVEL% EQU 0 goto exec_py

python3 -h >NUL 2>&1
if %ERRORLEVEL% EQU 0 goto exec_python3

python -h >NUL 2>&1
if %ERRORLEVEL% EQU 0 goto exec_python

echo Did not find Python 3.x in the PATH.
echo Please make sure Python 3.x is installed correctly.
pause
goto end


:exec_py
@echo on
py -3 -O %PYPROG% %1 %2 %3 %4 %5 %6 %7 %8 %9
@goto end


:exec_python3
@echo on
python3 -O %PYPROG% %1 %2 %3 %4 %5 %6 %7 %8 %9
@goto end


:exec_python
@echo on
python -O %PYPROG% %1 %2 %3 %4 %5 %6 %7 %8 %9
@goto end


:end

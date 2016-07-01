@ECHO OFF

SET PYPROG=awlsim-gui


SETLOCAL ENABLEDELAYEDEXPANSION

SET PATH=%PATH%;C:\WINDOWS;C:\WINDOWS\SYSTEM32
FOR /D %%f IN ( C:\PYTHON* ) DO SET PATH=!PATH!;%%f

py -h >NUL 2>&1
if %ERRORLEVEL% EQU 0 GOTO exec_py

python3 -h >NUL 2>&1
if %ERRORLEVEL% EQU 0 GOTO exec_python3

python -h >NUL 2>&1
if %ERRORLEVEL% EQU 0 GOTO exec_python

echo Did not find Python 3.x in the PATH.
echo Please make sure Python 3.x is installed correctly.
pause
goto end


:exec_py
@ECHO ON
py -3 -O %PYPROG%
GOTO end


:exec_python3
@ECHO ON
python3 -O %PYPROG%
GOTO end


:exec_python
@ECHO ON
python -O %PYPROG%
GOTO end


:end

@ECHO OFF

SET PATH=%PATH%;C:\WINDOWS;C:\WINDOWS\SYSTEM32;C:\PYTHON;C:\PYTHON34;C:\PYTHON33;C:\PYTHON32;C:\PYTHON31;C:\PYTHON30

SET PYPROG=awlsimgui


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

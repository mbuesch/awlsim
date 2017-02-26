@echo off
setlocal ENABLEDELAYEDEXPANSION


set PATH=%PATH%;C:\WINDOWS;C:\WINDOWS\SYSTEM32
for /D %%f in ( "C:\PYTHON*" ) do set PATH=!PATH!;%%f
for /D %%f in ( "%USERPROFILE%\AppData\Local\Programs\Python\Python*" ) do set PATH=!PATH!;%%f;%%f\Scripts


echo Installing PyQt5 ...
pip3 install PyQt5
if ERRORLEVEL 1 goto error_qt5

echo Installing cx_Freeze ...
pip3 install cx_Freeze
if ERRORLEVEL 1 goto error_cx_freeze


echo ---
echo finished successfully
pause
exit /B 0


:error_qt5
echo FAILED to install PyQt5
goto error

:error_cx_freeze
echo FAILED to install cx_Freeze
goto error

:error
pause
exit 1
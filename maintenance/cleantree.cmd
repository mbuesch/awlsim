@echo off
setlocal

pushd "%~dp0.." || goto :pushd_error

if not exist "awlsim-test" (
	echo basedir sanity check failed
	popd
	pause
	exit /b 1
)
if not exist "pyproject.toml" (
	echo basedir sanity check failed
	popd
	pause
	exit /b 1
)

for /d /r %%D in (__pycache__) do if exist "%%~fD" rd /s /q "%%~fD" || goto :error
for /r %%F in (*.pyo *.pyc *$py.class) do if exist "%%~fF" del /q "%%~fF" || goto :error

call :remove_dir "build" || goto :error
call :remove_dir "dist" || goto :error
call :remove_dir ".pybuild" || goto :error
for /d %%D in (*.egg-info) do if exist "%%~fD" rd /s /q "%%~fD" || goto :error
call :remove_file "MANIFEST" || goto :error

for %%F in (*.html) do if exist "%%~fF" del /q "%%~fF" || goto :error
for /r "doc" %%F in (*.html) do if exist "%%~fF" del /q "%%~fF" || goto :error

call :remove_dir "tests\build" || goto :error
for /r "tests" %%F in (__init__.py) do if exist "%%~fF" del /q "%%~fF" || goto :error

popd
exit /b 0

:remove_dir
if not exist "%~1\" exit /b 0
rd /s /q "%~1"
if errorlevel 1 exit /b 1
exit /b 0

:remove_file
if not exist "%~1" exit /b 0
del /q "%~1"
if errorlevel 1 exit /b 1
exit /b 0

:pushd_error
echo Failed to enter repository directory.
pause
exit /b 1

:error
echo Cleanup failed.
popd
pause
exit /b 1

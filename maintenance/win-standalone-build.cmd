@echo off
rem
rem AWL simulator - Windows frozen package build script
rem
rem Copyright 2012-2022 Michael Buesch <m@bues.ch>
rem
rem This program is free software; you can redistribute it and/or modify
rem it under the terms of the GNU General Public License as published by
rem the Free Software Foundation; either version 2 of the License, or
rem (at your option) any later version.
rem
rem This program is distributed in the hope that it will be useful,
rem but WITHOUT ANY WARRANTY; without even the implied warranty of
rem MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
rem GNU General Public License for more details.
rem
rem You should have received a copy of the GNU General Public License along
rem with this program; if not, write to the Free Software Foundation, Inc.,
rem 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
rem
setlocal ENABLEDELAYEDEXPANSION

set project=awlsim

set PATH=%PATH%;C:\WINDOWS;C:\WINDOWS\SYSTEM32
for /D %%f in ( "C:\PYTHON*" ) do set PATH=!PATH!;%%f
for /D %%f in ( "%USERPROFILE%\AppData\Local\Programs\Python\Python*" ) do set PATH=!PATH!;%%f;%%f\Scripts
set PATH=%PATH%;%ProgramFiles%\7-Zip


cd ..
if ERRORLEVEL 1 goto error_basedir


call :detect_version
if "%PROCESSOR_ARCHITECTURE%" == "x86" (
    set winprefix=win32
) else (
    set winprefix=win64
)
set distdir=%project%-%winprefix%-standalone-%version%
set sfxfile=%project%-%winprefix%-%version%.package.exe
set bindirname=%project%-bin
set bindir=%distdir%\%bindirname%
set libcythontmpdir=%distdir%\lib_cython.tmp
set builddir=%bindir%\build
set licensedirname=licenses
set licensedir=%distdir%\%licensedirname%


echo Building standalone Windows executable for %project%-%version%

call :select_buildcython
call :prepare_env
call :build_cxfreeze
call :build_doc
call :copy_cython_modules_stage1
call :build_cxfreeze_exe
call :copy_cython_modules_stage2
call :copy_files
call :gen_startup_wrapper
call :make_archive

echo ---
echo finished
pause
exit /B 0


:detect_version
    py -c "from awlsim.common.version import VERSION_STRING; print(VERSION_STRING)" > version.txt
    if ERRORLEVEL 1 goto error_version
    set /p version= < version.txt
    del version.txt
    exit /B 0


:select_buildcython
    echo.
    echo Build optimized Cython modules?
    echo   1)  Do not build Cython modules (default)
    echo   2)  Build Cython modules
    set /p buildcython=Selection: 
    if "%buildcython%" == "" goto buildcython_no
    if "%buildcython%" == "1" goto buildcython_no
    if "%buildcython%" == "2" goto buildcython_yes
    echo "Error: Invalid selection"
    goto error

    :buildcython_yes
    echo Building Cython modules
    set AWLSIM_CYTHON_BUILD=1
    exit /B 0

    :buildcython_no
    echo Not building Cython modules
    set AWLSIM_CYTHON_BUILD=0
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


:build_cxfreeze
    echo === Building the cx_Freeze distribution
    py setup.py build --build-base=%builddir%
    if ERRORLEVEL 1 goto error_exe
    exit /B 0


:build_one_doc
    echo Generating %~2.html from %~1 ...
    echo ^<!DOCTYPE html^>^<html^>^<head^>^<meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\"^>^</head^>^<body^> > %~2.html
    if ERRORLEVEL 1 goto error_doc
    py -c "import re; print(re.subn(r'\.md\)', '.html)', open('"%~1"', 'r').read())[0])" >> %~2.md.tmp
    if ERRORLEVEL 1 goto error_doc
    py -c "from readme_renderer.markdown import render; print(render(open('"%~2.md.tmp"', 'r').read()))" >> %~2.html
    if ERRORLEVEL 1 goto error_doc
    del %~2.md.tmp
    if ERRORLEVEL 1 goto error_doc
    echo ^</body^>^</html^> >> %~2.html
    if ERRORLEVEL 1 goto error_doc
    exit /B 0

:build_doc
    for %%i in (*.md) do (
        call :build_one_doc %%i, %%~ni
    )
    pushd doc\fup
    if ERRORLEVEL 1 goto error_doc
    for %%i in (*.md) do (
        call :build_one_doc %%i, %%~ni
    )
    popd
    exit /B 0


:build_cxfreeze_exe
    echo === Building the cx_Freeze distribution executables
    py setup.py build_exe --build-exe=%bindir%
    if ERRORLEVEL 1 goto error_exe
    exit /B 0


:copy_cython_modules_stage1
    if %AWLSIM_CYTHON_BUILD% NEQ 0 (
        echo === Copying Cython modules from builddir to temporary dir ...
        mkdir %libcythontmpdir%
        if ERRORLEVEL 1 goto error_copy
        for /D %%f in ( "%builddir%\lib*" ) do (
            for /D %%i in ( "%%f\*_cython" ) do (
                echo === Copying %%i to %libcythontmpdir%\%%~ni ...
                xcopy /E /I %%i %libcythontmpdir%\%%~ni
                if ERRORLEVEL 1 goto error_copy
            )
        )
    )
    exit /B 0


:copy_cython_modules_stage2
    if %AWLSIM_CYTHON_BUILD% NEQ 0 (
        echo === Copying Cython modules from builddir to bindir ...
        for /D %%i in ( "%libcythontmpdir%\*" ) do (
            echo === Copying %%i to %bindir%\lib\%%~ni ...
            xcopy /E /I %%i %bindir%\lib\%%~ni
            if ERRORLEVEL 1 goto error_copy
        )
        rd /S /Q %libcythontmpdir%
        if ERRORLEVEL 1 goto error_copy
    )
    exit /B 0


:copy_files
    echo === Copying additional files
    mkdir %licensedir%
    if ERRORLEVEL 1 goto error_copy
    copy examples\*.awlpro %distdir%\
    if ERRORLEVEL 1 goto error_copy
    copy *.html %distdir%\
    if ERRORLEVEL 1 goto error_copy
    xcopy /E /I doc %distdir%\doc
    if ERRORLEVEL 1 goto error_copy
    rmdir /S /Q %distdir%\doc\foreign-licenses
    if ERRORLEVEL 1 goto error_copy
    copy doc\foreign-licenses\*.txt %licensedir%\
    if ERRORLEVEL 1 goto error_copy
    copy COPYING.txt %licensedir%\AWLSIM-LICENSE.txt
    if ERRORLEVEL 1 goto error_copy
    for /D %%f in ( "progs\putty\*" ) do (
        7z e -y -o%%f %%f\putty.zip PUTTY.EXE PLINK.EXE
        if ERRORLEVEL 1 goto error_copy
        copy %%f\PUTTY.EXE %bindir%\
        if ERRORLEVEL 1 goto error_copy
        del %%f\PUTTY.EXE
        if ERRORLEVEL 1 goto error_copy
        copy %%f\PLINK.EXE %bindir%\
        if ERRORLEVEL 1 goto error_copy
        del %%f\PLINK.EXE
        if ERRORLEVEL 1 goto error_copy
        copy %%f\LICENCE %licensedir%\PUTTY-LICENSE.txt
        if ERRORLEVEL 1 goto error_copy
    )
    rd /S /Q %builddir%
    if ERRORLEVEL 1 goto error_copy
    exit /B 0


:gen_startup_wrapper
    echo === Generating startup wrapper
    set wrapper=%distdir%\%project%.cmd
    echo @set PATH=%bindirname%;%bindirname%\lib;%bindirname%\platforms;%bindirname%\imageformats;%%PATH%% > %wrapper%
    echo @set AWLSIM_CYTHON=%AWLSIM_CYTHON_BUILD% >> %wrapper%
    echo @start %project%-bin\awlsim-gui.exe %%1 %%2 %%3 %%4 %%5 %%6 %%7 %%8 %%9 >> %wrapper%
    if ERRORLEVEL 1 goto error_wrapper
    exit /B 0


:make_archive
    echo === Creating the distribution archive
    7z a -mx=9 -sfx7z.sfx %sfxfile% %distdir%
    if ERRORLEVEL 1 goto error_7z
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

:error_doc
echo FAILED to build documentation
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

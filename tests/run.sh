#!/bin/sh

# basedir is the root of the test directory in the package
basedir="$(dirname "$0")"
[ "$(echo "$basedir" | cut -c1)" = '/' ] || basedir="$PWD/$basedir"

# rootdir is the root of the package
rootdir="$basedir/.."


failfile_write()
{
	(
		flock -x 9 || die "Failed to take lock"
		echo "$*" >> "$test_fail_file"
	) 9< "$test_fail_file"
}

infomsg()
{
	[ -z "$AWLSIM_TEST_QUIET" ] && echo "$@"
}

warnmsg()
{
	echo "WARNING: $@" >&2
}

errormsg()
{
	echo "$@" >&2
}

die()
{
	if [ -n "$*" ]; then
		errormsg "$*"
		# We might be in a sub-job. So write to fail-file.
		failfile_write "$*"
	fi
	exit 1
}

# Create a temporary file. $1=name, $2=subdir
maketemp()
{
	local prefix="$1"
	local subdir="$2"

	if [ -z "$subdir" ]; then
		local subdir="."
	else
		mkdir -p "$tmp_dir/$subdir"
	fi
	mktemp --tmpdir="$tmp_dir" "${subdir}/awlsim-test-${prefix}.XXXXXX"
}

# $1=message
test_failed()
{
	errormsg "=== TEST FAILED ==="
	die "$@"
}

cleanup()
{
	wait

	rm -rf "$tmp_dir" >/dev/null 2>&1
}

cleanup_and_exit()
{
	cleanup
	exit 1
}

# Get a configuration option.
# $1=configured_file
# $2=option_name
# ($3=default_value)
get_conf()
{
	local configured_file="$1"
	local option_name="$2"
	local default_value="$3"

	local conf="${configured_file}.conf"
	local val="$default_value"
	if [ -r "$conf" ]; then
		local regex="^${option_name}="
		if grep -qEe "$regex" "$conf"; then
			local val="$(grep -Ee "$regex" "$conf" | cut -d'=' -f2-)"
		fi
	fi
	printf '%s' "$val"
}

# Allocate a new port number.
get_port()
{
	(
		flock -x 8 || die "Failed to take port lock"

		local port="$(cat "$port_alloc_file")"
		local next="$(expr "$port" + 1)"
		echo "$next" > "$port_alloc_file" ||\
			die "Failed to update port allocation file"

		echo -n "$port"
	) 8> "${port_alloc_file}.lock"
}

# Returns true (0), if there are more than 1 jobs.
is_parallel_run()
{
	[ $opt_jobs -gt 1 ]
}

# Wait until there is at least one free job slot.
wait_for_free_job_slot()
{
	while true; do
		jobs -l > "$jobs_tmp_file" # can't use pipe on dash
		[ "$(cat "$jobs_tmp_file" | wc -l)" -lt $opt_jobs ] && break
		# Too many jobs. Waiting...
		sleep 0.1
	done
}

# $1 is the PID of the job to wait for.
wait_for_job_pid()
{
	local jobpid="$1"

	while true; do
		jobs -l > "$jobs_tmp_file" # can't use pipe on dash
		cat "$jobs_tmp_file" | tr -d '+-' |\
			sed -e 's/[[:blank:]]\+/\t/g' | cut -f2 |\
			grep -qe '^'"$jobpid"'$' || break
		# Job is still running...
		sleep 0.1
	done
}

# Returns true (0), if at least one background job failed.
check_job_failure()
{
	is_parallel_run &&\
	[ -e "$test_fail_file" ] &&\
	[ "0" != "$(du -s "$test_fail_file" | cut -f1)" ]
}

wait_for_all_background_jobs()
{
	is_parallel_run || return

	infomsg "Waiting for background jobs..."
	wait
	# Print the fail information.
	if check_job_failure; then
		errormsg
		errormsg "===== FAILURES in parallel run: ====="
		cat "$test_fail_file" >&2
		errormsg "====================================="
		global_retval=1
	fi
}

# $1=interpreter
# Returns version on stdout as:  MAJOR MINOR PATCHLEVEL
get_interpreter_version()
{
	local interpreter="$1"

	[ "$interpreter" = "cython3" ] && local interpreter=python3

	"$interpreter" -c 'import sys; print("%d %d %d" % sys.version_info[0:3]);' 2>/dev/null
}

# Check if an interpreter is able to run GUI code.
# $1=interpreter
interpreter_is_gui_compat()
{
	local interpreter="$1"

	[ $opt_nogui -eq 0 ] &&\
	[ "$interpreter" = "python3" -o \
	  "$interpreter" = "cython3" ]
}

# $1=program_name
have_prog()
{
	local program="$1"

	which "$program" >/dev/null 2>&1
}

# $1=executable_name
find_executable()
{
	local executable_name="$1"

	local executable_path="$(which "$executable_name")"
	[ -n "$executable_path" ] ||\
		die "$executable_name executable not found."\
		    "Please install $executable_name."
	RET="$executable_path"
}

# Check DOS file encoding.
# $1=file
check_dos_text_encoding()
{
	local file="$1"

	if [ x"$(du -b "$file" | cut -f1)" != x"0" ]; then
		# Check CR/LF
		file -L "$file" | grep -qe 'CRLF line terminators' || {
			die "ERROR: '$file' is not in DOS format."
		}
		# Check file encoding
		file -L "$file" | grep -qEe '(ISO-8859 text)|(ASCII text)' || {
			die "ERROR: '$file' invalid file encoding."
		}
	fi
}

# $1=interpreter $2=tested_file [$3=test_name]
setup_test_environment()
{
	local interpreter="$1"
	local tested_file="$2"
	local test_name="$3"

	[ -z "$test_name" ] && local test_name="$tested_file"
	local test_name="$(realpath -m --no-symlinks --relative-base="$rootdir" "$test_name" | tr '/\\' _)"

	# Check if we want to run on Cython3 and set up the environment.
	local use_cython=0
	if [ "$interpreter" = "cython3" ] ||\
	   [ "$interpreter" = "python3" -a "$AWLSIM_CYTHON" != "" ]; then
		# We want to run the test using Cython3

		local use_cython=3

		for i in "$rootdir"/build/lib.linux-*-3.*; do
			export PYTHONPATH="$i"
			break
		done
		# Enforce cython module usage
		export AWLSIM_CYTHON=2
		# The actual interpreter is Python
		local interpreter=python3

	elif [ "$interpreter" = "micropython" ]; then
		# We want to run the test using Micropython

		local interpreter="$rootdir/maintenance/micropython-wrapper.sh"

	else
		# Not Cython
		export PYTHONPATH=
		export AWLSIM_CYTHON=
	fi

	# Extra environment variables
	RAW_EXTRA_ENV="$(get_conf "$tested_file" env)"
	for env in $(printf '%s' "$RAW_EXTRA_ENV" | tr ':' ' '); do
		eval export "$env"
	done

	# Get extra PYTHONPATH from test case config file.
	local conf_pythonpath=
	if [ -n "$tested_file" ]; then
		local raw_conf_pythonpath="$(get_conf "$tested_file" PYTHONPATH)"
		local onepath=
		for onepath in $(printf '%s' "$raw_conf_pythonpath" | tr ':' ' '); do
			if [ -n "$conf_pythonpath" ]; then
				local conf_pythonpath="$conf_pythonpath:"
			fi
			local conf_pythonpath="${conf_pythonpath}$(realpath -m --no-symlinks "$rootdir/$onepath")"
		done
	fi

	# Export PYTHONPATHs
	export PYTHONPATH="$PYTHONPATH:$EXTRA_PYTHONPATH:$conf_pythonpath"
	export JYTHONPATH="$JYTHONPATH:$EXTRA_PYTHONPATH:$conf_pythonpath"
	export IRONPYTHONPATH="$IRONPYTHONPATH:$EXTRA_PYTHONPATH:$conf_pythonpath"
	export MICROPYPATH="$MICROPYPATH:$EXTRA_PYTHONPATH:$conf_pythonpath"

	# Disable Python optimization so that assert statements are enabled.
	# Enable warnings
	# Enable hash seed randomization.
	unset PYTHONSTARTUP
	unset PYTHONY2K
	unset PYTHONOPTIMIZE
	unset PYTHONDEBUG
	unset PYTHONDONTWRITEBYTECODE
	unset PYTHONINSPECT
	unset PYTHONIOENCODING
	unset PYTHONNOUSERSITE
	unset PYTHONUNBUFFERED
	unset PYTHONVERBOSE
	if [ $use_cython -eq 0 ]; then
		export PYTHONWARNINGS=once
	else
		export PYTHONWARNINGS=once,ignore::ImportWarning
	fi
	export PYTHONHASHSEED=random

	# Disable CPU affinity
	unset AWLSIM_AFFINITY

	# Setup coverage tracing
	if [ $coverage_enabled -eq 0 ]; then
		unset AWLSIM_COVERAGE
	else
		local coverage_data_file="$(maketemp "coverage_${test_name}" "$coverage_data_subdir")"
		rm "$coverage_data_file"

		export AWLSIM_COVERAGE="$coverage_data_file"
	fi

	RET="$interpreter"
}

cleanup_test_environment()
{
	export AWLSIM_CYTHON=

	export PYTHONPATH=
	export JYTHONPATH=
	export IRONPYTHONPATH=
	export MICROPYPATH=

	export EXTRA_PYTHONPATH=

	# Unexport all extra envs
	for env in $(printf '%s' "$RAW_EXTRA_ENV" | tr ':' ' '); do
		eval export "$(printf '%s' "$env" | cut -d'=' -f1)"=
	done
}

# $1=interpreter $2=awl_file ($3ff additional options to awlsim-test)
run_awl_test()
{
	local interpreter="$1"
	local awl="$2"
	shift; shift

	# By default run once with all optimizers enabled.
	local optimizer_runs="$(get_conf "$awl" optimizer_runs all)"

	local first_opti=1
	for optimizers in $optimizer_runs; do
		[ $first_opti -eq 0 ] && infomsg -n " / "
		local first_opti=0

		local tries="$(get_conf "$awl" tries 1)"
		[ $tries -lt 1 ] && local tries=1
		local first_try=1

		local ok=0
		local exit_code=-1
		local expected_exit_code=-2
		while [ $tries -gt 0 -a $ok -eq 0 ]; do
			local tries="$(expr "$tries" - 1)"

			(
				[ $first_try -ne 0 ] && adjust_niceness "$($SHELL -c 'echo $PPID')"
				setup_test_environment "$interpreter" "$awl"
				local actual_interpreter="$RET"

				local loglevel="$(get_conf "$awl" loglevel "$opt_loglevel")"
				local expected_exit_code="$(get_conf "$awl" exit_code 0)"
				[ $expected_exit_code -eq 0 ] || local loglevel=0
				local cycle_limit="$(get_conf "$awl" cycle_limit 60)"
				local max_runtime="$(get_conf "$awl" max_runtime -1)"
				local accus="$(get_conf "$awl" accus)"
				if [ "$accus" = "2" ]; then
					local accus=--twoaccu
				elif [ "$accus" = "4" ]; then
					local accus=--fouraccu
				elif [ -n "$accus" ]; then
					cleanup_test_environment
					die "Invalid 'accus' value in .conf"
				fi
				local dump_opt=
				[ $loglevel -ge 3 ] && local dump_opt="--no-cpu-dump"

				"$actual_interpreter" "$rootdir/awlsim-test" \
					--loglevel $loglevel \
					--extended-insns \
					--hardware debug:inputAddressBase=7:outputAddressBase=8:dummyParam=True \
					--cycle-limit "$cycle_limit" \
					--max-runtime "$max_runtime" \
					--optimizers "$optimizers" \
					$accus \
					$dump_opt \
					"$@" \
					"$awl"
				local exit_code=$?
				if [ $exit_code -ne $expected_exit_code ]; then
					# Test failed
					cleanup_test_environment
					if [ $tries -gt 0 ]; then
						infomsg "Test '$(basename "$awl")' FAILED, but retrying ($tries tries left)..."
						sleep 1
						die # Next try
					else
						test_failed "\nTest '$(basename "$awl")'   FAILED" \
							"\nInterpreter        = $interpreter" \
							"\nOptimizers         = $optimizers" \
							"\nActual exit code   = $exit_code" \
							"\nExpected exit code = $expected_exit_code"
					fi
				fi

				cleanup_test_environment
			) && local ok=1
			local first_try=0
		done
		if [ $ok -eq 0 ]; then
			die # Test failed
		fi
		if is_parallel_run; then
			infomsg "$(basename "$awl"): O=$optimizers -> OK"
		else
			infomsg -n "O=$optimizers -> OK"
		fi
	done
	is_parallel_run || infomsg
}

# $1=interpreter $2=sh_file
run_sh_test()
{
	local interpreter="$1"
	local sh_file="$2"
	shift; shift

	[ -x "$sh_file" ] && die "SH-file '$sh_file' must NOT be executable"

	[ "$(echo "$sh_file" | cut -c1)" = '/' ] || local sh_file="$(pwd)/$sh_file"

	# Run the test
	(
		# Source the test file
		. "$basedir/sh-test.defaults"
		. "$sh_file"

		adjust_niceness "$($SHELL -c 'echo $PPID')"
		setup_test_environment "$interpreter" "$sh_file"
		local interpreter="$RET"
		local test_dir="$(dirname "$sh_file")"
		local test_name="$(basename "$sh_file" .sh)"
		sh_test "$interpreter" "$test_dir" "$test_name"
		cleanup_test_environment
	)
	local result=$?

	[ $result -eq 0 ] || die "Test failed with error code $result"
	if is_parallel_run; then
		infomsg "$(basename "$sh_file"): OK"
	else
		infomsg "OK"
	fi
}

# $1=interpreter $2=test_file
run_pyunit_test()
{
	local interpreter="$1"
	local test_case="$2"
	shift; shift

	[ -z "$test_case" ] &&\
		die "Python unittest test case is missing"
	[ -d "$test_case" ] &&\
		die "Python unittest test case '$test_case' must not be a directory"
	[ -x "$test_case" ] &&\
		die "Python unittest test case '$test_case' must NOT be executable"

	# Resolve relative path
	[ "$(echo "$test_case" | cut -c1)" = '/' ] ||\
		local test_case="$(pwd)/$test_case"

	(
		# Add awlsim_tstlib.py to PYTHONPATH
		EXTRA_PYTHONPATH="$rootdir:$rootdir/tests:$EXTRA_PYTHONPATH"

		# Setup python environment
		adjust_niceness "$($SHELL -c 'echo $PPID')"
		local orig_interpreter="$interpreter"
		setup_test_environment "$interpreter" "$test_case"
		local interpreter="$RET"

		export PYTHONDONTWRITEBYTECODE=1

		if [ "$orig_interpreter" = "cython3" ] && ! [ -e "$(dirname "$test_case")/no_cython" ]; then
			# Get the relative test case path starting in 'tests' directory.
			local relpath="$(realpath -m --no-symlinks --relative-base="$rootdir/tests" "$test_case")"
			# Patch the module name to Cython name (append _cython).
			local patch_re='s/(tc[0-9][0-9][0-9]_[0-9a-zA-Z]*)/\1_cython/'
			local relpath_cython="$(printf "%s" "$relpath" | sed -Ee "$patch_re")"
			# Get the relative directory of the test case.
			local reldir_cython="$(dirname "$relpath_cython")"
			# Go to the unittest subdir to run the Cython unittest.
			cd "$rootdir/tests/build/"lib.*-3.*"/$reldir_cython" || die "Failed to cd to test directory."
		else
			# Go to the unittest subdir to run the Python unittest.
			cd "$(dirname "$test_case")" || die "Failed to cd to test directory."
		fi

		# Convert test name to module name (for python2)
		local test_case="$(basename "$test_case" .py)"

		# Run it.
		if [ -n "$AWLSIM_TEST_QUIET" ]; then
			"$interpreter" -m unittest "$test_case" >/dev/null 2>&1 ||\
				die "Python unittest test case '$(basename "$test_case")' failed."
		else
			"$interpreter" -m unittest "$test_case" ||\
				die "Python unittest test case '$(basename "$test_case")' failed."
		fi

		infomsg "$(basename "$test_case"): OK"

		cleanup_test_environment
	) || die "'$(basename "$test_case")' FAILED"
}

# $1=interpreter $2=testfile(.awl/.sh) ($3ff additional options to awlsim-test or testfile)
run_test()
{
	local interpreter="$1"
	local testfile="$2"
	shift; shift

	# Don't run ourself
	[ "$(basename "$testfile")" = "run.sh" ] && return
	# Don't run artifacts that aren't actual test cases.
	[ "$(basename "$testfile")" = "awlsim_tstlib.py" ] && return
	[ "$(basename "$testfile")" = "setup-cython-tests.py" ] && return
	[ "$(basename "$testfile")" = "__init__.py" ] && return

	local disabled="$(get_conf "$testfile" disabled)"
	if [ -z "$disabled" ]; then

		# Print test headline
		local nl="-n"
		is_parallel_run && local nl=
		infomsg $nl "$(basename "$testfile") @ $(basename "$interpreter"): "

		local prev_dir="$(pwd)"
		cd "$rootdir" || die "cd to $rootdir failed"

		# Check the file type and run the tester
		if [ "$(echo -n "$testfile" | tail -c4)" = ".awl" ]; then
			check_dos_text_encoding "$testfile"
			run_awl_test "$interpreter" "$testfile" "$@"
		elif [ "$(echo -n "$testfile" | tail -c7)" = ".awlpro" ]; then
			run_awl_test "$interpreter" "$testfile" "$@"
		elif [ "$(echo -n "$testfile" | tail -c3)" = ".sh" ]; then
			run_sh_test "$interpreter" "$testfile" "$@"
		elif [ "$(echo -n "$testfile" | tail -c3)" = ".py" ]; then
			run_pyunit_test "$interpreter" "$testfile" "$@"
		else
			die "Test file type of '$testfile' not recognized"
		fi

		cd "$prev_dir" || die "cd to $prev_dir failed"
	else
		warnmsg "Skipping '$testfile' as it is disabled."
	fi
}

run_test_parallel()
{
	if is_parallel_run; then
		# Run tests in parallel.
		wait_for_free_job_slot
		run_test "$@" &
	else
		# Run tests one-by-one.
		run_test "$@"
	fi
}

# $1=interpreter, $2=directory
run_test_directory()
{
	local interpreter="$1"
	local directory="$2"

	[ "$(basename "$directory")" = "build" ] && return

	local prettydir="$(realpath -m --no-symlinks --relative-base="$rootdir" "$directory")/"

	infomsg ">>> entering $prettydir"
	# run .awlpro tests
	for entry in "$directory"/*; do
		[ -d "$entry" ] && continue
		[ "$(echo -n "$entry" | tail -c7)" = ".awlpro" ] || continue
		[ -e "$(dirname "$entry")/$(basename "$entry" .awlpro).sh" ] && continue

		run_test_parallel "$interpreter" "$entry"
		check_job_failure && return
	done
	# run .awl tests
	for entry in "$directory"/*; do
		[ -d "$entry" ] && continue
		[ "$(echo -n "$entry" | tail -c4)" = ".awl" ] || continue
		[ -e "$(dirname "$entry")/$(basename "$entry" .awl).awlpro" ] && continue
		[ -e "$(dirname "$entry")/$(basename "$entry" .awl).sh" ] && continue

		run_test_parallel "$interpreter" "$entry"
		check_job_failure && return
	done
	# run .sh tests
	for entry in "$directory"/*; do
		[ -d "$entry" ] && continue
		[ "$(echo -n "$entry" | tail -c3)" = ".sh" ] || continue
		run_test_parallel "$interpreter" "$entry"
		check_job_failure && return
	done
	# run .py unittest tests
	for entry in "$directory"/*; do
		[ -d "$entry" ] && continue
		[ "$(echo -n "$entry" | tail -c3)" = ".py" ] || continue
		[ "$entry" = "__init__.py" ] && continue
		run_test_parallel "$interpreter" "$entry"
		check_job_failure && return
	done
	# Recurse into subdirectories
	for entry in "$directory"/*; do
		[ -d "$entry" ] || continue
		run_test_directory "$interpreter" "$entry"
	done
	infomsg "<<< leaving $prettydir"
}

# $1=interpreter
warn_skipped()
{
	local interpreter="$1"

	warnmsg "=== WARNING: '$interpreter' interpreter not found. Test skipped."
	warnmsg
}

__build_cython()
{
	local cython="$1"
	local python="$2"

	have_prog "$cython" && have_prog "$python" || {
		warnmsg "=== WARNING: Cannot build $cython modules"
		return 1
	}

	(
		infomsg "=== Building awlsim $cython modules with $python"
		cd "$rootdir" || die "cd to $rootdir failed"
		CFLAGS="-O0" CPPFLAGS= CXXFLAGS="-O0" LDFLAGS= \
			AWLSIM_CYTHON_BUILD=1 \
			AWLSIM_CYTHON_PARALLEL=1 \
			nice -n 5 \
			"$python" ./setup.py build >/dev/null ||\
			die "'$python ./setup.py build' failed"
	) || die

	(
		infomsg "=== Building awlsim $cython test cases with $python"
		cd "$rootdir/tests" || die "cd to $rootdir/tests failed"
		rm -rf build || die "Failed to clean test cases build"
		nice -n 5 \
			"$python" ./setup-cython-tests.py build >/dev/null ||\
			die "'$python ./setup-cython-tests.py build' failed"
	) || die

	return 0
}

build_cython3()
{
	__build_cython cython3 python3
}

# $@=testfiles
do_tests()
{
	cleanup_test_environment

	if [ $opt_quick -eq 0 ]; then
		local all_interp="python3 python2 cython3 pypy3"
		if [ $opt_extended -ne 0 ]; then
			local all_interp="$all_interp jython"
		fi
	else
		local all_interp="python3 python2"
		if [ $opt_extended -ne 0 ]; then
			die "The options --quick and --extended are mutually exclusive."
		fi
	fi

	for interpreter in "$opt_interpreter" $all_interp; do
		[ -z "$interpreter" ] && continue

		cleanup_test_environment

		# Create an interpreter name suitable as path component
		local interpreter_name="$(printf '%s' "$interpreter" | tr '/\\' _)"

		# Check if we should enable coverage tracing
		coverage_enabled=$opt_coverage
		if [ $coverage_enabled -ne 0 ] &&\
		   [ "$interpreter" = "pypy" -o "$interpreter" = "pypy3" ]; then
			# Performance impact of coverage on PyPy is too big.
			# Disable coverage to avoid test failures.
			warnmsg "Disabling code coverage tracing (-c|--coverage) on PyPy due to bad performace."
			coverage_enabled=0
		fi

		# Prepare code coverage directory
		coverage_data_subdir="coverage-$interpreter_name"
		mkdir -p "$tmp_dir/$coverage_data_subdir" || die "Failed to create coverage data dir"

		# Basic interpreter setup. Build Cython modules.
		if [ "$interpreter" = "cython3" ]; then
			have_prog cython3 && have_prog python3 || {
				warn_skipped "$interpreter"
				[ -n "$opt_interpreter" ] && break || continue
			}
			wait_for_all_background_jobs
			build_cython3 || die "Cython3 build failed."
		else
			have_prog "$interpreter" || {
				warn_skipped "$interpreter"
				[ -n "$opt_interpreter" ] && break || continue
			}
		fi

		local interp_ver="$(get_interpreter_version "$interpreter")"
		local interp_ver_dot="$(echo "$interp_ver" | tr ' ' '.')"
		local interp_major="$(echo "$interp_ver" | cut -d' ' -f 1)"
		local interp_minor="$(echo "$interp_ver" | cut -d' ' -f 2)"

		[ -z "$interp_ver" ] &&\
			die "Failed to get '$interpreter' version."
		[ "$interp_major" -eq 2 -a "$interp_minor" -lt 7 ] &&\
			die "'$interpreter' interpreter version '$interp_ver_dot' too old."

		infomsg "=== Running tests with '$interpreter'"
		if [ $# -eq 0 ]; then
			run_test_directory "$interpreter" "$basedir"
		else
			for opt in "$@"; do
				local opt="$(realpath -m --no-symlinks "$opt")"
				if [ -d "$opt" ]; then
					run_test_directory "$interpreter" "$opt"
				else
					run_test_parallel "$interpreter" "$opt"
				fi
				check_job_failure && break
			done
		fi
		infomsg

		check_job_failure && break

		# Generate code coverage report
		if [ $coverage_enabled -ne 0 ]; then
			# Wait for background jobs to finish
			wait_for_all_background_jobs

			if [ $global_retval -eq 0 ]; then
				infomsg "\nGenerating code coverage report..."
				local reportbase="$rootdir/code-coverage-report"
				local reportdir="$reportbase/awlsim-coverage-$interpreter_name"
				rm -rf "$reportdir"
				"$rootdir/awlsim-covreport" \
					"$reportdir" \
					"$tmp_dir/$coverage_data_subdir/" ||\
					die "Failed to generate code coverage report."
			fi
		fi

		[ -n "$opt_interpreter" ] && break
	done

	# Wait for background jobs to finish
	wait_for_all_background_jobs

	# Print summary
	if [ $global_retval -eq 0 ]; then
		infomsg
		infomsg -n "All tests succeeded"
	else
		errormsg
		errormsg -n "Some tests FAILED"
	fi
	if [ -n "$opt_interpreter" ]; then
		infomsg " (with interpreter '$opt_interpreter')"
	else
		if [ $opt_quick -eq 0 ]; then
			if [ $opt_extended -eq 0 ]; then
				infomsg " (full run)"
			else
				infomsg " (extended run)"
			fi
		else
			infomsg " (quick run)"
		fi
	fi
}

show_help()
{
	infomsg "awlsim unit test script"
	infomsg
	infomsg "Usage: run.sh [OPTIONS] [testdirectory/testscript.awl/.awlpro/.sh/.py]"
	infomsg
	infomsg "Options:"
	infomsg " -i|--interpreter INTER        Use INTER as interpreter for the tests"
	infomsg " -j|--jobs NR                  Set the number of jobs to run in parallel."
	infomsg "                               0 means number-of-CPUs"
	infomsg "                               Default: 0"
	infomsg " -q|--quick                    Only run python2 and python3 tests"
	infomsg " -g|--no-gui                   Avoid tests that need GUI libraries"
	infomsg " -x|--extended                 Run tests on additional interpreters"
	infomsg " -n|--renice NICENESS          Renice by NICENESS. Defaults to 10."
	infomsg " -Q|--quiet                    Less messages"
	infomsg " -L|--loglevel                 Default log level."
	infomsg " -l|--loop COUNT               Number of test loops to execute."
	infomsg "                               Default: 1"
	infomsg "                               Set to 0 for infinite looping."
	infomsg " -c|--coverage                 Enable code coverage tracing."
}

tmp_dir="/tmp/awlsim-test-$$"
rm -rf "$tmp_dir" >/dev/null 2>&1
if ! mkdir -p "$tmp_dir" >/dev/null 2>&1; then
	tmp_dir="$basedir/.tmp/awlsim-test-$$"
	rm -rf "$tmp_dir" >/dev/null 2>&1
	mkdir -p "$tmp_dir" || die "Failed to create temp dir '$tmp_dir'"
fi

trap cleanup_and_exit INT TERM
trap cleanup EXIT

test_fail_file="$(maketemp fail)"
port_alloc_file="$(maketemp port)"
jobs_tmp_file="$(maketemp jobs)"
touch "${port_alloc_file}.lock"
echo 4096 > "$port_alloc_file" || die "Failed to initialize port file"

have_prog file || die "Program 'file' not found."

opt_interpreter=
opt_quick=0
opt_nogui=0
opt_extended=0
opt_renice=
opt_jobs=0
opt_loglevel=2
opt_loop=1
opt_coverage=0

while [ $# -ge 1 ]; do
	[ "$(printf '%s' "$1" | cut -c1)" != "-" ] && break

	case "$1" in
	-h|--help)
		show_help
		exit 0
		;;
	-i|--interpreter)
		shift
		opt_interpreter="$1"
		have_prog "$opt_interpreter" ||\
			die "Interpreter '${opt_interpreter}' not found"
		;;
	-j|--jobs)
		shift
		opt_jobs="$1"
		;;
	-q|--quick)
		opt_quick=1
		;;
	-g|--no-gui)
		opt_nogui=1
		;;
	-x|--extended)
		opt_extended=1
		;;
	-n|--renice)
		shift
		opt_renice="$1"
		;;
	-Q|--quiet)
		export AWLSIM_TEST_QUIET=1
		;;
	-L|--loglevel)
		shift
		opt_loglevel="$1"
		;;
	-l|--loop)
		shift
		opt_loop="$1"
		;;
	-c|--coverage)
		opt_coverage=1
		;;
	*)
		errormsg "Unknown option: $1"
		exit 1
		;;
	esac
	shift
done

[ -z "$opt_jobs" -o -n "$(printf '%s' "$opt_jobs" | tr -d '[0-9]')" ] &&\
	die "--jobs: '$opt_jobs' is not a positive integer number."
if [ $opt_jobs -eq 0 ]; then
	opt_jobs="$(getconf _NPROCESSORS_ONLN)"
	opt_jobs="$(expr $opt_jobs + 2)"
fi
[ -z "$opt_jobs" ] &&\
	die "Could not detect number of CPUs."

if [ -z "$opt_loop" -o -n "$(printf '%s' "$opt_loop" | tr -d '[0-9]')" ] || [ $opt_loop -le 0 ]; then
	opt_loop=infinite
fi


do_renice()
{
	local niceness="$1"
	local pid="$2"

	renice "$niceness" "$pid" >/dev/null
}

adjust_niceness()
{
	local pid="$1"

	if [ -n "$opt_renice" ]; then
		do_renice "$opt_renice" "$pid" || die "Failed to renice"
	else
		# Try to renice. Ignore failure.
		do_renice 10 "$pid"
	fi
}


# Run the tests
global_retval=0
loop_iteration=0
while [ "$opt_loop" = "infinite" ] || [ $opt_loop -gt 0 ]; do
	infomsg "Running test loop iteration $(expr "$loop_iteration" + 1)"

	do_tests "$@"

	if [ $global_retval -ne 0 ]; then
		break
	fi
	if [ "$opt_loop" != "infinite" ]; then
		opt_loop="$(expr "$opt_loop" - 1)"
	fi
	loop_iteration="$(expr "$loop_iteration" + 1)"
done

exit $global_retval

#!/bin/sh

srcdir="$(dirname "$0")"
[ "$(echo "$srcdir" | cut -c1)" = '/' ] || srcdir="$PWD/$srcdir"

srcdir="$srcdir/.."

die() { echo "$*"; exit 1; }

# Import the makerelease.lib
# http://bues.ch/gitweb?p=misc.git;a=blob_plain;f=makerelease.lib;hb=HEAD
for path in $(echo "$PATH" | tr ':' ' '); do
	[ -f "$MAKERELEASE_LIB" ] && break
	MAKERELEASE_LIB="$path/makerelease.lib"
done
[ -f "$MAKERELEASE_LIB" ] && . "$MAKERELEASE_LIB" || die "makerelease.lib not found."

hook_get_version()
{
	local file="$1/awlsim/common/version.py"
	local maj="$(cat "$file" | grep -e VERSION_MAJOR | head -n1 | awk '{print $3;}')"
	local min="$(cat "$file" | grep -e VERSION_MINOR | head -n1 | awk '{print $3;}')"
	version="$maj.$min"
}

hook_post_checkout()
{
	default_hook_post_checkout "$@"

	rm -r "$1"/maintenance
}

hook_testbuild()
{
	export CYTHONPARALLEL=1
	default_hook_testbuild "$@"
}

hook_regression_tests()
{
	default_hook_regression_tests "$@"

	# Run selftests
	sh "$1/tests/run.sh" -j 0
}

hook_pre_archives()
{
	local archive_dir="$1"
	local checkout_dir="$2"

	default_hook_pre_archives "$@"

	echo "Building PiLC firmware..."
#	local raspihat_fw_dir="$checkout_dir/pilc/raspi-hat/firmware"
#	CFLAGS= CPPFLAGS= CXXFLAGS= LDFLAGS= make
#	mkdir "$raspihat_fw_dir/bin"
#	cp "$raspihat_fw_dir/"*.hex "$checkout_dir/bin/"
}

project=awlsim
default_archives=py-sdist-bz2
makerelease "$@"

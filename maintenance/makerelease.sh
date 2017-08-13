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
	local maj="$(cat "$file" | grep -e 'VERSION_MAJOR =' | head -n1 | awk '{print $3;}')"
	local min="$(cat "$file" | grep -e 'VERSION_MINOR =' | head -n1 | awk '{print $3;}')"
	local ext="$(cat "$file" | grep -e 'VERSION_EXTRA =' | head -n1 | awk '{print $3;}' | cut -d'"' -f2)"
	version="${maj}.${min}${ext}"
}

hook_post_checkout()
{
	info "Pulling in git submodules"
	git submodule update --init submodules/pyprofibus

	info "Removing version control files"
	default_hook_post_checkout "$@"
	rm "$1"/maintenance/update-submodules

	info "Checking signatures"
	for f in "$1"/progs/putty/*/*.gpg; do
		gpg --verify "$f" "$(dirname "$f")/$(basename "$f" .gpg)" ||\
			die "Signature check failed."
	done

	info "Unpacking PuTTY"
	for f in "$1"/progs/putty/*/*.zip; do
		7z x -o"$(dirname "$f")/$(basename "$f" .zip)" "$f" ||\
			die "Unzip failed"
		rm "$f" "$f".gpg ||\
			die "Failed to remove archives"
	done
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

	info "Building PiLC firmware"
	local raspihat_fw_dir="$checkout_dir/pilc/raspi-hat/firmware"
	for target in all clean; do
		CFLAGS= CPPFLAGS= CXXFLAGS= LDFLAGS= \
		make -C "$raspihat_fw_dir" $target
	done
}

export AWLSIM_FULL_BUILD=1
export AWLSIM_CYTHON=1
export AWLSIM_CYTHON_PARALLEL=1

project=awlsim
default_archives=py-sdist-bz2
makerelease "$@"

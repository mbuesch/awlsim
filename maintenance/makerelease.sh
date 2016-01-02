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

# $1=file
__check_text_encoding()
{
	local file="$1"

	[ x"$(du -b "$file" | cut -f1)" = x"0" ] && return

	# Check CR/LF
	file -L "$file" | grep -qe 'CRLF line terminators' || {
		die "ERROR: '$file' is not in DOS format."
	}
	# Check file encoding
	file -L "$file" | grep -qEe '(ISO-8859 text)|(ASCII text)' || {
		die "ERROR: '$file' invalid file encoding."
	}
}

# $1=directory
__check_test_dir_encoding()
{
	local directory="$1"

	for entry in "$directory"/*; do
		[ -d "$entry" ] && {
			__check_test_dir_encoding "$entry"
			continue
		}
		[ "$(echo -n "$entry" | tail -c4)" = ".awl" ] || continue
		__check_text_encoding "$entry"
	done
}

hook_post_checkout()
{
	default_hook_post_checkout "$@"

	rm -r "$1"/maintenance

	info "Checking test file encodings"
	__check_test_dir_encoding "$1"/tests
}

hook_regression_tests()
{
	# Run selftests
	sh "$1/tests/run.sh"
}

project=awlsim
default_archives=py-sdist-bz2
makerelease "$@"

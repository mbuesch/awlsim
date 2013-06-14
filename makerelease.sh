#!/bin/sh

srcdir="$(dirname "$0")"
[ "$(echo "$srcdir" | cut -c1)" = '/' ] || srcdir="$PWD/$srcdir"

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
	local file="$1/awlsim/main.py"
	local maj="$(cat "$file" | grep -e VERSION_MAJOR | head -n1 | awk '{print $3;}')"
	local min="$(cat "$file" | grep -e VERSION_MINOR | head -n1 | awk '{print $3;}')"
	version="$maj.$min"
}

hook_regression_tests()
{
	for awl in "$1"/tests/*.awl; do
		# Check CR/LF
		file -L "$awl" | grep -qe 'CRLF line terminators' || {
			die "ERROR: 'tests/$(basename "$awl")' is not in DOS format."
		}
		# Check file encoding
		file -L "$awl" | grep -qEe '(ISO-8859 text)|(ASCII text)' || {
			die "ERROR: 'tests/$(basename "$awl")' invalid file encoding."
		}
	done

	# Run selftests
	sh "$1/tests/run.sh"
}

project=awlsim
default_compress=zip
makerelease "$@"

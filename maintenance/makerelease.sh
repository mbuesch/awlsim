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
	local maj="$(cat "$file" | grep -Ee '^VERSION_MAJOR\s+=\s+' | head -n1 | awk '{print $3;}')"
	local min="$(cat "$file" | grep -Ee '^VERSION_MINOR\s+=\s+' | head -n1 | awk '{print $3;}')"
	local bug="$(cat "$file" | grep -Ee '^VERSION_BUGFIX\s+=\s+' | head -n1 | awk '{print $3;}')"
	local ext="$(cat "$file" | grep -Ee '^VERSION_EXTRA\s+=\s+' | head -n1 | awk '{print $3;}' | cut -d'"' -f2)"
	version="${maj}.${min}.${bug}${ext}"
}

hook_post_checkout()
{
	info "Pulling in git submodules"
	git submodule update --init --recursive

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
		"$SEVENZIP" x -o"$(dirname "$f")/$(basename "$f" .zip)" "$f" ||\
			die "Unzip failed"
		rm "$f" "$f".gpg ||\
			die "Failed to remove archives"
	done
}

hook_testbuild()
{
	CFLAGS=-O0 CPPFLAGS= CXXFLAGS=-O0 LDFLAGS= \
		default_hook_testbuild "$@"
}

hook_regression_tests()
{
	default_hook_regression_tests "$@"

	# Run selftests
	sh "$1/tests/run.sh" -j 0
}

hook_doc_archives()
{
	local archive_dir="$1"
	local checkout_dir="$2"

	local doc_name="$project-doc-$version"
	local doc_dir="$tmpdir/$doc_name"
	mkdir "$doc_dir" ||\
		die "Failed to create directory '$doc_dir'"
	(
		cd "$checkout_dir" || die "Failed to cd '$checkout_dir'"
		rsync --recursive --prune-empty-dirs \
			--include='/doc/' \
			--include='/doc/**/' \
			--include='/doc/**.png' \
			--include='/doc/**.jpg' \
			--include='/doc/**.jpeg' \
			--include='/doc/**.1' \
			--include='/doc/**.html' \
			--include='/doc/**.htm' \
			--include='/doc/**.txt' \
			--include='/doc/**/README' \
			--include='/*.html' \
			--include='/*.htm' \
			--include='/*.txt' \
			--exclude='*' \
			. "$doc_dir" ||\
			die "Failed to copy documentation."
		cd "$tmpdir" || die "Failed to cd '$tmpdir'"
		tar cJf "$archive_dir"/$doc_name.tar.xz \
			"$doc_name" ||\
			die "Failed to create doc archive."
	) || die
}

export AWLSIM_FULL_BUILD=1
export AWLSIM_CYTHON_BUILD=1
export AWLSIM_CYTHON_PARALLEL=1

project=awlsim
default_archives=py-sdist-xz
makerelease "$@"

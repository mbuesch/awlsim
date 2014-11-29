# awlsim-cli with coreserver tests

sh_test()
{
	local interpreter="$1"

	echo
	echo "--- Running coreserver tests"
	cd "$rootdir" || die "Failed to change to rootdir '$rootdir'"
	for testfile in 000-base/shutdown.awl; do
		run_test "$interpreter" "$basedir/$testfile" \
			--spawn-backend --interpreter "$interpreter"
	done
	echo -n "--- Finished coreserver tests "
}

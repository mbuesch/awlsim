# LinuxCNC hardware module test

sh_test()
{
	local interpreter="$1"

	cd "$rootdir" || die "Failed to change to rootdir '$rootdir'"

	modpath="$rootdir/fake/linuxcnc_fake_hal"

	for testfile in "000-base/empty.awl" "000-base/EXAMPLE.awlpro"; do
		PYTHONPATH="$modpath:$PYTHONPATH" \
		JYTHONPATH="$modpath:$JYTHONPATH" \
		IRONPYTHONPATH="$modpath:$IRONPYTHONPATH" \
			"$interpreter" ./awlsim-linuxcnc-hal \
			--check-cnc 0 --onecycle "$rootdir/tests/$testfile" ||\
				test_failed "LinuxCNC test '$testfile' failed"
	done
}

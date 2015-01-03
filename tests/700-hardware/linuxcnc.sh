# LinuxCNC hardware module test

sh_test()
{
	local interpreter="$1"
	local test_dir="$2"
	local test_name="$3"

	cd "$rootdir" || die "Failed to change to rootdir '$rootdir'"

	modpath="$rootdir/fake/linuxcnc_fake_hal"

	echo ""
	for testfile in "000-base/empty.awl"\
			"000-base/shutdown.awl"\
			"000-base/EXAMPLE.awlpro"; do
		echo "    Running linuxcnc test with: $testfile"

		FAKEHAL_HALFILE="${test_dir}/linuxcnc.hal" \
		PYTHONPATH="$modpath:$PYTHONPATH" \
		JYTHONPATH="$modpath:$JYTHONPATH" \
		IRONPYTHONPATH="$modpath:$IRONPYTHONPATH" \
			"$interpreter" ./awlsim-linuxcnc-hal \
			--watchdog off --max-runtime 1.0 --extended-insns \
			"$rootdir/tests/$testfile" >/dev/null ||\
				test_failed "LinuxCNC test '$testfile' failed"
	done
}

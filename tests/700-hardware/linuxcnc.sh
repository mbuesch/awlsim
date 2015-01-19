# LinuxCNC hardware module test

__run_awlsim_linuxcnc_hal()
{
	local interpreter="$1"
	local test_dir="$2"
	local awl_file="$3"
	shift 3

	local modpath="$rootdir/fake/linuxcnc_fake_hal"

	FAKEHAL_HALFILE="${test_dir}/linuxcnc.hal" \
	PYTHONPATH="$modpath:$PYTHONPATH" \
	JYTHONPATH="$modpath:$JYTHONPATH" \
	IRONPYTHONPATH="$modpath:$IRONPYTHONPATH" \
		"$interpreter" ./awlsim-linuxcnc-hal \
		--input-base 0 --input-size 32 \
		--output-base 0 --output-size 32 \
		--watchdog off --extended-insns \
		"$@" \
		"$awl_file" >/dev/null ||\
			test_failed "LinuxCNC test '$(basename "$awl_file")' failed"
}

sh_test()
{
	local interpreter="$1"
	local test_dir="$2"
	local test_name="$3"

	cd "$rootdir" || die "Failed to change to rootdir '$rootdir'"

	echo ""
	for testfile in "000-base/empty.awl"\
			"000-base/shutdown.awl"\
			"000-base/EXAMPLE.awlpro"; do
		echo "    Running linuxcnc test with: $testfile"

		__run_awlsim_linuxcnc_hal "$interpreter" "$test_dir" \
			"$rootdir/tests/$testfile" \
			--max-runtime 1.0
	done

	echo "    Running I/O test"
	__run_awlsim_linuxcnc_hal "$interpreter" "$test_dir" \
		"$test_dir/linuxcnc-iotest.awl__"
}

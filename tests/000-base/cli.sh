# command line interface tests

sh_test()
{
	local interpreter="$1"

	cd "$rootdir" || die "Failed to change to rootdir '$rootdir'"


	# check awlsim-test executable

	"$interpreter" ./awlsim-test -h >/dev/null ||\
		test_failed "Call to awlsim-test -h failed"
	"$interpreter" ./awlsim-test --help >/dev/null ||\
		test_failed "Call to awlsim-test -h failed"

	"$interpreter" ./awlsim-test -I dummy >/dev/null ||\
		test_failed "Call to awlsim-test -I dummy failed"
	"$interpreter" ./awlsim-test --hardware-info dummy >/dev/null ||\
		test_failed "Call to awlsim-test --hardware-info dummy failed"

	"$interpreter" ./awlsim-test --list-sfc >/dev/null ||\
		test_failed "Call to awlsim-test --list-sfc failed"
	"$interpreter" ./awlsim-test --list-sfc-verbose >/dev/null ||\
		test_failed "Call to awlsim-test --list-sfc-verbose failed"
	"$interpreter" ./awlsim-test --list-sfb >/dev/null ||\
		test_failed "Call to awlsim-test --list-sfb failed"
	"$interpreter" ./awlsim-test --list-sfb-verbose >/dev/null ||\
		test_failed "Call to awlsim-test --list-sfb-verbose failed"

}

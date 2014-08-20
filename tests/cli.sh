# awlsim-cli tests

sh_test()
{
	local interpreter="$1"

	cd "$rootdir" || die "Failed to change to rootdir '$rootdir'"


	"$interpreter" ./awlsim-cli -h >/dev/null ||\
		test_failed "Call to awlsim-cli -h failed"
	"$interpreter" ./awlsim-cli --help >/dev/null ||\
		test_failed "Call to awlsim-cli -h failed"

	"$interpreter" ./awlsim-cli -I dummy >/dev/null ||\
		test_failed "Call to awlsim-cli -I dummy failed"
	"$interpreter" ./awlsim-cli --hardware-info dummy >/dev/null ||\
		test_failed "Call to awlsim-cli --hardware-info dummy failed"

	"$interpreter" ./awlsim-cli --list-sfc >/dev/null ||\
		test_failed "Call to awlsim-cli --list-sfc failed"
	"$interpreter" ./awlsim-cli --list-sfc-verbose >/dev/null ||\
		test_failed "Call to awlsim-cli --list-sfc-verbose failed"
	"$interpreter" ./awlsim-cli --list-sfb >/dev/null ||\
		test_failed "Call to awlsim-cli --list-sfb failed"
	"$interpreter" ./awlsim-cli --list-sfb-verbose >/dev/null ||\
		test_failed "Call to awlsim-cli --list-sfb-verbose failed"

}

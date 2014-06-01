# awlsimcli tests

sh_test()
{
	local interpreter="$1"

	cd "$rootdir" || die "Failed to change to rootdir '$rootdir'"


	"$interpreter" ./awlsimcli -h >/dev/null ||\
		test_failed "Call to awlsimcli -h failed"
	"$interpreter" ./awlsimcli --help >/dev/null ||\
		test_failed "Call to awlsimcli -h failed"

	"$interpreter" ./awlsimcli -I dummy >/dev/null ||\
		test_failed "Call to awlsimcli -I dummy failed"
	"$interpreter" ./awlsimcli --hardware-info dummy >/dev/null ||\
		test_failed "Call to awlsimcli --hardware-info dummy failed"

	"$interpreter" ./awlsimcli --list-sfc >/dev/null ||\
		test_failed "Call to awlsimcli --list-sfc failed"
	"$interpreter" ./awlsimcli --list-sfb >/dev/null ||\
		test_failed "Call to awlsimcli --list-sfb failed"
}

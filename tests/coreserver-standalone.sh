# Standalone coreserver tests

sh_test()
{
	local interpreter="$1"

	cd "$rootdir" || die "Failed to change to rootdir '$rootdir'"

	# Quick test to awlsim-server
	"$interpreter" ./awlsim-server -h >/dev/null ||\
		test_failed "Call to awlsim-server -h failed"
}

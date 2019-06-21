# symtab parser tests

sh_test()
{
	local interpreter="$1"
	local test_dir="$2"
	local test_name="$3"

	cd "$rootdir" || die "Failed to change to rootdir '$rootdir'"

	local test_file="${test_dir}/${test_name}.asc"

	"$interpreter" ./awlsim-symtab -I auto -O asc \
		"$test_file" - >/dev/null ||\
		test_failed "$(basename "$test_file") test failed"
}

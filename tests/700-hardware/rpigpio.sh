# Raspberry Pi GPIO hardware module test

sh_test()
{
	local interpreter="$1"
	local test_dir="$2"
	local test_name="$3"

	export EXTRA_PYTHONPATH="$rootdir/libs/raspi_fake_gpio"
	run_awl_test "$interpreter" "$test_dir/rpigpio.awlpro"
}

# awlsim-test with coreserver tests

sh_test()
{
	local interpreter="$1"

	infomsg
	infomsg "--- Running coreserver tests"
	cd "$rootdir" || die "Failed to change to rootdir '$rootdir'"

	for testfile in tc000_base/shutdown.awl \
			tc000_base/EXAMPLE.awlpro; do
		run_test "$interpreter" "$basedir/$testfile" \
			--spawn-backend --interpreter "$interpreter" \
			--connect-to localhost:$(get_port)
	done

	infomsg "----- Testing MemoryArea accesses"
	run_test "$interpreter" "$basedir/tc000_base/EXAMPLE.awlpro" \
		--spawn-backend --interpreter "$interpreter" \
		--connect-to localhost:$(get_port) \
		--mem-read E:1:8 --mem-read A:2:16 --mem-read M:3:32 \
		--mem-read L:4:8 --mem-read DB:1:5:16 --mem-read T:10 \
		--mem-read Z:10 --mem-read STW \
		--mem-write E:50:8:1 --mem-write A:51:16:2 --mem-write M:52:32:3 \
		--mem-write DB:1:5:16:5 --mem-write T:0:0 \
		--mem-write Z:1:0

	infomsg -n "--- Finished coreserver tests "
}

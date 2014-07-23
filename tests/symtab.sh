# symtab parser tests

sh_test()
{
	local interpreter="$1"

	cd "$rootdir" || die "Failed to change to rootdir '$rootdir'"


	# Print help text
	"$interpreter" ./awlsim-symtab -h >/dev/null ||\
		test_failed "Call to awlsim-symtab -h failed"


	# Test CSV input
	cat << EOF |\
	"$interpreter" ./awlsim-symtab -I auto -O csv - - >/dev/null ||\
		test_failed "Call to awlsim-symtab -I auto -O csv failed"
Merker 1;M 0.0;BOOL;Symbol 1
Merker 2;M 0.1;BOOL;Symbol 2
EOF
	cat << EOF |\
	"$interpreter" ./awlsim-symtab -I csv -O csv - - >/dev/null ||\
		test_failed "Call to awlsim-symtab -I csv -O csv failed"
Merker 1;M 0.0;BOOL;Symbol 1
Merker 2;M 0.1;BOOL;Symbol 2
EOF
	cat << EOF |\
	"$interpreter" ./awlsim-symtab -I csv -O readable-csv - - >/dev/null ||\
		test_failed "Call to awlsim-symtab -I csv -O readable-csv failed"
Merker 1;M 0.0;BOOL;Symbol 1
Merker 2;M 0.1;BOOL;Symbol 2
EOF
	cat << EOF |\
	"$interpreter" ./awlsim-symtab -I csv -O asc - - >/dev/null ||\
		test_failed "Call to awlsim-symtab -I csv -O asc failed"
Merker 1;M 0.0;BOOL;Symbol 1
Merker 2;M 0.1;BOOL;Symbol 2
EOF


	# Test ASC input
	cat << EOF |\
	"$interpreter" ./awlsim-symtab -I auto -O asc - - >/dev/null ||\
		test_failed "Call to awlsim-symtab -I auto -O asc failed"
126,Merker 1                M       0.0 BOOL      Symbol 1                                                                        
126,Merker 2                M       0.1 BOOL      Symbol 2                                                                        
EOF
	cat << EOF |\
	"$interpreter" ./awlsim-symtab -I asc -O asc - - >/dev/null ||\
		test_failed "Call to awlsim-symtab -I asc -O asc failed"
126,Merker 1                M       0.0 BOOL      Symbol 1                                                                        
126,Merker 2                M       0.1 BOOL      Symbol 2                                                                        
EOF
	cat << EOF |\
	"$interpreter" ./awlsim-symtab -I asc -O csv - - >/dev/null ||\
		test_failed "Call to awlsim-symtab -I asc -O csv failed"
126,Merker 1                M       0.0 BOOL      Symbol 1                                                                        
126,Merker 2                M       0.1 BOOL      Symbol 2                                                                        
EOF
	cat << EOF |\
	"$interpreter" ./awlsim-symtab -I asc -O readable-csv - - >/dev/null ||\
		test_failed "Call to awlsim-symtab -I asc -O readable-csv failed"
126,Merker 1                M       0.0 BOOL      Symbol 1                                                                        
126,Merker 2                M       0.1 BOOL      Symbol 2                                                                        
EOF

}

#!/usr/bin/env python3
#
# This script is used to generate the music for
# examples/raspberrypi-pixtend-musicplayer.awlpro
#

notes = []

def note(name, value):
	nameMap = {
		"pause"	: 0,
		"c"	: 1,
		"d"	: 2,
		"e"	: 3,
		"f"	: 4,
		"g"	: 5,
		"a"	: 6,
		"b"	: 7,
		"c'"	: 8,
		"d'"	: 9,
		"e'"	: 10,
		"f'"	: 11,
		"g'"	: 12,
		"a'"	: 13,
		"b'"	: 14,
		None	: 15,
	}
	valueMap = {
		"1/1"	: 0,
		"1/2"	: 1,
		"1/4"	: 2,
		"1/8"	: 3,
		"1/16"	: 4,
		"1/32"	: 5,
		"1/64"	: 6,

		"sharp"	: 0,
		"dot"	: 1,
		"tie"	: 2,
		"up"	: 3,
		"down"	: 4,
	}
	notes.append(nameMap[name] | (valueMap[value] << 4))

n = note
tie = lambda: note(None, "tie")
dot = lambda: note(None, "dot")


# The Free Software Song
# Sadi moma bela loza (Bulgarian folk song)
# Words by Richard Stallman, the Free Software Foundation http://fsf.org/
# Richard Stallman and the Free Software Foundation claim no copyright on this song.
# The official homepage for this song is http://www.gnu.org/music/free-software-song.html

n("d'", "1/4"); n("c'", "1/8"); n("b", "1/4"); n("a", "1/4")
n("b", "1/4"); n("c'", "1/8"); n("b", "1/8"); tie(); n("a", "1/8"); n("g", "1/4")
n("g", "1/4"); dot(); n("a", "1/4"); dot(); tie(); n("b", "1/8")
n("c'", "1/4"); dot(); n("b", "1/4"); n("b", "1/8"); n("d'", "1/4")
n("a", "1/4"); dot(); n("a", "1/2")
n("d'", "1/4"); tie(); n("c'", "1/8"); tie(); n("b", "1/2")
n("d'", "1/4"); n("c'", "1/8"); n("b", "1/4"); n("a", "1/4")
n("b", "1/4"); n("c'", "1/8"); n("b", "1/8"); tie(); n("a", "1/8"); n("g", "1/4")
n("g", "1/4"); dot(); n("a", "1/4"); dot(); tie(); n("b", "1/8")
n("c'", "1/4"); dot(); n("b", "1/4"); n("b", "1/8"); n("d'", "1/4")
n("a", "1/4"); dot(); n("a", "1/2")
n("a", "1/4"); dot(); tie(); n("a", "1/2")


header="""DATA_BLOCK "DB_song"
	STRUCT
		SONG : ARRAY [0 .. %d] OF BYTE;
	END_STRUCT;
BEGIN
""" % (len(notes))

footer="END_DATA_BLOCK\n"

print(header, end='')
for i, n in enumerate(notes):
	print("\tSONG[%d] := B#16#%02X;\n" % (i, n), end='')
print("\tSONG[%d] := B#16#FF;\n" % (i + 1), end='')
print(footer, end='')

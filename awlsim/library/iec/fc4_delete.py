# -*- coding: utf-8 -*-
#
# AWL simulator - IEC library - FC 4 "DELETE"
#
# Copyright 2015 Michael Buesch <m@bues.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim.common.compat import *

from awlsim.library.libentry import *


class Lib__IEC__FC4_DELETE(AwlLibFC):
	libraryName	= "IEC"
	staticIndex	= 4
	symbolName	= "DELETE"
	description	= "Delete STRING characters"

	interfaceFields = {
		BlockInterfaceField.FTYPE_IN	: (
			VerboseBlockIntfField(name="IN", dataType="STRING",
					      desc="Input string"),
			VerboseBlockIntfField(name="L", dataType="INT",
					      desc="Number of characters to delete"),
			VerboseBlockIntfField(name="P", dataType="INT",
					      desc="Position of first character to delete"),
		),
		BlockInterfaceField.FTYPE_OUT	: (
			VerboseBlockIntfField(name="RET_VAL", dataType="STRING",
					      desc="Output string"),
		),
		BlockInterfaceField.FTYPE_TEMP	: (
			VerboseBlockIntfField(name="AR1_SAVE", dataType="DWORD",
					      desc="Saved AR1 register"),
			VerboseBlockIntfField(name="MAX_COPY_LEN", dataType="INT",
					      desc="Maximum number of characters to copy"),
			VerboseBlockIntfField(name="IN_END", dataType="DWORD",
					      desc="Pointer beyond end of #IN string"),
			VerboseBlockIntfField(name="DEL_START", dataType="DWORD",
					      desc="Pointer to first deleted character in #IN"),
			VerboseBlockIntfField(name="DEL_END", dataType="DWORD",
					      desc="Pointer beyond last deleted character in #IN"),
			VerboseBlockIntfField(name="RET_VAL_START", dataType="DWORD",
					      desc="Pointer to start of #RET_VAL"),
		),
	}

	awlCodeCopyright = "Copyright (c) 2015 Michael Buesch <m@bues.ch>"
	awlCodeLicense = "BSD-2-clause"
	awlCodeIsStandard = True
	awlCodeVersion = "0.1"

	awlCode = """
	TAR1	#AR1_SAVE	// Save AR1 register

// ---------------------------------------------------------------------------
// Load a pointer to #IN into AR1 and open the DB
	LAR1	P##IN		// AR1 := pointer to #IN DB-pointer.
	L	W [AR1, P#0.0]	// Get the DB number from the DB-pointer.
	T	#MAX_COPY_LEN	// Abuse #MAX_COPY_LEN variable temporarily.
	AUF	DB [#MAX_COPY_LEN] // Open the DB.
	L	D [AR1, P#2.0]	// Get the actual #IN data pointer...
	LAR1			// and store it in AR1.

// ---------------------------------------------------------------------------
// Load a pointer to #RET_VAL into AR2 and open the DB as DI
	LAR2	P##RET_VAL	// AR1 := pointer to #RET_VAL DB-pointer.
	L	W [AR2, P#0.0]	// Get the DB number from the DB-pointer.
	T	#MAX_COPY_LEN	// Abuse #MAX_COPY_LEN variable temporarily.
	AUF	DI [#MAX_COPY_LEN] // Open the DB as DI.
	L	D [AR2, P#2.0]	// Get the actual #RET_VAL data pointer.
	// If #RET_VAL points to DB (area 84) change it to DI (area 85).
	// This also works, if #RET_VAL points to VL (area 87).
	// Other areas are not possible.
	OD	DW#16#85000000
	LAR2			// Store #RET_VAL data pointer in AR2.
	T	#RET_VAL_START	// And also in #RET_VAL_START for later use.

// ---------------------------------------------------------------------------
// Calculate a pointer to the end of #IN.
// #IN_END is a pointer beyond the last character if #IN.
CEND:	L	B [AR1, P#1.0]	// Get actual length of #IN.
	+	2		// Plus two bytes (max-len and act-len bytes).
	SLD	3		// Convert to pointer format.
	TAR1			// Accu1 := pointer to #IN string.
	+D			// Add #IN pointer to length.
	T	#IN_END		// This is our end-pointer #IN_END.

// ---------------------------------------------------------------------------
// Check if #L or #P is negative.
	L	#L
	L	#P
	OW			// Combine #L with #P (bitwise OR).
	UW	W#16#8000	// Mask out sign bit.
	SPN	ERR		// Jump, if sign bit is set.

// ---------------------------------------------------------------------------
// Calculate the maximum number of characters to copy.
// Pseudo code:
//   #MAX_COPY_LEN := MIN(ACTUAL_LEN(#IN), MAX_LEN(#RET_VAL))
	L	B [AR2, P#0.0]	// Get #RET_VAL maximum length.
	T	#MAX_COPY_LEN	// Save this as the maximum copy length.
	L	B [AR1, P#1.0]	// Get #IN actual length.
	<=I			// If #RET_VAL max-len > #IN act-len...
	SPB	ZCHK
	T	#MAX_COPY_LEN	// ...save #IN act-len as maximum copy length.

// ---------------------------------------------------------------------------
// If #L or #P is zero or #P is bigger than the actual
// length of #IN, copy the whole #IN to #RET_VAL.
ZCHK:	L	#L
	OW	W#16#0		// Evaluate value of #L (sets A0/A1 STW).
	SPZ	FCPY		// Jump to full copy, if L# is zero (/A0 * /A1).
	L	#P
	OW	W#16#0		// Evaluate value of #P (sets A0/A1 STW).
	SPZ	FCPY		// Jump to full copy, if P# is zero (/A0 * /A1).
	L	#MAX_COPY_LEN
	>I			// If P# > #MAX_COPY_LEN ...
	SPB	FCPY		// ...jump to full copy.

// ---------------------------------------------------------------------------
// Calculate the start and the end of the deleted area.
// #DEL_START is a pointer to the first deleted character.
// #DEL_END is a pointer beyond the last deleted character.
	TAR1			// Accu1 := pointer to #IN string.
	L	#P		// Get the delete position.
	+	1		// Make zero based (-1) and skip to first character (+2).
	SLD	3		// Convert to pointer format.
	+D			// Add it to the #IN pointer.
	T	#DEL_START	// This is our #DEL_START pointer.
	L	#L		// Get the delete count (# of chars).
	SLD	3		// Convert to pointer format.
	+D			// Add it to #DEL_START.
	T	#DEL_END	// This is our #DEL_END.
	L	#IN_END		// Compare #DEL_END to #IN_END.
	<=D			// If #DEL_END is beyond our #IN string length...
	SPB	SNIP		//  (can happen if #P + #L is too big)
	T	#DEL_END	// ...use #IN_END as our #DEL_END.

// ---------------------------------------------------------------------------
// Restrict #DEL_START and #IN_END to the maximum number
// of characters to copy.
// First check (pseudo code):
//   LIMIT := #IN_PTR + ((#MAX_COPY_LEN + 2) << 3)
//   IF (#DEL_START > LIMIT) THEN
//       #DEL_START := LIMIT
//       #DEL_END := LIMIT
//   ENDIF
SNIP:	TAR1			// Accu1 := pointer to #IN string.
	L	#MAX_COPY_LEN	// Get maximum copy length.
	+	2		// Add two for max-len and act-len bytes.
	SLD	3		// Convert to pointer format.
	+D			// Add to #IN pointer.
	L	#DEL_START	// Compare to #DEL_START.
	>=D
	SPB	SNP2		// Jump, if bigger or equal.
	TAK			// Save computed value as #DEL_START and #DEL_END.
	T	#DEL_START
	T	#DEL_END

// Second check (pseudo code):
//   LIMIT := #IN_PTR + ((#MAX_COPY_LEN + 2) << 3) + (#DEL_END - #DEL_START)
//   IF (#IN_END > LIMIT) THEN
//       #IN_END := LIMIT
//   ENDIF
SNP2:	L	#DEL_END	// Subtract #DEL_START from #DEL_END.
	L	#DEL_START
	-D
	L	#MAX_COPY_LEN	// Get maximum copy length.
	+	2		// Add two for max-len and act-len bytes.
	SLD	3		// Convert to pointer format.
	+D			// Add to computed del range.
	TAR1			// Accu1 := pointer to #IN string.
	+D			// Add #IN pointer to computed value.
	L	#IN_END		// Compare to #IN_END.
	>=D
	SPB	SKIP		// Jump, if bigger or equal.
	TAK			// Save computed value as #IN_END.
	T	#IN_END

// ---------------------------------------------------------------------------
// Skip the max-len and actual-len bytes in #IN and #RET_VAL.
// This makes both pointers point to the first character.
SKIP:	+AR1	P#2.0		// Skip 2 bytes in #IN string.
	+AR2	P#2.0		// Skip 2 bytes in #RET_VAL string.

// ---------------------------------------------------------------------------
// Copy the first part of the string from #IN to #RET_VAL.
// (The part before the deleted section)
CPY1:	TAR1			// Accu1 := pointer to #IN string.
	L	#DEL_START	// Get the end of the first copy chunk.
	>=D			// If current pointer is beyond end of chunk...
	SPB	DEL		// ...jump to second chunk (the part after del).
	L	B [AR1, P#0.0]	// Get one character from #IN.
	T	B [AR2, P#0.0]	// Put the character to #RET_VAL.
	+AR1	P#1.0		// Increment #IN pointer.
	+AR2	P#1.0		// Increment #RET_VAL pointer.
	SPA	CPY1		// Jump back to first copy loop start.

// ---------------------------------------------------------------------------
// Copy the second part of the string from #IN to #RET_VAL.
// (The part after the deleted section)
DEL:	LAR1	#DEL_END	// AR1 := pointer to second chunk of #IN string.
CPY2:	TAR1			// Accu1 := pointer to #IN string.
	L	#IN_END		// Get the end of the second copy chunk.
	>=D			// If current pointer is beyond end of chunk...
	SPB	WLEN		// ...we are done and jump to writing the length.
	L	B [AR1, P#0.0]	// Get one character from #IN.
	T	B [AR2, P#0.0]	// Put the character to #RET_VAL.
	+AR1	P#1.0		// Increment #IN pointer.
	+AR2	P#1.0		// Increment #RET_VAL pointer.
	SPA	CPY2		// Jump back to second copy loop start.

// ---------------------------------------------------------------------------
// Write #RET_VAL actual length
// Calculate it from AR2.
// AR2 currently points one character beyond the #RET_VAL string.
// (So it represents the actual length of the string.)
WLEN:	TAR2			// Accu1 := #RET_VAL pointer (AR2).
	L	#RET_VAL_START	// Get the start pointer to the #RET_VAL string.
	LAR2			// Save the start pointer (for later use) in AR2.
	-D			// Subtract #RET_VAL start pointer from actual pointer.
	SRD	3		// Convert from pointer format to byte count.
	+	-2		// Subtract two bytes (max-len and actual-len bytes).
	T	B [AR2, P#1.0]	// We have the #RET_VAL actual length. Store it in #RET_VAL.

// ---------------------------------------------------------------------------
// Everything is Ok.
	SET			// VKE := 1
	SAVE			// BIE := 1
END:	LAR1	#AR1_SAVE	// Restore AR1 register
// ---------------------------------------------------------------------------
	BEA			// BLOCK END
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Do a full copy of all #IN characters to #RET_VAL.
// Set #DEL_START and #DEL_END to #IN string end (that is #IN_END),
// so nothing will get deleted.
FCPY:	L	#IN_END
	T	#DEL_START
	T	#DEL_END
	SPA	SNIP		// Jump to the copying routine.

// ---------------------------------------------------------------------------
// Input value error handler (#P or #L have invalid values).
ERR:	L	0
	T	B [AR2, P#1.0]	// #RET_VAL actual string length := 0
	CLR			// VKE := 0
	SAVE			// BIE := 0
	SPA	END
// ---------------------------------------------------------------------------
	BE			// BLOCK END
"""

AwlLib.registerEntry(Lib__IEC__FC4_DELETE)

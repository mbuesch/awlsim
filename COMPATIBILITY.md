Awlsim - STEP 7 compatibility
=============================

The execution of AWL/STL programs by Awlsim is supposed to be fully compatible with the execution of compiled AWL/STL programs on the real Siemens S7 CPU. However, there currently are some known differences. These are listed below. Any undocumented difference between Awlsim and STEP 7 is considered to be a bug that should be reported.

* Awlsim does not implement all features of STEP 7, yet. See TODO.md for a list of missing features.

* Changing a symbol's address or data type in Awlsim does change the AWL/STL semantics of the code that uses this symbol. This is due to source text being the first class program object in Awlsim. (In STEP 7 first class program objects are the compiled blocks.) Awlsim compiles and reinterpretes the symbol information of the plain source text on each download to the CPU. The same thing happens in STEP 7, if a source text is imported.

* Awlsim does not compile AWL/STL to MC7 code and it cannot execute MC7 code. On startup Awlsim translates the AWL/STL code to an Awlsim specific in-memory representation of the code. There is no byte-code representation of this code.

* Some key concepts, such as `CALL` or memory indirect addressing are implemented natively in Awlsim. This means to improve runtime performance in Awlsim `CALL` is not a macro. From a user's perspective there should not be any functional difference visible in `CALL`. Any such difference is a bug. However, due to these constraints, it is not possible to call `FBs` or `FCs` with an interface (`IN/OUT/INOUT` variables) via `UC` or `CC` instructions.

* Undefined behavior is not emulated. For example: If reading uninitialized L-stack space in STEP 7 always yields a certain reproducible result, that does not mean that this AWL/STL code does the same thing in Awlsim. Reading uninitialized `TEMP`-memory is undefined.


Awlsim extensions
=================

Extensions are features that Awlsim supports, but STEP 7 does not support.

* Semicolons: AWL/STL requires semicolons (;) after each declaration, initialization and statement. As an Awlsim convenience service, terminating semicolons can be omitted in AWL/STL statements. Data declarations and initializations (in `DBs` and `FB/FC` interfaces), however, must end with a semicolon.

* Awlsim supports `DATE_AND_TIME` immediate constants (for example `DT#2012-01-02-13:37:00.000`) to `FC` and `FB` `DATE_AND_TIME` `IN`-variables. In `FC` calls the `DATE_AND_TIME` constant is copied to `VL` memory and passed via `DB`-pointer (that is itself stored in `VL`).

* Awlsim supports passing `STRING` immediate constants (for example 'Test') to `FC` and `FB` `STRING` `IN`-variables. In `FC` calls the `STRING` constant is copied to `VL` memory and passed via `DB`-pointer (that is itself stored in `VL`). The maximum length of the `STRING` immediate is casted up to the parameter's maximum length and added characters are filled with zero-bytes. The actual length of the string does not change.

* Awlsim supports `STRING` parameters in `FCs` with sizes unequal to 254 characters. Only actual-parameters with exactly the specified max-size as specified in the `FC` interface are allowed in the `CALL` assignment. (One exception being `STRING` immediates. See above.)

* Awlsim supports pointer immediates to named `DB` variables. Whether a 32 bit pointer (area spanning), a 48 bit `DB` pointer or a 80 bit `ANY` pointer is generated, depends on the context. For example:

<pre>
// Load a pointer to VARIABLE with DBX area code into accu 1.
// Note that the DB number information is lost (32 bit pointer).
L  P#DB1.VARIABLE

// Pass pointer immediates as actual values in calls.
// Values are passed as DB pointer or ANY pointer, according to the
// parameter type.
CALL  FC 1 (
    POINTER_VAR := P#DB1.VARIABLE,
    ANY_VAR     := P#DB1.VARIABLE,
)
</pre>

However, for the pointer parameter passing in `CALL` you could just write it in an S7 compatible way without the `P#` prefix.

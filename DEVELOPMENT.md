# Awlsim development notes


## Unit tests

The unit test suite can be run with the invocation of the command `./tests/run.sh`. This will run all unit tests and show the results.
Please see `./tests/run.sh --help` for more options.


### Code coverage tracing

To run a code statement coverage trace during unit testing the option `./tests/run.sh --coverage` is available. The results will be stored in `./code-coverage-report/`. It is desired to have a reasonable code coverage of the unit tests. All main code paths should be covered.


## Special annotations in the source code

In order to support both compiling the Awlsim core with Cython and running the same code in a plain Python interpreter without compilation, a method to patch the files is required. The setup.py scrips patch each .py source file and create a .pyx file before starting Cython compilation. The Cython patching mechanism rewrites all `import`s to import the compiled Cython modules instead of the plain Python modules. In addition to that some special comments are provided as hint to the Cython patcher:

* `#@cy` : Enable (un-comment) this line during Cython patching.
* `#@cy-posix` : Enable (un-comment) this line during Cython patching, if compiling for a Posix platform.
* `#@cy-win` : Enable (un-comment) this line during Cython patching, if compiling for a Windows platform.
* `#@nocy` : Disable (comment) this line during Cython patching.
* `#@no-cython-patch` : Do not touch this line during cython patching.
* `#+NoneToNULL` : Transform all `None` keywords in this line into `NULL`.
* `#+cimport` : Transform all `import` keywords in this line into `cimport`.
* `#+cdef` : Add a `cdef` to this line. For functions or methods that means to change `def` into `cdef` in the function signature. For classes that means to change `class` to `cdef class`.
* `#+cpdef` : Same as `#+cdef`, but add `cpdef` instead.
* `#+cdef-foobar-bizz` : Same as `#+cdef`, but also add the additional words `foobar bizz` after `cdef`. Arbitrary words may be specified and the number of words is not limited. The dash `-` will be transformed into a space character.
* `#+likely` : Mark an `if` condition as being likely to evaluate to True. This annotation can only be used in lines with an `if` statement. It helps the C compiler to generate better machine code.
* `#+unlikely` : Mark an `if` condition as being unlikely to evaluate to True. This annotation can only be used in lines with an `if` statement. It helps the C compiler to generate better machine code.
* `#+suffix-u` : Add an `u` suffix to all decimal and hexadecimal immediates in the line.
* `#+suffix-LL` : Add an `L` suffix to all decimal and hexadecimal immediates in the line.

To disable code coverage tracing an additional special comment is provided:

* `#@nocov` : This excludes the line from Python `coverage` tracing.


# Incomplete awlsim TODO list

## S7 compatibility

* Add feature: Missing SFCs/SFBs
* Add feature: Missing library FCs/FBs
* Add feature: Parsing of attributes

## core

* Improve performance (cython)
* Single download of symtab causes a redefinition error.
* Add feature: LAD (KOP) compiler

## AWL / STL optimizer

* Add optimization pass: O(UU)O(UU) -> UUOUU
* Add optimization pass: U(UU)= -> UU=  (also for other insn types)
* Add optimization pass: Reordering of TEMP variables for space packing

## GUI

* Add feature: LAD (KOP) editor
* Add feature: Global find/replace
* Add feature: find/replace for symbol table editor
* Add feature: find/replace for library selection editor
* Add feature: Symbol table editor and interface editor: Copy/paste
* Add feature: Symbol table editor and interface editor: Context menu (right click).
* Add feature: Symbol table editor and interface editor: Data type auto completion. (Issue #23)
* Add feature: Symbol table editor and interface editor: Name suggestions based on existing names. (Issue #23)
* Add feature: Library selections editor copy/paste

## FBD / FUP GUI

* Rewrite wire drawing algorithm
* Improve performance in big diagrams
* Add feature: Support modifying wires by clicking onto them
* Add feature: Make width (and height?) of operands selectable
* Add feature: Exchange elements
* Add feature: Live view of signal states (online diagnosis)
* Add feature: find/replace for FUP editor

## FBD / FUP compiler

* Fix evaluation order in case of multiple parallel assignments and other elements
* Add element: CALL

Incomplete awlsim TODO list
===========================

S7 compatibility
----------------

* Add feature: Parsing of attributes
* Add feature: Implement the remaining FUP block types

core
----

* Improve performance (cython)
* Blocks that are no longer linked to (created by) sources should be removed.
* Single download of symtab causes a redefinition error.
* Add feature: FBD (FUP) decompiler
* Add feature: LAD (KOP) (de-)compiler

AWL / STL optimizer
-------------------

* Add optimization pass: O(UU)O(UU) -> UUOUU
* Add optimization pass: U(UU)= -> UU=  (also for other insn types)

GUI
---

* Add feature: Save window status (open MDI windows, positions, etc)
* Add feature: Show UDTs in block tree
* Add feature: LAD (KOP) editor

FBD / FUP
---------

* Fix evaluation order in case of multiple parallel assignments and other elements
* Add feature: Exchange elements
* Add feature: Duplicate diagrams
* Add feature: Copy & paste elements
* Add feature: Undo/redo
* Add feature: XML input and export of single diagrams
* Add feature: Live view of signal states (online diagnosis)
* Add feature: Support modifying wires by clicking onto them

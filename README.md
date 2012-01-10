TinyCPSInterpreter
===

This is an interpreter for very small, lisp like language. It's entirely
impractical (an interpreted language written in an interpreted language...)
and entirely for my own education. 

The language is purely functional and free of side effects (including I/O for now).
The mechanism for control flow is explicitly passed continuations, thus
every named function must take a continuation as its first parameter.

CPS was chosen because it could be a good intermediate representation
for a compiled (semi-)functional language.

Project structure:
---

- tinycps.py is the driver for the interpreter. It allows either
evaluation of a module read from a file or an interactive REPL.

- parser_combinator.py is a set of parser combinators for python.

- sexp_parser.py is a parser for s-expressions using the parser 
  combinator library included.

- sexp_to_cps.py is a utility module that converts the output of the
  parser into nodes in an expression tree.

- expression_tree.py is the intermediate representation of tinycas programs.
  It allows for both recursive, tree-walking evaluation and compilation to
  a linear pseudo-bytecode.

- vm.py is a virtual machine for the bytecode generated by compiling tinycas
  programs using expression_tree.py
  
- For examples in action, see the tests folder. The most interesting program
  is hailstone.tcps which computes the length of the Collatz sequence for
  a given natural number.

To do:
---

- Fix bugs in the REPL. There are some cases where badly behaved programs can crash
  the entire REPL.

- Better error reporting. Error reporting for runtime and compile errors is vague.

- Output true bytecode to a file to be run at a later time.

- Get rid of the jump table in the vm. It's unnecessary and reduces performance.

- More language features. To be a interesting language, some sort of data structure
  other than floating point numbers is necessary.

- Type checking. Since this is an exploration of language implementation, one of the
  primary aspects that needs to be looked at is static typing.

- Possibly compilation to LLVM IR although a direct translation between VM instructions
  and LLVM IR may be difficult.

- Better syntax. S-expressions are easy to parse but annoying to write.

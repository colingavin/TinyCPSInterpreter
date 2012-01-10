#!/usr/bin/python

import sys
from copy import copy

import tinycps.sexp_parser as sexp_parser
import tinycps.sexp_to_cps as sexp_to_cps
import tinycps.expression_tree as expression_tree
import tinycps.vm as vm

INTERACTIVE_MAIN = "__main__"

def convert_def(parse, module):
    new_module = copy(module)
    main_already_present = "main" in new_module
    new_module.update(sexp_to_cps.convert_parse_to_cps(parse))
    if "main" in new_module and not main_already_present:
        new_module[INTERACTIVE_MAIN] = expression_tree.Func(["ret"], expression_tree.Call("main", [expression_tree.Finish()]))
    return new_module

def convert_call(parse, module):
    call = sexp_to_cps.convert_func_body(parse[0], True)
    new_module = copy(module)
    new_module[INTERACTIVE_MAIN] = expression_tree.Func(["ret"], call)
    return new_module

def convert_const(parse, module):
    value = sexp_to_cps.convert_argument(parse[0], True)
    new_module = copy(module)
    new_module[INTERACTIVE_MAIN] = expression_tree.Func(["ret"], expression_tree.Call("ret", [value]))
    return new_module

def add_parse_to_module(parse, module):
    error_text = ""
    success = False
    for conversion in [convert_def, convert_call, convert_const]:
        try:
            module = conversion(parse, module)
            success = True
        except Exception as e:
            error_text += str(e) + "\n"
    if success:
        return module, ""
    else:
        return None, error_text


def interactive_eval(txt, module):
    stream, result, parse = sexp_parser.SExpGrammer().parse(txt)
    if not result or stream.position != len(txt):
        print " " * (stream.position + 2) + "^"
        print "Parse error at position: %i" % stream.position
        return None

    module, error_text = add_parse_to_module(parse, module)
    if not module:
        print "Could not interpret syntax:"
        print error_text
        return None
    
    if INTERACTIVE_MAIN not in module:
        return module
    
    try:
        prog = expression_tree.Prog(module, main=INTERACTIVE_MAIN)
        instrs, jumps = prog.compile()
    except Exception as e:
        print "Compile error: " + str(e)
        return None
    
    try:
        print vm.run_program(instrs, jumps)
    except vm.RuntimeException as e:
        print "Runtime error: " + str(e)
        return None
    
    del module[INTERACTIVE_MAIN]
    return module


def repl():
    module = {}
    while True:
        try:
            txt = raw_input("> ")
            new_module = interactive_eval(txt, module)
            if new_module:
                module = new_module
        except EOFError:
            print "Goodbye."
            return


def static_eval(txt):
    stream, result, parse = sexp_parser.SExpGrammer().parse(txt)
    if not result or stream.position != len(txt):
        print " " * (stream.position + 2) + "^"
        print "Parse error at position: %i" % stream.position
        return
    
    try:
        module = sexp_to_cps.convert_parse_to_cps(parse, False)
    except Exception as e:
        print "Could not interpret syntax: " + str(e)
        return

    try:
        prog = expression_tree.Prog(module)
        instrs, jumps = prog.compile()
    except Exception as e:
        print "Compile error: " + str(e)
        return
    
    try:
        print "Program output: " + str(vm.run_program(instrs, jumps))
    except vm.RuntimeException as e:
        print "Runtime error: " + str(e)
        return


def main():
    if len(sys.argv) == 1:
        repl()
    elif len(sys.argv) == 2:
        with open(sys.argv[1]) as f:
            static_eval(f.read())
    else:
        print "Usage: tinycps [filename]"

            
if __name__ == "__main__":
    main()

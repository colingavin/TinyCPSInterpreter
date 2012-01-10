"""
This module uses the parser_combinator module to implement
a grammer for s-expressions.
"""

from parser_combinator import *

class SExpGrammer(Grammer):
    strip = lambda self, x: x[0] if len(x) == 1 else x
    reducer = lambda self, x: "".join(x)
    var = lambda self, x: self.reducer(x)
    parse_float = lambda self, x: float(self.reducer(x))
    
    def identifier(self):
        return Seq(Alpha(), Star(Or(Alpha(), Num()), post=self.reducer), post=self.var)
    
    def number(self):
        return Plus(Num(), post=self.reducer)
    
    def decimal(self):
        return Seq(Ref("number"), Opt(Seq(Symbol("."), Ref("number"), post=self.reducer)), post=self.parse_float)
    
    def operator(self):
        return Or(Symbol("+"), Symbol("-"), Symbol("*"), Symbol("/"), Symbol("^"), Symbol("!"), Symbol("="), Symbol("<"), Symbol("_"), Symbol("%"))
    
    def atom(self):
        return Seq(Ref("consume_whitespace"), Or(Ref("identifier"), Ref("decimal"), Ref("operator")), Ref("consume_whitespace"), post=self.strip)
    
    def consume_whitespace(self):
        return Star(White(), post=lambda x: None)
    
    def sexp(self):
        return Or(Ref("atom"),
                  Seq(Ref("consume_whitespace"),
                      Word("("),
                      Ref("consume_whitespace"),
                      Star(Ref("sexp")),
                      Ref("consume_whitespace"),
                      Word(")"), post=self.strip))

    def start(self):
        return Star(Seq(Ref("sexp"), Ref("consume_whitespace"), post=self.strip))

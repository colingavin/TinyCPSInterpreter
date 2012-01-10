"""
A small parser combinator library in python.

Combinators are objects with have an apply method which takes an input
stream and a grammer and returns a modified stream, whether a match was made,
and what was produced by the match, if anything.

The basic parsers are Word, Seq, and Or, but others are provided as a convenience.
"""

class Stream(object):
    def __init__(self, string, position=0):
        self.string = string
        self.position = position
        
    def __repr__(self):
        return "'%s'@%i" % (self.string, self.position)
    
    def advanced(self, characters):
        return Stream(self.string, self.position + characters)
    
    def startswith(self, prefix):
        return self.string[self.position:].startswith(prefix)

class Grammer(object):
    def __getitem__(self, name):
        return self.__getattribute__(name)
    
    def start(self):
        raise Exception("Start must be implemented to create a grammer.")

    def parse(self, s):
        if not isinstance(s, Stream):
            s = Stream(s)
        res = self.start().apply(s, self)
        return res

class Parser(object):
    # apply is the method which evaluates a parser with the given grammer
    # stream is the current input stream, grammer is a reference to the Grammer object being parsed
    # returns a tuple (stream, matched, production)
    def __init__(self):
        self.postprocessor = lambda x: x
    
    def apply(self, stream, grammer):
        raise Exception("apply called on generic Parser.");

# a Ref parser simply calls an existing parser by name
class Ref(Parser):
    def __init__(self, name):
        self.reference = name
    
    def __repr__(self):
        return self.reference
    
    def apply(self, stream, grammer):
        actual = grammer[self.reference]
        if callable(actual):
            actual = actual()
        res = actual.apply(stream, grammer)
        return res

# a Word parser matches a constant string against the head of the stream and produces None
class Word(Parser):
    def __init__(self, symbol, post=None):
        super(Word, self).__init__()
        self.symbol = symbol
        if post:
            self.postprocessor = post
    
    def __repr__(self):
        return "'%s'" % self.symbol
    
    def apply(self, stream, grammer):
        if stream.startswith(self.symbol):
            return (stream.advanced(len(self.symbol)), True, self.postprocessor(None))
        else:
            return (stream, False, None)

def Symbol(symb):
    return Word(symb, post=lambda x: symb)

# an Opt parser matches a constant string or nothing and produces None
class Opt(Parser):
    def __init__(self, subparser, post=None):
        super(Opt, self).__init__()
        self.subparser = subparser
        if post:
            self.postprocessor = post
    
    def __repr__(self):
        return "?%s" % repr(self.subparser)
    
    def apply(self, stream, grammer):
        new_stream, res, production = self.subparser.apply(stream, grammer)
        if res:
            return (new_stream, True, self.postprocessor(production))
        else:
            return (stream, True, None)

# a Charset parser matches any number of characters from the head of the stream that are in its charset
# it produces the string that it matched
class Charset(Parser):
    def __init__(self, charset):
        super(Charset, self).__init__()
        self.charset = charset
    
    def __repr__(self):
        return "[%s]" % str(self.charset)
    
    def apply(self, stream, grammer):
        adv = 0
        rest = stream.string[stream.position:]
        while adv < len(rest) and rest[adv] in self.charset:
            adv += 1
        if adv > 0:
            ret = rest[:adv]
            return (stream.advanced(adv), True, self.postprocessor(ret))
        else:
            return (stream, False, None)

# an Alpha parser is an alias for a Charset parser that accepts only characters in the range [a, z]
class AlphaSet(object):
    def __repr__(self):
        return "a-zA-z"
    
    def __contains__(self, char):
        return ("a" <= char <= "z") or ("A" <= char <= "Z")
    
def Alpha():
    return Charset(AlphaSet())

# a Num parser is an alias for a Charset parser that accepts only characters in the range [0, 9]
class NumSet(object):
    def __repr__(self):
        return "0-9"
    
    def __contains__(self, char):
        return "0" <= char <= "9"

def Num():
    return Charset(NumSet())
    
def White():
    return Charset(" \t\n")

# a Seq parser matches all of its subparsers or nothing
# it produces a list of its subparsers productions
class Seq(Parser):
    def __init__(self, *subparsers, **kwargs):
        super(Seq, self).__init__()
        self.subparsers = subparsers
        self.postprocessor = kwargs["post"] if "post" in kwargs else self.postprocessor
    
    def __repr__(self):
        return "(%s)" % " ~ ".join([repr(p) for p in self.subparsers])
    
    def apply(self, stream, grammer):
        new_stream = stream
        productions = []
        for parser in self.subparsers:
            new_stream, match, production = parser.apply(new_stream, grammer)
            if match:
                if production is not None:
                    productions.append(production)
            else:
                return (stream, False, None)
        return (new_stream, True, self.postprocessor(productions))

# a Or parser matches any of its subparsers in order
# it produces the production of the first subparser to match
class Or(Parser):
    def __init__(self, *subparsers, **kwargs):
        super(Or, self).__init__()
        self.subparsers = subparsers
        self.postprocessor = kwargs["post"] if "post" in kwargs else self.postprocessor
    
    def __repr__(self):
        return "(%s)" % " | ".join([repr(p) for p in self.subparsers])
    
    def apply(self, stream, grammer):
        for parser in self.subparsers:
            res_stream, match, production = parser.apply(stream, grammer)
            if match:
                return (res_stream, True, self.postprocessor(production))
        return (stream, False, None)

# a Star parser matches its subparser zero or more times
# it produces a list of the productions of its subparser
class Star(Parser):
    def __init__(self, subparser, post=None):
        super(Star, self).__init__()
        self.subparser = subparser
        if post:
            self.postprocessor = post
    
    def __repr__(self):
        return "*%s" % repr(self.subparser)
    
    def apply(self, stream, grammer):
        productions = []
        new_stream, match, production = self.subparser.apply(stream, grammer)
        while match:
            if production is not None:
                productions.append(production)
            new_stream, match, production = self.subparser.apply(new_stream, grammer)
        return (new_stream, True, self.postprocessor(productions))

class Plus(Parser):
    def __init__(self, subparser, post=None):
        super(Plus, self).__init__()
        self.subparser = subparser
        if post:
            self.postprocessor = post
    
    def __repr__(self):
        return "+%s" % repr(self.subparser)
    
    def apply(self, stream, grammer):
        productions = []
        new_stream, match, production = self.subparser.apply(stream, grammer)
        while match:
            if production is not None:
                productions.append(production)
            new_stream, match, production = self.subparser.apply(new_stream, grammer)
        if len(productions) > 0:
            return (new_stream, True, self.postprocessor(productions))
        else:
            return (stream, False, None)

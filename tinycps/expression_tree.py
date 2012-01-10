from copy import copy

import vm

class Node(object):
    def __init__(self):
        super(Node, self).__init__()
    
    def apply(self, env):
        raise Exception("Cannot call apply on abstract Node. Did you forget to override?")

class Var(Node):
    def __init__(self, symbol):
        super(Var, self).__init__()
        self.symbol = symbol
    
    def __repr__(self):
        return "'%s" % self.symbol
    
    def apply(self, env):
        if self.symbol in env:
            return env[self.symbol]
        else:
            raise Exception("The symbol %s is not in the current scope." % self.symbol)

    def instructions(self, name, funcs_list, scope, offset):
        if not self.symbol in scope:
            if self.symbol in funcs_list:
                return {}, [vm.PushThunk(self.symbol, len(funcs_list[self.symbol].args))]
            raise Exception("The symbol %s is not in the current scope." % self.symbol)
        return {}, [vm.PushRel(scope[self.symbol] - offset)]

class Const(Node):
    def __init__(self, value):
        super(Const, self).__init__()
        self.value = value
    
    def __repr__(self):
        return str(self.value)
    
    def apply(self, env):
        return self
    
    def instructions(self, name, funcs_list, scope, offset):
        return {}, [vm.PushConst(self.value)]

class Func(Node):
    def __init__(self, args, body):
        super(Func, self).__init__()
        self.scope = {}
        self.args = args
        self.body = body
    
    def __repr__(self):
        return "{%s | %s}" % (" ".join(self.args), repr(self.body))
    
    def apply(self, env):
        self.body.apply(env)
    
    def compile(self, name, funcs_list, scope={}, offset=0):
        if not isinstance(self.body, Call):
            raise Exception("Function body must be a call.")
        scope = copy(scope)
        offset += len(self.args)
        for bound in scope:
            scope[bound] = scope[bound] - offset
        idx = len(self.args) - 1
        for local in self.args:
            scope[local] = -idx
            idx -= 1
        return self.body.compile(name, funcs_list, scope)

class FuncLiteral(Node):
    def __init__(self, func):
        super(FuncLiteral, self).__init__()
        self.func = func
    
    def __repr__(self):
        return repr(self.func)
    
    def apply(self, env):
        new_func = copy(self.func)
        new_func.scope = copy(env)
        return new_func
    
    def instructions(self, name, funcs_list, scope, offset):
        lambda_name = name + "_lambda_" + str(offset)
        new_functions, instructions = self.func.compile(lambda_name, funcs_list, scope, offset=offset)
        new_functions[lambda_name] = instructions
        return new_functions, [vm.PushLambda(lambda_name, len(self.func.args))]

class Call(Node):
    def __init__(self, func, args):
        super(Call, self).__init__()
        self.func = func
        self.args = args
    
    def __repr__(self):
        return "%s(%s)" % (self.func, " ".join([repr(arg) for arg in self.args]))
    
    def apply(self, env):
        if self.func not in env or not isinstance(env[self.func], Func):
            raise Exception("The function %s is not in the current scope." % self.func)
        to_call = env[self.func]
        if not len(to_call.args) == len(self.args):
            raise Exception("The function %s cannot be called with %i arguments." % (self.func, len(self.args)))
        new_env = copy(env)
        new_env.update(to_call.scope)
        for (idx, arg) in enumerate(self.args):
            new_env[to_call.args[idx]] = arg.apply(env)
        to_call.apply(new_env)
    
    def compile(self, name, funcs_list, scope):
        instructions = []
        offset = 0
        functions = {}
        for arg in self.args:
            funcs, instrs = arg.instructions(name, funcs_list, scope, offset)
            functions.update(funcs)
            instructions += instrs
            offset += 1
        if self.func in scope:
            instructions += [vm.JumpLambda(scope[self.func] - offset)]
        elif self.func in Prog.builtins:
            _, insts = Prog.builtins[self.func].instructions(name, funcs_list, scope, offset)
            instructions += insts
        else:
            instructions += [vm.JumpLabel(self.func, len(self.args))]
        return functions, instructions

class Builtin(Func):
    def __init__(self, args, impl, instrs):
        super(Builtin, self).__init__(["ret"] + args, self)
        self.impl = impl
        self.instrs = instrs
    
    def __repr__(self):
        return "{%s | <builtin>}" % " ".join(self.args)
    
    def apply(self, env):
        self.impl(env)
    
    def instructions(self, name, funcs_list, scope, offset):
        return {}, self.instrs(name, scope, offset)

class Finish(Func):
    def __init__(self):
        super(Finish, self).__init__(["__final"], self)
    
    def __repr__(self):
        return "<exit>"
    
    def apply(self, env):
        print "The result of the program was: %s." % str(env["__final"])
    
    def instructions(self, name, funcs_list, scope, offset):
        return {}, [vm.PushConst([vm.FINISH])]

class Prog(object):
    builtins = {}
    
    @classmethod
    def register_builtin(self, name, func):
        Prog.builtins[name] = func
    
    def __init__(self, module, main="main"):
        self.module = module
        self.main = main
    
    def run(self):
        if self.main not in self.module:
            raise Exception("Invalid module: missing entry: %s." % self.main)
        main = self.module[self.main]
        if not isinstance(main, Func):
            raise Exception("Invalid module: main is not a function.")
        new_module = copy(Prog.builtins)
        new_module.update(self.module)
        new_module[main.args[0]] = Finish()
        main.apply(new_module)
    
    def compile(self):
        if self.main not in self.module:
            raise Exception("Invalid module: missing entry: %s." % self.main)
        main = self.module[self.main]
        if not isinstance(main, Func):
            raise Exception("Invalid module: main is not a function.")
        # compile each function, because of lambdas, compiling a single function 
        # may create more than one actual function entry, thus the 'update'
        func_instr_blocks = {}
        for func_name in self.module:
            if not isinstance(self.module[func_name], Builtin):
                other_funcs, instructions = self.module[func_name].compile(func_name, self.module)
                func_instr_blocks.update(other_funcs)
                func_instr_blocks[func_name] = instructions
        # stitch the blocks together and generate the jump table
        instrs = func_instr_blocks[self.main]
        del func_instr_blocks[self.main]
        jump_table = {}
        jump_table[self.main] = 0
        idx = len(instrs)
        for func_name in func_instr_blocks:
            func = func_instr_blocks[func_name]
            instrs += func
            jump_table[func_name] = idx
            idx += len(func)
        return instrs, jump_table

add_node = Builtin( ["a", "b"], 
                    lambda env: Call("ret", [Const(env["a"].value + env["b"].value)]).apply(env),
                    lambda name, scope, offset: [vm.AddInst()])
Prog.register_builtin("+", add_node)

sub_node = Builtin( ["a", "b"],
                    lambda env: Call("ret", [Const(env["a"].value - env["b"].value)]).apply(env),
                    lambda name, scope, offset: [vm.SubInst()])
Prog.register_builtin("-", sub_node)

mul_node = Builtin( ["a", "b"],
                    lambda env: Call("ret", [Const(env["a"].value * env["b"].value)]).apply(env),
                    lambda name, scope, offset: [vm.MulInst()])
Prog.register_builtin("*", mul_node)

less_node = Builtin(["a", "b"],
                    lambda env: Call("ret", [Const(env["a"].value < env["b"].value)]).apply(env),
                    lambda name, scope, offset: [vm.LessInst()])
Prog.register_builtin("<", less_node)

eq_node = Builtin(  ["a", "b"],
                    lambda env: Call("ret", [Const(bool(env["a"].value == env["b"].value))]).apply(env),
                    lambda name, scope, offset: [vm.EqInst()])
Prog.register_builtin("=", eq_node)

mod_node = Builtin(  ["a", "b"],
                    lambda env: Call("ret", [Const(bool(env["a"].value % env["b"].value))]).apply(env),
                    lambda name, scope, offset: [vm.ModInst()])
Prog.register_builtin("%", mod_node)

def if_func(env):
    res = bool(env["cond"].value)
    if res:
        cont_branch = env["iftrue"]
    else:
        cont_branch = env["iffalse"]
    new_env = copy(env)
    new_env[cont_branch.args[0]] = env["ret"]
    cont_branch.apply(new_env)

def if_instr(name, scope, offset):
    return [vm.CondBranch()]

if_node = Builtin(["cond", "iftrue", "iffalse"], if_func, if_instr)
Prog.register_builtin("if", if_node)

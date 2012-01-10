from copy import copy

FINISH = "FINISH"
FINISH_IP = -1

class RuntimeException(Exception):
    def __init__(self, description, ip=None, jump_table=None, prog=None):
        super(RuntimeException, self).__init__()
        self.description = description
        self.ip = ip
        self.prog = prog
        self.jump_table = jump_table
    
    def __str__(self):
        return "Runtime error at instruction (%i: %s): %s." % (self.ip, str(self.prog[self.ip]), self.description)

# The abstract superclass for vm instructions.
class Instruction(object):
    def __init__(self):
        super(Instruction, self).__init__()
    
    def evaluate(self, stack, ip, jump_table):
        raise Exception("Cannot call evaluate on abstract Instruction. Did you forget to override?")

# Removes the value at the top of the stack
class Pop(Instruction):
    def __init__(self):
        super(Pop, self).__init__()

    def __repr__(self):
        return "Pop()"

    def evaluate(self, stack, ip, jump_table):
        del stack[-1]
        return ip + 1

# Pushes a constant value to the stack.
class PushConst(Instruction):
    def __init__(self, value):
        super(PushConst, self).__init__()
        self.value = value

    def __repr__(self):
        return "PushConst(%s)" % str(self.value)

    def evaluate(self, stack, ip, jump_table):
        stack.append(self.value)
        return ip + 1

# Pushes the value in the stack at offset onto the stack.
# To dup the top of the stack: PushRel(0)
class PushRel(Instruction):
    def __init__(self, offset):
        super(PushRel, self).__init__()
        self.offset = offset - 1

    def __repr__(self):
        return "PushRel(%i)" % (self.offset + 1)

    def evaluate(self, stack, ip, jump_table):
        stack.append(stack[self.offset])
        return ip + 1

# Pushes a lambda to the stack bound to the current scope.
class PushLambda(Instruction):
    def __init__(self, label, arg_count):
        super(PushLambda, self).__init__()
        self.label = label
        self.arg_count = arg_count

    def __repr__(self):
        return "PushLambda(%s, %i)" % (self.label, self.arg_count)

    def evaluate(self, stack, ip, jump_table):
        stack.append([self.label, self.arg_count] + copy(stack))
        return ip + 1

# Pushes a continuation to the top of the stack corresponding to a named function
# that is not a closure.
class PushThunk(Instruction):
    def __init__(self, label, arg_count):
        super(PushThunk, self).__init__()
        self.label = label
        self.arg_count = arg_count
    
    def __repr__(self):
        return "PushThunk(%s, %i)" % (self.label, self.arg_count)
    
    def evaluate(self, stack, ip, jump_table):
        stack.append([self.label, self.arg_count])
        return ip + 1

# Jumps to the continuation at the given offset on the stack.
class JumpLambda(Instruction):
    def __init__(self, offset):
        super(JumpLambda, self).__init__()
        self.offset = offset - 1
    
    def __repr__(self):
        return "JumpLambda(%i)" % (self.offset + 1)
    
    def evaluate(self, stack, ip, jump_table):
        lamb = stack[self.offset]
        if not isinstance(lamb, list):
            print stack
            raise RuntimeException("In JumpLambda stack value %s at offset %i is not a lambda." % (repr(lamb), self.offset + 1))
        if lamb[0] == FINISH:
            return FINISH_IP
        arg_count = lamb[1]
        args = stack[(-arg_count):]
        stack[:] = lamb[2:]
        stack += args
        return jump_table[lamb[0]]

# Jumps to the named function, clearing everything but the last arg_count entries from the stack.
class JumpLabel(Instruction):
    def __init__(self, label, arg_count):
        super(JumpLabel, self).__init__()
        self.label = label
        self.arg_count = arg_count
    
    def __repr__(self):
        return "JumpLabel(%s, %i)" % (self.label, self.arg_count)
    
    def evaluate(self, stack, ip, jump_table):
        #delete all but arg_count from the stack
        del stack[:-self.arg_count]
        if not self.label in jump_table:
            raise RuntimeException("In JumpLabel: there is no entry for %s in the jump table." % str(self.label))
        return jump_table[self.label]

# Implements 'if'. Jumps to iftrue if test or iffalse otherwise, passing continuation as
# the only argument.
# The last four elements of the stack should be [continuation, test, iftrue, iffalse]
class CondBranch(Instruction):
    def __init__(self):
        super(CondBranch, self).__init__()
    
    def __repr__(self):
        return "CondBranch()"
    
    def evaluate(self, stack, ip, jump_table):
        if stack[-3]:
            branch_offset = -2
        else:
            branch_offset = -1
        stack.append(stack[-4])
        return JumpLambda(branch_offset).evaluate(stack, ip, jump_table)
        
# Pops the last two entries off the stack, adds them, and pushes the value.
# Jumps to the continuation given.
class AddInst(Instruction):
    def __init__(self):
        super(AddInst, self).__init__()
    
    def __repr__(self):
        return "AddInst()"
    
    def evaluate(self, stack, ip, jump_table):
        rhs = stack.pop()
        lhs = stack.pop()
        stack.append(lhs + rhs)
        return JumpLambda(-1).evaluate(stack, ip, jump_table)

# Pops the last two entries off the stack, subtracts them, and pushes the value.
# Jumps to the continuation given.
class SubInst(Instruction):
    def __init__(self):
        super(SubInst, self).__init__()

    def __repr__(self):
        return "SubInst()"

    def evaluate(self, stack, ip, jump_table):
        rhs = stack.pop()
        lhs = stack.pop()
        stack.append(lhs - rhs)
        return JumpLambda(-1).evaluate(stack, ip, jump_table)

# Pops the last two entries off the stack, multiplies them, and pushes the value.
# Jumps to the continuation given.
class MulInst(Instruction):
    def __init__(self):
        super(MulInst, self).__init__()

    def __repr__(self):
        return "MulInst()"

    def evaluate(self, stack, ip, jump_table):
        rhs = stack.pop()
        lhs = stack.pop()
        stack.append(lhs * rhs)
        return JumpLambda(-1).evaluate(stack, ip, jump_table)

class LessInst(Instruction):
    def __init__(self):
        super(LessInst, self).__init__()

    def __repr__(self):
        return "LessInst()"

    def evaluate(self, stack, ip, jump_table):
        rhs = stack.pop()
        lhs = stack.pop()
        stack.append(lhs < rhs)
        return JumpLambda(-1).evaluate(stack, ip, jump_table)

class EqInst(Instruction):
    def __init__(self):
        super(EqInst, self).__init__()

    def __repr__(self):
        return "EqInst()"

    def evaluate(self, stack, ip, jump_table):
        rhs = stack.pop()
        lhs = stack.pop()
        stack.append(lhs == rhs)
        return JumpLambda(-1).evaluate(stack, ip, jump_table)

class ModInst(Instruction):
    def __init__(self):
        super(ModInst, self).__init__()

    def __repr__(self):
        return "EqInst()"

    def evaluate(self, stack, ip, jump_table):
        rhs = stack.pop()
        lhs = stack.pop()
        stack.append(lhs % rhs)
        return JumpLambda(-1).evaluate(stack, ip, jump_table)

def run_program(instructions, jump_table):
    stack = [[FINISH]]
    ip = 0
    while ip < len(instructions):
        try:
            ip = instructions[ip].evaluate(stack, ip, jump_table)
        except RuntimeException as e:
            e.ip = ip
            e.jump_table = jump_table
            e.prog = instructions
            raise e
        if ip is FINISH_IP:
            return stack[-1]
    raise RuntimeException("Program ended without calling exit continuation.", ip, jump_table, instructions)

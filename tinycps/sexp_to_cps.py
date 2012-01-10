"""
A small utility module that cleans up the output of the parser into usable Nodes.
"""

import numbers

import expression_tree

def convert_parse_to_cps(parse_output, transform_finish=True):
    module = {}
    for func in parse_output:
        if not isinstance(func, list) or len(func) != 4 or func[0] != "def":
            raise Exception("Top level definitions must be 'def'.")
        name, cps_func = convert_def(func, transform_finish)
        module[name] = cps_func
    return module

def convert_def(func, transform_finish):
    name = func[1]
    args = func[2]
    check_args(args)
    body = convert_func_body(func[3], transform_finish)
    return name, expression_tree.Func(args, body)

def convert_func_body(body, transform_finish):
    if not isinstance(body, list) or len(body) < 1 or not isinstance(body[0], str):
        raise Exception("Function body must be a call.")
    call_func = body[0]
    call_args = body[1:]
    converted_args = []
    for arg in call_args:
        converted_args.append(convert_argument(arg, transform_finish))
    return expression_tree.Call(call_func, converted_args)

def convert_argument(arg, transform_finish):
    if isinstance(arg, list):
        return convert_lambda(arg, transform_finish)
    if arg == "finish" and transform_finish:
        return expression_tree.Finish()
    if isinstance(arg, numbers.Number) or isinstance(arg, bool):
        return expression_tree.Const(arg)
    else:
        return expression_tree.Var(arg)
        
def convert_lambda(lamb, transform_finish):
    if lamb[0] != "lambda" or len(lamb) != 3:
        raise Exception("Lambda was expected but a call was found.")
    args = lamb[1]
    check_args(args)
    body = convert_func_body(lamb[2], transform_finish)
    return expression_tree.FuncLiteral(expression_tree.Func(args, body))
    
def check_args(args):
    for arg in args:
        if not isinstance(arg, str):
            raise Exception("Arguments in the arguments list must by symbols.")

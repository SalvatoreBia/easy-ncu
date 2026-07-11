# easy-ncu - A smart CLI tool for NVIDIA Nsight Compute report analysis.
# Copyright (C) 2026  Salvatore Biamonte
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import ast
import os
import re


def eval_node(node, variables):
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.Name):
        name = node.id
        if name in variables:
            return variables[name]
        else:
            raise NameError(f"Variable '{name}' not defined in rule file.")
    elif isinstance(node, ast.BinOp):
        left  = eval_node(node.left, variables)
        right = eval_node(node.right, variables)
        if isinstance(node.op, ast.Add):      return left + right
        elif isinstance(node.op, ast.Sub):    return left - right
        elif isinstance(node.op, ast.Mult):   return left * right
        elif isinstance(node.op, ast.Pow):    return left ** right
        elif isinstance(node.op, ast.Div):
            if right == 0:
                return 0.0
            return left / right
        else:
            raise TypeError(f"Operator not supported.")
    elif isinstance(node, ast.Call):
        op = node.func.id
        calc_args = [eval_node(arg, variables) for arg in node.args]
        if op == 'max':     return max(calc_args)
        elif op == 'min':   return min(calc_args)
        else:
            raise NameError(f"Function '{op}' not supported.")
    else:
        raise TypeError('Formula\'s structure not supported.')


class RuleParser:
    BLOCKS = {
        'vars' : '[VARIABLES]',
        'expr' : '[EXPRESSION]'
    }

    def __init__ (self):
        import __main__ as main_module
        self.main_mod = main_module
        self.block_pattern = re.compile(r'\[\w*\]')

    def is_block_header(self, s):
        return True if self.block_pattern.match(s) else False

    def evaluate(self, path, action):
        if not os.path.exists(path):
            print('[ERROR] Rule file does not exist.')
            return None
        
        variables = {}
        expressions = {}

        vars_block_found = False
        is_reading_vars = False
        with open(path, 'r') as file:
            for line in file:
                l = line.strip()
                if not l or l.startswith('#'):
                    continue

                if self.is_block_header(l):
                    if l == self.BLOCKS['vars']:
                        if not vars_block_found:
                            vars_block_found = True
                            is_reading_vars = True
                            continue
                        else:
                            print('[ERROR] Only one variables block can be defined.')
                            return None
                    else:
                        if not vars_block_found:
                            print('[ERROR] Variables block should be on top of every other block.')
                            return None
                        is_reading_vars = False
                        continue
                else:
                    if is_reading_vars:
                        key, val = l.split('=', maxsplit=1)
                        varname = key.strip()
                        ncu_name = val.strip()
                        metric = self.main_mod.get_metric(action, '', ncu_name)
                        if not metric['value']:
                            print(f'[WARNING] Query for metric {val} has returned None. Setting it to zero...')
                            variables[varname] = 0
                        else:
                            variables[varname] = metric['value']
                    else:
                        key, val = l.split('=', maxsplit=1)
                        out = key.strip()
                        expr = val.strip()
                        try:
                            tree = ast.parse(expr, mode='eval')
                            res  = eval_node(tree.body, variables)
                            expressions[out] = variables[out] = res
                        except Exception as e:
                            print(f'[ERROR] Unable to evaluate expression: {expr}')
                            print(e)
                            return None
        return expressions

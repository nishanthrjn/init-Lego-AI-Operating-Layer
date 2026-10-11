"""Reject Python outside a deliberately tiny scalar fixture language.

This is a language gate, not a claim to sandbox arbitrary Python. No attributes,
indirection, loops, recursion, decorators, plugins or model-selected commands.
"""

from __future__ import annotations

import ast

from .contracts import Rejected

ALLOWED = (
    ast.Module,
    ast.ImportFrom,
    ast.alias,
    ast.FunctionDef,
    ast.arguments,
    ast.arg,
    ast.Return,
    ast.Assign,
    ast.If,
    ast.Assert,
    ast.Expr,
    ast.Constant,
    ast.Name,
    ast.Load,
    ast.Store,
    ast.BinOp,
    ast.Add,
    ast.Sub,
    ast.UnaryOp,
    ast.USub,
    ast.UAdd,
    ast.Not,
    ast.Compare,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.IfExp,
    ast.Call,
)


def admitted(source: str, *, test: bool) -> ast.Module:
    if len(source.encode()) > 8192 or "#" in source or "\\" in source:
        raise Rejected("PYTHON_SUBSET_REJECTED")
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        raise Rejected("SYNTAX_INVALID") from None
    nodes = list(ast.walk(tree))
    if len(nodes) > 512:
        raise Rejected("PYTHON_SUBSET_REJECTED")
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if not functions or (not test and len(functions) != 1):
        raise Rejected("PYTHON_SUBSET_REJECTED")
    docstrings = {
        id(node.value)
        for body in [tree.body, *(function.body for function in functions)]
        for node in body[:1]
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    }
    for node in nodes:
        if not isinstance(node, ALLOWED):
            raise Rejected("PYTHON_SUBSET_REJECTED")
        if isinstance(node, (ast.Name, ast.arg)):
            name = node.id if isinstance(node, ast.Name) else node.arg
            if name.startswith("_") or "__" in name:
                raise Rejected("PYTHON_SUBSET_REJECTED")
        if isinstance(node, ast.Constant):
            if type(node.value) not in (int, bool, str, type(None)):
                raise Rejected("PYTHON_SUBSET_REJECTED")
            if isinstance(node.value, int) and abs(node.value) > 256:
                raise Rejected("PYTHON_SUBSET_REJECTED")
            if isinstance(node.value, str) and len(node.value) > 128:
                raise Rejected("PYTHON_SUBSET_REJECTED")
            if isinstance(node.value, str) and id(node) not in docstrings:
                raise Rejected("PYTHON_SUBSET_REJECTED")
        if isinstance(node, ast.ImportFrom):
            if not test or node.module != "subject" or node.level != 0:
                raise Rejected("PYTHON_SUBSET_REJECTED")
            if len(node.names) != 1 or node.names[0].name != "solve":
                raise Rejected("PYTHON_SUBSET_REJECTED")
            if node.names[0].asname is not None or node not in tree.body:
                raise Rejected("PYTHON_SUBSET_REJECTED")
        if isinstance(node, ast.FunctionDef):
            if node not in tree.body or node.decorator_list:
                raise Rejected("PYTHON_SUBSET_REJECTED")
            if (test and not node.name.startswith("test_")) or (
                not test and node.name != "solve"
            ):
                raise Rejected("PYTHON_SUBSET_REJECTED")
            args = node.args
            if args.defaults or args.kw_defaults or args.vararg or args.kwarg:
                raise Rejected("PYTHON_SUBSET_REJECTED")
            if args.posonlyargs or args.kwonlyargs or (test and args.args):
                raise Rejected("PYTHON_SUBSET_REJECTED")
            for annotation in [node.returns, *(a.annotation for a in args.args)]:
                if annotation is not None and not (
                    isinstance(annotation, ast.Name)
                    and annotation.id in {"int", "bool", "str"}
                    or isinstance(annotation, ast.Constant)
                    and annotation.value is None
                ):
                    raise Rejected("PYTHON_SUBSET_REJECTED")
        if isinstance(node, ast.Assign):
            if test or any(
                not isinstance(target, ast.Name)
                or target.id in {"solve", "int", "bool", "str"}
                for target in node.targets
            ):
                raise Rejected("PYTHON_SUBSET_REJECTED")
        if isinstance(node, ast.Call):
            if (
                not test
                or not isinstance(node.func, ast.Name)
                or node.func.id != "solve"
            ):
                raise Rejected("PYTHON_SUBSET_REJECTED")
            if node.keywords or not all(
                isinstance(arg, ast.Constant)
                and type(arg.value) is int
                or isinstance(arg, ast.UnaryOp)
                and isinstance(arg.op, ast.USub)
                and isinstance(arg.operand, ast.Constant)
                and type(arg.operand.value) is int
                for arg in node.args
            ):
                raise Rejected("PYTHON_SUBSET_REJECTED")
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.ImportFrom)) and not (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            raise Rejected("PYTHON_SUBSET_REJECTED")
    return tree

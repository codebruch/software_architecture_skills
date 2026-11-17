"""Per-function size and cyclomatic complexity, standard library only.

    python3 tools/complexity.py orderdesk

Cyclomatic complexity = 1 + decision points (if/elif, for, while, except,
each extra and/or operand, conditional expression, comprehension if).
LOC = lines in the function excluding the signature, blank lines and comments.
"""
import ast
import os
import sys


def complexity(func):
    score = 1
    for node in ast.walk(func):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.IfExp)):
            score += 1
        elif isinstance(node, ast.BoolOp):
            score += len(node.values) - 1
        elif isinstance(node, ast.comprehension):
            score += len(node.ifs)
    return score


def loc(func, lines):
    start = func.body[0].lineno
    count = 0
    for line in lines[start - 1:func.end_lineno]:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            count += 1
    return count


def main():
    rows = []
    for root in sys.argv[1:] or ["."]:
        for folder, _, files in os.walk(root):
            for name in sorted(files):
                if not name.endswith(".py"):
                    continue
                path = os.path.join(folder, name)
                source = open(path).read()
                lines = source.splitlines()
                for node in ast.walk(ast.parse(source)):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        rows.append((complexity(node), loc(node, lines), "%s:%d" % (path, node.lineno), node.name))
    rows.sort(reverse=True)
    print("%-4s %-4s %-34s %s" % ("CC", "LOC", "location", "function"))
    for cc, n, where, name in rows:
        print("%-4d %-4d %-34s %s" % (cc, n, where, name))


if __name__ == "__main__":
    main()

"""Safe Python code executor for controlled snippets."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any


@dataclass
class ExecutionResult:
    ok: bool
    output: Any
    error: str = ""


ALLOWED_BUILTINS = {
    "len": len,
    "min": min,
    "max": max,
    "sum": sum,
    "sorted": sorted,
    "range": range,
}

DISALLOWED_NODES = (
    ast.Import,
    ast.ImportFrom,
    ast.With,
    ast.Try,
    ast.Raise,
    ast.ClassDef,
    ast.Global,
    ast.Nonlocal,
)


def safe_exec(code: str, context: dict[str, Any] | None = None) -> ExecutionResult:
    """Execute constrained Python code after AST validation."""

    context = context or {}
    try:
        tree = ast.parse(code, mode="exec")
        for node in ast.walk(tree):
            if isinstance(node, DISALLOWED_NODES):
                return ExecutionResult(False, None, f"Disallowed syntax: {type(node).__name__}")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in {"exec", "eval", "open", "compile", "__import__"}:
                    return ExecutionResult(False, None, f"Disallowed call: {node.func.id}")

        local_env: dict[str, Any] = {}
        global_env = {"__builtins__": ALLOWED_BUILTINS, **context}
        exec(compile(tree, "<safe_exec>", "exec"), global_env, local_env)
        return ExecutionResult(True, {**global_env, **local_env})
    except Exception as exc:
        return ExecutionResult(False, None, str(exc))

"""Conservative lint before import; not an OS security sandbox."""

import ast
import builtins
import re
from types import ModuleType
import hashlib
import importlib.util
from pathlib import Path
from .base import BaseStrategy
from quantlab.types import InvalidStrategyOutputError

ALLOWED = {
    "math",
    "numpy",
    "pandas",
    "statistics",
    "typing",
    "collections",
    "datetime",
    "quantlab.strategy.base",
}
FORBIDDEN_CALLS = {
    "open",
    "eval",
    "exec",
    "compile",
    "getattr",
    "setattr",
    "delattr",
    "globals",
    "locals",
    "vars",
    "input",
    "breakpoint",
    "__import__",
}
FORBIDDEN_ATTRS = {
    "open",
    "DataSource",
    "ExcelFile",
    "ExcelWriter",
    "HDFStore",
    "read_clipboard",
    "read_gbq",
    "to_clipboard",
    "read_csv",
    "read_parquet",
    "read_pickle",
    "read_json",
    "read_html",
    "read_excel",
    "read_sql",
    "read_sql_query",
    "read_sql_table",
    "read_feather",
    "read_hdf",
    "read_orc",
    "read_fwf",
    "read_xml",
    "read_table",
    "read_sas",
    "read_stata",
    "read_spss",
    "load",
    "loads",
    "loadtxt",
    "genfromtxt",
    "fromfile",
    "memmap",
    "save",
    "savez",
    "savez_compressed",
    "savetxt",
    "to_csv",
    "to_parquet",
    "to_pickle",
    "to_json",
    "to_sql",
    "to_excel",
    "to_hdf",
    "to_feather",
    "to_orc",
    "to_xml",
    "to_html",
    "tofile",
    "dump",
    "dumps",
    "eval",
    "query",
    "io",
    "ctypeslib",
    "ctypes",
    "testing",
}


def lint_strategy(path, allowed_modules=None):
    allowed_modules = ALLOWED if allowed_modules is None else allowed_modules
    path = Path(path)
    source = path.read_text()
    tree = ast.parse(source, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = (
                [a.name for a in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
            if isinstance(node, ast.ImportFrom) and (
                node.level or any(a.name == "*" for a in node.names)
            ):
                raise InvalidStrategyOutputError(
                    "Relative/wildcard imports are forbidden"
                )
            if any(m not in allowed_modules for m in modules):
                raise InvalidStrategyOutputError(
                    f"Forbidden strategy import: {modules}"
                )
            if any(
                a.name in FORBIDDEN_ATTRS or a.name.startswith("_") for a in node.names
            ):
                raise InvalidStrategyOutputError("Forbidden import member")
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_CALLS:
            raise InvalidStrategyOutputError(f"Forbidden strategy operation: {node.id}")
        if isinstance(node, ast.Attribute) and (
            node.attr.startswith("_")
            and node.attr != "__init__"
            or node.attr in FORBIDDEN_ATTRS
        ):
            raise InvalidStrategyOutputError(
                f"Forbidden strategy attribute: {node.attr}"
            )
        if isinstance(node, ast.Attribute) and isinstance(
            node.ctx, (ast.Store, ast.Del)
        ):
            # A strategy may maintain its own state, never mutate data or context.
            if not isinstance(node.value, ast.Name) or node.value.id != "self":
                raise InvalidStrategyOutputError(
                    "Only strategy self attributes may be assigned"
                )
    return source


def load_strategy(path, params, factor_paths=None):
    factor_paths = factor_paths or {}
    factors = {}
    for factor_name, factor_path in factor_paths.items():
        if not re.fullmatch(r"factors\.[A-Za-z][A-Za-z0-9_]*", factor_name):
            raise InvalidStrategyOutputError(f"Invalid factor binding: {factor_name}")
        factor_source = lint_strategy(factor_path)
        factor = ModuleType(factor_name)
        exec(compile(factor_source, str(factor_path), "exec"), factor.__dict__)
        factors[factor_name] = factor
    source = lint_strategy(path, ALLOWED | set(factors))
    # Require explicit from-imports, resolved to exactly the configured source file.
    # No sys.path modification or sys.modules cache can redirect frozen factors.
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import) and any(a.name in factors for a in node.names):
            raise InvalidStrategyOutputError("Use from factors.module import function")

    def factor_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in factors and fromlist and level == 0:
            return factors[name]
        return builtins.__import__(name, globals, locals, fromlist, level)

    name = "quantlab_user_" + hashlib.sha256(source.encode()).hexdigest()[:12]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise InvalidStrategyOutputError("Strategy must be a Python file")
    module = importlib.util.module_from_spec(spec)
    module.__dict__["__builtins__"] = dict(vars(builtins), __import__=factor_import)
    exec(compile(source, str(path), "exec"), module.__dict__)
    meta = getattr(module, "STRATEGY_META", None)
    if not isinstance(meta, dict) or any(
        not isinstance(meta.get(k), str) or not meta[k].strip()
        for k in ("name", "version", "description")
    ):
        raise InvalidStrategyOutputError(
            "STRATEGY_META requires name, version, description strings"
        )
    if not callable(getattr(module, "build_strategy", None)):
        raise InvalidStrategyOutputError("Missing build_strategy")
    strategy = module.build_strategy(params)
    if not isinstance(strategy, BaseStrategy):
        raise InvalidStrategyOutputError("build_strategy must return BaseStrategy")
    warmup = strategy.warmup_bars()
    if type(warmup) is not int or warmup < 0:
        raise InvalidStrategyOutputError("warmup_bars must be a non-negative integer")
    return strategy, meta, source

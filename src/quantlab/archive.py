"""Freeze all experiment inputs and archive each attempt without overwriting history."""

from datetime import datetime, timezone
import hashlib
from importlib.metadata import distributions, metadata
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import time
import webbrowser
import yaml
from quantlab.data.providers import get_provider
from quantlab.engine.backtest import run_backtest
from quantlab.metrics.performance import performance_metrics
from quantlab.report.builder import build_report, audit_assumptions
from quantlab.utils.serialization import write_json
from quantlab.utils.paths import allocate_run
from quantlab.utils.logging import run_logging


def git_info(root):
    def command(args):
        r = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True
        )
        return r.stdout.strip() if r.returncode == 0 else None

    return {
        "git_commit": command(["rev-parse", "HEAD"]),
        "git_status": command(["status", "--porcelain"]),
    }


def package_versions():
    return dict(
        sorted(
            (d.metadata["Name"], d.version)
            for d in distributions()
            if d.metadata["Name"]
        )
    )


def code_fingerprint():
    root = Path(__file__).parent
    files = sorted(
        p for p in root.rglob("*") if p.is_file() and p.suffix in (".py", ".j2")
    )
    digest = hashlib.sha256()
    for p in files:
        digest.update(str(p.relative_to(root)).encode())
        digest.update(p.read_bytes())
    return digest.hexdigest()


def archive_run(config):
    c = config.model_copy(deep=True)
    c.report.runs_dir = c.report.runs_dir.resolve()
    c.strategy.path = c.strategy.path.resolve()
    source = c.strategy.path.read_text()
    digest = hashlib.sha256(
        (source + str(c.model_dump(mode="json"))).encode()
    ).hexdigest()
    run = allocate_run(c.report.runs_dir, c.strategy.path.stem, digest)
    start = time.perf_counter()
    with run_logging(run / "logs.txt") as log:
        log.info("Run start %s", run.name)
        try:
            symbols = list(dict.fromkeys(c.universe.symbols + [c.data.benchmark]))
            raw = get_provider(c.data).load_prices(
                symbols, c.backtest.start_date, c.backtest.end_date
            )
            raw.to_parquet(run / "data.snapshot.parquet", index=False)
            (run / "strategy.snapshot.py").write_text(source)
            write_json(run / "config.original.json", c.model_dump(mode="json"))
            frozen = c.model_copy(deep=True)
            frozen.data.provider = "parquet_local"
            frozen.data.path = run / "data.snapshot.parquet"
            frozen.strategy.path = run / "strategy.snapshot.py"
            frozen.report.open_after_run = False
            factor_fingerprints = {}
            frozen.strategy.factor_paths = {}
            for name, factor_path in c.strategy.factor_paths.items():
                factor_source = Path(factor_path).read_bytes()
                # Hash-based names avoid interpreting configured module names as paths.
                digest = hashlib.sha256(factor_source).hexdigest()
                destination = run / "factors.snapshot" / f"{digest}.py"
                destination.parent.mkdir(exist_ok=True)
                destination.write_bytes(factor_source)
                frozen.strategy.factor_paths[name] = destination
                factor_fingerprints[name] = digest
            (run / "config.snapshot.yaml").write_text(
                yaml.safe_dump(frozen.model_dump(mode="json"), sort_keys=False)
            )
            log.info("Resolved config: %s", c.model_dump(mode="json"))
            result = run_backtest(frozen, raw)
            performance_metrics(result, c.analytics)
            versions = package_versions()
            result.metadata.update(
                {
                    "run_id": run.name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "python_version": platform.python_version(),
                    "platform": platform.platform(),
                    "package_versions": versions,
                    "engine_fingerprint": code_fingerprint(),
                    "factor_fingerprints": factor_fingerprints,
                    "strategy_fingerprint": hashlib.sha256(source.encode()).hexdigest(),
                    **git_info(config.strategy.path.parent),
                    "original_data_provider": c.data.provider,
                    "data_source": c.data.source,
                    "status": "complete",
                }
            )
            result.metadata.pop("strategy_source", None)
            source_root = Path(__file__).parent
            shutil.copytree(
                source_root,
                run / "code.snapshot/src/quantlab",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            project_root = source_root.parents[1]
            for filename in ["pyproject.toml", "README.md"]:
                if (project_root / filename).exists():
                    shutil.copy2(
                        project_root / filename, run / "code.snapshot" / filename
                    )
            # Wheel installs have no repository pyproject; generate installable snapshot metadata.
            snapshot_project = run / "code.snapshot/pyproject.toml"
            if not snapshot_project.exists():
                import json

                package = metadata("us-equity-quant-lab")
                dependencies = [
                    r
                    for r in package.get_all("Requires-Dist", [])
                    if "extra ==" not in r
                ]
                snapshot_project.write_text(
                    '[build-system]\nrequires = ["setuptools>=69"]\nbuild-backend = "setuptools.build_meta"\n[project]\nname = "us-equity-quant-lab"\nversion = "'
                    + package["Version"]
                    + '"\nrequires-python = ">=3.12"\ndependencies = '
                    + json.dumps(dependencies)
                    + '\n[project.scripts]\nquantlab = "quantlab.cli:app"\n[tool.setuptools.packages.find]\nwhere = ["src"]\n[tool.setuptools.package-data]\nquantlab = ["report/templates/*.j2"]\n'
                )
            (run / "requirements.snapshot.txt").write_text(
                "".join(
                    f"{name}=={version}\n"
                    for name, version in versions.items()
                    if name.lower().replace("_", "-") != "us-equity-quant-lab"
                )
            )
            for name, frame in [
                ("equity", result.equity_curve),
                ("returns", result.returns),
                ("orders", result.orders),
                ("fills", result.fills),
                ("benchmark", result.benchmark),
                ("decisions", result.decisions),
            ]:
                frame.to_csv(run / f"{name}.csv", index=False, float_format="%.17g")
            result.positions.to_parquet(run / "positions.parquet", index=False)
            write_json(run / "metrics.json", result.metrics)
            write_json(run / "warnings.json", result.warnings)
            write_json(
                run / "summary.json",
                {
                    "run_id": run.name,
                    "initial_cash": c.backtest.initial_cash,
                    "final_equity": float(result.equity_curve.equity.iloc[-1]),
                    "metrics": result.metrics,
                    "audit_assumptions": audit_assumptions(c),
                },
            )
            command = f"quantlab backtest run --strategy {shlex.quote(str(run / 'strategy.snapshot.py'))} --config {shlex.quote(str(run / 'config.snapshot.yaml'))}"
            (run / "reproduce.sh").write_text("#!/bin/sh\nset -eu\n" + command + "\n")
            if c.report.enabled:
                log.info("Report generation")
                build_report(result, c, run / "report.html", command)
            result.metadata["elapsed_seconds"] = time.perf_counter() - start
            write_json(run / "metadata.pending.json", result.metadata)
            # Hash every archive file except logs (still open) and the manifest itself.
            manifest = {
                (
                    "metadata.json"
                    if p.name == "metadata.pending.json"
                    else str(p.relative_to(run))
                ): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(run.rglob("*"))
                if p.is_file() and p.name != "logs.txt"
            }
            write_json(run / "manifest.json", manifest)
            (run / "metadata.pending.json").rename(run / "metadata.json")
            log.info(
                "Run end success elapsed_seconds=%.3f",
                result.metadata["elapsed_seconds"],
            )
        except Exception as exc:
            log.exception("Run failed")
            write_json(
                run / "failure.json",
                {"status": "failed", "error": str(exc), "run_id": run.name},
            )
            raise
    if c.report.open_after_run and c.report.enabled:
        webbrowser.open((run / "report.html").as_uri())
    return run, result

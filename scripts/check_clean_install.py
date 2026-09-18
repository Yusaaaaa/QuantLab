"""Install the built wheel in an isolated environment, entirely from local wheels."""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheelhouse", type=Path, default=root / ".wheelhouse")
    args = parser.parse_args()
    wheel = sorted((root / "dist").glob("us_equity_quant_lab-*.whl"))[-1]
    with tempfile.TemporaryDirectory(prefix="quantlab-clean-") as temp:
        folder = Path(temp)
        envdir = folder / "env"

        def run(command, **kwargs):
            print("+", " ".join(map(str, command)), flush=True)
            subprocess.run(list(map(str, command)), check=True, cwd=folder, **kwargs)

        run([sys.executable, "-m", "venv", envdir])
        python = envdir / "bin/python"
        cli = envdir / "bin/quantlab"
        environment = dict(os.environ)
        environment.pop("PYTHONPATH", None)
        environment["PIP_NO_INDEX"] = "1"
        run(
            [
                python,
                "-m",
                "pip",
                "install",
                "--no-index",
                "--find-links",
                args.wheelhouse.resolve(),
                "-r",
                root / "requirements.lock",
                wheel,
            ],
            env=environment,
        )
        run([python, "-m", "pip", "check"], env=environment)
        run(
            [
                python,
                "-c",
                'import quantlab; print(quantlab.__file__); assert "site-packages" in quantlab.__file__',
            ],
            env=environment,
        )
        run([cli, "--help"], env=environment)
        run(
            [
                python,
                "-m",
                "pytest",
                root / "tests",
                "-c",
                root / "pyproject.toml",
                "-q",
            ],
            env=environment,
        )
        run(
            [
                python,
                root / "scripts/make_sample_data.py",
                "--output-dir",
                folder / "data",
            ],
            env=environment,
        )
        config = folder / "clean.yaml"
        # Absolute strategy path points at the user's single official strategy, not engine code.
        config.write_text(f"""backtest:
  start_date: "2020-01-01"
  end_date: "2024-12-31"
data:
  path: {folder / "data/sample.csv"}
  source: "synthetic offline sample; not real market prices"
strategy:
  path: {root / "strategies/fixed_weight_buy_and_hold.py"}
report:
  runs_dir: {folder / "runs"}
""")
        run(
            [
                cli,
                "strategies",
                "validate",
                root / "strategies/fixed_weight_buy_and_hold.py",
                "--config",
                config,
            ],
            env=environment,
        )
        run([cli, "backtest", "run", "--config", config], env=environment)
        reports = list((folder / "runs").glob("*/report.html"))
        assert len(reports) == 1
        assert reports[0].read_text().count("data:image/png;base64,") == 10
        assert (reports[0].parent / "code.snapshot/pyproject.toml").exists()
        print("CLEAN INSTALL + OFFLINE FIVE-YEAR EXAMPLE PASSED", flush=True)


if __name__ == "__main__":
    main()

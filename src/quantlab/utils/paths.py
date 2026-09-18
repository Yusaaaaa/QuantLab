from pathlib import Path
import re
from datetime import datetime, timezone


def allocate_run(root, strategy, digest):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", strategy)[:60] or "strategy"
    base = f"{datetime.now(timezone.utc):%Y%m%d_%H%M%S}_{name}_{digest[:6]}"
    index = 0
    while True:
        path = root / (base if index == 0 else f"{base}_{index}")
        try:
            path.mkdir()
            return path
        except FileExistsError:
            index += 1

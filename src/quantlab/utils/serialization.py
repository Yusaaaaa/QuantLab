import hashlib
import json
import math
import numpy as np
import pandas as pd


def json_safe(value):
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.generic):
        return json_safe(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return value


def write_json(path, value):
    path.write_text(
        json.dumps(
            json_safe(value), indent=2, ensure_ascii=False, allow_nan=False, default=str
        )
        + "\n"
    )


def data_fingerprint(frame):
    normalized = frame.sort_values(["date", "symbol"]).reset_index(drop=True)
    normalized = normalized.reindex(sorted(normalized.columns), axis=1)
    return hashlib.sha256(
        normalized.to_csv(
            index=False, float_format="%.17g", date_format="%Y-%m-%d"
        ).encode()
    ).hexdigest()

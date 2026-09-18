from pathlib import Path
import argparse
from quantlab.data.sample import write_sample_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate artificial offline data, not real stock history"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data/raw",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(write_sample_data(args.output_dir, args.seed))

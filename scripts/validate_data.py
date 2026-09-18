import argparse
from quantlab.config import load_config
from quantlab.data.csv_local import CSVLocalDataProvider
from quantlab.data.parquet_local import ParquetLocalDataProvider
from quantlab.data.validator import validate_prices

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    args = parser.parse_args()
    c = load_config(args.config)
    provider = {
        "csv_local": CSVLocalDataProvider,
        "parquet_local": ParquetLocalDataProvider,
    }[c.data.provider](c.data.path)
    symbols = list(dict.fromkeys(c.universe.symbols + [c.data.benchmark]))
    frame, warnings = validate_prices(
        provider.load_prices(symbols, c.backtest.start_date, c.backtest.end_date),
        symbols,
        c.backtest.start_date,
        c.backtest.end_date,
        c.data.price_mode,
        c.data.extreme_return_threshold,
    )
    print(f"Validated {len(frame)} rows")
    for warning in warnings:
        print(warning)

from .csv_local import CSVLocalDataProvider
from .parquet_local import ParquetLocalDataProvider
from .yahoo import YahooDataProvider


def get_provider(config):
    if config.provider == "csv_local":
        return CSVLocalDataProvider(config.path)
    if config.provider == "parquet_local":
        return ParquetLocalDataProvider(config.path)
    if config.provider == "yahoo":
        return YahooDataProvider()
    raise ValueError(f"Unknown provider: {config.provider}")

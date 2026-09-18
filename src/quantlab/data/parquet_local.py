from pathlib import Path
import pandas as pd
from .base import select_prices


class ParquetLocalDataProvider:
    def __init__(self, path):
        self.path = Path(path)

    def load_prices(self, symbols, start_date, end_date):
        return select_prices(pd.read_parquet(self.path), symbols, start_date, end_date)

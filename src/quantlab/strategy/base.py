from abc import ABC, abstractmethod
from copy import deepcopy


class BaseStrategy(ABC):
    def __init__(self, params):
        self.params = deepcopy(params)

    def warmup_bars(self) -> int:
        return 0

    def decision_metadata(self) -> dict:
        """Optional auditable explanation of the latest decision, without side effects."""
        return {}

    @abstractmethod
    def generate_target_weights(self, dt, data, ctx) -> dict[str, float] | None: ...

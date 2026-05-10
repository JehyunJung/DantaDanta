"""매매 전략 추상 기반 클래스."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

import pandas as pd


class Signal(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class TradeSignal:
    signal: Signal
    symbol: str
    reason: str
    confidence: float = 1.0  # 0.0 ~ 1.0


class BaseStrategy(ABC):
    """모든 전략이 구현해야 하는 인터페이스."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def evaluate(self, symbol: str, df: pd.DataFrame) -> TradeSignal:
        """OHLCV + 지표가 포함된 DataFrame을 받아 매매 신호 반환."""
        ...

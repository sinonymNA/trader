from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from app.core.enums import Side, SignalStrength, TradeStatus


@dataclass
class Price:
    instrument: str
    bid: float
    ask: float
    time: str

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0

    @property
    def spread(self) -> float:
        return self.ask - self.bid


@dataclass
class Candle:
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    complete: bool = True


@dataclass
class FeatureSet:
    instrument: str
    timestamp: datetime
    mid_price: float
    spread: float
    candles: list[Candle] = field(default_factory=list)
    extra: dict = field(default_factory=dict)


@dataclass
class Signal:
    instrument: str
    side: Side
    strength: SignalStrength
    units: int
    reason: str
    generated_at: datetime


@dataclass
class OrderIntent:
    instrument: str
    side: Side
    units: int
    comment: str = ""


@dataclass
class OrderResult:
    success: bool
    order_id: str
    instrument: str
    side: Side
    units: int
    fill_price: float
    dry_run: bool = False
    error: str = ""


@dataclass
class TradeRecord:
    id: str
    broker_trade_id: str
    instrument: str
    side: str
    units: int
    open_price: float
    status: str
    opened_at: datetime
    close_price: float | None = None
    closed_at: datetime | None = None


@dataclass
class AccountSummary:
    account_id: str
    balance: Decimal
    nav: Decimal
    unrealized_pl: Decimal
    open_trade_count: int
    currency: str = "USD"


@runtime_checkable
class ApexSimulator(Protocol):
    """
    APEX_SIMULATOR_HOOK

    Implement this protocol to inject a custom Apex-challenge simulator.
    The simulator receives an OrderIntent and returns an OrderResult
    without calling the real broker.

    Example:
        class MyApexSim:
            async def simulate_order(self, intent: OrderIntent) -> OrderResult:
                # Enforce Apex challenge rules: daily loss limit,
                # max trailing drawdown, profit target, min trading days.
                return OrderResult(success=True, order_id="APEX-123", ...)

    Inject via app/main.py:
        policy = ExecutionPolicy(client=..., simulator=MyApexSim())
    """

    async def simulate_order(self, intent: OrderIntent) -> OrderResult:
        ...

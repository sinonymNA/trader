from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"


class WorkerStatus(str, Enum):
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


class SignalStrength(str, Enum):
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"


class TradeStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class JournalEventType(str, Enum):
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_FILLED = "ORDER_FILLED"
    TRADE_CLOSED = "TRADE_CLOSED"
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    RISK_REJECTED = "RISK_REJECTED"
    KILL_SWITCH_TRIGGERED = "KILL_SWITCH_TRIGGERED"
    WORKER_PAUSED = "WORKER_PAUSED"
    WORKER_RESUMED = "WORKER_RESUMED"

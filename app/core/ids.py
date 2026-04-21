import uuid


def new_trade_id() -> str:
    return f"TRD-{uuid.uuid4().hex}"


def new_journal_id() -> str:
    return uuid.uuid4().hex

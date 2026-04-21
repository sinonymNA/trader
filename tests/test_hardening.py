"""
Tests for production hardening: retry/backoff and stale data protection.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.broker.oanda_client import OandaClient
from app.schemas.domain import Candle, FeatureSet
from app.strategy.features import _is_stale
from app.strategy.signal_engine import SignalEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def live_client() -> OandaClient:
    return OandaClient(
        api_key="test-api-key",
        account_id="101-001-9999999",
        base_url="https://api-fxpractice.oanda.com",
        dry_run=False,
    )


def _make_resp(payload: dict, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = payload
    if status >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status}",
            request=MagicMock(spec=httpx.Request),
            response=resp,
        )
    else:
        resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# Retry / backoff tests
# ---------------------------------------------------------------------------


async def test_retries_on_503_then_succeeds(live_client: OandaClient) -> None:
    payload = {"account": {"id": "101-001-9999999", "balance": "10000.0000"}}
    resp_503 = _make_resp({}, status=503)
    resp_200 = _make_resp(payload, status=200)

    http = AsyncMock()
    http.get = AsyncMock(side_effect=[resp_503, resp_503, resp_200])
    http.is_closed = False
    live_client._http = http

    with patch("asyncio.sleep"):  # no real waiting
        result = await live_client.get_account_summary()

    assert result["account"]["id"] == "101-001-9999999"
    assert http.get.call_count == 3


async def test_does_not_retry_on_401(live_client: OandaClient) -> None:
    resp_401 = _make_resp({}, status=401)

    http = AsyncMock()
    http.get = AsyncMock(return_value=resp_401)
    http.is_closed = False
    live_client._http = http

    with pytest.raises(httpx.HTTPStatusError):
        await live_client.get_account_summary()

    assert http.get.call_count == 1  # no retry


async def test_raises_after_three_failures(live_client: OandaClient) -> None:
    resp_503 = _make_resp({}, status=503)

    http = AsyncMock()
    http.get = AsyncMock(return_value=resp_503)
    http.is_closed = False
    live_client._http = http

    with patch("asyncio.sleep"):
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await live_client.get_account_summary()

    assert exc_info.value.response.status_code == 503
    assert http.get.call_count == 3


# ---------------------------------------------------------------------------
# Stale data tests
# ---------------------------------------------------------------------------


def _candle_with_time(time_str: str) -> Candle:
    return Candle(time=time_str, open=1.0, high=1.0, low=1.0, close=1.0, volume=1)


def test_stale_detection_old_candle() -> None:
    old_time = datetime.now(timezone.utc) - timedelta(minutes=20)
    time_str = old_time.strftime("%Y-%m-%dT%H:%M:%S.000000000Z")
    candles = [_candle_with_time(time_str)]
    assert _is_stale(candles, max_age_seconds=600) is True


def test_stale_detection_fresh_candle() -> None:
    fresh_time = datetime.now(timezone.utc) - timedelta(minutes=2)
    time_str = fresh_time.strftime("%Y-%m-%dT%H:%M:%S.000000000Z")
    candles = [_candle_with_time(time_str)]
    assert _is_stale(candles, max_age_seconds=600) is False


def test_stale_detection_empty_candles_not_stale() -> None:
    # Empty candles = insufficient data, not stale (handled by MA None check)
    assert _is_stale([], max_age_seconds=600) is False


def test_signal_returns_none_on_stale_features() -> None:
    engine = SignalEngine(trade_units=100)
    features = FeatureSet(
        instrument="EUR_USD",
        timestamp=datetime.now(timezone.utc),
        mid_price=1.10100,
        spread=0.00020,
        short_ma=1.10050,
        long_ma=1.09900,
        breakout_high=1.10000,
        breakout_low=1.09800,
        stale=True,
    )
    assert engine.evaluate(features) is None

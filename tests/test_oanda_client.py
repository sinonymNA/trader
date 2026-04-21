"""
Unit tests for OandaClient.

Dry-run tests need no mocking — they exercise the built-in stubs.
Live-path tests patch OandaClient._http with a mock httpx.AsyncClient so no
real network calls are made.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.broker.oanda_client import OandaClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def dry_client() -> OandaClient:
    """Client with DRY_RUN=true and no credentials — pure stub mode."""
    return OandaClient(
        api_key="",
        account_id="",
        base_url="https://api-fxpractice.oanda.com",
        dry_run=True,
    )


@pytest.fixture
def live_client() -> OandaClient:
    """Client with DRY_RUN=false and dummy credentials — http will be mocked."""
    return OandaClient(
        api_key="test-api-key",
        account_id="101-001-9999999",
        base_url="https://api-fxpractice.oanda.com",
        dry_run=False,
    )


def _mock_http(payload: dict, status: int = 200) -> AsyncMock:
    """Return a mock httpx.AsyncClient whose methods return the given payload."""
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

    http = AsyncMock()
    http.get = AsyncMock(return_value=resp)
    http.post = AsyncMock(return_value=resp)
    http.put = AsyncMock(return_value=resp)
    http.is_closed = False
    return http


# ---------------------------------------------------------------------------
# Dry-run tests (no HTTP, no credentials)
# ---------------------------------------------------------------------------


async def test_dry_account_summary_returns_stub(dry_client: OandaClient) -> None:
    result = await dry_client.get_account_summary()
    assert result["account"]["id"] == "DRY-RUN-ACCOUNT"
    assert float(result["account"]["balance"]) == 10_000.0


async def test_dry_latest_prices_returns_one_entry_per_instrument(
    dry_client: OandaClient,
) -> None:
    instruments = ["EUR_USD", "GBP_USD", "USD_JPY"]
    result = await dry_client.get_latest_prices(instruments)
    assert len(result) == 3
    assert {r["instrument"] for r in result} == set(instruments)
    assert "asks" in result[0]
    assert "bids" in result[0]


async def test_dry_get_candles_returns_empty(dry_client: OandaClient) -> None:
    result = await dry_client.get_candles("EUR_USD")
    assert result == []


async def test_dry_list_open_trades_returns_empty(dry_client: OandaClient) -> None:
    result = await dry_client.list_open_trades()
    assert result == []


async def test_dry_place_market_order_returns_fill(dry_client: OandaClient) -> None:
    result = await dry_client.place_market_order("EUR_USD", 100)
    fill = result["orderFillTransaction"]
    assert fill["instrument"] == "EUR_USD"
    assert fill["type"] == "ORDER_FILL"
    assert "DRY" in fill["id"]


async def test_dry_place_market_order_with_sl_tp(dry_client: OandaClient) -> None:
    # SL/TP in dry-run only affects the log — response shape must still be valid
    result = await dry_client.place_market_order(
        "EUR_USD", 100, stop_loss=1.0800, take_profit=1.1200
    )
    fill = result["orderFillTransaction"]
    assert fill["instrument"] == "EUR_USD"


async def test_dry_close_trade_returns_fill(dry_client: OandaClient) -> None:
    result = await dry_client.close_trade("TRADE-42")
    fill = result["orderFillTransaction"]
    assert "DRY-CLOSE-TRADE-42" == fill["id"]


# ---------------------------------------------------------------------------
# Missing-credentials guard
# ---------------------------------------------------------------------------


async def test_live_mode_without_credentials_raises() -> None:
    no_creds = OandaClient("", "", "https://api-fxpractice.oanda.com", dry_run=False)
    with pytest.raises(RuntimeError, match="credentials"):
        await no_creds.get_account_summary()


# ---------------------------------------------------------------------------
# Live-path tests (mocked httpx.AsyncClient)
# ---------------------------------------------------------------------------


async def test_live_get_account_summary(live_client: OandaClient) -> None:
    payload = {
        "account": {
            "id": "101-001-9999999",
            "balance": "10000.0000",
            "NAV": "9998.5000",
            "unrealizedPL": "-1.5000",
            "openTradeCount": 2,
            "currency": "USD",
        }
    }
    live_client._http = _mock_http(payload)
    result = await live_client.get_account_summary()
    assert result["account"]["id"] == "101-001-9999999"
    assert result["account"]["openTradeCount"] == 2
    live_client._http.get.assert_called_once()


async def test_live_get_latest_prices(live_client: OandaClient) -> None:
    payload = {
        "prices": [
            {
                "instrument": "EUR_USD",
                "asks": [{"price": "1.08512", "liquidity": 1_000_000}],
                "bids": [{"price": "1.08498", "liquidity": 1_000_000}],
                "time": "2024-06-01T12:00:00.000Z",
                "tradeable": True,
            }
        ]
    }
    live_client._http = _mock_http(payload)
    result = await live_client.get_latest_prices(["EUR_USD"])
    assert result[0]["instrument"] == "EUR_USD"
    assert result[0]["asks"][0]["price"] == "1.08512"


async def test_live_get_candles(live_client: OandaClient) -> None:
    payload = {
        "candles": [
            {
                "time": "2024-06-01T12:00:00Z",
                "mid": {"o": "1.08500", "h": "1.08600", "l": "1.08400", "c": "1.08550"},
                "volume": 1234,
                "complete": True,
            }
        ]
    }
    live_client._http = _mock_http(payload)
    result = await live_client.get_candles("EUR_USD", granularity="M5", count=1)
    assert len(result) == 1
    assert result[0]["volume"] == 1234


async def test_live_list_open_trades(live_client: OandaClient) -> None:
    payload = {
        "trades": [
            {"id": "501", "instrument": "EUR_USD", "currentUnits": "100"}
        ]
    }
    live_client._http = _mock_http(payload)
    result = await live_client.list_open_trades()
    assert len(result) == 1
    assert result[0]["id"] == "501"


async def test_live_place_market_order_sends_correct_body(
    live_client: OandaClient,
) -> None:
    payload = {
        "orderFillTransaction": {
            "id": "12345",
            "instrument": "GBP_USD",
            "units": "500",
            "price": "1.27050",
            "type": "ORDER_FILL",
        }
    }
    live_client._http = _mock_http(payload)
    await live_client.place_market_order("GBP_USD", 500)

    _, call_kwargs = live_client._http.post.call_args
    order = call_kwargs["json"]["order"]
    assert order["instrument"] == "GBP_USD"
    assert order["units"] == "500"
    assert order["type"] == "MARKET"
    assert "stopLossOnFill" not in order
    assert "takeProfitOnFill" not in order


async def test_live_place_market_order_includes_sl_tp(
    live_client: OandaClient,
) -> None:
    payload = {
        "orderFillTransaction": {
            "id": "12346",
            "instrument": "EUR_USD",
            "units": "1000",
            "price": "1.09500",
            "type": "ORDER_FILL",
        }
    }
    live_client._http = _mock_http(payload)
    await live_client.place_market_order(
        "EUR_USD", 1000, stop_loss=1.0750, take_profit=1.1150
    )

    _, call_kwargs = live_client._http.post.call_args
    order = call_kwargs["json"]["order"]
    assert order["stopLossOnFill"]["price"] == "1.07500"
    assert order["stopLossOnFill"]["timeInForce"] == "GTC"
    assert order["takeProfitOnFill"]["price"] == "1.11500"
    assert order["takeProfitOnFill"]["timeInForce"] == "GTC"


async def test_live_place_market_order_jpy_formats_price(
    live_client: OandaClient,
) -> None:
    payload = {
        "orderFillTransaction": {
            "id": "12347",
            "instrument": "USD_JPY",
            "units": "-100",
            "price": "149.500",
            "type": "ORDER_FILL",
        }
    }
    live_client._http = _mock_http(payload)
    await live_client.place_market_order(
        "USD_JPY", -100, stop_loss=150.200, take_profit=148.100
    )

    _, call_kwargs = live_client._http.post.call_args
    order = call_kwargs["json"]["order"]
    # JPY pairs use 3 decimal places
    assert order["stopLossOnFill"]["price"] == "150.200"
    assert order["takeProfitOnFill"]["price"] == "148.100"


async def test_live_close_trade(live_client: OandaClient) -> None:
    payload = {
        "orderFillTransaction": {
            "id": "99001",
            "price": "1.08000",
            "type": "ORDER_FILL",
        }
    }
    live_client._http = _mock_http(payload)
    result = await live_client.close_trade("501")
    assert result["orderFillTransaction"]["id"] == "99001"
    live_client._http.put.assert_called_once()


# ---------------------------------------------------------------------------
# verify() tests
# ---------------------------------------------------------------------------


async def test_verify_passes_with_valid_credentials(live_client: OandaClient) -> None:
    payload = {"account": {"id": "101-001-9999999", "balance": "10000.0000"}}
    live_client._http = _mock_http(payload)
    await live_client.verify()  # must not raise


async def test_verify_raises_on_401(live_client: OandaClient) -> None:
    live_client._http = _mock_http({}, status=401)
    with pytest.raises(RuntimeError, match="authentication failed"):
        await live_client.verify()


async def test_verify_raises_on_403(live_client: OandaClient) -> None:
    live_client._http = _mock_http({}, status=403)
    with pytest.raises(RuntimeError, match="authentication failed"):
        await live_client.verify()


async def test_verify_raises_on_connect_error(live_client: OandaClient) -> None:
    http = AsyncMock()
    http.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
    http.is_closed = False
    live_client._http = http
    with pytest.raises(RuntimeError, match="Cannot reach"):
        await live_client.verify()

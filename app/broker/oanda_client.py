from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_DRY_PRICE = "1.10000"
_DRY_PRICE_BID = "1.09990"


class OandaClient:
    """
    Async OANDA v20 REST API client.

    When dry_run=True and credentials are absent, all methods return
    plausible stub data so the app can boot and loop without touching OANDA.
    """

    def __init__(
        self,
        api_key: str,
        account_id: str,
        base_url: str,
        dry_run: bool = True,
    ) -> None:
        self._api_key = api_key
        self._account_id = account_id
        self._base_url = base_url.rstrip("/")
        self._dry_run = dry_run
        self._http: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _has_credentials(self) -> bool:
        return bool(self._api_key and self._account_id)

    def _require_credentials(self) -> None:
        if not self._has_credentials():
            raise RuntimeError(
                "OANDA credentials are required for live API calls. "
                "Set OANDA_API_KEY and OANDA_ACCOUNT_ID, or enable DRY_RUN=true."
            )

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
        return self._http

    async def close(self) -> None:
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    async def get_account_summary(self) -> dict[str, Any]:
        if self._dry_run and not self._has_credentials():
            logger.debug("[DRY-RUN] get_account_summary → stub")
            return {
                "account": {
                    "id": "DRY-RUN-ACCOUNT",
                    "balance": "10000.0000",
                    "NAV": "10000.0000",
                    "unrealizedPL": "0.0000",
                    "openTradeCount": 0,
                    "currency": "USD",
                }
            }
        self._require_credentials()
        c = await self._client()
        resp = await c.get(f"/v3/accounts/{self._account_id}/summary")
        resp.raise_for_status()
        return resp.json()

    async def get_latest_prices(self, instruments: list[str]) -> list[dict[str, Any]]:
        if self._dry_run and not self._has_credentials():
            logger.debug("[DRY-RUN] get_latest_prices → stub for %s", instruments)
            return [
                {
                    "instrument": instr,
                    "asks": [{"price": _DRY_PRICE, "liquidity": 10_000_000}],
                    "bids": [{"price": _DRY_PRICE_BID, "liquidity": 10_000_000}],
                    "time": "2024-01-01T00:00:00.000000000Z",
                    "tradeable": True,
                }
                for instr in instruments
            ]
        self._require_credentials()
        c = await self._client()
        params = {"instruments": ",".join(instruments)}
        resp = await c.get(f"/v3/accounts/{self._account_id}/pricing", params=params)
        resp.raise_for_status()
        return resp.json().get("prices", [])

    async def get_candles(
        self,
        instrument: str,
        granularity: str = "M5",
        count: int = 50,
    ) -> list[dict[str, Any]]:
        if self._dry_run and not self._has_credentials():
            logger.debug("[DRY-RUN] get_candles → empty list")
            return []
        self._require_credentials()
        c = await self._client()
        params = {"granularity": granularity, "count": str(count)}
        resp = await c.get(f"/v3/instruments/{instrument}/candles", params=params)
        resp.raise_for_status()
        return resp.json().get("candles", [])

    async def list_open_trades(self) -> list[dict[str, Any]]:
        if self._dry_run and not self._has_credentials():
            logger.debug("[DRY-RUN] list_open_trades → empty list")
            return []
        self._require_credentials()
        c = await self._client()
        resp = await c.get(f"/v3/accounts/{self._account_id}/openTrades")
        resp.raise_for_status()
        return resp.json().get("trades", [])

    async def place_market_order(self, instrument: str, units: int) -> dict[str, Any]:
        """Place a market order. units > 0 = BUY, units < 0 = SELL."""
        if self._dry_run:
            logger.info("[DRY-RUN] place_market_order %s units=%d", instrument, units)
            return {
                "orderFillTransaction": {
                    "id": f"DRY-{instrument}-{abs(units)}",
                    "instrument": instrument,
                    "units": str(units),
                    "price": _DRY_PRICE,
                    "type": "ORDER_FILL",
                }
            }
        self._require_credentials()
        c = await self._client()
        body = {
            "order": {
                "type": "MARKET",
                "instrument": instrument,
                "units": str(units),
                "timeInForce": "FOK",
                "positionFill": "DEFAULT",
            }
        }
        resp = await c.post(f"/v3/accounts/{self._account_id}/orders", json=body)
        resp.raise_for_status()
        return resp.json()

    async def close_trade(self, trade_id: str) -> dict[str, Any]:
        if self._dry_run:
            logger.info("[DRY-RUN] close_trade %s", trade_id)
            return {
                "orderFillTransaction": {
                    "id": f"DRY-CLOSE-{trade_id}",
                    "price": _DRY_PRICE_BID,
                    "type": "ORDER_FILL",
                }
            }
        self._require_credentials()
        c = await self._client()
        resp = await c.put(
            f"/v3/accounts/{self._account_id}/trades/{trade_id}/close"
        )
        resp.raise_for_status()
        return resp.json()

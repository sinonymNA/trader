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
    When dry_run=True with credentials, reads use real API; writes are still stubbed.
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

    @staticmethod
    def _fmt_price(instrument: str, price: float) -> str:
        """Format a price with the correct decimal places for the instrument."""
        return f"{price:.3f}" if "JPY" in instrument else f"{price:.5f}"

    async def close(self) -> None:
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    # ------------------------------------------------------------------
    # Credential verification
    # ------------------------------------------------------------------

    async def verify(self) -> None:
        """
        Call the OANDA account summary endpoint to confirm credentials are valid.
        Raises RuntimeError with a human-readable message on failure.
        Should be called at startup when DRY_RUN=false.
        """
        try:
            await self.get_account_summary()
            logger.info("OANDA credential check passed (account_id=%s)", self._account_id)
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            if code in (401, 403):
                raise RuntimeError(
                    f"OANDA authentication failed (HTTP {code}). "
                    "Check that OANDA_API_KEY and OANDA_ACCOUNT_ID are correct "
                    "and that the key has not expired."
                ) from exc
            raise RuntimeError(
                f"OANDA API returned HTTP {code} during credential check"
            ) from exc
        except httpx.ConnectError as exc:
            raise RuntimeError(
                f"Cannot reach OANDA API at {self._base_url}: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise RuntimeError(
                f"OANDA API timed out during credential check: {exc}"
            ) from exc

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

    async def place_market_order(
        self,
        instrument: str,
        units: int,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> dict[str, Any]:
        """
        Place a MARKET order. units > 0 = BUY, units < 0 = SELL.

        Args:
            instrument:  OANDA instrument name, e.g. "EUR_USD"
            units:       Positive for BUY, negative for SELL
            stop_loss:   Absolute price level for stop-loss order (GTC)
            take_profit: Absolute price level for take-profit order (GTC)
        """
        if self._dry_run:
            sl_str = f" SL={self._fmt_price(instrument, stop_loss)}" if stop_loss else ""
            tp_str = f" TP={self._fmt_price(instrument, take_profit)}" if take_profit else ""
            logger.info(
                "[DRY-RUN] place_market_order %s units=%d%s%s",
                instrument, units, sl_str, tp_str,
            )
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
        body: dict[str, Any] = {
            "order": {
                "type": "MARKET",
                "instrument": instrument,
                "units": str(units),
                "timeInForce": "FOK",
                "positionFill": "DEFAULT",
            }
        }
        if stop_loss is not None:
            body["order"]["stopLossOnFill"] = {
                "price": self._fmt_price(instrument, stop_loss),
                "timeInForce": "GTC",
            }
        if take_profit is not None:
            body["order"]["takeProfitOnFill"] = {
                "price": self._fmt_price(instrument, take_profit),
                "timeInForce": "GTC",
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

"""MCP server exposing Oanda trading operations as tools."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from oandapyV20 import API
from oandapyV20.endpoints import accounts, instruments, orders, positions, pricing
from oandapyV20.exceptions import V20Error


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


OANDA_API_KEY = os.getenv("OANDA_API_KEY")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
OANDA_ENVIRONMENT = os.getenv("OANDA_ENVIRONMENT", "practice")

if not OANDA_API_KEY or not OANDA_ACCOUNT_ID:
    logger.error("Missing Oanda API credentials")
    raise ValueError("Oanda API credentials not found in environment variables.")

try:
    oanda_client = API(access_token=OANDA_API_KEY, environment=OANDA_ENVIRONMENT)
    logger.info("Oanda client initialized for %s environment", OANDA_ENVIRONMENT)
except Exception as exc:  # pragma: no cover - defensive logging
    logger.error("Failed to initialize Oanda client: %s", exc)
    raise


INSTRUCTIONS = (
    "This MCP server exposes Oanda account management tools. "
    "Use these tools to review account state, inspect positions and orders, "
    "and place or manage trades."
)


async def _request(endpoint: Any) -> Dict[str, Any]:
    """Execute an Oanda endpoint in a background thread and return the response."""

    def _do_request() -> Dict[str, Any]:
        oanda_client.request(endpoint)
        return endpoint.response  # type: ignore[no-any-return]

    return await asyncio.to_thread(_do_request)


def create_server() -> FastMCP:
    """Configure and return the MCP server."""

    mcp = FastMCP(name="Oanda MCP Server", instructions=INSTRUCTIONS)

    @mcp.tool()
    async def health_check() -> Dict[str, Any]:
        """Check connectivity with the configured Oanda account."""

        try:
            endpoint = accounts.AccountDetails(accountID=OANDA_ACCOUNT_ID)
            response = await _request(endpoint)
            account = response.get("account", {})
            return {
                "status": "healthy",
                "account_id": account.get("id"),
                "environment": OANDA_ENVIRONMENT,
                "server_time": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            logger.error("Health check failed: %s", exc)
            raise ValueError(f"Health check failed: {exc}") from exc

    @mcp.tool()
    async def get_account_summary() -> Dict[str, Any]:
        """Retrieve account balance, NAV, and margin information."""

        try:
            endpoint = accounts.AccountDetails(accountID=OANDA_ACCOUNT_ID)
            response = await _request(endpoint)
            account = response.get("account", {})
            return {
                "id": account.get("id"),
                "currency": account.get("currency"),
                "balance": account.get("balance"),
                "nav": account.get("NAV"),
                "unrealized_pl": account.get("unrealizedPL"),
                "margin_used": account.get("marginUsed"),
                "margin_available": account.get("marginAvailable"),
                "margin_rate": account.get("marginRate"),
                "open_trade_count": account.get("openTradeCount"),
                "open_position_count": account.get("openPositionCount"),
                "pending_order_count": account.get("pendingOrderCount"),
            }
        except V20Error as exc:
            logger.error("Oanda API error in get_account_summary: %s", exc)
            raise ValueError(f"Oanda API error: {exc}") from exc
        except Exception as exc:  # pragma: no cover - unexpected failures
            logger.error("Unexpected error in get_account_summary: %s", exc)
            raise ValueError(f"Internal error: {exc}") from exc

    @mcp.tool()
    async def list_positions() -> Dict[str, Any]:
        """Return all open positions."""

        try:
            endpoint = positions.OpenPositions(accountID=OANDA_ACCOUNT_ID)
            response = await _request(endpoint)
            positions_data: List[Dict[str, Any]] = response.get("positions", [])
            return {"positions": positions_data, "count": len(positions_data)}
        except V20Error as exc:
            logger.error("Oanda API error in list_positions: %s", exc)
            raise ValueError(f"Oanda API error: {exc}") from exc
        except Exception as exc:  # pragma: no cover
            logger.error("Unexpected error in list_positions: %s", exc)
            raise ValueError(f"Internal error: {exc}") from exc

    @mcp.tool()
    async def list_orders() -> Dict[str, Any]:
        """Return all pending orders."""

        try:
            endpoint = orders.OrderList(accountID=OANDA_ACCOUNT_ID)
            response = await _request(endpoint)
            orders_data: List[Dict[str, Any]] = response.get("orders", [])
            return {"orders": orders_data, "count": len(orders_data)}
        except V20Error as exc:
            logger.error("Oanda API error in list_orders: %s", exc)
            raise ValueError(f"Oanda API error: {exc}") from exc
        except Exception as exc:  # pragma: no cover
            logger.error("Unexpected error in list_orders: %s", exc)
            raise ValueError(f"Internal error: {exc}") from exc

    @mcp.tool()
    async def get_price(instrument: str) -> Dict[str, Any]:
        """Fetch the latest bid and ask prices for an instrument."""

        try:
            endpoint = pricing.PricingInfo(
                accountID=OANDA_ACCOUNT_ID, params={"instruments": instrument}
            )
            response = await _request(endpoint)
            prices: List[Dict[str, Any]] = response.get("prices", [])
            if not prices:
                raise ValueError(f"No price data found for {instrument}")

            price_data = prices[0]
            bid = float(price_data.get("bids", [{}])[0].get("price", 0))
            ask = float(price_data.get("asks", [{}])[0].get("price", 0))
            return {
                "instrument": instrument,
                "bid": bid,
                "ask": ask,
                "spread": ask - bid,
                "time": price_data.get("time"),
            }
        except V20Error as exc:
            logger.error("Oanda API error in get_price: %s", exc)
            raise ValueError(f"Oanda API error: {exc}") from exc
        except Exception as exc:  # pragma: no cover
            logger.error("Unexpected error in get_price: %s", exc)
            raise

    @mcp.tool()
    async def get_historical_data(
        instrument: str, granularity: str = "D", count: int = 100
    ) -> Dict[str, Any]:
        """Retrieve historical candle data for an instrument."""

        try:
            params = {"granularity": granularity, "count": min(count, 5000)}
            endpoint = instruments.InstrumentsCandles(
                instrument=instrument, params=params
            )
            response = await _request(endpoint)
            candles: List[Dict[str, Any]] = response.get("candles", [])
            return {
                "instrument": instrument,
                "granularity": granularity,
                "candles": candles,
                "count": len(candles),
            }
        except V20Error as exc:
            logger.error("Oanda API error in get_historical_data: %s", exc)
            raise ValueError(f"Oanda API error: {exc}") from exc
        except Exception as exc:  # pragma: no cover
            logger.error("Unexpected error in get_historical_data: %s", exc)
            raise ValueError(f"Internal error: {exc}") from exc

    @mcp.tool()
    async def place_market_order(
        instrument: str,
        units: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Place a market order."""

        order_data: Dict[str, Any] = {
            "order": {
                "type": "MARKET",
                "instrument": instrument,
                "units": str(units),
            }
        }

        if stop_loss is not None:
            order_data["order"]["stopLossOnFill"] = {"price": str(stop_loss)}
        if take_profit is not None:
            order_data["order"]["takeProfitOnFill"] = {"price": str(take_profit)}

        try:
            endpoint = orders.OrderCreate(accountID=OANDA_ACCOUNT_ID, data=order_data)
            response = await _request(endpoint)
            return response
        except V20Error as exc:
            logger.error("Oanda API error in place_market_order: %s", exc)
            raise ValueError(f"Oanda API error: {exc}") from exc
        except Exception as exc:  # pragma: no cover
            logger.error("Unexpected error in place_market_order: %s", exc)
            raise ValueError(f"Internal error: {exc}") from exc

    @mcp.tool()
    async def place_limit_order(
        instrument: str,
        units: int,
        price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Place a limit order."""

        order_data: Dict[str, Any] = {
            "order": {
                "type": "LIMIT",
                "instrument": instrument,
                "units": str(units),
                "price": str(price),
            }
        }

        if stop_loss is not None:
            order_data["order"]["stopLossOnFill"] = {"price": str(stop_loss)}
        if take_profit is not None:
            order_data["order"]["takeProfitOnFill"] = {"price": str(take_profit)}

        try:
            endpoint = orders.OrderCreate(accountID=OANDA_ACCOUNT_ID, data=order_data)
            response = await _request(endpoint)
            return response
        except V20Error as exc:
            logger.error("Oanda API error in place_limit_order: %s", exc)
            raise ValueError(f"Oanda API error: {exc}") from exc
        except Exception as exc:  # pragma: no cover
            logger.error("Unexpected error in place_limit_order: %s", exc)
            raise ValueError(f"Internal error: {exc}") from exc

    @mcp.tool()
    async def cancel_order(order_id: str) -> Dict[str, Any]:
        """Cancel a pending order."""

        try:
            endpoint = orders.OrderCancel(accountID=OANDA_ACCOUNT_ID, orderID=order_id)
            response = await _request(endpoint)
            return response
        except V20Error as exc:
            logger.error("Oanda API error in cancel_order: %s", exc)
            raise ValueError(f"Oanda API error: {exc}") from exc
        except Exception as exc:  # pragma: no cover
            logger.error("Unexpected error in cancel_order: %s", exc)
            raise ValueError(f"Internal error: {exc}") from exc

    @mcp.tool()
    async def close_position(instrument: str, units: Optional[str] = None) -> Dict[str, Any]:
        """Close a position for an instrument."""

        if not units or units.upper() == "ALL":
            close_data: Dict[str, Any] = {"longUnits": "ALL", "shortUnits": "ALL"}
        else:
            try:
                parsed_units = int(units)
            except ValueError as exc:
                raise ValueError("units must be an integer or 'ALL'") from exc

            if parsed_units > 0:
                close_data = {"longUnits": str(parsed_units)}
            else:
                close_data = {"shortUnits": str(abs(parsed_units))}

        try:
            endpoint = positions.PositionClose(
                accountID=OANDA_ACCOUNT_ID, instrument=instrument, data=close_data
            )
            response = await _request(endpoint)
            return response
        except V20Error as exc:
            logger.error("Oanda API error in close_position: %s", exc)
            raise ValueError(f"Oanda API error: {exc}") from exc
        except Exception as exc:  # pragma: no cover
            logger.error("Unexpected error in close_position: %s", exc)
            raise ValueError(f"Internal error: {exc}") from exc

    return mcp


def main() -> None:
    """Entry point to run the MCP server using SSE transport."""

    server = create_server()
    port = int(os.getenv("PORT", 8000))
    logger.info("Starting MCP server on port %s", port)
    server.run(transport="sse", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()


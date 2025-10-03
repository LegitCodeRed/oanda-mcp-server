# Oanda MCP Server

A REST API server for Oanda trading operations, deployed on Railway and compatible with Model Context Protocol (MCP).

In addition to the REST interface, the project now includes a dedicated MCP server that exposes trading operations as tools that can be used by MCP-compatible clients such as ChatGPT.

## Features

- Account information retrieval
- Position management
- Order placement (market and limit orders)
- Current price data
- Historical data
- Order cancellation

## API Endpoints

- `GET /` - Health check
- `GET /account` - Get account information
- `GET /positions` - Get current positions
- `GET /orders` - Get pending orders
- `GET /price/{instrument}` - Get current price for instrument
- `GET /historical/{instrument}` - Get historical data
- `POST /order/market` - Place market order
- `POST /order/limit` - Place limit order
- `DELETE /order/{order_id}` - Cancel order
- `POST /position/close/{instrument}` - Close position

## MCP Server

- `python mcp_server.py` - Starts the MCP server with SSE transport on port `8000` (configurable via `PORT`).
- Tools available include health checks, account summaries, position and order listings, price lookups, market/limit order placement, order cancellation, and position closing.

## Environment Variables

- `OANDA_API_KEY` - Your Oanda API key
- `OANDA_ACCOUNT_ID` - Your Oanda account ID
- `OANDA_ENVIRONMENT` - 'practice' or 'live'
- `PORT` - Server port (set automatically by Railway)




npx @srbhptl39/mcp-superassistant-proxy@latest --config ./mcpconfig.json
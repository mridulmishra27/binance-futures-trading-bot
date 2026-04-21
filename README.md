# Trading Bot — Binance Futures Testnet (USDT-M)

A small Python CLI that places **Market**, **Limit**, and **Stop-Limit** (bonus) orders on the [Binance USDT-M Futures Testnet](https://testnet.binancefuture.com). Built with `python-binance`, `typer`, and `rich`.

## Features

- Market, Limit, and Stop-Limit order types (BUY / SELL).
- Clean separation between the API client layer (`trading_bot/bot/`) and the CLI layer (`trading_bot/cli.py`).
- Typer + Rich for colored output, subcommand help, and a request / response panel after each run.
- Structured logging of every request, response, and error to `logs/trading_bot.log` (rotated at 5 MB, 3 backups).
- Input validation before any network call; API keys masked in logs.

## Setup

1. **Create a testnet account.** Sign in at https://testnet.binancefuture.com, generate an API key + secret, and use the portfolio faucet to fund your USDT-M wallet (10,000 USDT).
2. **Python 3.10+** is required.
3. Install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate        # on Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. Copy the environment template and fill in your credentials:
   ```bash
   cp .env.example .env
   # then edit .env
   ```

## Usage

All commands are run from the project root.

### Verify credentials (no order placed)
```bash
python -m trading_bot.cli check-auth
```
Calls a signed endpoint (`/fapi/v2/balance`) to confirm the API key is valid and has Futures-testnet trading permission. Useful to run once after copying your keys into `.env`.

### Market order
```bash
python -m trading_bot.cli market --symbol BTCUSDT --side BUY --quantity 0.01
```

### Limit order
```bash
python -m trading_bot.cli limit --symbol BTCUSDT --side SELL --quantity 0.01 --price 60000
```

### Stop-Limit order (bonus)
```bash
python -m trading_bot.cli stop-limit --symbol BTCUSDT --side BUY --quantity 0.01 --price 60500 --stop-price 60000
```

### Help
```bash
python -m trading_bot.cli --help
python -m trading_bot.cli limit --help
```

### Global options

| Flag | Default | Purpose |
| --- | --- | --- |
| `--log-dir PATH` | `./logs` | Directory for `trading_bot.log`. |
| `--testnet / --no-testnet` | from `BINANCE_TESTNET` env, else `true` | Target testnet vs. live. |

### Example of a validation failure (no API call made)
```bash
python -m trading_bot.cli limit --symbol BTCUSDT --side BUY --quantity 0.01
# → red "Validation error: price is required for this order type", exit code 2
```

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | Unexpected error (full traceback in log) |
| `2` | Local input validation failed |
| `3` | API credentials missing from env |
| `4` | Binance API error (the API rejected the order) |
| `5` | Network error reaching Binance |

## Logging

- Log file: `logs/trading_bot.log` (created on first run).
- Every request (order params), every response, and every error (with traceback) is written at `DEBUG` / `INFO` / `ERROR` as appropriate.
- API keys are masked (`abcd***`). API **secrets** are never logged under any path.

## Assumptions

- **USDT-M futures only.** `COIN-M` symbols are not supported.
- **Exchange-info precision validation is deferred.** `stepSize`, `tickSize`, and `minNotional` are not pre-checked locally; instead, the bot relies on the API to reject and surfaces the Binance error code/message cleanly. A future enhancement could cache `futures_exchange_info()` at startup.
- **`timeInForce` defaults to `GTC`** for LIMIT and STOP-LIMIT orders; override with `--tif IOC|FOK|GTX`.
- **One-way position mode assumed.** `reduceOnly` / `positionSide` are not exposed on the CLI; configure hedge-mode in the testnet UI if required.
- **Leverage and margin type** are managed via the testnet web UI, not by this bot.

## Project structure

```
trading_bot/
  __init__.py
  bot/
    __init__.py
    client.py           # BinanceFuturesClient wrapper
    orders.py           # place_market / place_limit / place_stop_limit
    validators.py       # symbol, side, type, quantity, price checks
    logging_config.py   # file + Rich console handlers
    exceptions.py       # ValidationError
  cli.py                # Typer app + subcommands
logs/                   # runtime log output (gitignored)
.env.example            # template for BINANCE_API_KEY / BINANCE_API_SECRET
requirements.txt
README.md
```

## Deliverable log files

After running the three example commands above against the testnet, `logs/trading_bot.log` contains one request/response pair per order. Sample excerpts (API keys masked):

```
2026-04-21 ... | INFO | trading_bot | Initialized Binance futures client (testnet=True, api_key=abcd***)
2026-04-21 ... | INFO | trading_bot | Submitting futures order: {'symbol': 'BTCUSDT', 'side': 'BUY', 'type': 'MARKET', 'quantity': 0.01}
2026-04-21 ... | INFO | trading_bot | Futures order response: {'orderId': 12345, 'status': 'FILLED', ...}
```

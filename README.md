# Binance Futures Testnet Trading Bot

A Python CLI for placing **Market**, **Limit**, and **Stop-Limit** orders on the
[Binance USDT-M Futures Testnet](https://testnet.binancefuture.com). Built on top of
`python-binance`, with a `typer` CLI and `rich`-formatted output.

---

## Highlights

- Three order types: `market`, `limit`, `stop-limit` (BUY / SELL).
- `check-auth` command to verify credentials without placing an order.
- Clean layering: API wrapper (`trading_bot/bot/`) is independent of the CLI (`trading_bot/cli.py`).
- Pre-flight input validation — bad input fails before any network call.
- Rich request/response panels on every run, color-coded success and failure.
- Rotating file logs at `logs/trading_bot.log` (5 MB x 3 backups); API keys masked, secrets never logged.

---

## Prerequisites

- Python **3.10** or newer.
- A **Binance Futures testnet** account at https://testnet.binancefuture.com.
  - Generate an API key + secret from the testnet dashboard.
  - Use the faucet to fund your USDT-M wallet (10,000 USDT).

---

## Installation

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure credentials
cp .env.example .env               # Windows: copy .env.example .env
# then open .env and fill in BINANCE_API_KEY / BINANCE_API_SECRET
```

---

## Quick start

Run all commands from the project root.

### 1. Verify your API key

```bash
python -m trading_bot.cli check-auth
```

Hits the signed `/fapi/v2/balance` endpoint. Useful as a first sanity check after
pasting keys into `.env`.

### 2. Place a Market order

```bash
python -m trading_bot.cli market --symbol BTCUSDT --side BUY --quantity 0.01
```

### 3. Place a Limit order

```bash
python -m trading_bot.cli limit --symbol BTCUSDT --side SELL --quantity 0.01 --price 60000
```

### 4. Place a Stop-Limit order (bonus)

```bash
python -m trading_bot.cli stop-limit \
    --symbol BTCUSDT --side BUY \
    --quantity 0.01 --price 60500 --stop-price 60000
```

### Discover all commands

```bash
python -m trading_bot.cli --help
python -m trading_bot.cli limit --help
```

---

## Command reference

### Global options (apply to every command)

| Flag                        | Default                                | Description                                         |
| --------------------------- | -------------------------------------- | --------------------------------------------------- |
| `--log-dir PATH`            | `./logs`                               | Output directory for `trading_bot.log`.             |
| `--testnet / --no-testnet`  | `BINANCE_TESTNET` env var, else `true` | Target the testnet (`true`) or live API (`false`).  |

### Per-order options

| Flag             | Applies to            | Required | Notes                              |
| ---------------- | --------------------- | -------- | ---------------------------------- |
| `--symbol, -s`   | all                   | yes      | e.g. `BTCUSDT`                     |
| `--side`         | all                   | yes      | `BUY` or `SELL`                    |
| `--quantity, -q` | all                   | yes      | Base-asset quantity (> 0)          |
| `--price, -p`    | limit, stop-limit     | yes      | Limit price (> 0)                  |
| `--stop-price`   | stop-limit            | yes      | Trigger price (> 0)                |
| `--tif`          | limit, stop-limit     | no       | `GTC` (default), `IOC`, `FOK`, `GTX` |

### Example: validation failure (no API call)

```bash
python -m trading_bot.cli limit --symbol BTCUSDT --side BUY --quantity 0.01
# → red "Validation error: price is required for this order type"
# → exit code 2
```

---

## Exit codes

| Code | Meaning                                          |
| ---- | ------------------------------------------------ |
| `0`  | Success                                          |
| `1`  | Unexpected error (full traceback in log)         |
| `2`  | Local input validation failed                    |
| `3`  | API credentials missing from environment         |
| `4`  | Binance API error (order rejected by exchange)   |
| `5`  | Network error reaching Binance                   |

---

## Logging

- Path: `logs/trading_bot.log` (created on first run).
- Rotation: 5 MB per file, 3 backups.
- Every request, response, and error is recorded at `DEBUG` / `INFO` / `ERROR` levels.
- API keys are masked (`abcd***`). API secrets are **never** written to any log.

Sample entries:

```
2026-04-21 ... | INFO | trading_bot | Initialized Binance futures client (testnet=True, api_key=abcd***)
2026-04-21 ... | INFO | trading_bot | Submitting futures order: {'symbol': 'BTCUSDT', 'side': 'BUY', 'type': 'MARKET', 'quantity': 0.01}
2026-04-21 ... | INFO | trading_bot | Futures order response: {'orderId': 12345, 'status': 'FILLED', ...}
```

---

## Project layout

```
trading_bot/
├── __init__.py
├── cli.py                    # Typer app + subcommands
└── bot/
    ├── __init__.py
    ├── client.py             # BinanceFuturesClient wrapper
    ├── orders.py             # place_market / place_limit / place_stop_limit
    ├── validators.py         # symbol, side, type, quantity, price checks
    ├── logging_config.py     # file + Rich console handlers
    └── exceptions.py         # ValidationError
logs/                         # runtime output (gitignored)
.env.example                  # template for BINANCE_API_KEY / BINANCE_API_SECRET
requirements.txt
README.md
```

---

## Scope and assumptions

- **USDT-M futures only.** `COIN-M` symbols are not supported.
- **One-way position mode.** `reduceOnly` and `positionSide` are not exposed on the CLI;
  configure hedge mode in the testnet UI if you need it.
- **Leverage and margin type** are managed through the testnet web UI, not this bot.
- **`timeInForce` defaults to `GTC`** for LIMIT and STOP-LIMIT; override with `--tif`.
- **Exchange-info precision is not validated locally.** `stepSize`, `tickSize`, and
  `minNotional` are enforced by the exchange — the bot surfaces the Binance error
  code/message cleanly. Caching `futures_exchange_info()` at startup is a natural
  follow-up enhancement.

---

## Dependencies

See [requirements.txt](requirements.txt):

- `python-binance` — REST client for Binance Futures
- `typer` — CLI framework
- `rich` — colorized terminal output
- `python-dotenv` — loads credentials from `.env`

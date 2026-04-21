from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

import typer
from binance.exceptions import BinanceAPIException, BinanceRequestException
from dotenv import load_dotenv
from requests.exceptions import RequestException
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .bot import orders as order_helpers
from .bot import validators
from .bot.client import BinanceFuturesClient
from .bot.exceptions import ValidationError
from .bot.logging_config import configure_logging, get_logger

EXIT_VALIDATION = 2
EXIT_MISSING_CREDS = 3
EXIT_API_ERROR = 4
EXIT_NETWORK = 5
EXIT_UNEXPECTED = 1

app = typer.Typer(
    name="trading-bot",
    help="Binance USDT-M Futures Testnet CLI — place Market, Limit, and Stop-Limit orders.",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"false", "0", "no", "off", ""}


@app.callback()
def main(
    ctx: typer.Context,
    log_dir: Path = typer.Option(
        Path("./logs"),
        "--log-dir",
        help="Directory where trading_bot.log is written.",
    ),
    testnet: Optional[bool] = typer.Option(
        None,
        "--testnet/--no-testnet",
        help="Target the Binance testnet. Defaults from BINANCE_TESTNET env var, else true.",
    ),
) -> None:
    load_dotenv()
    configure_logging(log_dir)
    resolved_testnet = _bool_env("BINANCE_TESTNET", True) if testnet is None else testnet
    ctx.obj = {"testnet": resolved_testnet, "log_dir": log_dir}


def _load_credentials() -> tuple[str, str]:
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
    if not api_key or not api_secret:
        console.print(
            Panel.fit(
                "[red]BINANCE_API_KEY and BINANCE_API_SECRET are not set.[/red]\n"
                "Copy [cyan].env.example[/cyan] to [cyan].env[/cyan] and paste your "
                "testnet credentials from https://testnet.binancefuture.com.",
                title="Missing credentials",
                border_style="red",
            )
        )
        raise typer.Exit(code=EXIT_MISSING_CREDS)
    return api_key, api_secret


def _request_summary(order_type: str, fields: dict[str, Any]) -> Panel:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", justify="right")
    table.add_column(style="white")
    for key, value in fields.items():
        if value is None:
            continue
        table.add_row(key, str(value))
    return Panel(table, title=f"Request · {order_type}", border_style="cyan")


def _response_panel(response: dict[str, Any]) -> Panel:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold green", justify="right")
    table.add_column(style="white")
    interesting = [
        "orderId",
        "clientOrderId",
        "symbol",
        "status",
        "type",
        "side",
        "origQty",
        "executedQty",
        "price",
        "avgPrice",
        "stopPrice",
        "timeInForce",
        "updateTime",
    ]
    for key in interesting:
        if key in response and response[key] not in (None, "", "0", 0):
            table.add_row(key, str(response[key]))
    return Panel(table, title="Response · SUCCESS", border_style="green")


def _handle_api_error(exc: BinanceAPIException) -> None:
    log = get_logger()
    log.exception("Binance API error surfaced to user")
    console.print(
        Panel.fit(
            f"[bold red]Binance rejected the order.[/bold red]\n"
            f"code: [yellow]{exc.code}[/yellow]\n"
            f"message: {exc.message}",
            title="Response · FAILURE",
            border_style="red",
        )
    )


def _run_order(
    ctx: typer.Context,
    order_type_label: str,
    summary_fields: dict[str, Any],
    place_order,
) -> None:
    log = get_logger()
    console.print(_request_summary(order_type_label, summary_fields))
    try:
        api_key, api_secret = _load_credentials()
        client = BinanceFuturesClient(
            api_key=api_key, api_secret=api_secret, testnet=ctx.obj["testnet"]
        )
        client.ping()
        response = place_order(client)
    except BinanceAPIException as exc:
        _handle_api_error(exc)
        raise typer.Exit(code=EXIT_API_ERROR)
    except BinanceRequestException as exc:
        log.exception("Binance request exception")
        console.print(f"[red]Binance request error:[/red] {exc}")
        raise typer.Exit(code=EXIT_API_ERROR)
    except RequestException as exc:
        log.exception("Network error contacting Binance")
        console.print(f"[red]Network error:[/red] {exc}")
        raise typer.Exit(code=EXIT_NETWORK)
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001 — last-resort guard, full traceback in log file
        log.exception("Unexpected error")
        console.print(f"[red]Unexpected error:[/red] {exc}")
        raise typer.Exit(code=EXIT_UNEXPECTED)

    console.print(_response_panel(response))


def _validate_common(symbol: str, side: str, quantity: float) -> tuple[str, str, float]:
    try:
        s = validators.validate_symbol(symbol)
        sd = validators.validate_side(side)
        q = validators.validate_quantity(quantity)
    except ValidationError as exc:
        get_logger().warning("Validation failed: %s", exc)
        console.print(f"[red]Validation error:[/red] {exc}")
        raise typer.Exit(code=EXIT_VALIDATION)
    return s, sd, q


@app.command("check-auth")
def check_auth_cmd(ctx: typer.Context) -> None:
    """Verify the API key by calling a signed endpoint (no order placed)."""
    log = get_logger()
    try:
        api_key, api_secret = _load_credentials()
        client = BinanceFuturesClient(
            api_key=api_key, api_secret=api_secret, testnet=ctx.obj["testnet"]
        )
        client.ping()
        balances = client.account_balance()
    except BinanceAPIException as exc:
        _handle_api_error(exc)
        console.print(
            "[yellow]Hint:[/yellow] code -2015 usually means the key was not generated on "
            "the Futures testnet, lacks trading permission, or has an IP allowlist."
        )
        raise typer.Exit(code=EXIT_API_ERROR)
    except RequestException as exc:
        log.exception("Network error")
        console.print(f"[red]Network error:[/red] {exc}")
        raise typer.Exit(code=EXIT_NETWORK)

    usdt = next((b for b in balances if b.get("asset") == "USDT"), None)
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold green", justify="right")
    table.add_column(style="white")
    table.add_row("assets returned", str(len(balances)))
    if usdt:
        table.add_row("USDT balance", str(usdt.get("balance")))
        table.add_row("USDT available", str(usdt.get("availableBalance")))
    console.print(Panel(table, title="Auth check · SUCCESS", border_style="green"))


@app.command("market")
def market_cmd(
    ctx: typer.Context,
    symbol: str = typer.Option(..., "--symbol", "-s", help="Trading pair, e.g. BTCUSDT"),
    side: str = typer.Option(..., "--side", help="BUY or SELL"),
    quantity: float = typer.Option(..., "--quantity", "-q", help="Base asset quantity (> 0)"),
) -> None:
    """Place a MARKET order."""
    sym, sd, qty = _validate_common(symbol, side, quantity)
    _run_order(
        ctx,
        order_type_label="MARKET",
        summary_fields={"symbol": sym, "side": sd, "type": "MARKET", "quantity": qty},
        place_order=lambda c: order_helpers.place_market_order(c, sym, sd, qty),
    )


@app.command("limit")
def limit_cmd(
    ctx: typer.Context,
    symbol: str = typer.Option(..., "--symbol", "-s", help="Trading pair, e.g. BTCUSDT"),
    side: str = typer.Option(..., "--side", help="BUY or SELL"),
    quantity: float = typer.Option(..., "--quantity", "-q", help="Base asset quantity (> 0)"),
    price: float = typer.Option(..., "--price", "-p", help="Limit price (> 0)"),
    time_in_force: str = typer.Option("GTC", "--tif", help="GTC | IOC | FOK | GTX"),
) -> None:
    """Place a LIMIT order."""
    sym, sd, qty = _validate_common(symbol, side, quantity)
    try:
        px = validators.validate_price(price, required=True, field="price")
        tif = validators.validate_time_in_force(time_in_force)
    except ValidationError as exc:
        get_logger().warning("Validation failed: %s", exc)
        console.print(f"[red]Validation error:[/red] {exc}")
        raise typer.Exit(code=EXIT_VALIDATION)
    _run_order(
        ctx,
        order_type_label="LIMIT",
        summary_fields={
            "symbol": sym,
            "side": sd,
            "type": "LIMIT",
            "quantity": qty,
            "price": px,
            "timeInForce": tif,
        },
        place_order=lambda c: order_helpers.place_limit_order(c, sym, sd, qty, px, tif),
    )


@app.command("stop-limit")
def stop_limit_cmd(
    ctx: typer.Context,
    symbol: str = typer.Option(..., "--symbol", "-s", help="Trading pair, e.g. BTCUSDT"),
    side: str = typer.Option(..., "--side", help="BUY or SELL"),
    quantity: float = typer.Option(..., "--quantity", "-q", help="Base asset quantity (> 0)"),
    price: float = typer.Option(..., "--price", "-p", help="Limit price (> 0)"),
    stop_price: float = typer.Option(..., "--stop-price", help="Trigger (stop) price (> 0)"),
    time_in_force: str = typer.Option("GTC", "--tif", help="GTC | IOC | FOK | GTX"),
) -> None:
    """Place a STOP-LIMIT order (bonus)."""
    sym, sd, qty = _validate_common(symbol, side, quantity)
    try:
        px = validators.validate_price(price, required=True, field="price")
        sp = validators.validate_price(stop_price, required=True, field="stop_price")
        tif = validators.validate_time_in_force(time_in_force)
    except ValidationError as exc:
        get_logger().warning("Validation failed: %s", exc)
        console.print(f"[red]Validation error:[/red] {exc}")
        raise typer.Exit(code=EXIT_VALIDATION)
    _run_order(
        ctx,
        order_type_label="STOP-LIMIT",
        summary_fields={
            "symbol": sym,
            "side": sd,
            "type": "STOP",
            "quantity": qty,
            "price": px,
            "stopPrice": sp,
            "timeInForce": tif,
        },
        place_order=lambda c: order_helpers.place_stop_limit_order(c, sym, sd, qty, px, sp, tif),
    )


if __name__ == "__main__":
    app()

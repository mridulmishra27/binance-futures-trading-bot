from __future__ import annotations

import re

from .exceptions import ValidationError

_SYMBOL_RE = re.compile(r"^[A-Z0-9]{5,20}$")
_ALLOWED_SIDES = frozenset({"BUY", "SELL"})
_ALLOWED_TYPES = frozenset({"MARKET", "LIMIT", "STOP"})
_ALLOWED_TIF = frozenset({"GTC", "IOC", "FOK", "GTX"})


def validate_symbol(symbol: str) -> str:
    if symbol is None:
        raise ValidationError("symbol is required")
    cleaned = symbol.strip().upper()
    if not _SYMBOL_RE.match(cleaned):
        raise ValidationError(
            f"symbol {symbol!r} is invalid: expected 5-20 uppercase alphanumeric characters, e.g. BTCUSDT"
        )
    return cleaned


def validate_side(side: str) -> str:
    if side is None:
        raise ValidationError("side is required")
    cleaned = side.strip().upper()
    if cleaned not in _ALLOWED_SIDES:
        raise ValidationError(f"side {side!r} is invalid: expected one of {sorted(_ALLOWED_SIDES)}")
    return cleaned


def validate_order_type(order_type: str) -> str:
    if order_type is None:
        raise ValidationError("order type is required")
    cleaned = order_type.strip().upper()
    if cleaned not in _ALLOWED_TYPES:
        raise ValidationError(
            f"order type {order_type!r} is invalid: expected one of {sorted(_ALLOWED_TYPES)}"
        )
    return cleaned


def validate_quantity(quantity: float | None) -> float:
    if quantity is None:
        raise ValidationError("quantity is required")
    try:
        value = float(quantity)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"quantity {quantity!r} is not a number") from exc
    if value <= 0:
        raise ValidationError(f"quantity must be > 0, got {value}")
    return value


def validate_price(price: float | None, *, required: bool, field: str = "price") -> float | None:
    if price is None:
        if required:
            raise ValidationError(f"{field} is required for this order type")
        return None
    try:
        value = float(price)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field} {price!r} is not a number") from exc
    if value <= 0:
        raise ValidationError(f"{field} must be > 0, got {value}")
    return value


def validate_time_in_force(tif: str) -> str:
    if tif is None:
        raise ValidationError("time_in_force is required")
    cleaned = tif.strip().upper()
    if cleaned not in _ALLOWED_TIF:
        raise ValidationError(
            f"time_in_force {tif!r} is invalid: expected one of {sorted(_ALLOWED_TIF)}"
        )
    return cleaned

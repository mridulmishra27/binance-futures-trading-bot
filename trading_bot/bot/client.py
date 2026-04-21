from __future__ import annotations

from typing import Any

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException

from .logging_config import get_logger, mask_secret


class BinanceFuturesClient:
    """Thin wrapper around python-binance's Client focused on USDT-M futures.

    Passing testnet=True rewrites the futures base URL to https://testnet.binancefuture.com,
    so every futures_* call targets the testnet.
    """

    def __init__(self, api_key: str, api_secret: str, testnet: bool = True) -> None:
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret are required")
        self._log = get_logger()
        self._testnet = testnet
        self._client = Client(api_key, api_secret, testnet=testnet)
        self._log.info(
            "Initialized Binance futures client (testnet=%s, api_key=%s)",
            testnet,
            mask_secret(api_key),
        )

    @property
    def testnet(self) -> bool:
        return self._testnet

    def ping(self) -> None:
        self._log.debug("Pinging futures endpoint")
        try:
            self._client.futures_ping()
        except (BinanceAPIException, BinanceRequestException) as exc:
            self._log.exception("Futures ping failed with Binance error")
            raise
        except Exception:
            self._log.exception("Futures ping failed with unexpected error")
            raise
        self._log.debug("Futures ping ok")

    def account_balance(self) -> list[dict[str, Any]]:
        """Signed GET /fapi/v2/balance — fastest way to verify the API key works."""
        self._log.debug("Requesting futures account balance")
        try:
            response = self._client.futures_account_balance()
        except BinanceAPIException:
            self._log.exception("Binance API error on account_balance")
            raise
        except BinanceRequestException:
            self._log.exception("Binance request error on account_balance")
            raise
        except Exception:
            self._log.exception("Unexpected error on account_balance")
            raise
        self._log.info("Futures account balance entries: %d", len(response))
        return response

    def create_order(self, **params: Any) -> dict[str, Any]:
        safe_params = {k: v for k, v in params.items() if k not in {"api_key", "api_secret"}}
        self._log.info("Submitting futures order: %s", safe_params)
        try:
            response = self._client.futures_create_order(**params)
        except BinanceAPIException as exc:
            self._log.error(
                "Binance API error on create_order: code=%s message=%s params=%s",
                exc.code,
                exc.message,
                safe_params,
            )
            raise
        except BinanceRequestException as exc:
            self._log.exception("Binance request error on create_order params=%s", safe_params)
            raise
        except Exception:
            self._log.exception("Unexpected error on create_order params=%s", safe_params)
            raise
        self._log.info("Futures order response: %s", response)
        return response

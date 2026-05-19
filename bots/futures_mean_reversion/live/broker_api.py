"""
Broker API abstraction layer.
Supports Tradovate (REST + WebSocket) and a stub for Rithmic/TopstepX.

Usage:
  broker = TradovateBroker(cfg)
  broker.connect()
  position = broker.get_position("MESH5")
  broker.place_market_order("MESH5", 1, "Buy")
  broker.place_stop_order("MESH5", 1, "Sell", stop_price=4900.0)
"""

import logging
import time
import requests
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Abstract Base ────────────────────────────────────────────────────────────

class BrokerBase(ABC):

    @abstractmethod
    def connect(self) -> bool: ...

    @abstractmethod
    def get_account_balance(self) -> float: ...

    @abstractmethod
    def get_position(self, symbol: str) -> int: ...

    @abstractmethod
    def place_market_order(self, symbol: str, qty: int, side: str) -> dict: ...

    @abstractmethod
    def place_stop_order(self, symbol: str, qty: int, side: str, stop_price: float) -> dict: ...

    @abstractmethod
    def cancel_all_orders(self, symbol: str) -> bool: ...

    @abstractmethod
    def get_latest_ohlcv(self, symbol: str, n_bars: int) -> list: ...


# ─── Tradovate ────────────────────────────────────────────────────────────────

class TradovateBroker(BrokerBase):
    """
    Tradovate REST API broker.
    Docs: https://api.tradovate.com/
    Topstep uses Tradovate as their execution platform.
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self._token: Optional[str] = None
        self._account_id: Optional[int] = None
        self._base = cfg.live.tradovate_base_url

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    def connect(self) -> bool:
        payload = {
            "name": self.cfg.live.tradovate_user,
            "password": self.cfg.live.tradovate_password,
            "appId": self.cfg.live.tradovate_app_id,
            "appVersion": self.cfg.live.tradovate_app_version,
            "cids": [],
            "sec": "API",
        }
        try:
            r = requests.post(f"{self._base}/auth/accesstokenrequest", json=payload, timeout=15)
            r.raise_for_status()
            data = r.json()
            self._token = data["accessToken"]
            self._account_id = data["accounts"][0]["id"]
            logger.info(f"Tradovate connected. Account ID: {self._account_id}")
            return True
        except Exception as e:
            logger.error(f"Tradovate connect failed: {e}")
            return False

    def get_account_balance(self) -> float:
        try:
            r = requests.get(
                f"{self._base}/cashbalance/getcashbalancesnapshot",
                params={"accountId": self._account_id},
                headers=self._headers(), timeout=10,
            )
            r.raise_for_status()
            return float(r.json().get("totalCashValue", 0))
        except Exception as e:
            logger.error(f"get_account_balance failed: {e}")
            return 0.0

    def get_position(self, symbol: str) -> int:
        try:
            r = requests.get(f"{self._base}/position/list", headers=self._headers(), timeout=10)
            r.raise_for_status()
            for pos in r.json():
                if pos.get("contractId") and symbol in str(pos.get("contractId", "")):
                    return int(pos.get("netPos", 0))
            return 0
        except Exception as e:
            logger.error(f"get_position failed: {e}")
            return 0

    def place_market_order(self, symbol: str, qty: int, side: str) -> dict:
        """side: 'Buy' | 'Sell'"""
        order = {
            "accountSpec": self.cfg.live.tradovate_user,
            "accountId": self._account_id,
            "action": side,
            "symbol": symbol,
            "orderQty": qty,
            "orderType": "Market",
            "isAutomated": True,
        }
        try:
            r = requests.post(f"{self._base}/order/placeorder", json=order,
                              headers=self._headers(), timeout=10)
            r.raise_for_status()
            result = r.json()
            logger.info(f"Market order placed: {side} {qty}x {symbol} → {result}")
            return result
        except Exception as e:
            logger.error(f"place_market_order failed: {e}")
            return {"error": str(e)}

    def place_stop_order(self, symbol: str, qty: int, side: str, stop_price: float) -> dict:
        order = {
            "accountSpec": self.cfg.live.tradovate_user,
            "accountId": self._account_id,
            "action": side,
            "symbol": symbol,
            "orderQty": qty,
            "orderType": "Stop",
            "stopPrice": stop_price,
            "isAutomated": True,
        }
        try:
            r = requests.post(f"{self._base}/order/placeorder", json=order,
                              headers=self._headers(), timeout=10)
            r.raise_for_status()
            result = r.json()
            logger.info(f"Stop order placed: {side} {qty}x {symbol} @ stop={stop_price} → {result}")
            return result
        except Exception as e:
            logger.error(f"place_stop_order failed: {e}")
            return {"error": str(e)}

    def cancel_all_orders(self, symbol: str) -> bool:
        try:
            r = requests.get(f"{self._base}/order/list", headers=self._headers(), timeout=10)
            r.raise_for_status()
            for order in r.json():
                if order.get("status") == "Working":
                    requests.post(
                        f"{self._base}/order/cancelorder",
                        json={"orderId": order["id"]},
                        headers=self._headers(), timeout=10,
                    )
            return True
        except Exception as e:
            logger.error(f"cancel_all_orders failed: {e}")
            return False

    def get_latest_ohlcv(self, symbol: str, n_bars: int = 350) -> list:
        """
        Fetch OHLCV bars from Tradovate market data endpoint.
        Returns list of dicts with keys: timestamp, open, high, low, close, volume.
        """
        try:
            r = requests.get(
                f"{self._base}/md/chart",
                params={
                    "symbol": symbol,
                    "chartDescription": {"underlyingType": "Daily", "elementSize": 1,
                                         "elementSizeUnit": "UnderlyingUnits",
                                         "withHistogram": False},
                    "timeRange": {"asMuchAsElements": n_bars},
                },
                headers=self._headers(), timeout=15,
            )
            r.raise_for_status()
            return r.json().get("bars", [])
        except Exception as e:
            logger.error(f"get_latest_ohlcv failed: {e}")
            return []


# ─── Paper Broker (no network calls) ─────────────────────────────────────────

class PaperBroker(BrokerBase):
    """In-memory paper trading broker for testing live logic without real API."""

    def __init__(self, cfg, starting_balance: float = 50_000.0):
        self.cfg = cfg
        self._balance = starting_balance
        self._position = 0
        self._orders = []

    def connect(self) -> bool:
        logger.info("Paper broker connected.")
        return True

    def get_account_balance(self) -> float:
        return self._balance

    def get_position(self, symbol: str) -> int:
        return self._position

    def place_market_order(self, symbol: str, qty: int, side: str) -> dict:
        sign = 1 if side == "Buy" else -1
        self._position += sign * qty
        logger.info(f"[PAPER] {side} {qty}x {symbol}. Position: {self._position}")
        return {"orderId": f"paper_{int(time.time())}", "status": "Filled"}

    def place_stop_order(self, symbol: str, qty: int, side: str, stop_price: float) -> dict:
        self._orders.append({"symbol": symbol, "qty": qty, "side": side, "stop": stop_price})
        logger.info(f"[PAPER] Stop order: {side} {qty}x {symbol} @ {stop_price}")
        return {"orderId": f"paper_stop_{int(time.time())}", "status": "Working"}

    def cancel_all_orders(self, symbol: str) -> bool:
        self._orders = [o for o in self._orders if o["symbol"] != symbol]
        return True

    def get_latest_ohlcv(self, symbol: str, n_bars: int = 350) -> list:
        # Falls back to yfinance for paper mode
        try:
            from data.loader import load_yfinance
            import pandas as pd
            df = load_yfinance(symbol, start="2020-01-01",
                               end=pd.Timestamp.today().strftime("%Y-%m-%d"))
            return df.tail(n_bars).reset_index().to_dict("records")
        except Exception:
            return []


def create_broker(cfg) -> BrokerBase:
    if cfg.live.paper_trade:
        logger.info("Using PaperBroker (paper_trade=True)")
        return PaperBroker(cfg)
    if cfg.live.broker == "tradovate":
        return TradovateBroker(cfg)
    raise ValueError(f"Unknown broker: {cfg.live.broker}")

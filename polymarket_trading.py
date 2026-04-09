import os
import time
import hmac
import hashlib
import base64
import json
import requests
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class PolymarketTrader:
    """
    Authenticated Polymarket CLOB client for placing and managing orders.
    Reads credentials from environment variables — never hardcode keys.

    Required .env variables:
        POLYMARKET_API_KEY
        POLYMARKET_API_SECRET
        POLYMARKET_API_PASSPHRASE
        POLYMARKET_ADDRESS
        POLYMARKET_PRIVATE_KEY  (only needed for on-chain approvals)
    """

    def __init__(self):
        self.base_url = os.getenv("POLYMARKET_BASE_URL", "https://clob.polymarket.com")
        self.api_key = os.getenv("POLYMARKET_API_KEY")
        self.api_secret = os.getenv("POLYMARKET_API_SECRET")
        self.api_passphrase = os.getenv("POLYMARKET_API_PASSPHRASE")
        self.address = os.getenv("POLYMARKET_ADDRESS")

        if not all([self.api_key, self.api_secret, self.api_passphrase, self.address]):
            raise EnvironmentError(
                "Missing Polymarket credentials. "
                "Set POLYMARKET_API_KEY, POLYMARKET_API_SECRET, "
                "POLYMARKET_API_PASSPHRASE, and POLYMARKET_ADDRESS in .env"
            )

    def _get_auth_headers(self, method: str, path: str, body: str = "") -> Dict:
        """Build the L2 authentication headers required by every trading request."""
        timestamp = str(int(time.time()))
        message = timestamp + method.upper() + path + body
        secret_bytes = base64.b64decode(self.api_secret)
        signature = base64.b64encode(
            hmac.new(secret_bytes, message.encode("utf-8"), hashlib.sha256).digest()
        ).decode("utf-8")

        return {
            "Content-Type": "application/json",
            "POLY_ADDRESS": self.address,
            "POLY_API_KEY": self.api_key,
            "POLY_PASSPHRASE": self.api_passphrase,
            "POLY_TIMESTAMP": timestamp,
            "POLY_SIGNATURE": signature,
        }

    def get_balance(self) -> Dict:
        """Get your current USDC balance on Polymarket."""
        path = "/balance"
        headers = self._get_auth_headers("GET", path)
        try:
            resp = requests.get(f"{self.base_url}{path}", headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching balance: {e}")
            return {}

    def get_open_orders(self) -> list:
        """Get all your currently open orders."""
        path = "/orders"
        headers = self._get_auth_headers("GET", path)
        try:
            resp = requests.get(f"{self.base_url}{path}", headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching orders: {e}")
            return []

    def get_positions(self) -> list:
        """Get all your current positions."""
        path = f"/positions?user={self.address}"
        headers = self._get_auth_headers("GET", path)
        try:
            resp = requests.get(f"{self.base_url}{path}", headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else data.get("positions", [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching positions: {e}")
            return []

    def place_market_order(
        self,
        token_id: str,
        side: str,          # "BUY" or "SELL"
        amount_usdc: float, # how much USDC to spend
        price: float,       # limit price (0.0 – 1.0)
        dry_run: bool = True,
    ) -> Dict:
        """
        Place a limit order on a Polymarket market.

        Args:
            token_id:     The token_id from the market's tokens list (outcome token)
            side:         "BUY" or "SELL"
            amount_usdc:  Amount in USDC to spend (e.g. 5.0 = $5)
            price:        Price per share (0.01 – 0.99), e.g. 0.55 = 55 cents
            dry_run:      If True, prints the order but does NOT submit it

        Returns:
            Order response dict, or dry-run preview dict
        """
        size = round(amount_usdc / price, 4)  # shares = dollars / price

        order = {
            "tokenID": token_id,
            "side": side.upper(),
            "type": "LIMIT",
            "price": str(price),
            "size": str(size),
            "timeInForce": "GTC",  # Good-Till-Cancelled
        }

        if dry_run:
            print("\n[DRY RUN] Order preview (not submitted):")
            print(json.dumps(order, indent=2))
            print(f"  Spending: ${amount_usdc:.2f} USDC")
            print(f"  Shares:   {size:.4f}")
            print(f"  Price:    {price} ({int(price*100)}¢ per share)")
            return {"dry_run": True, "order": order}

        path = "/order"
        body = json.dumps(order)
        headers = self._get_auth_headers("POST", path, body)

        try:
            resp = requests.post(
                f"{self.base_url}{path}",
                headers=headers,
                data=body,
                timeout=10,
            )
            resp.raise_for_status()
            result = resp.json()
            print(f"Order placed: {result}")
            return result
        except requests.exceptions.RequestException as e:
            print(f"Error placing order: {e}")
            if hasattr(e, "response") and e.response is not None:
                print(f"Response: {e.response.text}")
            return {}

    def cancel_order(self, order_id: str) -> Dict:
        """Cancel an open order by ID."""
        path = f"/order/{order_id}"
        headers = self._get_auth_headers("DELETE", path)
        try:
            resp = requests.delete(f"{self.base_url}{path}", headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            print(f"Error cancelling order {order_id}: {e}")
            return {}

    def test_connection(self) -> bool:
        """Verify credentials are working by fetching balance."""
        print("Testing Polymarket connection...")
        balance = self.get_balance()
        if balance:
            print(f"Connected! Balance: {balance}")
            return True
        else:
            print("Connection failed — check your credentials in .env")
            return False

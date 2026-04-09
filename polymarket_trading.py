import os
import json
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()


def _build_client(level: int = 2):
    """
    Build an authenticated py-clob-client ClobClient.
    level=1  → wallet-only (L1 auth)
    level=2  → full L2 API key auth (needed for orders/balance)
    """
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import ApiCreds

    host = os.getenv("POLYMARKET_BASE_URL", "https://clob.polymarket.com")
    key = os.getenv("POLYMARKET_PRIVATE_KEY")
    chain_id = int(os.getenv("POLYMARKET_CHAIN_ID", "137"))

    if level == 1:
        return ClobClient(host=host, chain_id=chain_id, key=key)

    creds = ApiCreds(
        api_key=os.getenv("POLYMARKET_API_KEY"),
        api_secret=os.getenv("POLYMARKET_API_SECRET"),
        api_passphrase=os.getenv("POLYMARKET_API_PASSPHRASE"),
    )
    return ClobClient(host=host, chain_id=chain_id, key=key, creds=creds)


class PolymarketTrader:
    """
    Authenticated Polymarket trading client.
    Uses the official py-clob-client for correct L2 HMAC signing.

    Required .env variables:
        POLYMARKET_PRIVATE_KEY
        POLYMARKET_API_KEY
        POLYMARKET_API_SECRET
        POLYMARKET_API_PASSPHRASE
        POLYMARKET_ADDRESS
    """

    def __init__(self):
        self.address = os.getenv("POLYMARKET_ADDRESS")
        self._client = _build_client(level=2)

    def test_connection(self) -> bool:
        """Verify credentials work by fetching the API key details."""
        try:
            result = self._client.get_api_keys()
            print(f"✅ Connected to Polymarket!")
            print(f"   Address:  {self.address}")
            print(f"   API keys: {result}")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

    def get_balance(self) -> Dict:
        """Get your USDC balance and allowance on Polymarket."""
        try:
            from py_clob_client.clob_types import BalanceAllowanceParams, AssetType
            params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
            return self._client.get_balance_allowance(params)
        except Exception as e:
            print(f"Error fetching balance: {e}")
            return {}

    def get_open_orders(self) -> List:
        """Get all your currently open orders."""
        try:
            return self._client.get_orders()
        except Exception as e:
            print(f"Error fetching orders: {e}")
            return []

    def get_positions(self) -> List:
        """Get all your current open positions."""
        try:
            return self._client.get_positions()
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return []

    def get_trades(self) -> List:
        """Get your recent trade history."""
        try:
            return self._client.get_trades()
        except Exception as e:
            print(f"Error fetching trades: {e}")
            return []

    def place_order(
        self,
        token_id: str,
        side: str,
        price: float,
        size: float,
        dry_run: bool = True,
    ) -> Dict:
        """
        Place a limit order on a Polymarket market.

        Args:
            token_id:  The outcome token ID from the market's tokens list
            side:      "BUY" or "SELL"
            price:     Price per share (0.01 – 0.99), e.g. 0.55 = 55 cents
            size:      Number of shares (e.g. 10 = 10 shares at $0.55 = $5.50)
            dry_run:   If True, preview only — does NOT submit the order

        Returns:
            Order result dict, or dry-run preview
        """
        from py_clob_client.clob_types import OrderArgs, OrderType

        order_args = OrderArgs(
            token_id=token_id,
            price=price,
            size=size,
            side=side.upper(),
        )

        if dry_run:
            print("\n[DRY RUN] Order preview — not submitted:")
            print(f"  Token:  {token_id}")
            print(f"  Side:   {side.upper()}")
            print(f"  Price:  {price} ({int(price*100)}¢)")
            print(f"  Size:   {size} shares")
            print(f"  Cost:   ~${round(price * size, 2)} USDC")
            return {"dry_run": True, "token_id": token_id, "side": side, "price": price, "size": size}

        try:
            signed = self._client.create_order(order_args)
            result = self._client.post_order(signed, OrderType.GTC)
            print(f"Order placed: {result}")
            return result
        except Exception as e:
            print(f"Error placing order: {e}")
            return {}

    def cancel_order(self, order_id: str) -> Dict:
        """Cancel an open order by ID."""
        try:
            return self._client.cancel(order_id)
        except Exception as e:
            print(f"Error cancelling order {order_id}: {e}")
            return {}

    def cancel_all_orders(self) -> Dict:
        """Cancel all open orders."""
        try:
            return self._client.cancel_all()
        except Exception as e:
            print(f"Error cancelling all orders: {e}")
            return {}

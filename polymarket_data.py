import os
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class PolymarketDataFetcher:
    def __init__(self):
        self.base_url = os.getenv("POLYMARKET_BASE_URL", "https://clob.polymarket.com")
        # Public read endpoints require no auth headers
        self.headers = {"Content-Type": "application/json"}

    def get_nba_markets(self, limit: int = 50) -> List[Dict]:
        """
        Fetch active NBA prediction markets from Polymarket.
        Filters by 'NBA' in the question title using cursor-based pagination.
        """
        try:
            url = f"{self.base_url}/markets"
            all_markets = []
            next_cursor = None

            while True:
                params = {"limit": 100}
                if next_cursor:
                    params["next_cursor"] = next_cursor

                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                for market in data.get("data", []):
                    question = market.get("question", "")
                    if "NBA" in question and market.get("active") and not market.get("closed"):
                        all_markets.append(market)

                next_cursor = data.get("next_cursor")
                if not next_cursor or next_cursor == "LTE=":
                    break
                if len(all_markets) >= limit:
                    break

            return all_markets[:limit]

        except requests.exceptions.RequestException as e:
            print(f"Error fetching NBA markets: {e}")
            return []

    def get_market_by_id(self, condition_id: str) -> Dict:
        """Get a specific market by its condition_id."""
        try:
            url = f"{self.base_url}/markets/{condition_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching market {condition_id}: {e}")
            return {}

    def get_market_prices(self, condition_id: str) -> Dict:
        """
        Get current prices and implied probabilities for a market.
        Prices live inside market['tokens'] — each token has a price 0.0–1.0.
        """
        market = self.get_market_by_id(condition_id)
        if not market:
            return {}

        tokens = market.get("tokens", [])
        if not tokens:
            return {}

        outcomes = {t.get("outcome"): float(t.get("price", 0)) for t in tokens}
        main_price = float(tokens[0].get("price", 0))

        return {
            "condition_id": condition_id,
            "outcomes": outcomes,
            "bid": round(main_price - 0.005, 4),
            "ask": round(main_price + 0.005, 4),
            "mid": main_price,
            "implied_probability": main_price,
        }

    def search_nba_game(self, team1: str, team2: str) -> Optional[Dict]:
        """Search for a specific NBA game market by team names."""
        markets = self.get_nba_markets()
        for market in markets:
            question = market.get("question", "").lower()
            if team1.lower() in question and team2.lower() in question:
                return market
        return None

    def get_game_odds(self, home_team: str, away_team: str) -> Dict:
        """Get Polymarket implied odds for a specific NBA game."""
        market = self.search_nba_game(home_team, away_team)
        if not market:
            return {"error": f"No active market found for {home_team} vs {away_team}"}

        condition_id = market.get("condition_id")
        prices = self.get_market_prices(condition_id)

        return {
            "market_question": market.get("question"),
            "condition_id": condition_id,
            "home_team": home_team,
            "away_team": away_team,
            "market_prices": prices,
            "game_start_time": market.get("game_start_time"),
            "end_date_iso": market.get("end_date_iso"),
            "active": market.get("active"),
            "accepting_orders": market.get("accepting_orders"),
        }

from typing import Dict, Optional, Tuple
from polymarket_data import PolymarketDataFetcher
from nba_stats import NBAStatsFetcher


class NBAPredictor:
    """
    Compares Polymarket implied probabilities against NBA statistical win rates
    to surface potentially mispriced prediction markets.
    """

    def __init__(self):
        self.polymarket = PolymarketDataFetcher()
        self.nba = NBAStatsFetcher()

    def predict_game(self, home_team_name: str, away_team_name: str) -> Dict:
        """
        Generate a prediction for an NBA game by comparing:
          - Polymarket implied win probability
          - Statistical win rate from recent game history

        Returns a dict with both signals and a recommended action.
        """
        print(f"\nAnalyzing: {home_team_name} vs {away_team_name}")

        # --- Polymarket signal ---
        odds = self.polymarket.get_game_odds(home_team_name, away_team_name)
        if "error" in odds:
            return {"error": odds["error"]}

        market_prices = odds.get("market_prices", {})
        outcomes = market_prices.get("outcomes", {})

        # Match the home team to its outcome token
        poly_home_prob = self._find_team_probability(outcomes, home_team_name)
        poly_away_prob = 1.0 - poly_home_prob if poly_home_prob is not None else None

        # --- Statistical signal ---
        home_team = self.nba.find_team_by_name(home_team_name)
        away_team = self.nba.find_team_by_name(away_team_name)

        stat_home_prob = None
        stat_away_prob = None

        if home_team and away_team:
            home_win_rate = self.nba.calculate_team_win_rate(home_team["id"])
            away_win_rate = self.nba.calculate_team_win_rate(away_team["id"])
            # Normalize to a probability (simple relative strength)
            total = home_win_rate + away_win_rate
            if total > 0:
                stat_home_prob = round(home_win_rate / total, 4)
                stat_away_prob = round(away_win_rate / total, 4)

        # --- Edge detection ---
        edge, recommendation = self._calculate_edge(
            poly_home_prob, stat_home_prob, home_team_name, away_team_name
        )

        return {
            "game": f"{home_team_name} vs {away_team_name}",
            "market_question": odds.get("market_question"),
            "condition_id": odds.get("condition_id"),
            "game_start_time": odds.get("game_start_time"),
            "polymarket": {
                "home_win_prob": poly_home_prob,
                "away_win_prob": poly_away_prob,
                "outcomes": outcomes,
                "accepting_orders": odds.get("accepting_orders"),
            },
            "statistical": {
                "home_win_prob": stat_home_prob,
                "away_win_prob": stat_away_prob,
                "note": "Based on last 10 games win rate",
            },
            "edge_pct": edge,
            "recommendation": recommendation,
        }

    def _find_team_probability(self, outcomes: Dict, team_name: str) -> Optional[float]:
        """Match a team name to its Polymarket outcome token probability."""
        team_lower = team_name.lower()
        for outcome_name, prob in outcomes.items():
            if any(word in outcome_name.lower() for word in team_lower.split()):
                return float(prob)
        # Fallback: return first outcome probability
        if outcomes:
            return float(list(outcomes.values())[0])
        return None

    def _calculate_edge(
        self,
        poly_prob: Optional[float],
        stat_prob: Optional[float],
        home_team: str,
        away_team: str,
    ) -> Tuple[Optional[float], str]:
        """
        Calculate the edge between Polymarket pricing and statistical probability.
        A positive edge means the market is underpricing the home team.
        """
        if poly_prob is None or stat_prob is None:
            return None, "Insufficient data for recommendation"

        edge = round(stat_prob - poly_prob, 4)
        edge_pct = round(edge * 100, 2)

        if edge > 0.05:
            recommendation = (
                f"POTENTIAL VALUE: Market underprices {home_team} by ~{edge_pct}%. "
                f"Stats suggest {int(stat_prob*100)}% win prob vs market's {int(poly_prob*100)}%."
            )
        elif edge < -0.05:
            recommendation = (
                f"POTENTIAL VALUE: Market underprices {away_team} by ~{abs(edge_pct)}%. "
                f"Stats suggest {int((1-stat_prob)*100)}% win prob vs market's {int((1-poly_prob)*100)}%."
            )
        else:
            recommendation = (
                f"FAIR PRICED: Market and stats are aligned within 5%. "
                f"No strong edge detected."
            )

        return edge_pct, recommendation

    def scan_todays_games(self) -> list:
        """
        Scan all of today's NBA games and return predictions for each.
        """
        print("Fetching today's NBA games...")
        games = self.nba.get_todays_games()

        if not games:
            print("No NBA games scheduled today.")
            return []

        results = []
        for game in games:
            home = game.get("home_team", {}).get("full_name", "")
            away = game.get("visitor_team", {}).get("full_name", "")
            if home and away:
                result = self.predict_game(home, away)
                results.append(result)

        return results

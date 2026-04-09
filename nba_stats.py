import os
import requests
from typing import List, Dict, Optional
from datetime import date
from dotenv import load_dotenv

load_dotenv()

# BallDontLie is a free NBA stats API — no API key required
NBA_API_BASE = os.getenv("NBA_API_BASE_URL", "https://api.balldontlie.io/v1")


class NBAStatsFetcher:
    def __init__(self):
        self.base_url = NBA_API_BASE
        self.headers = {"Content-Type": "application/json"}

    def get_todays_games(self) -> List[Dict]:
        """Fetch all NBA games scheduled for today."""
        today = date.today().isoformat()
        return self.get_games_by_date(today)

    def get_games_by_date(self, game_date: str) -> List[Dict]:
        """
        Fetch NBA games for a specific date.
        Args:
            game_date: ISO date string e.g. '2024-04-08'
        """
        try:
            url = f"{self.base_url}/games"
            params = {"dates[]": game_date, "per_page": 100}
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching games for {game_date}: {e}")
            return []

    def get_team_season_stats(self, team_id: int, season: int = 2023) -> Dict:
        """
        Get season averages for all players on a team.
        Uses these to estimate team offensive/defensive strength.
        """
        try:
            url = f"{self.base_url}/season_averages"
            # First get players on the team
            players = self.get_team_players(team_id)
            player_ids = [p["id"] for p in players[:15]]  # cap at 15 (roster size)

            if not player_ids:
                return {}

            params = {"season": season}
            for pid in player_ids:
                params.setdefault("player_ids[]", [])
                params["player_ids[]"].append(pid)  # type: ignore

            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return {"players": data.get("data", []), "team_id": team_id}
        except requests.exceptions.RequestException as e:
            print(f"Error fetching season stats for team {team_id}: {e}")
            return {}

    def get_team_players(self, team_id: int) -> List[Dict]:
        """Get active players for a team."""
        try:
            url = f"{self.base_url}/players"
            params = {"team_ids[]": team_id, "per_page": 100}
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json().get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching players for team {team_id}: {e}")
            return []

    def get_team_recent_games(self, team_id: int, last_n: int = 10) -> List[Dict]:
        """Get the last N completed games for a team."""
        try:
            url = f"{self.base_url}/games"
            params = {"team_ids[]": team_id, "per_page": last_n, "seasons[]": 2023}
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            games = data.get("data", [])
            # Filter to completed games only
            completed = [g for g in games if g.get("status") == "Final"]
            return completed[-last_n:]
        except requests.exceptions.RequestException as e:
            print(f"Error fetching recent games for team {team_id}: {e}")
            return []

    def calculate_team_win_rate(self, team_id: int, last_n: int = 10) -> float:
        """
        Calculate a team's win rate over their last N games.
        Returns a float between 0.0 and 1.0.
        """
        games = self.get_team_recent_games(team_id, last_n)
        if not games:
            return 0.5  # default to 50% if no data

        wins = 0
        for game in games:
            home_team = game.get("home_team", {})
            visitor_team = game.get("visitor_team", {})
            home_score = game.get("home_team_score", 0)
            visitor_score = game.get("visitor_team_score", 0)

            if home_team.get("id") == team_id and home_score > visitor_score:
                wins += 1
            elif visitor_team.get("id") == team_id and visitor_score > home_score:
                wins += 1

        return wins / len(games)

    def get_all_teams(self) -> List[Dict]:
        """Get all NBA teams."""
        try:
            url = f"{self.base_url}/teams"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json().get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching teams: {e}")
            return []

    def find_team_by_name(self, name: str) -> Optional[Dict]:
        """Find a team by full name, city, or abbreviation."""
        teams = self.get_all_teams()
        name_lower = name.lower()
        for team in teams:
            if (name_lower in team.get("full_name", "").lower() or
                    name_lower in team.get("city", "").lower() or
                    name_lower in team.get("name", "").lower() or
                    name_lower == team.get("abbreviation", "").lower()):
                return team
        return None

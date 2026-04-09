# nba-polymarket-predictor

NBA game predictions using Polymarket implied odds vs statistical win rates.

## What it does

This agent compares two signals for every NBA game:

1. **Polymarket implied probability** — the crowd's real-money prediction for who wins
2. **Statistical win rate** — each team's actual win rate over their last 10 games

When there's a meaningful gap between the two (>5%), it flags the game as potentially mispriced.

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/kiyanete-code/nba-polymarket-predictor.git
cd nba-polymarket-predictor

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env if needed (no keys required for read-only market data)
```

## Usage

```bash
# Scan all of today's NBA games
python main.py

# Analyze a specific matchup
python main.py --home "Los Angeles Lakers" --away "Golden State Warriors"

# Output raw JSON
python main.py --json
```

## Example output

```
============================================================
  Los Angeles Lakers vs Golden State Warriors
  Start: 2024-04-08T19:30:00Z
============================================================

  Polymarket Odds:
    Lakers: 54.0%
    Warriors: 46.0%

  Statistical Win Rates (last 10 games):
    Los Angeles Lakers: 61.3%
    Golden State Warriors: 38.7%

  Edge: +7.3%

  Recommendation: POTENTIAL VALUE: Market underprices Los Angeles Lakers
    by ~7.3%. Stats suggest 61% win prob vs market's 54%.
```

## Project structure

```
nba-polymarket-predictor/
├── main.py              # Entry point — run predictions from CLI
├── predictor.py         # Core logic: compares Polymarket vs stats
├── polymarket_data.py   # Fetches NBA markets and prices from Polymarket CLOB API
├── nba_stats.py         # Fetches team stats and game data from BallDontLie API
├── requirements.txt
├── .env.example         # Template for environment variables
└── .gitignore
```

## APIs used

| API | Auth required | Purpose |
|-----|---------------|---------|
| [Polymarket CLOB API](https://docs.polymarket.com) | No (read-only) | NBA market odds |
| [BallDontLie](https://www.balldontlie.io) | No | NBA game stats |

## Disclaimer

This tool is for educational and research purposes. Prediction markets involve financial risk. Always do your own research before placing any bets.

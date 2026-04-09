#!/usr/bin/env python3
"""
NBA Polymarket Predictor
========================
Compares Polymarket implied win probabilities against NBA statistical
win rates to surface potentially mispriced prediction markets.

Usage:
    # Scan today's games automatically
    python main.py

    # Predict a specific game
    python main.py --home "Los Angeles Lakers" --away "Golden State Warriors"
"""

import argparse
import json
from predictor import NBAPredictor


def print_prediction(pred: dict):
    """Pretty-print a single game prediction."""
    if "error" in pred:
        print(f"  Error: {pred['error']}")
        return

    print(f"\n{'='*60}")
    print(f"  {pred['game']}")
    print(f"  {pred.get('market_question', 'N/A')}")
    print(f"  Start: {pred.get('game_start_time', 'N/A')}")
    print(f"{'='*60}")

    poly = pred.get("polymarket", {})
    stat = pred.get("statistical", {})

    print(f"\n  Polymarket Odds:")
    for outcome, prob in poly.get("outcomes", {}).items():
        print(f"    {outcome}: {round(float(prob)*100, 1)}%")

    print(f"\n  Statistical Win Rates (last 10 games):")
    if stat.get("home_win_prob") is not None:
        home, away = pred["game"].split(" vs ")
        print(f"    {home.strip()}: {round(stat['home_win_prob']*100, 1)}%")
        print(f"    {away.strip()}: {round(stat['away_win_prob']*100, 1)}%")
    else:
        print("    No statistical data available")

    edge = pred.get("edge_pct")
    if edge is not None:
        print(f"\n  Edge: {edge:+.1f}%")
    print(f"\n  Recommendation: {pred.get('recommendation', 'N/A')}")
    print(f"  Accepting Orders: {poly.get('accepting_orders', 'N/A')}")
    print(f"  Condition ID: {pred.get('condition_id', 'N/A')}")


def main():
    parser = argparse.ArgumentParser(description="NBA Polymarket Predictor")
    parser.add_argument("--home", type=str, help="Home team name (e.g. 'Los Angeles Lakers')")
    parser.add_argument("--away", type=str, help="Away team name (e.g. 'Golden State Warriors')")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    predictor = NBAPredictor()

    if args.home and args.away:
        # Single game mode
        pred = predictor.predict_game(args.home, args.away)
        if args.json:
            print(json.dumps(pred, indent=2))
        else:
            print_prediction(pred)
    else:
        # Scan today's games
        print("Scanning today's NBA games on Polymarket...\n")
        results = predictor.scan_todays_games()

        if not results:
            print("No predictions generated. Try specifying --home and --away manually.")
            return

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"\nFound {len(results)} game(s) to analyze:")
            for pred in results:
                print_prediction(pred)

        # Summary: highlight best edges
        actionable = [r for r in results if r.get("edge_pct") and abs(r["edge_pct"]) > 5]
        if actionable:
            print(f"\n{'='*60}")
            print(f"  TOP EDGES (>5%): {len(actionable)} game(s)")
            for r in sorted(actionable, key=lambda x: abs(x.get("edge_pct", 0)), reverse=True):
                print(f"  - {r['game']}: {r.get('edge_pct', 0):+.1f}% edge")


if __name__ == "__main__":
    main()

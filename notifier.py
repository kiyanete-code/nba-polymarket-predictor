import os
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()


class TelegramNotifier:
    """
    Sends Telegram alerts for NBA Polymarket events.

    Required .env variables:
        TELEGRAM_BOT_TOKEN   — from @BotFather
        TELEGRAM_CHAT_ID     — your personal chat ID
    """

    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.base_url = f"https://api.telegram.org/bot{self.token}"

        if not self.token or not self.chat_id:
            raise EnvironmentError(
                "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env"
            )

    def send(self, message: str, silent: bool = False) -> bool:
        """Send a plain text message to your Telegram chat."""
        try:
            resp = requests.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                    "disable_notification": silent,
                },
                timeout=10,
            )
            resp.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Telegram send failed: {e}")
            return False

    def alert_edge_detected(self, prediction: Dict) -> bool:
        """
        Alert when a market pricing edge > 5% is detected.
        """
        edge = prediction.get("edge_pct", 0)
        game = prediction.get("game", "Unknown game")
        poly = prediction.get("polymarket", {})
        stat = prediction.get("statistical", {})
        condition_id = prediction.get("condition_id", "")
        start_time = prediction.get("game_start_time", "TBD")

        # Format start time
        try:
            dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            start_fmt = dt.strftime("%b %d, %I:%M %p UTC")
        except Exception:
            start_fmt = start_time

        direction = "📈" if edge > 0 else "📉"
        home, away = game.split(" vs ") if " vs " in game else (game, "")

        msg = (
            f"{direction} <b>Edge Detected — {abs(edge):.1f}%</b>\n\n"
            f"🏀 <b>{game}</b>\n"
            f"🕐 {start_fmt}\n\n"
            f"<b>Polymarket odds:</b>\n"
        )
        for outcome, prob in poly.get("outcomes", {}).items():
            msg += f"  {outcome}: {int(float(prob)*100)}%\n"

        msg += f"\n<b>Statistical win rate (last 10 games):</b>\n"
        if stat.get("home_win_prob") is not None:
            msg += f"  {home.strip()}: {int(stat['home_win_prob']*100)}%\n"
            msg += f"  {away.strip()}: {int(stat['away_win_prob']*100)}%\n"

        msg += f"\n💡 {prediction.get('recommendation', '')}"

        if condition_id:
            msg += f"\n\n🔗 <a href='https://polymarket.com/event/{condition_id}'>View on Polymarket</a>"

        return self.send(msg)

    def alert_new_nba_market(self, market: Dict) -> bool:
        """
        Alert when a new NBA game market goes live on Polymarket.
        """
        question = market.get("question", "Unknown")
        condition_id = market.get("condition_id", "")
        start_time = market.get("game_start_time", "TBD")
        tokens = market.get("tokens", [])

        try:
            dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            start_fmt = dt.strftime("%b %d, %I:%M %p UTC")
        except Exception:
            start_fmt = start_time

        msg = (
            f"🆕 <b>New NBA Market Live</b>\n\n"
            f"🏀 {question}\n"
            f"🕐 {start_fmt}\n\n"
            f"<b>Current odds:</b>\n"
        )
        for token in tokens:
            outcome = token.get("outcome", "")
            price = float(token.get("price", 0))
            msg += f"  {outcome}: {int(price*100)}%\n"

        if condition_id:
            msg += f"\n🔗 <a href='https://polymarket.com/event/{condition_id}'>Trade on Polymarket</a>"

        return self.send(msg)

    def alert_order_placed(self, order: Dict, game: str = "") -> bool:
        """
        Alert when an order is placed or cancelled.
        """
        if order.get("dry_run"):
            return False  # Don't alert on dry runs

        side = order.get("side", "BUY")
        price = order.get("price", 0)
        size = order.get("size", 0)
        token_id = order.get("tokenID", order.get("token_id", ""))[:12] + "..."
        emoji = "🟢" if side == "BUY" else "🔴"

        msg = (
            f"{emoji} <b>Order Placed</b>\n\n"
            f"{'🏀 ' + game + chr(10) if game else ''}"
            f"Side:   <b>{side}</b>\n"
            f"Price:  {price} ({int(float(price)*100)}¢)\n"
            f"Size:   {size} shares\n"
            f"Cost:   ~${round(float(price)*float(size), 2)} USDC\n"
            f"Token:  {token_id}"
        )
        return self.send(msg)

    def alert_order_cancelled(self, order_id: str) -> bool:
        """Alert when an order is cancelled."""
        msg = f"🚫 <b>Order Cancelled</b>\n\nOrder ID: <code>{order_id}</code>"
        return self.send(msg)

    def send_daily_summary(self, predictions: List[Dict]) -> bool:
        """
        Morning digest of today's NBA games with Polymarket odds and edges.
        """
        today = datetime.utcnow().strftime("%A, %b %d")
        total = len(predictions)
        edges = [p for p in predictions if p.get("edge_pct") and abs(p["edge_pct"]) > 5]

        msg = (
            f"☀️ <b>NBA Polymarket Daily Briefing</b>\n"
            f"📅 {today} UTC\n\n"
            f"Games today: <b>{total}</b>\n"
            f"Edges found (>5%): <b>{len(edges)}</b>\n"
        )

        if edges:
            msg += "\n<b>🔥 Top Edges:</b>\n"
            for p in sorted(edges, key=lambda x: abs(x.get("edge_pct", 0)), reverse=True)[:5]:
                game = p.get("game", "")
                edge = p.get("edge_pct", 0)
                accepting = p.get("polymarket", {}).get("accepting_orders", False)
                status = "✅ Open" if accepting else "⛔ Closed"
                msg += f"  • {game}: {edge:+.1f}% {status}\n"

        if not predictions:
            msg += "\nNo NBA games scheduled today."

        msg += "\n\n<i>Run python main.py for full analysis</i>"
        return self.send(msg)

    @staticmethod
    def get_chat_id(token: str) -> Optional[str]:
        """
        Helper to find your chat ID after you've sent the bot a message.
        Call this once during setup.
        """
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                timeout=10,
            )
            data = resp.json()
            updates = data.get("result", [])
            if updates:
                chat_id = str(updates[-1]["message"]["chat"]["id"])
                print(f"Your Chat ID: {chat_id}")
                return chat_id
            else:
                print("No messages found. Send any message to your bot first, then run this again.")
                return None
        except Exception as e:
            print(f"Error fetching chat ID: {e}")
            return None

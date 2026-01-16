"""
terminal_blackjack_sql_accuracy.py

Terminal Blackjack that tracks player's Hit/Stand accuracy vs a MySQL chart table.

Requires:
  pip install mysql-connector-python

Expected tables (MySQL):
  bj_chart(chart_id PK, name, notes)
  bj_hit_stand(chart_id, hand_kind, player_total, dealer_upcard, action)

Where bj_hit_stand.action is 'H' or 'S'
and dealer_upcard is one of: '2','3','4','5','6','7','8','9','10','A'
and hand_kind is 'HARD' or 'SOFT'

Notes:
- If the chart doesn't have a row for a situation (e.g., soft 12), that decision is "skipped" and not counted.
- This is hit/stand only (no split/double/surrender).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict

import mysql.connector
from mysql.connector import Error as MySQLError


# ----------------------------
# CONFIG: set these to your DB
# ----------------------------
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "YOUR_PASSWORD_HERE",
    "database": "blackjack",  # the DB where you created bj_chart/bj_hit_stand
    "port": 3306,
}

CHART_ID = 1  # which chart_id to use from bj_chart

NUM_DECKS = 1
DEALER_HITS_SOFT_17 = False  # typical rules vary


# ----------------------------
# Card / Deck / Hand
# ----------------------------
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = ["♠", "♥", "♦", "♣"]
RANK_VALUE = {
    "A": 11,
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 10, "Q": 10, "K": 10
}


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    @property
    def value(self) -> int:
        return RANK_VALUE[self.rank]

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"


class Deck:
    def __init__(self, num_decks: int = 1) -> None:
        self.num_decks = num_decks
        self.cards: List[Card] = []
        self._build_and_shuffle()

    def _build_and_shuffle(self) -> None:
        self.cards = [Card(rank, suit) for _ in range(self.num_decks) for suit in SUITS for rank in RANKS]
        random.shuffle(self.cards)

    def draw(self) -> Card:
        if not self.cards:
            self._build_and_shuffle()
        return self.cards.pop()


class Hand:
    def __init__(self) -> None:
        self.cards: List[Card] = []

    def add(self, card: Card) -> None:
        self.cards.append(card)

    def totals(self) -> Tuple[int, bool]:
        """
        Returns (best_total, is_soft)
        is_soft=True means at least one Ace is counted as 11 in the best_total.
        """
        total = sum(c.value for c in self.cards)
        aces = sum(1 for c in self.cards if c.rank == "A")

        # Convert Aces from 11 to 1 as needed to avoid busting
        conversions = 0
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
            conversions += 1

        total_aces = sum(1 for c in self.cards if c.rank == "A")
        # If there is at least one ace not converted, it's "soft"
        is_soft = (total_aces - conversions) > 0 and total <= 21

        return total, is_soft

    def is_blackjack(self) -> bool:
        return len(self.cards) == 2 and self.totals()[0] == 21

    def is_bust(self) -> bool:
        return self.totals()[0] > 21

    def __str__(self) -> str:
        return " ".join(str(c) for c in self.cards)


# ----------------------------
# MySQL chart lookup
# ----------------------------
def dealer_upcard_key(card: Card) -> str:
    """Convert dealer upcard to the key used in the SQL table."""
    if card.rank in ("J", "Q", "K", "10"):
        return "10"
    return "A" if card.rank == "A" else card.rank


def hand_kind_and_total(player_hand: Hand) -> Tuple[str, int]:
    """Return (hand_kind, player_total) as expected by the SQL chart."""
    total, is_soft = player_hand.totals()
    return ("SOFT" if is_soft else "HARD"), total


def get_recommended_action(
    cursor,
    chart_id: int,
    hand_kind: str,
    player_total: int,
    dealer_up: str
) -> Optional[str]:
    """
    Returns "hit" or "stand" based on bj_hit_stand, or None if no row exists.
    """
    sql = """
      SELECT action
      FROM bj_hit_stand
      WHERE chart_id = %s
        AND hand_kind = %s
        AND player_total = %s
        AND dealer_upcard = %s
      LIMIT 1
    """
    cursor.execute(sql, (chart_id, hand_kind, player_total, dealer_up))
    row = cursor.fetchone()
    if not row:
        return None
    return "hit" if row[0] == "H" else "stand"


# ----------------------------
# Game helpers
# ----------------------------
def dealer_should_hit(total: int, is_soft: bool) -> bool:
    if total < 17:
        return True
    if total > 17:
        return False
    # total == 17
    return DEALER_HITS_SOFT_17 and is_soft


def show_table(player: Hand, dealer: Hand, hide_dealer_hole: bool) -> None:
    if hide_dealer_hole:
        shown = str(dealer.cards[0]) + " ??"
        print(f"\nDealer: {shown}")
    else:
        d_total, d_soft = dealer.totals()
        soft_tag = " (soft)" if d_soft else ""
        print(f"\nDealer: {dealer}  => {d_total}{soft_tag}")

    p_total, p_soft = player.totals()
    soft_tag = " (soft)" if p_soft else ""
    print(f"Player: {player}  => {p_total}{soft_tag}\n")


def round_result(player: Hand, dealer: Hand) -> str:
    p_total, _ = player.totals()
    d_total, _ = dealer.totals()

    if player.is_bust():
        return "LOSE (you busted)"
    if dealer.is_bust():
        return "WIN (dealer busted)"
    if player.is_blackjack() and not dealer.is_blackjack():
        return "WIN (blackjack)"
    if dealer.is_blackjack() and not player.is_blackjack():
        return "LOSE (dealer blackjack)"
    if p_total > d_total:
        return "WIN"
    if p_total < d_total:
        return "LOSE"
    return "PUSH (tie)"


def prompt_action() -> str:
    """
    Returns: 'hit', 'stand', or 'quit'
    """
    while True:
        choice = input("Hit, Stand, or Quit? [h/s/q] ").strip().lower()
        if choice in ("h", "hit"):
            return "hit"
        if choice in ("s", "stand"):
            return "stand"
        if choice in ("q", "quit"):
            return "quit"
        print("Please type 'h' (hit), 's' (stand), or 'q' (quit).")


# ----------------------------
# Main gameplay with accuracy
# ----------------------------
def play_round(deck: Deck, cursor, stats: Dict[str, int]) -> bool:
    """
    Plays one round.
    Returns False if the user chose to quit during the round, True otherwise.
    """
    player = Hand()
    dealer = Hand()

    # Initial deal
    player.add(deck.draw())
    dealer.add(deck.draw())
    player.add(deck.draw())
    dealer.add(deck.draw())

    show_table(player, dealer, hide_dealer_hole=True)

    # Naturals end the round (no hit/stand decisions to count)
    if player.is_blackjack() or dealer.is_blackjack():
        show_table(player, dealer, hide_dealer_hole=False)
        print("Result:", round_result(player, dealer))
        return True

    # Player decisions
    while True:
        if player.is_bust():
            show_table(player, dealer, hide_dealer_hole=False)
            print("Result:", round_result(player, dealer))
            return True

        # Look up the "correct" action from SQL
        hk, pt = hand_kind_and_total(player)
        du = dealer_upcard_key(dealer.cards[0])
        recommended = get_recommended_action(cursor, CHART_ID, hk, pt, du)

        action = prompt_action()
        if action == "quit":
            return False  # end the whole game

        # Count accuracy only if chart has an entry
        if recommended is None:
            stats["skipped"] += 1
        else:
            stats["counted"] += 1
            if action == recommended:
                stats["correct"] += 1

        if action == "hit":
            player.add(deck.draw())
            show_table(player, dealer, hide_dealer_hole=True)
        else:
            break  # stand ends player turn

    # Dealer turn
    show_table(player, dealer, hide_dealer_hole=False)
    while True:
        d_total, d_soft = dealer.totals()
        if dealer_should_hit(d_total, d_soft):
            print("Dealer hits...")
            dealer.add(deck.draw())
            show_table(player, dealer, hide_dealer_hole=False)
            if dealer.is_bust():
                break
        else:
            print("Dealer stands.")
            break

    print("Result:", round_result(player, dealer))
    return True


def print_accuracy(stats: Dict[str, int]) -> None:
    counted = stats["counted"]
    correct = stats["correct"]
    skipped = stats["skipped"]

    print("\n=== Your Hit/Stand Accuracy ===")
    print(f"Counted decisions: {counted}")
    print(f"Correct decisions: {correct}")
    if counted > 0:
        pct = (correct / counted) * 100.0
        print(f"Accuracy: {pct:.1f}%")
    else:
        print("Accuracy: N/A (no decisions matched chart rows)")
    print(f"Skipped (no chart row found): {skipped}")
    print("================================\n")


def main() -> None:
    print("=== Terminal Blackjack (SQL Accuracy) ===")
    print(f"Using chart_id={CHART_ID} | Decks={NUM_DECKS} | Dealer hits soft 17={DEALER_HITS_SOFT_17}")

    # Stats
    stats = {"counted": 0, "correct": 0, "skipped": 0}

    # Connect to MySQL
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
    except MySQLError as e:
        print("\nCould not connect to MySQL.")
        print("Error:", e)
        print("\nFix DB_CONFIG at the top of the file (host/user/password/database/port).")
        return

    deck = Deck(NUM_DECKS)

    try:
        while True:
            keep_playing = play_round(deck, cursor, stats)
            if not keep_playing:
                print_accuracy(stats)
                print("Goodbye!")
                break

            again = input("\nPlay another round? [y/n] ").strip().lower()
            if again not in ("y", "yes"):
                print_accuracy(stats)
                print("Goodbye!")
                break
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()

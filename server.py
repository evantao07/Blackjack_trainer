# server.py
from flask import Flask, jsonify, request, session, send_from_directory
from datetime import timedelta

import blackjack  # imports your blackjack.py

app = Flask(__name__, static_folder=".")
app.secret_key = "change-this-to-any-random-string"
app.permanent_session_lifetime = timedelta(hours=6)

def ensure_db_ready():
    conn = blackjack.db_connect()
    cur = conn.cursor()
    chart_id = blackjack.get_or_create_chart(cur)
    if not blackjack.chart_has_rows(cur, chart_id):
        blackjack.seed_hit_stand_chart(cur, chart_id)
        conn.commit()
    return conn, cur, chart_id

def shoe_pop(deck):
    if not deck or len(deck) < 67:
        deck = blackjack.make_deck()
    card = deck.pop()
    return deck, card

def round_state(conn, cur, chart_id, db_session_id):
    player = session.get("player", [])
    dealer = session.get("dealer", [])
    hide_second = session.get("hide_dealer_second", True)

    s_total, s_correct = blackjack.get_accuracy(cur, db_session_id)
    a_total, a_correct = blackjack.get_all_time_accuracy(cur, chart_id)

    return {
        "player": player,
        "dealer": dealer,
        "hideDealerSecond": hide_second,
        "playerTotal": blackjack.hand_value(player) if player else 0,
        "dealerUpcard": blackjack.dealer_upcard_str(dealer[0]) if dealer else None,
        "dealerTotal": None if hide_second else (blackjack.hand_value(dealer) if dealer else 0),
        "handKind": ("SOFT" if blackjack.is_soft(player) else "HARD") if player else "HARD",
        "roundOver": session.get("round_over", True),
        "sessionAccuracy": {"total": s_total, "correct": s_correct},
        "allTimeAccuracy": {"total": a_total, "correct": a_correct},
    }

@app.get("/")
def home():
    return send_from_directory(".", "blackjack.html")

@app.get("/style.css")
def css():
    return send_from_directory(".", "style.css")

@app.get("/app.js")
def js():
    return send_from_directory(".", "app.js")

@app.get("/api/start")
def api_start():
    session.permanent = True
    conn, cur, chart_id = ensure_db_ready()

    if "db_session_id" not in session:
        db_session_id = blackjack.start_session(cur, chart_id)
        conn.commit()
        session["db_session_id"] = db_session_id
        session["chart_id"] = chart_id

    # start a new round
    deck = session.get("deck", blackjack.make_deck())
    deck, c1 = shoe_pop(deck)
    deck, c2 = shoe_pop(deck)
    deck, c3 = shoe_pop(deck)
    deck, c4 = shoe_pop(deck)

    session["player"] = [c1, c3]
    session["dealer"] = [c2, c4]
    session["deck"] = deck
    session["hide_dealer_second"] = True
    session["round_over"] = False

    data = round_state(conn, cur, chart_id, session["db_session_id"])
    cur.close(); conn.close()
    return jsonify(data)

@app.post("/api/new-round")
def api_new_round():
    conn, cur, chart_id = ensure_db_ready()
    db_session_id = session.get("db_session_id")
    if not db_session_id:
        db_session_id = blackjack.start_session(cur, chart_id)
        conn.commit()
        session["db_session_id"] = db_session_id
        session["chart_id"] = chart_id

    deck = session.get("deck", blackjack.make_deck())
    deck, c1 = shoe_pop(deck)
    deck, c2 = shoe_pop(deck)
    deck, c3 = shoe_pop(deck)
    deck, c4 = shoe_pop(deck)

    session["player"] = [c1, c3]
    session["dealer"] = [c2, c4]
    session["deck"] = deck
    session["hide_dealer_second"] = True
    session["round_over"] = False

    data = round_state(conn, cur, chart_id, db_session_id)
    cur.close(); conn.close()
    return jsonify(data)

@app.post("/api/action")
def api_action():
    action = request.json.get("action")  # "H" or "S"
    if action not in ("H", "S"):
        return jsonify({"error": "Invalid action"}), 400

    conn, cur, chart_id = ensure_db_ready()
    db_session_id = session.get("db_session_id")
    if not db_session_id:
        db_session_id = blackjack.start_session(cur, chart_id)
        conn.commit()
        session["db_session_id"] = db_session_id
        session["chart_id"] = chart_id

    if session.get("round_over", True):
        return jsonify({"error": "Round is over. Start a new round."}), 400

    player = session.get("player", [])
    dealer = session.get("dealer", [])
    deck = session.get("deck", blackjack.make_deck())

    # log correctness BEFORE changing hand
    kind = "SOFT" if blackjack.is_soft(player) else "HARD"
    total = blackjack.hand_value(player)
    up = blackjack.dealer_upcard_str(dealer[0])
    correct = blackjack.get_correct_action(cur, chart_id, kind, total, up)
    blackjack.log_decision(cur, db_session_id, kind, total, up, action, correct)
    conn.commit()

    # apply action
    if action == "H":
        deck, card = shoe_pop(deck)
        player.append(card)
        session["player"] = player
        session["deck"] = deck

        if blackjack.hand_value(player) > 21:
            session["round_over"] = True
            session["hide_dealer_second"] = False
    else:
        # stand: dealer plays
        session["hide_dealer_second"] = False
        while blackjack.hand_value(dealer) < 17:
            deck, card = shoe_pop(deck)
            dealer.append(card)
        session["dealer"] = dealer
        session["deck"] = deck
        session["round_over"] = True

    data = round_state(conn, cur, chart_id, db_session_id)
    data["lastDecision"] = action
    data["correctMove"] = correct

    cur.close(); conn.close()
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)

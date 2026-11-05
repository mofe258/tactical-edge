"""
sportybet.py — Live SportyBet Nigeria Slip Builder & Booking Code Generator
Matches model predictions to live SportyBet event IDs and generates real booking codes.
"""

import requests
from difflib import SequenceMatcher

SPORTY_BASE = "https://www.sportybet.com/api/ng"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
    "clientid": "web",
    "operid": "2",
    "platform": "web",
    "Origin": "https://www.sportybet.com",
    "Referer": "https://www.sportybet.com/ng/sport/football/"
}


def _clean_name(name):
    noise = ["fc", "sc", "cf", "ac", "bc", "afc", "fk", "sk", "vv", "aif", "kaa"]
    tokens = name.lower().replace("&", " ").replace("-", " ").split()
    filtered = [t for t in tokens if t not in noise]
    return " ".join(filtered) if filtered else name.lower().strip()


def _team_similarity(a, b):
    ca, cb = _clean_name(a), _clean_name(b)
    if ca in cb or cb in ca:
        return 0.92
    return SequenceMatcher(None, ca, cb).ratio()


def fetch_sportybet_live_events(pages=3):
    """
    Pulls upcoming/today's football matches with 1X2, Double Chance, Over/Under, and BTTS markets
    directly from SportyBet NG.
    """
    events = []
    seen = set()

    for page in range(1, pages + 1):
        url = (
            f"{SPORTY_BASE}/factsCenter/pcUpcomingEvents"
            f"?sportId=sr%3Asport%3A1&marketId=1%2C10%2C18%2C29%2C37"
            f"&pageSize=100&pageNum={page}&todayGames=true"
        )
        try:
            res = requests.get(url, headers=HEADERS, timeout=12)
            if res.status_code != 200:
                break
            body = res.json()
            if body.get("bizCode") != 10000:
                break

            tournaments = body.get("data", {}).get("tournaments", [])
            if not tournaments:
                break

            for tourn in tournaments:
                comp_name = tourn.get("name", "Football")
                for ev in tourn.get("events", []):
                    eid = ev.get("eventId")
                    if eid and eid not in seen:
                        seen.add(eid)
                        ev["_competition"] = comp_name
                        events.append(ev)
        except Exception:
            break

    return events


def _map_pick_to_sporty_selection(event, pick_text):
    """
    Finds the exact active marketId, specifier, and outcomeId on SportyBet
    matching our engine's prediction (with safe fallback if a combo market is locked).
    """
    markets = event.get("markets", [])
    pick_lower = pick_text.lower()

    def find_outcome(mkt_id, target_desc_list, spec=None):
        for m in markets:
            if str(m.get("id")) != str(mkt_id):
                continue
            m_spec = (m.get("specifier") or "").strip()
            if spec is not None and m_spec != spec:
                continue
            for out in m.get("outcomes", []):
                if out.get("isActive") != 1:
                    continue
                desc = (out.get("desc") or "").strip().lower()
                if any(td == desc or td in desc for td in target_desc_list):
                    return {
                        "eventId": event["eventId"],
                        "marketId": str(m["id"]),
                        "specifier": m.get("specifier") if m.get("specifier") else None,
                        "outcomeId": str(out["id"]),
                        "odds": float(out.get("odds", 1.20)),
                        "picked_label": f"{m.get('desc', 'Market')}: {out.get('desc', '')}"
                    }
        return None

    # 1. Match model pick to exact SportyBet market
    if "home & over 1.5" in pick_lower:
        sel = find_outcome("37", ["home & over 1.5"], spec="total=1.5")
        if sel:
            return sel
        sel = find_outcome("1", ["home"])
        if sel:
            return sel

    if "away & over 1.5" in pick_lower:
        sel = find_outcome("37", ["away & over 1.5"], spec="total=1.5")
        if sel:
            return sel
        sel = find_outcome("1", ["away"])
        if sel:
            return sel

    if "home or draw" in pick_lower or "1x" in pick_lower:
        sel = find_outcome("10", ["home or draw", "1x"])
        if sel:
            return sel

    if "draw or away" in pick_lower or "x2" in pick_lower:
        sel = find_outcome("10", ["draw or away", "x2"])
        if sel:
            return sel

    if "over 2.5" in pick_lower:
        sel = find_outcome("18", ["over 2.5"], spec="total=2.5")
        if sel:
            return sel

    if "under 3.5" in pick_lower:
        sel = find_outcome("18", ["under 3.5"], spec="total=3.5")
        if sel:
            return sel

    if "over 1.5" in pick_lower:
        sel = find_outcome("18", ["over 1.5"], spec="total=1.5")
        if sel:
            return sel

    # Safe high-probability fallback: Over 1.5 or 1X
    return (
        find_outcome("18", ["over 1.5"], spec="total=1.5")
        or find_outcome("10", ["home or draw", "1x"])
        or find_outcome("1", ["home"])
    )


def generate_sportybet_code(app_legs, target_odds=5.0, engine=None):
    """
    Matches app predictions against SportyBet's live catalog (and supplements from
    SportyBet's live matches if needed to hit target_odds), then books the slip on SportyBet.
    Returns: (share_code, booked_legs, final_odds, error_message)
    """
    live_events = fetch_sportybet_live_events(pages=3)
    if not live_events:
        return None, [], 0.0, (
            "Could not reach SportyBet Nigeria servers. Make sure you are running the app "
            "locally on a Nigerian internet connection (SportyBet blocks foreign cloud IPs)."
        )

    selections_payload = []
    booked_legs = []
    used_event_ids = set()
    running_odds = 1.0

    # Step 1: Match predictions from our app's accumulator legs first
    for leg in app_legs:
        best_ev = None
        best_score = 0.0
        for ev in live_events:
            if ev["eventId"] in used_event_ids:
                continue
            h_sim = _team_similarity(leg["home_team"], ev.get("homeTeamName", ""))
            a_sim = _team_similarity(leg["away_team"], ev.get("awayTeamName", ""))
            avg_sim = (h_sim + a_sim) / 2.0
            if h_sim >= 0.60 and a_sim >= 0.60 and avg_sim > best_score:
                best_score = avg_sim
                best_ev = ev

        if best_ev:
            mapped = _map_pick_to_sporty_selection(best_ev, leg["market_pick"])
            if mapped and mapped["odds"] > 1.05:
                used_event_ids.add(best_ev["eventId"])
                running_odds *= mapped["odds"]
                selections_payload.append({
                    "eventId": mapped["eventId"],
                    "marketId": mapped["marketId"],
                    "specifier": mapped["specifier"],
                    "outcomeId": mapped["outcomeId"]
                })
                booked_legs.append({
                    "match": f"{best_ev.get('homeTeamName')} vs {best_ev.get('awayTeamName')}",
                    "competition": best_ev.get("_competition", ""),
                    "pick": mapped["picked_label"],
                    "odds": mapped["odds"]
                })
                if running_odds >= target_odds:
                    break

    # Step 2: If target odds not yet reached, top up using live SportyBet games evaluated by our engine
    if running_odds < target_odds:
        for ev in live_events:
            if ev["eventId"] in used_event_ids:
                continue

            # Derive implied strength from SportyBet 1X2 odds to feed our engine pick logic
            h_odds, a_odds = 2.20, 3.10
            for m in ev.get("markets", []):
                if str(m.get("id")) == "1":
                    for o in m.get("outcomes", []):
                        if str(o.get("id")) == "1":
                            h_odds = float(o.get("odds", 2.20))
                        elif str(o.get("id")) == "3":
                            a_odds = float(o.get("odds", 3.10))

            if h_odds <= 1.65:
                desired_pick = "Home or Draw (1X)" if h_odds > 1.38 else "Home & Over 1.5"
            elif a_odds <= 1.70:
                desired_pick = "Draw or Away (X2)"
            else:
                desired_pick = "Over 1.5 Goals"

            mapped = _map_pick_to_sporty_selection(ev, desired_pick)
            if mapped and 1.14 <= mapped["odds"] <= 2.10:
                used_event_ids.add(ev["eventId"])
                running_odds *= mapped["odds"]
                selections_payload.append({
                    "eventId": mapped["eventId"],
                    "marketId": mapped["marketId"],
                    "specifier": mapped["specifier"],
                    "outcomeId": mapped["outcomeId"]
                })
                booked_legs.append({
                    "match": f"{ev.get('homeTeamName')} vs {ev.get('awayTeamName')}",
                    "competition": ev.get("_competition", ""),
                    "pick": mapped["picked_label"],
                    "odds": mapped["odds"]
                })
                if running_odds >= target_odds:
                    break

    if not selections_payload:
        return None, [], 0.0, "No active SportyBet markets matched right now."

    # Step 3: POST slip to SportyBet to receive official Share / Booking Code
    share_url = f"{SPORTY_BASE}/orders/share"
    try:
        resp = requests.post(share_url, json={"selections": selections_payload}, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            res_json = resp.json()
            if res_json.get("bizCode") == 10000 and res_json.get("data", {}).get("shareCode"):
                code = res_json["data"]["shareCode"]
                return code, booked_legs, round(running_odds, 2), None
            return None, booked_legs, round(running_odds, 2), f"SportyBet response: {res_json.get('message', 'Unable to book slip')}"
        return None, [], 0.0, f"SportyBet HTTP Error {resp.status_code} (Check Nigerian network connection)."
    except Exception as e:
        return None, [], 0.0, f"Connection error while booking code: {str(e)}"
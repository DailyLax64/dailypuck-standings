import urllib.request
import urllib.error
import urllib.parse
import json
import os
import re
import time
from datetime import datetime, timezone

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://gamesheetstats.com/shares/dashboard',
    'Origin': 'https://gamesheetstats.com'
}

def clean_name(val):
    return ' '.join(str(val or "").split()).strip()

def detect_cohort(text):
    """
    Identifies U11 AA and U14 AA.
    Since these Season IDs (15497, 15489, 15493) are already AA leagues,
    GameSheet labels the divisions as 'U11', 'U14', 'U11 AA', etc.
    """
    t = str(text or "").upper().strip()
    if not t:
        return None
    if re.search(r'\b(U[- ]?11|ATOM)\b', t):
        return "U11 AA"
    if re.search(r'\b(U[- ]?14|BANTAM)\b', t):
        return "U14 AA"
    return None

def fetch_json(url, retries=3):
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2.0)
                continue
            print(f"   WARNING: Request failed for {url}: {e}", flush=True)
            return None
    return None

# 1. Load Sources Configuration
if not os.path.exists("sources.json"):
    raise FileNotFoundError("sources.json not found.")

with open("sources.json", "r", encoding="utf-8") as f:
    sources_cfg = json.load(f)

leagues = sources_cfg.get("leagues", {})
all_standings = []
all_games = []
valid_finals = ["final", "official", "completed", "complete", "played", "finished", "2", "3"]

# 2. Extract League Data
for league_name, config in leagues.items():
    s_id = str(config.get("id", config)).strip()
    print(f"\nProcessing [{league_name}] (Season ID: {s_id})...", flush=True)

    # Step A: Fetch Standings
    standings_url = f"https://gamesheetstats.com/api/standings/{s_id}?"
    standings_data = fetch_json(standings_url)

    league_standings_count = 0
    if standings_data and "data" in standings_data:
        for div_group in standings_data["data"]:
            div_title = clean_name(div_group.get("title") or div_group.get("name") or "")
            cohort = detect_cohort(div_title)

            standings_rows = div_group.get("standings", [])
            for row in standings_rows:
                row_div = clean_name(row.get("division", {}).get("title") or "")
                effective_cohort = cohort or detect_cohort(row_div)
                if not effective_cohort:
                    continue

                t_info = row.get("team", {})
                st = row.get("stats", {})

                t_name = clean_name(t_info.get("title") or t_info.get("name") or row.get("team_name") or "")
                if not t_name:
                    continue

                all_standings.append({
                    "league": league_name,
                    "league_id": s_id,
                    "cohort": effective_cohort,
                    "team_id": str(t_info.get("id") or ""),
                    "team_name": t_name,
                    "gp": int(st.get("gp") or 0),
                    "w": int(st.get("w") or 0),
                    "l": int(st.get("l") or 0),
                    "t": int(st.get("t") or 0),
                    "pts": int(st.get("pts") or 0),
                    "gf": int(st.get("gf") or 0),
                    "ga": int(st.get("ga") or 0),
                    "diff": int(st.get("diff") or (int(st.get("gf") or 0) - int(st.get("ga") or 0))),
                    "pim": int(st.get("pim") or 0)
                })
                league_standings_count += 1

    print(f"   Standings rows collected: {league_standings_count}", flush=True)

    # Step B: Fetch Games (Completed & Scheduled)
    games_url = f"https://gamesheetstats.com/api/unified-games/{s_id}?filter[limit]=10000"
    games_data = fetch_json(games_url)

    raw_games = games_data if isinstance(games_data, list) else (
        games_data.get("games") or games_data.get("data") or []
    ) if isinstance(games_data, dict) else []

    league_game_count = 0
    for g in raw_games:
        gid = str(g.get("gameId") or g.get("id") or "")
        if not gid:
            continue

        visitor = g.get("visitor") or {}
        home = g.get("home") or {}
        g_div = clean_name(
            g.get("division", {}).get("title") or 
            visitor.get("division", {}).get("title") or 
            home.get("division", {}).get("title") or ""
        )
        cohort = detect_cohort(g_div)
        if not cohort:
            continue

        status_str = str(g.get("status") or "").strip().lower()
        is_final = status_str in valid_finals

        h_goals = int(home.get("goals") or g.get("homeGoals") or 0) if is_final else None
        v_goals = int(visitor.get("goals") or g.get("visitorGoals") or 0) if is_final else None

        all_games.append({
            "game_id": gid,
            "league": league_name,
            "league_id": s_id,
            "cohort": cohort,
            "date": g.get("date", ""),
            "time": g.get("time", ""),
            "status": "final" if is_final else "scheduled",
            "location": g.get("location") or g.get("arena") or "",
            "home_id": str(home.get("id") or ""),
            "home_name": clean_name(home.get("title") or home.get("name") or ""),
            "home_goals": h_goals,
            "visitor_id": str(visitor.get("id") or ""),
            "visitor_name": clean_name(visitor.get("title") or visitor.get("name") or ""),
            "visitor_goals": v_goals
        })
        league_game_count += 1

    print(f"   Games collected: {league_game_count}", flush=True)
    time.sleep(1.0)

# 3. Save Output Data
output = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "standings": all_standings,
    "games": all_games
}

with open("omha_raw_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print("\n" + "=" * 50, flush=True)
print(f" Total Standings Rows Collected: {len(all_standings)}", flush=True)
print(f" Total Games Collected:          {len(all_games)}", flush=True)
print(" Saved to omha_raw_data.json", flush=True)
print("=" * 50, flush=True)

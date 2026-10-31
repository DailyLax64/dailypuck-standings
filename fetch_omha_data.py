import urllib.request
import urllib.error
import json
import os
import re
import time
from datetime import datetime, timezone

# 1. API Headers & Optional Auth
FIREBASE_API_KEY = os.environ.get("GAMESHEET_FIREBASE_KEY", "").strip()
AUTH_GATEWAY_URL = "https://gateway-authserver-awy26srzoa-nn.a.run.app/auth/v4/tokens"
GAMESHEET_EMAIL = os.environ.get("GAMESHEET_EMAIL", "").strip()
GAMESHEET_PASSWORD = os.environ.get("GAMESHEET_PASSWORD", "").strip()
FALLBACK_AUTH = os.environ.get("GAMESHEET_AUTH", "").strip()

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://gamesheetstats.com/shares/dashboard',
    'Origin': 'https://gamesheetstats.com'
}

def authenticate_gamesheet(email, password):
    if not FIREBASE_API_KEY:
        return None
    try:
        fb_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
        payload = json.dumps({"email": email, "password": password, "returnSecureToken": True}).encode('utf-8')
        req = urllib.request.Request(fb_url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            fb_data = json.loads(resp.read().decode('utf-8'))
            id_token = fb_data.get("idToken")

        if not id_token:
            return None

        gw_req = urllib.request.Request(
            AUTH_GATEWAY_URL,
            headers={"Authorization": f"Bearer {id_token}", "Origin": "https://gamesheet.app"}
        )
        with urllib.request.urlopen(gw_req, timeout=15) as resp:
            gw_data = json.loads(resp.read().decode('utf-8'))
            return gw_data.get("access")
    except Exception as e:
        print(f"⚠️ Auth failed, attempting anonymous fetch: {e}")
        return None

token = authenticate_gamesheet(GAMESHEET_EMAIL, GAMESHEET_PASSWORD) if GAMESHEET_EMAIL else FALLBACK_AUTH
if token:
    headers['Authorization'] = f"Bearer {token}"
    headers['Cookie'] = f"__session={token}"

def clean_name(val):
    return ' '.join(str(val or "").split()).strip()

def detect_cohort(text):
    """Identifies if a string corresponds to U11 AA or U14 AA."""
    t = str(text or "").upper()
    if not re.search(r'\bAA\b', t):
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
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1.5)
                continue
            print(f"❌ Failed to fetch {url}: {e}")
            return None
    return None

# 2. Load Sources
if not os.path.exists("sources.json"):
    raise FileNotFoundError("sources.json not found.")

with open("sources.json", "r", encoding="utf-8") as f:
    sources_cfg = json.load(f)

leagues = sources_cfg.get("leagues", {})
all_standings = []
all_games = []
valid_finals = ["final", "official", "completed", "complete", "played", "finished", "2", "3"]

# 3. Pull Standings & Schedules
for league_name, config in leagues.items():
    s_id = str(config.get("id", config))
    print(f"\n📡 Processing [{league_name}] (ID: {s_id})...")

    # A. Fetch Standings
    standings_data = fetch_json(f"https://gamesheetstats.com/api/standings/{s_id}?")
    if standings_data and "data" in standings_data:
        for div_group in standings_data["data"]:
            div_title = clean_name(div_group.get("title") or div_group.get("name") or "")
            cohort = detect_cohort(div_title)
            
            for row in div_group.get("standings", []):
                row_div = clean_name(row.get("division", {}).get("title") or "")
                effective_cohort = cohort or detect_cohort(row_div)
                if not effective_cohort:
                    continue  # Only keep U11 AA and U14 AA

                t_info = row.get("team", {})
                st = row.get("stats", {})

                all_standings.append({
                    "league": league_name,
                    "league_id": s_id,
                    "cohort": effective_cohort,
                    "team_id": t_info.get("id"),
                    "team_name": clean_name(t_info.get("title") or t_info.get("name")),
                    "gp": int(st.get("gp") or 0),
                    "w": int(st.get("w") or 0),
                    "l": int(st.get("l") or 0),
                    "t": int(st.get("t") or 0),
                    "pts": int(st.get("pts") or 0),
                    "gf": int(st.get("gf") or 0),
                    "ga": int(st.get("ga") or 0),
                    "diff": int(st.get("diff") or 0),
                    "pim": int(st.get("pim") or 0)
                })

    # B. Fetch Games (Completed & Scheduled)
    games_data = fetch_json(f"https://gamesheetstats.com/api/unified-games/{s_id}?filter[limit]=10000")
    raw_games = games_data if isinstance(games_data, list) else (games_data.get("games") or games_data.get("data") or []) if isinstance(games_data, dict) else []

    for g in raw_games:
        gid = g.get("gameId")
        if not gid:
            continue

        visitor = g.get("visitor") or {}
        home = g.get("home") or {}
        g_div = clean_name(g.get("division", {}).get("title") or visitor.get("division", {}).get("title") or home.get("division", {}).get("title") or "")
        cohort = detect_cohort(g_div)

        if not cohort:
            continue

        status_str = str(g.get("status") or "").strip().lower()
        is_final = status_str in valid_finals

        h_goals = int(home.get("goals") or 0) if is_final else None
        v_goals = int(visitor.get("goals") or 0) if is_final else None

        all_games.append({
            "game_id": str(gid),
            "league": league_name,
            "league_id": s_id,
            "cohort": cohort,
            "date": g.get("date", ""),
            "time": g.get("time", ""),
            "status": "final" if is_final else "scheduled",
            "location": g.get("location", ""),
            "home_id": home.get("id"),
            "home_name": clean_name(home.get("title") or home.get("name")),
            "home_goals": h_goals,
            "visitor_id": visitor.get("id"),
            "visitor_name": clean_name(visitor.get("title") or visitor.get("name")),
            "visitor_goals": v_goals
        })

    time.sleep(0.5)

# 4. Save Extracted Data
output = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "standings": all_standings,
    "games": all_games
}

with open("omha_raw_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print("\n" + "=" * 50)
print(f" Standings Rows Collected: {len(all_standings)}")
print(f" Games Collected:          {len(all_games)}")
print(" Saved to omha_raw_data.json")
print("=" * 50)

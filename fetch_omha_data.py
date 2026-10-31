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
    'Referer': 'https://gamesheetstats.com/',
    'Origin': 'https://gamesheetstats.com'
}

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
            print(f"   ⚠️ Request error for {url}: {e}", flush=True)
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
    print(f"\n📡 Processing [{league_name}] (Season ID: {s_id})...", flush=True)

    # Step A: Discover all divisions for this season
    div_url = f"https://gamesheetstats.com/api/useSeasonDivisions/getDivisions/{s_id}"
    div_res = fetch_json(div_url)
    raw_divs = div_res if isinstance(div_res, list) else (div_res.get("data") or div_res.get("divisions") or []) if isinstance(div_res, dict) else []

    target_div_map = {}  # div_id -> cohort name
    for d in raw_divs:
        d_id = str(d.get("id") or d.get("division_id") or "")
        d_title = clean_name(d.get("title") or d.get("name") or "")
        cohort = detect_cohort(d_title)
        if cohort and d_id:
            target_div_map[d_id] = cohort
            print(f"   🎯 Found division: [{d_title}] -> {cohort} (ID: {d_id})", flush=True)

    if not target_div_map:
        print(f"   ⚠️ No U11 AA or U14 AA divisions detected in {league_name}.", flush=True)
        continue

    div_ids_str = ",".join(target_div_map.keys())

    # Step B: Pull Standings
    standings_url = f"https://gamesheetstats.com/api/useStandings/getDivisionStandings/{s_id}?filter[divisions]={div_ids_str}"
    standings_res = fetch_json(standings_url)
    raw_standings_groups = standings_res if isinstance(standings_res, list) else (standings_res.get("data") or standings_res.get("standings") or []) if isinstance(standings_res, dict) else []

    league_standings_count = 0
    for group in raw_standings_groups:
        g_div = group.get("division", {})
        g_div_id = str(g_div.get("id") or group.get("division_id") or "")
        cohort = target_div_map.get(g_div_id) or detect_cohort(g_div.get("title") or group.get("title") or "")
        if not cohort:
            continue

        team_rows = group.get("standings") or group.get("teams") or [group] if "team" in group or "stats" in group else []
        for row in team_rows:
            t_info = row.get("team", {}) if "team" in row else row
            st = row.get("stats", {}) if "stats" in row else row

            t_name = clean_name(t_info.get("title") or t_info.get("name") or row.get("team_name") or "")
            if not t_name:
                continue

            all_standings.append({
                "league": league_name,
                "league_id": s_id,
                "cohort": cohort,
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

    print(f"   📊 Standings collected: {league_standings_count}", flush=True)

    # Step C: Pull Full Schedule (Paginated)
    offset = 0
    limit = 250
    league_game_count = 0

    while True:
        sched_url = f"https://gamesheetstats.com/api/useSchedule/getSeasonSchedule/{s_id}?filter[divisions]={div_ids_str}&filter[offset]={offset}&filter[limit]={limit}"
        sched_res = fetch_json(sched_url)
        games_batch = sched_res if isinstance(sched_res, list) else (sched_res.get("data") or sched_res.get("games") or sched_res.get("schedule") or []) if isinstance(sched_res, dict) else []

        if not games_batch:
            break

        for g in games_batch:
            gid = str(g.get("gameId") or g.get("id") or "")
            if not gid:
                continue

            visitor = g.get("visitor") or {}
            home = g.get("home") or {}

            g_div_id = str(g.get("divisionId") or g.get("division_id") or g.get("division", {}).get("id") or "")
            g_div_title = clean_name(g.get("division", {}).get("title") or visitor.get("division", {}).get("title") or home.get("division", {}).get("title") or "")
            cohort = target_div_map.get(g_div_id) or detect_cohort(g_div_title)

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

        if len(games_batch) < limit:
            break
        offset += limit
        time.sleep(0.3)

    print(f"   🏒 Games collected: {league_game_count}", flush=True)
    time.sleep(0.5)

# 3. Save Output JSON
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

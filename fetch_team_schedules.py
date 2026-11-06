import json
import urllib.request
import re
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TORONTO_TZ = ZoneInfo("America/Toronto")

# Blacklist of known tournament games that adopted league bracket syntax
EXCLUDED_GAME_KEYS = {
    # (cohort, date, game_code)
    ("U11 AA", "2026-10-17", "U11AA-19"),  # Brampton vs Centre Wellington tournament matchup
}

def parse_dt(dt_str):
    """
    Parses iCal DTSTART strings and converts UTC (Z) timestamps 
    to local Eastern Time (America/Toronto).
    Example: '20261106T010000Z' (8:00 PM EST Nov 5) -> ('2026-11-05', '20:00')
    """
    if not dt_str:
        return "", ""
    s = str(dt_str).strip()

    # 1. UTC Timestamp ending in 'Z'
    if s.endswith("Z"):
        clean = re.sub(r'[^0-9T]', '', s)
        if "T" in clean:
            fmt = "%Y%m%dT%H%M%S" if len(clean) >= 15 else "%Y%m%dT%H%M"
            try:
                dt_utc = datetime.strptime(clean[:15], fmt).replace(tzinfo=timezone.utc)
                dt_local = dt_utc.astimezone(TORONTO_TZ)
                return dt_local.strftime("%Y-%m-%d"), dt_local.strftime("%H:%M")
            except Exception as e:
                pass

    # 2. Local or naive timestamp (no Z)
    clean = re.sub(r'[^0-9T]', '', s)
    date_part, time_part = "", ""
    if "T" in clean:
        d, t = clean.split("T", 1)
        if len(d) == 8:
            date_part = f"{d[0:4]}-{d[4:6]}-{d[6:8]}"
        if len(t) >= 4:
            time_part = f"{t[0:2]}:{t[2:4]}"
    elif len(clean) == 8:
        date_part = f"{clean[0:4]}-{clean[4:6]}-{clean[6:8]}"
    return date_part, time_part

def fetch_feed(url):
    url = url.replace("webcal://", "https://")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"   [!] Failed to fetch {url}: {e}", flush=True)
        return None

def build_team_resolver(master_teams):
    lookup = {}
    for cohort, teams in master_teams.items():
        lookup[cohort] = {}
        for team_name, meta in teams.items():
            league = meta.get("league")
            clean_k = re.sub(r'[^A-Z0-9]', '', team_name.upper())
            lookup[cohort][clean_k] = (team_name, league)
            for alias in meta.get("aliases", []):
                alias_k = re.sub(r'[^A-Z0-9]', '', alias.upper())
                lookup[cohort][alias_k] = (team_name, league)
    return lookup

def resolve_team(lookup, cohort, name):
    clean = re.sub(r'[^A-Z0-9]', '', str(name or '').upper())
    if clean in lookup.get(cohort, {}):
        return lookup[cohort][clean]
    for k, v in lookup.get(cohort, {}).items():
        if k in clean or clean in k:
            return v
    return None, None

def is_valid_league_code(league, code):
    c = str(code).upper()
    if league == "York-Simcoe":
        return bool(re.search(r'U\d{1,2}AA-RS', c))
    elif league in ["Tri-County", "Lakeshore"]:
        return bool(re.match(r'^U\d{1,2}AA-\d+$', c))
    return False

def main():
    with open("team_calendars.json", "r", encoding="utf-8") as f:
        calendars = json.load(f)

    with open("master_teams.json", "r", encoding="utf-8") as f:
        master_teams = json.load(f)

    resolver = build_team_resolver(master_teams)
    all_league_games = []
    seen_matchups = set()
    
    # Calculate local today string in Ontario Eastern Time
    today_str = datetime.now(TORONTO_TZ).strftime("%Y-%m-%d")

    for cohort, teams in calendars.items():
        print(f"\n📡 Processing cohort: {cohort}", flush=True)

        for source_team, feed_url in teams.items():
            if not feed_url or not feed_url.strip():
                continue

            content = fetch_feed(feed_url)
            if not content:
                continue

            events, curr = [], None
            for raw_line in content.splitlines():
                line = raw_line.strip()
                if line == "BEGIN:VEVENT":
                    curr = {}
                elif line == "END:VEVENT":
                    if curr: events.append(curr)
                    curr = None
                elif curr is not None and ":" in line:
                    k_part, v = line.split(":", 1)
                    k = k_part.split(";")[0].upper()
                    curr[k] = v.replace("\\n", " ").replace("\\,", ",")

            for ev in events:
                summary = ev.get("SUMMARY", "").strip()
                description = ev.get("DESCRIPTION", "").strip()
                dtstart = ev.get("DTSTART", "").strip()
                full_text = f"{summary} {description}"

                match = re.search(r'(?:vs\.?|@)\s+(.*?)\s*\[([A-Za-z0-9-]+)\]', full_text, re.IGNORECASE)
                if not match:
                    continue

                opp_raw = match.group(1).strip()
                game_code = match.group(2).strip()

                is_away = "@" in summary.split("[")[0] if "[" in summary else "@" in summary
                home_raw = opp_raw if is_away else source_team
                visitor_raw = source_team if is_away else opp_raw

                home_can, home_league = resolve_team(resolver, cohort, home_raw)
                visitor_can, visitor_league = resolve_team(resolver, cohort, visitor_raw)

                # Validation guardrails
                if not home_can or not visitor_can:
                    continue
                if home_league != visitor_league:
                    continue
                if not is_valid_league_code(home_league, game_code):
                    continue

                date_val, time_val = parse_dt(dtstart)

                # Tournament exclusion check
                if (cohort, date_val, game_code) in EXCLUDED_GAME_KEYS:
                    continue

                # Deduplication across home/away feeds
                matchup_key = (cohort, date_val, home_can, visitor_can)
                if matchup_key in seen_matchups:
                    continue
                seen_matchups.add(matchup_key)

                game_status = "played" if date_val < today_str else "scheduled"

                all_league_games.append({
                    "game_code": game_code,
                    "cohort": cohort,
                    "league": home_league,
                    "date": date_val,
                    "time": time_val,
                    "status": game_status,
                    "home": home_can,
                    "visitor": visitor_can,
                    "location": ev.get("LOCATION", "").strip()
                })

            time.sleep(0.3)

    all_league_games.sort(key=lambda x: (x["cohort"], x["date"], x["time"]))

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_season_games": len(all_league_games),
        "games": all_league_games
    }

    with open("full_season_games.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    played_cnt = sum(1 for g in all_league_games if g["status"] == "played")
    sched_cnt = sum(1 for g in all_league_games if g["status"] == "scheduled")
    print(f"\n✅ Total Season Games: {len(all_league_games)} (Played: {played_cnt}, Remaining: {sched_cnt})", flush=True)

if __name__ == "__main__":
    main()

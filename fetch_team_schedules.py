import json
import urllib.request
import re
import time
from datetime import datetime, timezone

def parse_dt(dt_str):
    clean = re.sub(r'[^0-9T]', '', dt_str or "")
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
    # Convert webcal:// to https://
    url = url.replace("webcal://", "https://")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"   [!] Failed to fetch {url}: {e}")
        return None

def main():
    with open("team_calendars.json", "r", encoding="utf-8") as f:
        calendars = json.load(f)

    with open("master_teams.json", "r", encoding="utf-8") as f:
        master_teams = json.load(f)

    all_future_games = []
    processed_game_codes = set() # For deduplication

    for cohort, teams in calendars.items():
        print(f"\n📡 Processing cohort: {cohort}")
        
        for team_name, feed_url in teams.items():
            if not feed_url or feed_url.strip() == "":
                continue
                
            print(f"   Fetching {team_name}...")
            content = fetch_feed(feed_url)
            if not content:
                continue

            # Parse iCal VEVENTs
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

            # Extract regular season games
            for ev in events:
                summary = ev.get("SUMMARY", "").strip()
                description = ev.get("DESCRIPTION", "").strip()
                dtstart = ev.get("DTSTART", "").strip()
                full_text = f"{summary} {description}"

                # Match official bracket codes (e.g. [U11AA-123] or [U14AA-RS-005])
                match = re.search(r'(?:vs\.?|@)\s+(.*?)\s*\[([A-Za-z0-9-]+)\]', full_text, re.IGNORECASE)
                if not match:
                    continue

                opp_raw = match.group(1).strip()
                game_code = match.group(2).strip()

                # Filter out pure integers (typically tournament games in Lakeshore/Tri-County)
                if game_code.isdigit():
                    continue

                # Deduplicate cross-team entries
                if game_code in processed_game_codes:
                    continue
                processed_game_codes.add(game_code)

                date_val, time_val = parse_dt(dtstart)
                
                # Check if the game is in the future
                if date_val < datetime.now(timezone.utc).strftime("%Y-%m-%d"):
                    continue

                is_away = "@" in summary.split("[")[0] if "[" in summary else "@" in summary
                home_team = opp_raw if is_away else team_name
                visitor_team = team_name if is_away else opp_raw

                all_future_games.append({
                    "game_code": game_code,
                    "cohort": cohort,
                    "date": date_val,
                    "time": time_val,
                    "home": home_team,
                    "visitor": visitor_team,
                    "location": ev.get("LOCATION", "").strip()
                })
            time.sleep(0.5)

    all_future_games.sort(key=lambda x: (x["date"], x["time"]))

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "scheduled_games": all_future_games
    }

    with open("future_games.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Extracted {len(all_future_games)} future league games across all teams.")
    print("Saved to future_games.json")

if __name__ == "__main__":
    main()

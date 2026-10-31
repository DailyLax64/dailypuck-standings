import json
import os
import re
import urllib.request

LEAGUES = {
    "Tri-County": "15497",
    "York-Simcoe": "15489",
    "Lakeshore": "15493"
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://gamesheetstats.com/shares/dashboard',
    'Origin': 'https://gamesheetstats.com'
}

def clean_name(val):
    return ' '.join(str(val or "").split()).strip()

def detect_cohort(text):
    t = str(text or "").upper()
    if re.search(r'\b(U[- ]?11|ATOM)\b', t):
        return "U11 AA"
    if re.search(r'\b(U[- ]?14|BANTAM)\b', t):
        return "U14 AA"
    return None

def build_master():
    master_path = "master_teams.json"
    if os.path.exists(master_path):
        with open(master_path, "r", encoding="utf-8") as f:
            master_db = json.load(f)
    else:
        master_db = {"U11 AA": {}, "U14 AA": {}}

    found_count = 0

    for league_name, s_id in LEAGUES.items():
        print(f"📡 Querying GameSheet for {league_name} (ID: {s_id})...")
        url = f"https://gamesheetstats.com/api/standings/{s_id}?"
        req = urllib.request.Request(url, headers=HEADERS)

        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            print(f"❌ Failed to fetch standings for {league_name}: {e}")
            continue

        for group in data.get("data", []):
            group_title = clean_name(group.get("title") or group.get("name") or "")
            cohort = detect_cohort(group_title)

            for row in group.get("standings", []):
                row_div = clean_name(row.get("division", {}).get("title") or "")
                effective_cohort = cohort or detect_cohort(row_div)

                if not effective_cohort:
                    continue

                t_info = row.get("team", {})
                raw_team_name = clean_name(t_info.get("title") or t_info.get("name") or "")
                if not raw_team_name:
                    continue

                # Generate clean aliases to help MHR matching
                base_name = re.sub(r'\b(U\d{1,2}|AA|A|BB)\b', '', raw_team_name, flags=re.IGNORECASE).strip()
                base_name = ' '.join(base_name.split())
                aliases = []
                if base_name and base_name.upper() != raw_team_name.upper():
                    aliases.append(base_name)

                if raw_team_name not in master_db[effective_cohort]:
                    master_db[effective_cohort][raw_team_name] = {
                        "aliases": aliases,
                        "league": league_name,
                        "mhr_rank": "n/a",
                        "mhr_rating": 0.0,
                        "mhr_record": "",
                        "mhr_agd": "0.00",
                        "mhr_sched": "0.00"
                    }
                    found_count += 1
                    print(f"   ➕ [{effective_cohort}] Added: {raw_team_name} ({league_name})")

    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(master_db, f, indent=2)

    print(f"\n🎉 Successfully generated {master_path}!")
    print(f"U11 AA Teams: {len(master_db['U11 AA'])}")
    print(f"U14 AA Teams: {len(master_db['U14 AA'])}")

if __name__ == "__main__":
    build_master()

import json
import re
from collections import defaultdict

with open("master_teams.json", "r", encoding="utf-8") as f:
    master_db = json.load(f)

with open("full_season_games.json", "r", encoding="utf-8") as f:
    season_data = json.load(f)

try:
    with open("omha_raw_data.json", "r", encoding="utf-8") as f:
        omha_data = json.load(f)
except Exception:
    omha_data = {"games": [], "standings": []}

games = season_data.get("games", [])

# Tally Played vs Remaining by team
played_by_team = defaultdict(int)
rem_by_team = defaultdict(int)

for g in games:
    cohort = g.get("cohort")
    h = g.get("home")
    v = g.get("visitor")
    st = g.get("status")

    if st == "played":
        played_by_team[(cohort, h)] += 1
        played_by_team[(cohort, v)] += 1
    else:
        rem_by_team[(cohort, h)] += 1
        rem_by_team[(cohort, v)] += 1

# Expected regular season game targets
LEAGUE_TARGETS = {
    "Tri-County": 26,
    "Lakeshore": 24,
    "York-Simcoe": 26
}

print("=" * 85)
print(f"FULL REGULAR SEASON SCHEDULE RECONCILIATION ({len(games)} Total Games)")
print("=" * 85)

for cohort in ["U11 AA", "U14 AA"]:
    for league in ["Tri-County", "York-Simcoe", "Lakeshore"]:
        target = LEAGUE_TARGETS.get(league, 26)
        print(f"\n🏒 [{cohort}] {league} (Target: {target} Total Games per Team)")
        print(f"{'Team Name':<32} | {'Played':<6} | {'Rem':<6} | {'Total':<6} | {'Status'}")
        print("-" * 75)

        for team_name, meta in sorted(master_db.get(cohort, {}).items()):
            if meta.get("league") != league:
                continue

            gp = played_by_team.get((cohort, team_name), 0)
            rem = rem_by_team.get((cohort, team_name), 0)
            tot = gp + rem

            status_str = "✅ Verified" if tot == target else f"⚠️ Diff ({tot - target:+d})"
            print(f"{team_name[:30]:<32} | {gp:<6} | {rem:<6} | {tot:<6} | {status_str}")

# Cross-reference with GameSheet completed games
print("\n" + "=" * 85)
print("GAMESHEET CROSS-REFERENCE CHECK")
print("=" * 85)
gs_final_games = [g for g in omha_data.get("games", []) if g.get("status") == "final"]
cal_played_games = [g for g in games if g.get("status") == "played"]
print(f"GameSheet Official Final Games:   {len(gs_final_games)}")
print(f"Calendar Season Games to Date:    {len(cal_played_games)}")

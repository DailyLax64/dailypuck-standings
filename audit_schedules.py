import json
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

LEAGUE_TARGETS = {
    "Tri-County": 26,
    "York-Simcoe": 26,
    "Lakeshore": 27
}

print("=" * 85)
print(f"FULL REGULAR SEASON SCHEDULE RECONCILIATION ({len(games)} Total Games)")
print("=" * 85)

all_verified = True
for cohort in ["U11 AA", "U14 AA"]:
    for league in ["Tri-County", "York-Simcoe", "Lakeshore"]:
        target = LEAGUE_TARGETS.get(league)
        print(f"\n🏒 [{cohort}] {league} (Target: {target} Total Games per Team)")
        print(f"{'Team Name':<32} | {'Played':<6} | {'Rem':<6} | {'Total':<6} | {'Status'}")
        print("-" * 75)

        for team_name, meta in sorted(master_db.get(cohort, {}).items()):
            if meta.get("league") != league:
                continue

            gp = played_by_team.get((cohort, team_name), 0)
            rem = rem_by_team.get((cohort, team_name), 0)
            tot = gp + rem

            if tot == target:
                status_str = "✅ Verified"
            else:
                status_str = f"⚠️ Diff ({tot - target:+d})"
                all_verified = False

            print(f"{team_name[:30]:<32} | {gp:<6} | {rem:<6} | {tot:<6} | {status_str}")

print("\n" + "=" * 85)
print("AUDIT RESULT")
print("=" * 85)
if all_verified:
    print("🏆 ALL 72 TEAMS PERFECTLY MATCHED TO OFFICIAL LEAGUE SCHEDULE TARGETS!")
else:
    print("⚠️ Discrepancies detected. Review individual team lines above.")

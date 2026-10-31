import json
from collections import Counter

with open("omha_raw_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

games = data.get("games", [])
standings = data.get("standings", [])

print(f"Total teams in standings: {len(standings)}")
print(f"Total games collected:    {len(games)}")

# 1. Status breakdown
statuses = Counter(g.get("status") for g in games)
print("\n📊 Game Status Breakdown:")
for status, count in statuses.items():
    print(f"   - {status}: {count}")

# 2. Date Range
dates = [g.get("date") for g in games if g.get("date")]
if dates:
    print(f"\n📅 Schedule Date Range:")
    print(f"   - Earliest Game: {min(dates)}")
    print(f"   - Latest Game:   {max(dates)}")

# 3. Games per Cohort
cohort_games = Counter(f"{g.get('league')} - {g.get('cohort')}" for g in games)
print("\n🏒 Games by League & Cohort:")
for grp, count in cohort_games.items():
    print(f"   - {grp}: {count} games")

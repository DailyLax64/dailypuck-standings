import json
import re
from collections import defaultdict

# 1. Load Data
with open("master_teams.json", "r", encoding="utf-8") as f:
    master_db = json.load(f)

with open("omha_raw_data.json", "r", encoding="utf-8") as f:
    omha_data = json.load(f)

with open("future_games.json", "r", encoding="utf-8") as f:
    future_data = json.load(f)

# Build Lookup Dictionaries for Canonical Names
canonical_lookup = {}
for cohort, teams in master_db.items():
    canonical_lookup[cohort] = {}
    for team_name, meta in teams.items():
        league = meta.get("league")
        clean_key = re.sub(r'[^A-Z0-9]', '', team_name.upper())
        canonical_lookup[cohort][clean_key] = (team_name, league)
        for alias in meta.get("aliases", []):
            alias_key = re.sub(r'[^A-Z0-9]', '', alias.upper())
            canonical_lookup[cohort][alias_key] = (team_name, league)

def resolve_team(cohort, name):
    clean = re.sub(r'[^A-Z0-9]', '', str(name or '').upper())
    # Direct match
    if clean in canonical_lookup.get(cohort, {}):
        return canonical_lookup[cohort][clean]
    # Substring search
    for k, v in canonical_lookup.get(cohort, {}).items():
        if k in clean or clean in k:
            return v
    return None, None

# 2. Check for Non-League / Tournament Games
flagged_games = []
clean_future_games = []

for g in future_data.get("scheduled_games", []):
    cohort = g.get("cohort")
    code = g.get("game_code", "")
    h_raw = g.get("home", "")
    v_raw = g.get("visitor", "")

    h_can, h_league = resolve_team(cohort, h_raw)
    v_can, v_league = resolve_team(cohort, v_raw)

    issues = []
    if not h_can:
        issues.append(f"Unrecognized Home: '{h_raw}'")
    if not v_can:
        issues.append(f"Unrecognized Visitor: '{v_raw}'")
    if h_league and v_league and h_league != v_league:
        issues.append(f"Inter-League Matchup: {h_league} vs {v_league}")

    # York-Simcoe regular season check
    if (h_league == "York-Simcoe" or v_league == "York-Simcoe") and "RS" not in code.upper():
        issues.append(f"YS Non-Regular Season Code: '{code}'")

    if issues:
        flagged_games.append({
            "code": code,
            "cohort": cohort,
            "date": g.get("date"),
            "matchup": f"{h_raw} vs {v_raw}",
            "issues": issues
        })
    else:
        clean_future_games.append((cohort, h_league, h_can, v_can))

print("=" * 80)
print(f"SCHEDULE PURITY AUDIT: {len(future_data.get('scheduled_games', []))} Games Analyzed")
print("=" * 80)
print(f"Clean League Games:   {len(clean_future_games)}")
print(f"Flagged / Non-League: {len(flagged_games)}")

if flagged_games:
    print("\n⚠️ Flagged Games (Tournaments / Invalid Opponents / Non-RS):")
    for fg in flagged_games[:15]:
        print(f"   [{fg['date']}] {fg['code']:<14} | {fg['matchup']:<40} | {', '.join(fg['issues'])}")
    if len(flagged_games) > 15:
        print(f"   ... and {len(flagged_games) - 15} more.")

# 3. Tally Games per Team (Standings GP + Remaining Scheduled)
gp_by_team = defaultdict(int)
for row in omha_data.get("standings", []):
    cohort = row.get("cohort")
    t_name = row.get("team_name")
    t_can, _ = resolve_team(cohort, t_name)
    if t_can:
        gp_by_team[(cohort, t_can)] += row.get("gp", 0)

scheduled_by_team = defaultdict(int)
for cohort, league, h_can, v_can in clean_future_games:
    scheduled_by_team[(cohort, h_can)] += 1
    scheduled_by_team[(cohort, v_can)] += 1

print("\n" + "=" * 80)
print(f"{'Cohort':<8} | {'League':<12} | {'Team':<30} | {'GP':<4} | {'Rem':<4} | {'Total'}")
print("-" * 80)

cohort_league_totals = defaultdict(list)
for cohort, teams in master_db.items():
    for team_name, meta in teams.items():
        league = meta.get("league")
        gp = gp_by_team.get((cohort, team_name), 0)
        rem = scheduled_by_team.get((cohort, team_name), 0)
        total = gp + rem
        cohort_league_totals[(cohort, league)].append(total)

for (cohort, league), totals in sorted(cohort_league_totals.items()):
    min_g, max_g = min(totals), max(totals)
    print(f"\n📊 [{cohort}] {league} Summary: Expected games per team = {min_g} to {max_g}")
    for team_name, meta in master_db[cohort].items():
        if meta.get("league") == league:
            gp = gp_by_team.get((cohort, team_name), 0)
            rem = scheduled_by_team.get((cohort, team_name), 0)
            total = gp + rem
            flag = " ⚠️ OUTLIER" if (total != max_g and total != min_g) else ""
            print(f"{cohort:<8} | {league:<12} | {team_name[:28]:<30} | {gp:<4} | {rem:<4} | {total}{flag}")

import json
import math
import random
import re
from collections import defaultdict
from datetime import datetime, timezone

# 1. Configuration & Parameters
SIMULATION_RUNS = 10000
HOME_ICE_ADVANTAGE = 0.35  # MHR rating bonus for home ice
DEFAULT_MHR_RATING = 82.0   # Fallback if unranked

# Official Tri-County Playoff Group Seed Mappings
TRI_COUNTY_POOLS = {
    "U11 AA": {
        "Group A": {1, 6, 10, 11, 12},
        "Group B": {2, 5, 8, 9, 15},
        "Group C": {3, 4, 7, 13, 14}
    },
    "U14 AA": {
        "Group A": {1, 6, 7, 12, 13},
        "Group B": {2, 5, 9, 10},
        "Group C": {3, 4, 8, 11}
    }
}

def load_data():
    with open("master_teams.json", "r", encoding="utf-8") as f:
        master_db = json.load(f)

    with open("full_season_games.json", "r", encoding="utf-8") as f:
        season_games = json.load(f)

    try:
        with open("omha_raw_data.json", "r", encoding="utf-8") as f:
            omha_data = json.load(f)
    except FileNotFoundError:
        omha_data = {"standings": [], "games": []}

    return master_db, season_games.get("games", []), omha_data

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

def get_team_rating(master_db, cohort, team_name):
    cohort_teams = master_db.get(cohort, {})
    meta = cohort_teams.get(team_name, {})
    try:
        return float(meta.get("mhr_rating") or DEFAULT_MHR_RATING)
    except (ValueError, TypeError):
        return DEFAULT_MHR_RATING

def calculate_matchup_probabilities(r_home, r_visitor):
    delta = (r_home + HOME_ICE_ADVANTAGE) - r_visitor
    p_base_home = 1.0 / (1.0 + math.pow(10.0, -delta / 2.8))
    p_tie = 0.14 * math.exp(-math.pow(delta / 3.2, 2.0))

    p_home = max(0.01, min(0.98, p_base_home - (p_tie / 2.0)))
    p_visitor = max(0.01, min(0.98, 1.0 - p_home - p_tie))

    total = p_home + p_tie + p_visitor
    return p_home / total, p_tie / total, p_visitor / total

def simulate():
    master_db, all_games, omha_data = load_data()
    resolver = build_team_resolver(master_db)

    # 1. Base standings from completed GameSheet matches
    base_points = defaultdict(int)
    base_wins = defaultdict(int)
    base_losses = defaultdict(int)
    base_ties = defaultdict(int)
    base_gp = defaultdict(int)

    omha_games = omha_data.get("games", [])
    valid_final_games = 0

    for g in omha_games:
        if str(g.get("status", "")).lower() != "final":
            continue

        h_goals = g.get("home_goals")
        v_goals = g.get("visitor_goals")
        if h_goals is None or v_goals is None:
            continue

        cohort = g.get("cohort")
        h_raw = g.get("home_name")
        v_raw = g.get("visitor_name")

        h_can, _ = resolve_team(resolver, cohort, h_raw)
        v_can, _ = resolve_team(resolver, cohort, v_raw)

        if not h_can or not v_can:
            continue

        valid_final_games += 1
        base_gp[(cohort, h_can)] += 1
        base_gp[(cohort, v_can)] += 1

        if h_goals > v_goals:
            base_points[(cohort, h_can)] += 2
            base_wins[(cohort, h_can)] += 1
            base_losses[(cohort, v_can)] += 1
        elif v_goals > h_goals:
            base_points[(cohort, v_can)] += 2
            base_wins[(cohort, v_can)] += 1
            base_losses[(cohort, h_can)] += 1
        else:
            base_points[(cohort, h_can)] += 1
            base_points[(cohort, v_can)] += 1
            base_ties[(cohort, h_can)] += 1
            base_ties[(cohort, v_can)] += 1

    total_teams_count = len(master_db.get("U11 AA", {})) + len(master_db.get("U14 AA", {}))
    matched_teams_count = sum(1 for k in base_gp if base_gp[k] > 0)

    # Remaining regular season games
    remaining_games = [g for g in all_games if g.get("status") == "scheduled"]

    print("=" * 90)
    print(f"RUNNING MONTE CARLO SEASON SIMULATION ({SIMULATION_RUNS:,} iterations)")
    print(f"Official GameSheet Matches Processed: {valid_final_games}")
    print(f"Teams with Standings Computed:        {matched_teams_count} / {total_teams_count}")
    print(f"Remaining Games to Simulate:          {len(remaining_games)}")
    print("=" * 90)

    precomputed_matchups = []
    for g in remaining_games:
        cohort = g["cohort"]
        h_team = g["home"]
        v_team = g["visitor"]

        r_h = get_team_rating(master_db, cohort, h_team)
        r_v = get_team_rating(master_db, cohort, v_team)
        p_h, p_t, _ = calculate_matchup_probabilities(r_h, r_v)

        precomputed_matchups.append({
            "cohort": cohort,
            "home": h_team,
            "visitor": v_team,
            "p_home": p_h,
            "p_tie": p_t,
            "date": g.get("date"),
            "time": g.get("time"),
            "game_code": g.get("game_code")
        })

    sim_pts_totals = defaultdict(list)
    sim_rank_counts = defaultdict(lambda: defaultdict(int))

    # Monte Carlo simulation runs
    for _ in range(SIMULATION_RUNS):
        cur_pts = defaultdict(int)
        cur_wins = defaultdict(int)

        for (cohort, t), pts in base_points.items():
            cur_pts[(cohort, t)] = pts
            cur_wins[(cohort, t)] = base_wins[(cohort, t)]

        for m in precomputed_matchups:
            cohort = m["cohort"]
            h_team = m["home"]
            v_team = m["visitor"]

            roll = random.random()
            if roll < m["p_home"]:
                cur_pts[(cohort, h_team)] += 2
                cur_wins[(cohort, h_team)] += 1
            elif roll < (m["p_home"] + m["p_tie"]):
                cur_pts[(cohort, h_team)] += 1
                cur_pts[(cohort, v_team)] += 1
            else:
                cur_pts[(cohort, v_team)] += 2
                cur_wins[(cohort, v_team)] += 1

        for cohort in ["U11 AA", "U14 AA"]:
            leagues = defaultdict(list)
            for t, meta in master_db[cohort].items():
                league = meta.get("league")
                leagues[league].append((t, cur_pts[(cohort, t)], cur_wins[(cohort, t)]))

            for league, teams_data in leagues.items():
                # Tiebreaker: Points (desc), Wins (desc), random draw
                teams_data.sort(key=lambda x: (x[1], x[2], random.random()), reverse=True)
                for rank, (team_name, pts, wins) in enumerate(teams_data, 1):
                    sim_pts_totals[(cohort, team_name)].append(pts)
                    sim_rank_counts[(cohort, team_name)][rank] += 1

    results = {}
    for cohort in ["U11 AA", "U14 AA"]:
        results

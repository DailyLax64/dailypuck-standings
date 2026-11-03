import json
import math
import os
import random
import re
from collections import defaultdict
from functools import cmp_to_key
from datetime import datetime, timezone

# 1. Configuration & Parameters
SIMULATION_RUNS = 25000  # Runs in ~90s with ±0.2% variance
HOME_ICE_ADVANTAGE = 0.35  # MHR rating bonus for home ice
DEFAULT_MHR_RATING = 82.0   # Fallback if unranked

# Official Playoff Group Seed Mappings
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

YORK_SIMCOE_POOLS = {
    "Pool A": {1, 11, 12},
    "Pool B": {2, 9, 10},
    "Pool C": {3, 7, 8},
    "Pool D": {4, 5, 6}
}

LAKESHORE_POOLS = {
    "Pool A": {1, 4, 6, 8, 10},
    "Pool B": {2, 3, 5, 7, 9}
}

def load_data():
    with open("master_teams.json", "r", encoding="utf-8") as f:
        master_db = json.load(f)

    season_games = {"games": []}
    if os.path.exists("full_season_games.json"):
        with open("full_season_games.json", "r", encoding="utf-8") as f:
            season_games = json.load(f)
    elif os.path.exists("future_games.json"):
        with open("future_games.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            season_games = {"games": data if isinstance(data, list) else data.get("games", [])}

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

def simulate_game_score(r_home, r_visitor):
    delta = (r_home + HOME_ICE_ADVANTAGE) - r_visitor
    # Softened rating delta factor (0.70 down from 0.90) to factor in youth hockey volatility
    expected_margin = delta * 0.70
    base_goals = 3.2

    lam_home = max(0.5, base_goals + expected_margin / 2.0)
    lam_visitor = max(0.5, base_goals - expected_margin / 2.0)

    def sample_poisson(lam):
        L = math.exp(-lam)
        k, p = 0, 1.0
        while p > L:
            k += 1
            p *= random.random()
        return k - 1

    gh = sample_poisson(lam_home)
    gv = sample_poisson(lam_visitor)
    return gh, gv

def make_tiebreaker_comparator(cohort, cur_pts, cur_wins, cur_gf, cur_ga, h2h_pts):
    def compare(t1, t2):
        k1 = (cohort, t1)
        k2 = (cohort, t2)

        if cur_pts[k1] != cur_pts[k2]:
            return 1 if cur_pts[k1] > cur_pts[k2] else -1

        h2h_1 = h2h_pts.get((cohort, t1, t2), 0)
        h2h_2 = h2h_pts.get((cohort, t2, t1), 0)
        if h2h_1 != h2h_2:
            return 1 if h2h_1 > h2h_2 else -1

        if cur_wins[k1] != cur_wins[k2]:
            return 1 if cur_wins[k1] > cur_wins[k2] else -1

        gf1, ga1 = cur_gf[k1], cur_ga[k1]
        gf2, ga2 = cur_gf[k2], cur_ga[k2]
        pct1 = gf1 / (gf1 + ga1) if (gf1 + ga1) > 0 else 0.0
        pct2 = gf2 / (gf2 + ga2) if (gf2 + ga2) > 0 else 0.0
        if abs(pct1 - pct2) > 1e-6:
            return 1 if pct1 > pct2 else -1

        if ga1 != ga2:
            return 1 if ga1 < ga2 else -1

        if gf1 != gf2:
            return 1 if gf1 > gf2 else -1

        return 1 if random.random() > 0.5 else -1

    return compare

def simulate():
    master_db, all_games, omha_data = load_data()
    resolver = build_team_resolver(master_db)

    base_points = defaultdict(int)
    base_wins = defaultdict(int)
    base_losses = defaultdict(int)
    base_ties = defaultdict(int)
    base_gp = defaultdict(int)
    base_gf = defaultdict(int)
    base_ga = defaultdict(int)
    base_h2h_pts = defaultdict(int)

    team_completed_games = defaultdict(list)
    team_upcoming_games = defaultdict(list)

    omha_games = omha_data.get("games", [])
    valid_final_games = 0

    # 1. Process Completed GameSheet Matches
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
        base_gf[(cohort, h_can)] += int(h_goals)
        base_ga[(cohort, h_can)] += int(v_goals)
        base_gf[(cohort, v_can)] += int(v_goals)
        base_ga[(cohort, v_can)] += int(h_goals)

        h_res = "W" if h_goals > v_goals else ("L" if h_goals < v_goals else "T")
        v_res = "W" if v_goals > h_goals else ("L" if v_goals < h_goals else "T")

        if h_goals > v_goals:
            base_points[(cohort, h_can)] += 2
            base_wins[(cohort, h_can)] += 1
            base_losses[(cohort, v_can)] += 1
            base_h2h_pts[(cohort, h_can, v_can)] += 2
        elif v_goals > h_goals:
            base_points[(cohort, v_can)] += 2
            base_wins[(cohort, v_can)] += 1
            base_losses[(cohort, h_can)] += 1
            base_h2h_pts[(cohort, v_can, h_can)] += 2
        else:
            base_points[(cohort, h_can)] += 1
            base_points[(cohort, v_can)] += 1
            base_ties[(cohort, h_can)] += 1
            base_ties[(cohort, v_can)] += 1
            base_h2h_pts[(cohort, h_can, v_can)] += 1
            base_h2h_pts[(cohort, v_can, h_can)] += 1

        date_val = str(g.get("date") or "")
        loc_val = str(g.get("location") or "Arena")

        team_completed_games[(cohort, h_can)].append({
            "date": date_val,
            "opponent": v_can,
            "is_home": True,
            "team_goals": int(h_goals),
            "opp_goals": int(v_goals),
            "result": h_res,
            "location": loc_val
        })
        team_completed_games[(cohort, v_can)].append({
            "date": date_val,
            "opponent": h_can,
            "is_home": False,
            "team_goals": int(v_goals),
            "opp_goals": int(h_goals),
            "result": v_res,
            "location": loc_val
        })

    # 2. Process Scheduled Calendar Matches
    remaining_games = []
    for g in all_games:
        if str(g.get("status", "")).lower() == "scheduled":
            cohort = g.get("cohort")
            h_raw = g.get("home")
            v_raw = g.get("visitor")

            h_can, _ = resolve_team(resolver, cohort, h_raw)
            v_can, _ = resolve_team(resolver, cohort, v_raw)
            if not h_can or not v_can:
                continue

            remaining_games.append({
                "cohort": cohort,
                "home": h_can,
                "visitor": v_can,
                "date": str(g.get("date") or ""),
                "time": str(g.get("time") or "TBD"),
                "location": str(g.get("location") or "Arena")
            })

            team_upcoming_games[(cohort, h_can)].append({
                "date": str(g.get("date") or ""),
                "time": str(g.get("time") or "TBD"),
                "opponent": v_can,
                "is_home": True,
                "location": str(g.get("location") or "Home Arena")
            })
            team_upcoming_games[(cohort, v_can)].append({
                "date": str(g.get("date") or ""),
                "time": str(g.get("time") or "TBD"),
                "opponent": h_can,
                "is_home": False,
                "location": str(g.get("location") or "Away Arena")
            })

    total_teams_count = len(master_db.get("U11 AA", {})) + len(master_db.get("U14 AA", {}))
    matched_teams_count = sum(1 for k in base_gp if base_gp[k] > 0)

    print("=" * 95)
    print(f"RUNNING MONTE CARLO SEASON SIMULATION ({SIMULATION_RUNS:,} iterations)")
    print(f"Official GameSheet Matches Processed: {valid_final_games}")
    print(f"Teams with Standings Computed:        {matched_teams_count} / {total_teams_count}")
    print

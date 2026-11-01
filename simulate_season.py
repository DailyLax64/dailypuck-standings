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

    # Base standings from actual completed games
    base_points = defaultdict(int)
    base_wins = defaultdict(int)
    base_losses = defaultdict(int)
    base_ties = defaultdict(int)
    base_gp = defaultdict(int)

    # Ingest GameSheet official standings using resolver
    for row in omha_data.get("standings", []):
        cohort = row.get("cohort")
        raw_name = row.get("team_name")
        can_name, _ = resolve_team(resolver, cohort, raw_name)
        if can_name:
            base_points[(cohort, can_name)] = int(row.get("pts", 0) or 0)
            base_wins[(cohort, can_name)] = int(row.get("w", 0) or 0)
            base_losses[(cohort, can_name)] = int(row.get("l", 0) or 0)
            base_ties[(cohort, can_name)] = int(row.get("t", 0) or 0)
            base_gp[(cohort, can_name)] = int(row.get("gp", 0) or 0)

    total_teams_count = len(master_db.get("U11 AA", {})) + len(master_db.get("U14 AA", {}))
    matched_teams_count = sum(1 for k in base_gp if base_gp[k] > 0)

    completed_games = [g for g in all_games if g.get("status") == "played"]
    remaining_games = [g for g in all_games if g.get("status") == "scheduled"]

    print("=" * 85)
    print(f"RUNNING MONTE CARLO SEASON SIMULATION ({SIMULATION_RUNS:,} iterations)")
    print(f"Teams with Standings Ingested: {matched_teams_count} / {total_teams_count}")
    print(f"Completed Games Counted:      {len(completed_games)}")
    print(f"Remaining Games to Simulate:  {len(remaining_games)}")
    print("=" * 85)

    # Pre-calculate probabilities for remaining matchups
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

    # Track aggregates
    sim_pts_totals = defaultdict(list)
    sim_rank_counts = defaultdict(lambda: defaultdict(int))

    # Monte Carlo simulation loop
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

        # Group by cohort and league to rank
        for cohort in ["U11 AA", "U14 AA"]:
            leagues = defaultdict(list)
            for t, meta in master_db[cohort].items():
                league = meta.get("league")
                leagues[league].append((t, cur_pts[(cohort, t)], cur_wins[(cohort, t)]))

            for league, teams_data in leagues.items():
                # Sort: Points (descending), Wins (descending), random draw
                teams_data.sort(key=lambda x: (x[1], x[2], random.random()), reverse=True)
                for rank, (team_name, pts, wins) in enumerate(teams_data, 1):
                    sim_pts_totals[(cohort, team_name)].append(pts)
                    sim_rank_counts[(cohort, team_name)][rank] += 1

    # Format simulation results
    results = {}
    for cohort in ["U11 AA", "U14 AA"]:
        results[cohort] = {}
        for league in ["Tri-County", "York-Simcoe", "Lakeshore"]:
            results[cohort][league] = []

            for team_name, meta in master_db[cohort].items():
                if meta.get("league") != league:
                    continue

                pts_list = sim_pts_totals[(cohort, team_name)]
                avg_pts = sum(pts_list) / len(pts_list) if pts_list else 0.0
                rank_dist = sim_rank_counts[(cohort, team_name)]

                p_first = (rank_dist[1] / SIMULATION_RUNS) * 100.0
                p_top4 = (sum(rank_dist[r] for r in range(1, 5)) / SIMULATION_RUNS) * 100.0
                p_top8 = (sum(rank_dist[r] for r in range(1, 9)) / SIMULATION_RUNS) * 100.0

                results[cohort][league].append({
                    "team_name": team_name,
                    "mhr_rating": get_team_rating(master_db, cohort, team_name),
                    "current_gp": base_gp[(cohort, team_name)],
                    "current_pts": base_points[(cohort, team_name)],
                    "proj_pts_avg": round(avg_pts, 1),
                    "proj_pts_min": min(pts_list) if pts_list else 0,
                    "proj_pts_max": max(pts_list) if pts_list else 0,
                    "prob_1st_pct": round(p_first, 1),
                    "prob_top4_pct": round(p_top4, 1),
                    "prob_top8_pct": round(p_top8, 1)
                })

            results[cohort][league].sort(key=lambda x: x["proj_pts_avg"], reverse=True)

    final_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "simulations_count": SIMULATION_RUNS,
        "results": results,
        "upcoming_matchup_projections": precomputed_matchups[:40]
    }

    with open("simulation_results.json", "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2)

    # Print summary tables
    for cohort in ["U11 AA", "U14 AA"]:
        for league in ["Tri-County", "York-Simcoe", "Lakeshore"]:
            print(f"\n🏆 Projected Standings: [{cohort}] {league}")
            print(f"{'Rk':<3} | {'Team':<28} | {'Rating':<6} | {'GP':<3} | {'Cur Pts':<7} | {'Proj Pts':<8} | {'1st Place %':<11} | {'Top 4 %'}")
            print("-" * 90)
            for rk, row in enumerate(results[cohort][league], 1):
                print(f"{rk:<3} | {row['team_name'][:26]:<28} | {row['mhr_rating']:<6.1f} | {row['current_gp']:<3} | {row['current_pts']:<7} | {row['proj_pts_avg']:<8.1f} | {row['prob_1st_pct']:<10.1f}% | {row['prob_top4_pct']:<6.1f}%")

if __name__ == "__main__":
    simulate()

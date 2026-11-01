import json
import math
import random
from collections import defaultdict
from datetime import datetime, timezone

# 1. Configuration & Parameters
SIMULATION_RUNS = 10000
HOME_ICE_ADVANTAGE = 0.35  # MHR rating bonus for home team
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

def get_team_rating(master_db, cohort, team_name):
    cohort_teams = master_db.get(cohort, {})
    meta = cohort_teams.get(team_name, {})
    try:
        return float(meta.get("mhr_rating") or DEFAULT_MHR_RATING)
    except (ValueError, TypeError):
        return DEFAULT_MHR_RATING

def calculate_matchup_probabilities(r_home, r_visitor):
    # Delta R with home ice advantage
    delta = (r_home + HOME_ICE_ADVANTAGE) - r_visitor

    # Base logistic expectation
    p_base_home = 1.0 / (1.0 + math.pow(10.0, -delta / 2.8))

    # Tie probability modeled as bell curve peaking at ~14% for evenly matched teams
    p_tie = 0.14 * math.exp(-math.pow(delta / 3.2, 2.0))

    # Rebalance probabilities
    p_home = max(0.01, min(0.98, p_base_home - (p_tie / 2.0)))
    p_visitor = max(0.01, min(0.98, 1.0 - p_home - p_tie))

    # Normalize sum to 1.0
    total = p_home + p_tie + p_visitor
    return p_home / total, p_tie / total, p_visitor / total

def simulate():
    master_db, all_games, omha_data = load_data()

    # Base standings from actual completed games
    base_points = defaultdict(int)
    base_wins = defaultdict(int)
    base_losses = defaultdict(int)
    base_ties = defaultdict(int)
    base_gp = defaultdict(int)

    # Ingest actual completed GameSheet records or calendar played games
    completed_games = [g for g in all_games if g.get("status") == "played"]
    remaining_games = [g for g in all_games if g.get("status") == "scheduled"]

    # Match GameSheet results if available, else track known standings
    gs_standings = {
        (row.get("cohort"), row.get("team_name")): row
        for row in omha_data.get("standings", [])
    }

    # Initialize baseline records
    for cohort, teams in master_db.items():
        for team_name in teams:
            gs_row = gs_standings.get((cohort, team_name))
            if gs_row:
                base_points[(cohort, team_name)] = gs_row.get("pts", 0)
                base_wins[(cohort, team_name)] = gs_row.get("w", 0)
                base_losses[(cohort, team_name)] = gs_row.get("l", 0)
                base_ties[(cohort, team_name)] = gs_row.get("t", 0)
                base_gp[(cohort, team_name)] = gs_row.get("gp", 0)

    print("=" * 80)
    print(f"RUNNING MONTE CARLO SEASON SIMULATION ({SIMULATION_RUNS:,} iterations)")
    print(f"Completed Games Counted: {len(completed_games)}")
    print(f"Remaining Games to Simulate: {len(remaining_games)}")
    print("=" * 80)

    # Pre-calculate win/tie/loss probabilities for all remaining matchups
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

    # Tracking simulation aggregates
    sim_pts_totals = defaultdict(list)
    sim_rank_counts = defaultdict(lambda: defaultdict(int))  # (cohort, team) -> rank -> count

    # Run Monte Carlo loop
    for _ in range(SIMULATION_RUNS):
        cur_pts = defaultdict(int)
        for (cohort, t), pts in base_points.items():
            cur_pts[(cohort, t)] = pts

        for m in precomputed_matchups:
            cohort = m["cohort"]
            h_team = m["home"]
            v_team = m["visitor"]

            roll = random.random()
            if roll < m["p_home"]:
                cur_pts[(cohort, h_team)] += 2
            elif roll < (m["p_home"] + m["p_tie"]):
                cur_pts[(cohort, h_team)] += 1
                cur_pts[(cohort, v_team)] += 1
            else:
                cur_pts[(cohort, v_team)] += 2

        # Group by cohort and league to rank
        for cohort in ["U11 AA", "U14 AA"]:
            leagues = defaultdict(list)
            for t, meta in master_db[cohort].items():
                league = meta.get("league")
                leagues[league].append((t, cur_pts[(cohort, t)]))

            for league, teams_pts in leagues.items():
                # Sort descending by points (break random ties)
                teams_pts.sort(key=lambda x: (x[1], random.random()), reverse=True)
                for rank, (team_name, pts) in enumerate(teams_pts, 1):
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

                # Probabilities for top seed (1st), top 4, top 8
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

            # Sort teams by projected points descending
            results[cohort][league].sort(key=lambda x: x["proj_pts_avg"], reverse=True)

    # Save output artifact
    final_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "simulations_count": SIMULATION_RUNS,
        "results": results,
        "upcoming_matchup_projections": precomputed_matchups[:30]  # Next 30 game cards
    }

    with open("simulation_results.json", "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2)

    # Print Terminal Summary
    for cohort in ["U11 AA", "U14 AA"]:
        for league in ["Tri-County", "York-Simcoe", "Lakeshore"]:
            print(f"\n🏆 Projected Standings: [{cohort}] {league}")
            print(f"{'Rk':<3} | {'Team':<28} | {'Rating':<6} | {'Cur Pts':<7} | {'Proj Pts':<8} | {'1st Place %':<11} | {'Top 4 %'}")
            print("-" * 85)
            for rk, row in enumerate(results[cohort][league], 1):
                print(f"{rk:<3} | {row['team_name'][:26]:<28} | {row['mhr_rating']:<6.1f} | {row['current_pts']:<7} | {row['proj_pts_avg']:<8.1f} | {row['prob_1st_pct']:<10.1f}% | {row['prob_top4_pct']:<6.1f}%")

if __name__ == "__main__":
    simulate()

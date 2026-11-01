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

# ---------------------------------------------------------------------------
# Official Playoff Group / Pool Mappings
# ---------------------------------------------------------------------------

# Tri-County Playoff Groups
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

# York-Simcoe Playoff Pools (12-team loop, 1st in each pool to Semis)
YORK_SIMCOE_POOLS = {
    "Pool A": {1, 11, 12},
    "Pool B": {2, 9, 10},
    "Pool C": {3, 7, 8},
    "Pool D": {4, 5, 6}
}

# Lakeshore Playoff Pools (10-team loop, Top 2 in each pool to Crossover Semis)
LAKESHORE_POOLS = {
    "Pool A": {1, 4, 6, 8, 10},
    "Pool B": {2, 3, 5, 7, 9}
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

    # 1. Base standings calculated from GameSheet final scores
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
    remaining_games = [g for g in all_games if g.get("status") == "scheduled"]

    print("=" * 95)
    print(f"RUNNING MONTE CARLO SEASON SIMULATION ({SIMULATION_RUNS:,} iterations)")
    print(f"Official GameSheet Matches Processed: {valid_final_games}")
    print(f"Teams with Standings Computed:        {matched_teams_count} / {total_teams_count}")
    print(f"Remaining Games to Simulate:          {len(remaining_games)}")
    print("=" * 95)

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
        results[cohort] = {}
        for league in ["Tri-County", "York-Simcoe", "Lakeshore"]:
            results[cohort][league] = []

            for team_name, meta in master_db[cohort].items():
                if meta.get("league") != league:
                    continue

                pts_list = sim_pts_totals[(cohort, team_name)]
                avg_pts = sum(pts_list) / len(pts_list) if pts_list else 0.0
                rank_dist = sim_rank_counts[(cohort, team_name)]

                # Projected Finish (Expected Seed)
                exp_finish = sum(rank * count for rank, count in rank_dist.items()) / SIMULATION_RUNS

                # Key threshold odds
                p_first = (rank_dist[1] / SIMULATION_RUNS) * 100.0
                p_top2 = ((rank_dist[1] + rank_dist[2]) / SIMULATION_RUNS) * 100.0
                p_top4 = (sum(rank_dist[r] for r in range(1, 5)) / SIMULATION_RUNS) * 100.0

                pool_probs = {}
                likely_pool_str = "-"

                # Tri-County Pool Distribution
                if league == "Tri-County" and cohort in TRI_COUNTY_POOLS:
                    pools_def = TRI_COUNTY_POOLS[cohort]
                    for g_name, seeds in pools_def.items():
                        pool_probs[g_name] = (sum(rank_dist[r] for r in seeds) / SIMULATION_RUNS) * 100.0
                    sorted_p = sorted(pool_probs.items(), key=lambda x: x[1], reverse=True)
                    likely_pool_str = f"{sorted_p[0][0]} ({sorted_p[0][1]:.0f}%)"

                # York-Simcoe Pool Distribution
                elif league == "York-Simcoe":
                    for p_name, seeds in YORK_SIMCOE_POOLS.items():
                        pool_probs[p_name] = (sum(rank_dist[r] for r in seeds) / SIMULATION_RUNS) * 100.0
                    sorted_p = sorted(pool_probs.items(), key=lambda x: x[1], reverse=True)
                    likely_pool_str = f"{sorted_p[0][0]} ({sorted_p[0][1]:.0f}%)"

                # Lakeshore Pool Distribution
                elif league == "Lakeshore":
                    for p_name, seeds in LAKESHORE_POOLS.items():
                        pool_probs[p_name] = (sum(rank_dist[r] for r in seeds) / SIMULATION_RUNS) * 100.0
                    sorted_p = sorted(pool_probs.items(), key=lambda x: x[1], reverse=True)
                    likely_pool_str = f"{sorted_p[0][0]} ({sorted_p[0][1]:.0f}%)"

                results[cohort][league].append({
                    "team_name": team_name,
                    "mhr_rating": get_team_rating(master_db, cohort, team_name),
                    "current_gp": base_gp[(cohort, team_name)],
                    "current_pts": base_points[(cohort, team_name)],
                    "current_w": base_wins[(cohort, team_name)],
                    "current_l": base_losses[(cohort, team_name)],
                    "current_t": base_ties[(cohort, team_name)],
                    "proj_pts_avg": round(avg_pts, 1),
                    "proj_finish": round(exp_finish, 1),
                    "prob_1st_pct": round(p_first, 1),
                    "prob_top2_pct": round(p_top2, 1),
                    "prob_top4_pct": round(p_top4, 1),
                    "pool_probs": {k: round(v, 1) for k, v in pool_probs.items()},
                    "likely_pool": likely_pool_str
                })

            results[cohort][league].sort(key=lambda x: x["proj_pts_avg"], reverse=True)

    final_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "simulations_count": SIMULATION_RUNS,
        "results": results
    }

    with open("simulation_results.json", "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2)

    # =========================================================================
    # TERMINAL REPORTS (Full Standings + Playoff Cards for all 3 Leagues)
    # =========================================================================

    # 1. Tri-County Standings & Pools
    for cohort in ["U11 AA", "U14 AA"]:
        tc_teams = results[cohort]["Tri-County"]
        print(f"\n🏆 Projected Standings: [{cohort}] Tri-County")
        print(f"{'Rk':<3} | {'Team':<27} | {'Rating':<6} | {'GP':<3} | {'Record':<8} | {'Cur Pts':<7} | {'Proj Pts':<8} | {'Proj Finish':<11} | {'Top 2 % (Bye)':<14} | {'Likely Pool'}")
        print("-" * 115)
        for rk, row in enumerate(tc_teams, 1):
            rec_str = f"{row['current_w']}-{row['current_l']}-{row['current_t']}"
            print(f"{rk:<3} | {row['team_name'][:25]:<27} | {row['mhr_rating']:<6.1f} | {row['current_gp']:<3} | {rec_str:<8} | {row['current_pts']:<7} | {row['proj_pts_avg']:<8.1f} | {row['proj_finish']:<11.1f} | {row['prob_top2_pct']:<13.1f}% | {row['likely_pool']}")

        print(f"\n🏒 [{cohort}] Tri-County Projected Playoff Groups")
        pools_def = TRI_COUNTY_POOLS[cohort]
        for g_name, seeds in pools_def.items():
            seed_list = sorted(list(seeds))
            print(f"\n  📁 {g_name} (Seeds: {', '.join(str(s) for s in seed_list)})")
            print(f"  {'Seed':<5} | {'Projected Team':<28} | {'Proj Finish':<12} | {'Rating':<6} | {'Odds in Group'}")
            print("  " + "-" * 70)
            for s in seed_list:
                if s <= len(tc_teams):
                    t = tc_teams[s - 1]
                    odds = t["pool_probs"].get(g_name, 0.0)
                    print(f"  #{s:<4} | {t['team_name'][:26]:<28} | {t['proj_finish']:<12.1f} | {t['mhr_rating']:<6.1f} | {odds:.1f}%")

    # 2. York-Simcoe Standings & Pools
    for cohort in ["U11 AA", "U14 AA"]:
        ys_teams = results[cohort]["York-Simcoe"]
        print(f"\n🏆 Projected Standings: [{cohort}] York-Simcoe")
        print(f"{'Rk':<3} | {'Team':<28} | {'Rating':<6} | {'GP':<3} | {'Record':<8} | {'Cur Pts':<7} | {'Proj Pts':<8} | {'Proj Finish':<11} | {'Top 2 %':<8} | {'Top 4 %':<8} | {'Likely Pool'}")
        print("-" * 125)
        for rk, row in enumerate(ys_teams, 1):
            rec_str = f"{row['current_w']}-{row['current_l']}-{row['current_t']}"
            print(f"{rk:<3} | {row['team_name'][:26]:<28} | {row['mhr_rating']:<6.1f} | {row['current_gp']:<3} | {rec_str:<8} | {row['current_pts']:<7} | {row['proj_pts_avg']:<8.1f} | {row['proj_finish']:<11.1f} | {row['prob_top2_pct']:<7.1f}% | {row['prob_top4_pct']:<7.1f}% | {row['likely_pool']}")

        print(f"\n🏒 [{cohort}] York-Simcoe Projected Playoff Pools (1st Place Moves to Semis)")
        for p_name, seeds in YORK_SIMCOE_POOLS.items():
            seed_list = sorted(list(seeds))
            print(f"\n  📁 {p_name} (Seeds: {', '.join(str(s) for s in seed_list)})")
            print(f"  {'Seed':<5} | {'Projected Team':<28} | {'Proj Finish':<12} | {'Rating':<6} | {'Odds in Pool'}")
            print("  " + "-" * 70)
            for s in seed_list:
                if s <= len(ys_teams):
                    t = ys_teams[s - 1]
                    odds = t["pool_probs"].get(p_name, 0.0)
                    print(f"  #{s:<4} | {t['team_name'][:26]:<28} | {t['proj_finish']:<12.1f} | {t['mhr_rating']:<6.1f} | {odds:.1f}%")

    # 3. Lakeshore Standings & Pools
    for cohort in ["U11 AA", "U14 AA"]:
        ls_teams = results[cohort]["Lakeshore"]
        print(f"\n🏆 Projected Standings: [{cohort}] Lakeshore")
        print(f"{'Rk':<3} | {'Team':<28} | {'Rating':<6} | {'GP':<3} | {'Record':<8} | {'Cur Pts':<7} | {'Proj Pts':<8} | {'Proj Finish':<11} | {'Top 2 %':<8} | {'Top 4 %':<8} | {'Likely Pool'}")
        print("-" * 125)
        for rk, row in enumerate(ls_teams, 1):
            rec_str = f"{row['current_w']}-{row['current_l']}-{row['current_t']}"
            print(f"{rk:<3} | {row['team_name'][:26]:<28} | {row['mhr_rating']:<6.1f} | {row['current_gp']:<3} | {rec_str:<8} | {row['current_pts']:<7} | {row['proj_pts_avg']:<8.1f} | {row['proj_finish']:<11.1f} | {row['prob_top2_pct']:<7.1f}% | {row['prob_top4_pct']:<7.1f}% | {row['likely_pool']}")

        print(f"\n🏒 [{cohort}] Lakeshore Projected Playoff Pools (Top 2 Move to Crossover Semis)")
        for p_name, seeds in LAKESHORE_POOLS.items():
            seed_list = sorted(list(seeds))
            print(f"\n  📁 {p_name} (Seeds: {', '.join(str(s) for s in seed_list)})")
            print(f"  {'Seed':<5} | {'Projected Team':<28} | {'Proj Finish':<12} | {'Rating':<6} | {'Odds in Pool'}")
            print("  " + "-" * 70)
            for s in seed_list:
                if s <= len(ls_teams):
                    t = ls_teams[s - 1]
                    odds = t["pool_probs"].get(p_name, 0.0)
                    print(f"  #{s:<4} | {t['team_name'][:26]:<28} | {t['proj_finish']:<12.1f} | {t['mhr_rating']:<6.1f} | {odds:.1f}%")

if __name__ == "__main__":
    simulate()

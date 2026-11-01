import json
import math
import random
import re
from collections import defaultdict
from functools import cmp_to_key
from datetime import datetime, timezone

# 1. Configuration & Parameters
SIMULATION_RUNS = 10000
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

def simulate_game_score(r_home, r_visitor):
    """Simulates realistic minor hockey scores based on MHR rating differentials."""
    delta = (r_home + HOME_ICE_ADVANTAGE) - r_visitor
    expected_margin = delta * 0.90
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
    """
    Official OMHA Tiebreaker Resolution:
    1. Head-to-Head record between tied teams
    2. Most Wins
    3. Goals For Percentage: GF / (GF + GA)
    4. Fewest Goals Against
    5. Most Goals For
    """
    def compare(t1, t2):
        k1 = (cohort, t1)
        k2 = (cohort, t2)

        # 0. Total Points
        if cur_pts[k1] != cur_pts[k2]:
            return 1 if cur_pts[k1] > cur_pts[k2] else -1

        # 1. Head-to-Head Points
        h2h_1 = h2h_pts.get((cohort, t1, t2), 0)
        h2h_2 = h2h_pts.get((cohort, t2, t1), 0)
        if h2h_1 != h2h_2:
            return 1 if h2h_1 > h2h_2 else -1

        # 2. Most Wins
        if cur_wins[k1] != cur_wins[k2]:
            return 1 if cur_wins[k1] > cur_wins[k2] else -1

        # 3. Highest Goals For Percentage: GF / (GF + GA)
        gf1, ga1 = cur_gf[k1], cur_ga[k1]
        gf2, ga2 = cur_gf[k2], cur_ga[k2]
        pct1 = gf1 / (gf1 + ga1) if (gf1 + ga1) > 0 else 0.0
        pct2 = gf2 / (gf2 + ga2) if (gf2 + ga2) > 0 else 0.0
        if abs(pct1 - pct2) > 1e-6:
            return 1 if pct1 > pct2 else -1

        # 4. Fewest Goals Against
        if ga1 != ga2:
            return 1 if ga1 < ga2 else -1

        # 5. Most Goals For
        if gf1 != gf2:
            return 1 if gf1 > gf2 else -1

        # 6. Random Draw
        return 1 if random.random() > 0.5 else -1

    return compare

def simulate():
    master_db, all_games, omha_data = load_data()
    resolver = build_team_resolver(master_db)

    # 1. Base standings & head-to-head strictly keyed by (cohort, team)
    base_points = defaultdict(int)
    base_wins = defaultdict(int)
    base_losses = defaultdict(int)
    base_ties = defaultdict(int)
    base_gp = defaultdict(int)
    base_gf = defaultdict(int)
    base_ga = defaultdict(int)
    base_h2h_pts = defaultdict(int)

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
        base_gf[(cohort, h_can)] += int(h_goals)
        base_ga[(cohort, h_can)] += int(v_goals)
        base_gf[(cohort, v_can)] += int(v_goals)
        base_ga[(cohort, v_can)] += int(h_goals)

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

    total_teams_count = len(master_db.get("U11 AA", {})) + len(master_db.get("U14 AA", {}))
    matched_teams_count = sum(1 for k in base_gp if base_gp[k] > 0)
    remaining_games = [g for g in all_games if g.get("status") == "scheduled"]

    print("=" * 95)
    print(f"RUNNING MONTE CARLO SEASON SIMULATION ({SIMULATION_RUNS:,} iterations)")
    print(f"Official GameSheet Matches Processed: {valid_final_games}")
    print(f"Teams with Standings Computed:        {matched_teams_count} / {total_teams_count}")
    print(f"Remaining Games to Simulate:          {len(remaining_games)}")
    print(f"Tiebreaker Engine Active:             1. H2H -> 2. Wins -> 3. GF% -> 4. Fewest GA -> 5. GF")
    print("=" * 95)

    scheduled_matchups = []
    for g in remaining_games:
        cohort = g["cohort"]
        h_team = g["home"]
        v_team = g["visitor"]
        r_h = get_team_rating(master_db, cohort, h_team)
        r_v = get_team_rating(master_db, cohort, v_team)
        scheduled_matchups.append((cohort, h_team, v_team, r_h, r_v))

    sim_pts_totals = defaultdict(list)
    sim_rank_counts = defaultdict(lambda: defaultdict(int))

    # Monte Carlo simulation loop
    for _ in range(SIMULATION_RUNS):
        cur_pts = defaultdict(int)
        cur_wins = defaultdict(int)
        cur_gf = defaultdict(int)
        cur_ga = defaultdict(int)
        cur_h2h = defaultdict(int)

        # Initialize directly with (cohort, team) keys
        for (cohort, t), pts in base_points.items():
            cur_pts[(cohort, t)] = pts
            cur_wins[(cohort, t)] = base_wins[(cohort, t)]
            cur_gf[(cohort, t)] = base_gf[(cohort, t)]
            cur_ga[(cohort, t)] = base_ga[(cohort, t)]

        for (cohort, t1, t2), v in base_h2h_pts.items():
            cur_h2h[(cohort, t1, t2)] = v

        # Simulate remaining matchups with goal generation
        for cohort, h_team, v_team, r_h, r_v in scheduled_matchups:
            gh, gv = simulate_game_score(r_h, r_v)
            cur_gf[(cohort, h_team)] += gh
            cur_ga[(cohort, h_team)] += gv
            cur_gf[(cohort, v_team)] += gv
            cur_ga[(cohort, v_team)] += gh

            if gh > gv:
                cur_pts[(cohort, h_team)] += 2
                cur_wins[(cohort, h_team)] += 1
                cur_h2h[(cohort, h_team, v_team)] += 2
            elif gv > gh:
                cur_pts[(cohort, v_team)] += 2
                cur_wins[(cohort, v_team)] += 1
                cur_h2h[(cohort, v_team, h_team)] += 2
            else:
                cur_pts[(cohort, h_team)] += 1
                cur_pts[(cohort, v_team)] += 1
                cur_h2h[(cohort, h_team, v_team)] += 1
                cur_h2h[(cohort, v_team, h_team)] += 1

        # Rank each league using official 5-stage tiebreaker
        for cohort in ["U11 AA", "U14 AA"]:
            leagues = defaultdict(list)
            for t, meta in master_db[cohort].items():
                league = meta.get("league")
                leagues[league].append(t)

            for league, team_list in leagues.items():
                comparator = make_tiebreaker_comparator(cohort, cur_pts, cur_wins, cur_gf, cur_ga, cur_h2h)
                sorted_teams = sorted(team_list, key=cmp_to_key(comparator), reverse=True)

                for rank, team_name in enumerate(sorted_teams, 1):
                    sim_pts_totals[(cohort, team_name)].append(cur_pts[(cohort, team_name)])
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

                # Projected Finish (Expected Rank)
                exp_finish = sum(rank * count for rank, count in rank_dist.items()) / SIMULATION_RUNS

                p_first = (rank_dist[1] / SIMULATION_RUNS) * 100.0
                p_top2 = ((rank_dist[1] + rank_dist[2]) / SIMULATION_RUNS) * 100.0
                p_top4 = (sum(rank_dist[r] for r in range(1, 5)) / SIMULATION_RUNS) * 100.0

                pool_probs = {}
                if league == "Tri-County" and cohort in TRI_COUNTY_POOLS:
                    for g_name, seeds in TRI_COUNTY_POOLS[cohort].items():
                        pool_probs[g_name] = (sum(rank_dist[r] for r in seeds) / SIMULATION_RUNS) * 100.0
                elif league == "York-Simcoe":
                    for p_name, seeds in YORK_SIMCOE_POOLS.items():
                        pool_probs[p_name] = (sum(rank_dist[r] for r in seeds) / SIMULATION_RUNS) * 100.0
                elif league == "Lakeshore":
                    for p_name, seeds in LAKESHORE_POOLS.items():
                        pool_probs[p_name] = (sum(rank_dist[r] for r in seeds) / SIMULATION_RUNS) * 100.0

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
                    "pool_probs": {k: round(v, 1) for k, v in pool_probs.items()}
                })

            results[cohort][league].sort(key=lambda x: x["proj_pts_avg"], reverse=True)

    final_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "simulations_count": SIMULATION_RUNS,
        "results": results
    }

    with open("simulation_results.json", "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2)

    def get_assigned_pool(league, cohort, rank):
        if league == "Tri-County":
            for g, s in TRI_COUNTY_POOLS[cohort].items():
                if rank in s: return g
        elif league == "York-Simcoe":
            for g, s in YORK_SIMCOE_POOLS.items():
                if rank in s: return g
        elif league == "Lakeshore":
            for g, s in LAKESHORE_POOLS.items():
                if rank in s: return g
        return "-"

    # 1. Tri-County Standings & Pools
    for cohort in ["U11 AA", "U14 AA"]:
        tc_teams = results[cohort]["Tri-County"]
        print(f"\n🏆 Projected Standings: [{cohort}] Tri-County")
        print(f"{'Rk':<3} | {'Team':<26} | {'Rating':<6} | {'GP':<3} | {'Record':<8} | {'Pts':<5} | {'Proj Pts':<8} | {'Proj Fin':<8} | {'Top 2 %':<8} | {'Proj Pool':<10} | {'Grp A %':<7} | {'Grp B %':<7} | {'Grp C %'}")
        print("-" * 135)
        for rk, row in enumerate(tc_teams, 1):
            rec_str = f"{row['current_w']}-{row['current_l']}-{row['current_t']}"
            p_a = row['pool_probs'].get("Group A", 0.0)
            p_b = row['pool_probs'].get("Group B", 0.0)
            p_c = row['pool_probs'].get("Group C", 0.0)
            assigned_pool = get_assigned_pool("Tri-County", cohort, rk)
            print(f"{rk:<3} | {row['team_name'][:24]:<26} | {row['mhr_rating']:<6.1f} | {row['current_gp']:<3} | {rec_str:<8} | {row['current_pts']:<5} | {row['proj_pts_avg']:<8.1f} | {row['proj_finish']:<8.1f} | {row['prob_top2_pct']:<7.1f}% | {assigned_pool:<10} | {p_a:<7.1f} | {p_b:<7.1f} | {p_c:<.1f}%")

        print(f"\n🏒 [{cohort}] Tri-County Projected Playoff Groups (Strict Bracket Assignment)")
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
        print(f"{'Rk':<3} | {'Team':<26} | {'Rating':<6} | {'GP':<3} | {'Record':<8} | {'Pts':<5} | {'Proj Pts':<8} | {'Proj Fin':<8} | {'Top 2 %':<8} | {'Top 4 %':<8} | {'Proj Pool':<10} | {'Pool Odds (A / B / C / D)'}")
        print("-" * 135)
        for rk, row in enumerate(ys_teams, 1):
            rec_str = f"{row['current_w']}-{row['current_l']}-{row['current_t']}"
            p_a = row['pool_probs'].get("Pool A", 0.0)
            p_b = row['pool_probs'].get("Pool B", 0.0)
            p_c = row['pool_probs'].get("Pool C", 0.0)
            p_d = row['pool_probs'].get("Pool D", 0.0)
            assigned_pool = get_assigned_pool("York-Simcoe", cohort, rk)
            odds_str = f"{p_a:.0f}% / {p_b:.0f}% / {p_c:.0f}% / {p_d:.0f}%"
            print(f"{rk:<3} | {row['team_name'][:24]:<26} | {row['mhr_rating']:<6.1f} | {row['current_gp']:<3} | {rec_str:<8} | {row['current_pts']:<5} | {row['proj_pts_avg']:<8.1f} | {row['proj_finish']:<8.1f} | {row['prob_top2_pct']:<7.1f}% | {row['prob_top4_pct']:<7.1f}% | {assigned_pool:<10} | {odds_str}")

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
        print(f"{'Rk':<3} | {'Team':<26} | {'Rating':<6} | {'GP':<3} | {'Record':<8} | {'Pts':<5} | {'Proj Pts':<8} | {'Proj Fin':<8} | {'Top 2 %':<8} | {'Top 4 %':<8} | {'Proj Pool':<10} | {'Pool A %':<8} | {'Pool B %'}")
        print("-" * 135)
        for rk, row in enumerate(ls_teams, 1):
            rec_str = f"{row['current_w']}-{row['current_l']}-{row['current_t']}"
            p_a = row['pool_probs'].get("Pool A", 0.0)
            p_b = row['pool_probs'].get("Pool B", 0.0)
            assigned_pool = get_assigned_pool("Lakeshore", cohort, rk)
            print(f"{rk:<3} | {row['team_name'][:24]:<26} | {row['mhr_rating']:<6.1f} | {row['current_gp']:<3} | {rec_str:<8} | {row['current_pts']:<5} | {row['proj_pts_avg']:<8.1f} | {row['proj_finish']:<8.1f} | {row['prob_top2_pct']:<7.1f}% | {row['prob_top4_pct']:<7.1f}% | {assigned_pool:<10} | {p_a:<7.1f}% | {p_b:<.1f}%")

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

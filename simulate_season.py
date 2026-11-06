import json
import math
import os
import random
import re
from collections import defaultdict
from functools import cmp_to_key
from datetime import datetime, timezone

# 1. Configuration & Parameters
SIMULATION_RUNS = 25000        # 25,000 runs balances precision (±0.2%) and execution speed
HOME_ICE_ADVANTAGE = 0.35      # MHR rating bonus for home ice
DEFAULT_MHR_RATING = 82.0       # Fallback rating if unranked
VOLATILITY_FACTOR = 0.70        # Softened delta factor (0.70) accounts for kid hockey volatility

# Bayesian Dynamic Rating Parameters
BAYESIAN_K = 8                  # Half-life: at 8 GP, weight is 50% MHR / 50% GameSheet performance
MAX_MARGIN_CAP = 5.0            # Caps blowout scores at ±5 goals (OMHA tournament standard)
MARGIN_TO_RATING_FACTOR = 0.75  # Conversion of average goal margin to MHR rating points

# Expected Regular Season Games by League
EXPECTED_GAMES_BY_LEAGUE = {
    "Tri-County": 26,
    "York-Simcoe": 26,
    "Lakeshore": 27
}

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

def is_regular_season_date(date_str):
    """Returns True if the date falls between October 1 and January 21 inclusive."""
    if not date_str or date_str in ["-", "TBD"]:
        return False
    s = str(date_str).strip()
    m = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', s)
    if m:
        month = int(m.group(2))
        day = int(m.group(3))
    else:
        m2 = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', s)
        if m2:
            month = int(m2.group(1))
            day = int(m2.group(2))
        else:
            months = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                      'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
            m3 = re.search(r'([a-zA-Z]{3,9})\s+(\d{1,2}),?\s+(\d{4})', s)
            if m3:
                month = months.get(m3.group(1)[:3].lower(), 0)
                day = int(m3.group(2))
            else:
                return False

    # Oct 1 - Dec 31
    if month in (10, 11, 12):
        return True
    # Jan 1 - Jan 21
    if month == 1 and 1 <= day <= 21:
        return True
    return False

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
    """Simulates realistic minor hockey scorelines using Poisson distributions and softened rating delta."""
    delta = (r_home + HOME_ICE_ADVANTAGE) - r_visitor
    expected_margin = delta * VOLATILITY_FACTOR
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

    team_opponents = defaultdict(list)
    team_margins = defaultdict(list)
    team_completed_games = defaultdict(list)
    team_upcoming_games = defaultdict(list)

    omha_games = omha_data.get("games", [])
    valid_final_games = 0

    # 1. Ingest Completed GameSheet Scores (Filtered: Oct 1 - Jan 21)
    for g in omha_games:
        if str(g.get("status", "")).lower() != "final":
            continue

        date_val = str(g.get("date") or "")
        if not is_regular_season_date(date_val):
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
        h_g = int(h_goals)
        v_g = int(v_goals)

        base_gp[(cohort, h_can)] += 1
        base_gp[(cohort, v_can)] += 1
        base_gf[(cohort, h_can)] += h_g
        base_ga[(cohort, h_can)] += v_g
        base_gf[(cohort, v_can)] += v_g
        base_ga[(cohort, v_can)] += h_g

        # Cap goal differential to prevent blowouts from skewing ratings
        margin = max(-MAX_MARGIN_CAP, min(MAX_MARGIN_CAP, float(h_g - v_g)))
        team_margins[(cohort, h_can)].append(margin)
        team_margins[(cohort, v_can)].append(-margin)
        team_opponents[(cohort, h_can)].append(v_can)
        team_opponents[(cohort, v_can)].append(h_can)

        h_res = "W" if h_g > v_g else ("L" if h_g < v_g else "T")
        v_res = "W" if v_g > h_g else ("L" if v_g < h_g else "T")

        if h_g > v_g:
            base_points[(cohort, h_can)] += 2
            base_wins[(cohort, h_can)] += 1
            base_losses[(cohort, v_can)] += 1
            base_h2h_pts[(cohort, h_can, v_can)] += 2
        elif v_g > h_g:
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

        loc_val = str(g.get("location") or "Arena")

        team_completed_games[(cohort, h_can)].append({
            "date": date_val,
            "opponent": v_can,
            "is_home": True,
            "team_goals": h_g,
            "opp_goals": v_g,
            "result": h_res,
            "location": loc_val
        })
        team_completed_games[(cohort, v_can)].append({
            "date": date_val,
            "opponent": h_can,
            "is_home": False,
            "team_goals": v_g,
            "opp_goals": h_g,
            "result": v_res,
            "location": loc_val
        })

    # 2. Ingest Scheduled Games from Calendar (Filtered: Oct 1 - Jan 21)
    remaining_games = []
    for g in all_games:
        if str(g.get("status", "")).lower() == "scheduled":
            date_val = str(g.get("date") or "")
            if not is_regular_season_date(date_val):
                continue

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
                "date": date_val,
                "time": str(g.get("time") or "TBD"),
                "location": str(g.get("location") or "Arena")
            })

            team_upcoming_games[(cohort, h_can)].append({
                "date": date_val,
                "time": str(g.get("time") or "TBD"),
                "opponent": v_can,
                "is_home": True,
                "location": str(g.get("location") or "Home Arena")
            })
            team_upcoming_games[(cohort, v_can)].append({
                "date": date_val,
                "time": str(g.get("time") or "TBD"),
                "opponent": h_can,
                "is_home": False,
                "location": str(g.get("location") or "Away Arena")
            })

    # 3. Calculate Bayesian Blended Ratings (MHR Prior + GameSheet Likelihood)
    effective_ratings = {}
    actual_ratings = {}
    actual_weights = {}

    for cohort in master_db:
        for team_name in master_db[cohort]:
            k = (cohort, team_name)
            r_mhr = get_team_rating(master_db, cohort, team_name)
            gp = base_gp[k]
            opps = team_opponents[k]
            margins = team_margins[k]

            if gp > 0 and len(opps) > 0:
                opp_ratings = [get_team_rating(master_db, cohort, opp) for opp in opps]
                avg_opp_rating = sum(opp_ratings) / len(opp_ratings)
                avg_margin = sum(margins) / len(margins)
                r_actual = avg_opp_rating + (avg_margin * MARGIN_TO_RATING_FACTOR)

                w_mhr = BAYESIAN_K / (BAYESIAN_K + gp)
                w_actual = 1.0 - w_mhr
                r_eff = (w_mhr * r_mhr) + (w_actual * r_actual)
            else:
                r_actual = r_mhr
                r_eff = r_mhr
                w_actual = 0.0

            effective_ratings[k] = r_eff
            actual_ratings[k] = r_actual
            actual_weights[k] = w_actual

    total_teams_count = len(master_db.get("U11 AA", {})) + len(master_db.get("U14 AA", {}))
    matched_teams_count = sum(1 for k in base_gp if base_gp[k] > 0)

    print("=" * 105)
    print(f"RUNNING MONTE CARLO SEASON SIMULATION ({SIMULATION_RUNS:,} iterations)")
    print(f"GameSheet Matches Processed:          {valid_final_games} (Window: Oct 1 - Jan 21)")
    print(f"Teams with Standings Computed:        {matched_teams_count} / {total_teams_count}")
    print(f"Remaining Games to Simulate:          {len(remaining_games)} (Window: Oct 1 - Jan 21)")
    print(f"Engine Calibration:                   Bayesian blend active (MHR prior + GameSheet MOV, K={BAYESIAN_K})")
    print(f"Kid Hockey Volatility Factor:         Margin delta = {VOLATILITY_FACTOR:.2f} (Upsets enabled)")
    print("=" * 105)

    # Build scheduled matchups using the effective Bayesian rating
    scheduled_matchups = []
    for g in remaining_games:
        cohort = g["cohort"]
        h_team = g["home"]
        v_team = g["visitor"]
        r_h = effective_ratings.get((cohort, h_team), get_team_rating(master_db, cohort, h_team))
        r_v = effective_ratings.get((cohort, v_team), get_team_rating(master_db, cohort, v_team))
        scheduled_matchups.append((cohort, h_team, v_team, r_h, r_v))

    sim_pts_totals = defaultdict(list)
    sim_rank_counts = defaultdict(lambda: defaultdict(int))

    # 4. Monte Carlo Simulation Engine
    for _ in range(SIMULATION_RUNS):
        cur_pts = defaultdict(int)
        cur_wins = defaultdict(int)
        cur_gf = defaultdict(int)
        cur_ga = defaultdict(int)
        cur_h2h = defaultdict(int)

        for (cohort, t), pts in base_points.items():
            cur_pts[(cohort, t)] = pts
            cur_wins[(cohort, t)] = base_wins[(cohort, t)]
            cur_gf[(cohort, t)] = base_gf[(cohort, t)]
            cur_ga[(cohort, t)] = base_ga[(cohort, t)]

        for (cohort, t1, t2), v in base_h2h_pts.items():
            cur_h2h[(cohort, t1, t2)] = v

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

    # 5. Compile Final Aggregations
    results = {}
    for cohort in ["U11 AA", "U14 AA"]:
        results[cohort] = {}
        for league in ["Tri-County", "York-Simcoe", "Lakeshore"]:
            results[cohort][league] = []

            for team_name, meta in master_db[cohort].items():
                if meta.get("league") != league:
                    continue

                k = (cohort, team_name)
                pts_list = sim_pts_totals[k]
                avg_pts = sum(pts_list) / len(pts_list) if pts_list else 0.0
                rank_dist = sim_rank_counts[k]

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

                comp_list = sorted(team_completed_games.get(k, []), key=lambda x: x.get("date", ""), reverse=True)
                up_list = sorted(team_upcoming_games.get(k, []), key=lambda x: (x.get("date", ""), x.get("time", "")))

                results[cohort][league].append({
                    "team_name": team_name,
                    "mhr_rating": get_team_rating(master_db, cohort, team_name),
                    "effective_rating": round(effective_ratings.get(k, get_team_rating(master_db, cohort, team_name)), 2),
                    "gamesheet_rating": round(actual_ratings.get(k, get_team_rating(master_db, cohort, team_name)), 2),
                    "gamesheet_weight_pct": round(actual_weights.get(k, 0.0) * 100, 1),
                    "current_gp": base_gp[k],
                    "current_pts": base_points[k],
                    "current_w": base_wins[k],
                    "current_l": base_losses[k],
                    "current_t": base_ties[k],
                    "proj_pts_avg": round(avg_pts, 1),
                    "proj_finish": round(exp_finish, 1),
                    "prob_1st_pct": round(p_first, 1),
                    "prob_top2_pct": round(p_top2, 1),
                    "prob_top4_pct": round(p_top4, 1),
                    "pool_probs": {name: round(prob, 1) for name, prob in pool_probs.items()},
                    "completed_games": comp_list,
                    "upcoming_games": up_list
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

    # Terminal Standings Reports
    for cohort in ["U11 AA", "U14 AA"]:
        for league in ["Tri-County", "York-Simcoe", "Lakeshore"]:
            teams = results[cohort][league]
            is_ys = (league == "York-Simcoe")
            top4_header = f" | {'Top 4 %':<8}" if is_ys else ""

            print(f"\n🏆 Projected Standings: [{cohort}] {league}")
            print(f"{'Rk':<3} | {'Team':<26} | {'GP':<3} | {'Record':<8} | {'Pts':<5} | {'Proj Pts':<8} | {'Proj Fin':<8} | {'Top 2 %':<8}{top4_header} | {'Proj Pool':<10} | {'MHR':<5} | {'Eff Rtg'}")
            print("-" * (132 if is_ys else 122))
            for rk, row in enumerate(teams, 1):
                rec_str = f"{row['current_w']}-{row['current_l']}-{row['current_t']}"
                assigned_pool = get_assigned_pool(league, cohort, rk)
                top4_val = f" | {row['prob_top4_pct']:<7.1f}%" if is_ys else ""
                print(f"{rk:<3} | {row['team_name'][:24]:<26} | {row['current_gp']:<3} | {rec_str:<8} | {row['current_pts']:<5} | {row['proj_pts_avg']:<8.1f} | {row['proj_finish']:<8.1f} | {row['prob_top2_pct']:<7.1f}%{top4_val} | {assigned_pool:<10} | {row['mhr_rating']:<5.1f} | {row['effective_rating']:<5.1f}")

if __name__ == "__main__":
    simulate()

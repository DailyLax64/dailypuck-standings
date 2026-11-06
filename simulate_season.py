<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
    <title>Daily Puck Standings | OMHA Analytics & Playoff Projections</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {
            background-color: #f0fdf9;
            background-image: 
                radial-gradient(at 0% 0%, rgba(20, 184, 166, 0.08) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(6, 182, 212, 0.09) 0px, transparent 50%),
                radial-gradient(at 50% 100%, rgba(16, 185, 129, 0.06) 0px, transparent 50%);
        }
        .neon-glow-cyan { box-shadow: 0 0 15px rgba(6, 182, 212, 0.35); }
        .neon-glow-mint { box-shadow: 0 0 15px rgba(20, 184, 166, 0.35); }
        .neon-card-glow { box-shadow: 0 4px 20px -2px rgba(13, 148, 136, 0.08), 0 0 1px 1px rgba(20, 184, 166, 0.2); }
        .neon-pill-active { box-shadow: 0 0 12px rgba(13, 148, 136, 0.4); }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeIn { animation: fadeIn 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        .touch-scroll { -webkit-overflow-scrolling: touch; }
    </style>
</head>
<body class="text-slate-900 font-sans antialiased min-h-screen flex flex-col selection:bg-teal-500 selection:text-white text-sm overflow-x-hidden">

    <!-- Header Navigation -->
    <header class="bg-white/95 backdrop-blur-md shadow-sm border-b border-teal-200/80 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-3 sm:px-6 py-2.5 sm:py-3.5 flex flex-col sm:flex-row justify-between items-center gap-3">
            <div class="flex items-center space-x-3 cursor-pointer" onclick="switchMainTab('standings')">
                <div class="bg-gradient-to-r from-teal-500 via-emerald-500 to-cyan-600 text-white font-black px-3.5 py-1.5 rounded-lg text-lg sm:text-2xl tracking-tight uppercase shadow-md transform -skew-x-6 flex items-baseline">
                    Daily Puck<span class="text-xs sm:text-sm font-black tracking-normal ml-1.5 uppercase text-teal-100">Standings</span>
                </div>
                <div class="hidden md:block pl-2 border-l border-teal-200">
                    <span class="block text-[10px] font-black tracking-widest text-teal-600 uppercase leading-none">Minor Hockey Hub</span>
                    <span class="text-xs text-slate-500 font-mono font-medium">OMHA AA League Intelligence</span>
                </div>
            </div>

            <!-- View Switcher Tabs -->
            <nav class="flex w-full sm:w-auto gap-1 bg-teal-50/80 p-1 rounded-xl border border-teal-200 justify-between sm:justify-start">
                <button onclick="switchMainTab('standings')" id="tab-standings" class="flex-1 sm:flex-initial text-center px-3.5 sm:px-5 py-1.5 rounded-lg text-xs sm:text-sm font-black uppercase tracking-wider transition-all bg-teal-600 text-white shadow-sm neon-pill-active">
                    Standings
                </button>
                <button onclick="switchMainTab('pools')" id="tab-pools" class="flex-1 sm:flex-initial text-center px-3.5 sm:px-5 py-1.5 rounded-lg text-xs sm:text-sm font-black uppercase tracking-wider text-slate-600 hover:text-teal-700 transition-all">
                    Playoff Pools
                </button>
                <button onclick="switchMainTab('simulator')" id="tab-simulator" class="flex-1 sm:flex-initial text-center px-3.5 sm:px-5 py-1.5 rounded-lg text-xs sm:text-sm font-black uppercase tracking-wider text-slate-600 hover:text-teal-700 transition-all flex items-center justify-center gap-1.5">
                    <span>⚡</span> Simulator
                </button>
            </nav>
        </div>
    </header>

    <!-- Main Content Canvas -->
    <main class="max-w-7xl w-full mx-auto px-3 sm:px-6 py-4 sm:py-6 flex-grow space-y-4 sm:space-y-6">

        <!-- Selector Filter Controls Card -->
        <section class="bg-white rounded-2xl p-4 sm:p-5 border border-teal-200 neon-card-glow flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 sm:gap-4">
            <div class="flex flex-wrap items-center gap-2 sm:gap-4">
                <!-- Cohort Selection -->
                <div class="flex items-center space-x-1.5">
                    <span class="text-[11px] font-mono font-bold uppercase tracking-wider text-teal-800">Age:</span>
                    <div class="inline-flex rounded-lg bg-teal-50 p-0.5 border border-teal-200">
                        <button onclick="setCohort('U11 AA')" id="cohort-btn-u11" class="px-3 py-1 rounded-md text-xs font-black uppercase tracking-wider bg-teal-600 text-white shadow-sm">U11 AA</button>
                        <button onclick="setCohort('U14 AA')" id="cohort-btn-u14" class="px-3 py-1 rounded-md text-xs font-black uppercase tracking-wider text-teal-900 hover:text-teal-700">U14 AA</button>
                    </div>
                </div>

                <!-- League Selection -->
                <div class="flex items-center space-x-1.5">
                    <span class="text-[11px] font-mono font-bold uppercase tracking-wider text-teal-800">League:</span>
                    <select id="league-select" onchange="onLeagueChange()" class="bg-teal-50/80 border border-teal-300 text-teal-950 font-black text-xs uppercase tracking-wider rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-teal-500 cursor-pointer">
                        <option value="Tri-County">Tri-County (15 Teams)</option>
                        <option value="York-Simcoe">York-Simcoe (12 Teams)</option>
                        <option value="Lakeshore">Lakeshore (10 Teams)</option>
                    </select>
                </div>
            </div>

            <!-- Quick Search Bar -->
            <div class="relative w-full sm:w-64">
                <input type="text" id="team-search-filter" oninput="onSearchInput()" placeholder="Search team..." class="w-full bg-teal-50/50 border border-teal-200 rounded-lg pl-8 pr-3 py-1.5 text-xs font-bold uppercase tracking-wider text-slate-800 focus:outline-none focus:border-teal-500 focus:bg-white placeholder-slate-400">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
            </div>
        </section>

        <!-- VIEW 1: STANDINGS PROJECTION MATRIX -->
        <section id="view-standings" class="tab-view space-y-4 animate-fadeIn">
            <div class="bg-white rounded-2xl border border-teal-200 neon-card-glow overflow-hidden shadow-sm">
                <div class="p-4 border-b border-teal-100 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 bg-gradient-to-r from-teal-50/70 to-emerald-50/50">
                    <div>
                        <h2 id="standings-table-title" class="text-base sm:text-lg font-black uppercase tracking-tight text-teal-950 flex items-center gap-2">
                            <span>🏆</span> Standings Matrix
                        </h2>
                        <p id="standings-table-subtitle" class="text-xs font-mono text-slate-500 mt-0.5">Click any team to expand their game results & upcoming calendar.</p>
                    </div>
                    <div id="standings-count-badge" class="px-2.5 py-1 rounded-md text-[11px] font-mono font-bold bg-teal-100/70 border border-teal-300 text-teal-800">
                        15 Teams
                    </div>
                </div>

                <div class="overflow-x-auto touch-scroll">
                    <table class="w-full text-left border-collapse whitespace-nowrap text-xs font-sans">
                        <thead>
                            <tr class="bg-teal-50/90 border-b border-teal-200 text-teal-900 text-[10px] sm:text-[11px] font-black uppercase tracking-wider select-none">
                                <th onclick="handleSort('team_name')" class="py-3 px-3 sm:px-4 cursor-pointer hover:text-teal-600">
                                    Team Name <span id="sort-icon-team_name" class="ml-0.5 text-slate-400"></span>
                                </th>
                                <th onclick="handleSort('current_gp')" class="py-3 px-2 text-center cursor-pointer hover:text-teal-600">
                                    GP <span id="sort-icon-current_gp" class="ml-0.5 text-slate-400"></span>
                                </th>
                                <th class="py-3 px-2 text-center">Record</th>
                                <th onclick="handleSort('current_pts')" class="py-3 px-3 text-center cursor-pointer text-teal-800 bg-teal-100/60 hover:text-teal-600">
                                    Cur Pts <span id="sort-icon-current_pts" class="ml-0.5 text-teal-600 font-black">▼</span>
                                </th>
                                <th onclick="handleSort('pt_pct')" class="py-3 px-2.5 text-center cursor-pointer hover:text-teal-600">
                                    Pt % <span id="sort-icon-pt_pct" class="ml-0.5 text-slate-400"></span>
                                </th>
                                <th onclick="handleSort('proj_pts_avg')" class="py-3 px-3 text-center cursor-pointer hover:text-teal-600">
                                    Proj Pts <span id="sort-icon-proj_pts_avg" class="ml-0.5 text-slate-400"></span>
                                </th>
                                <th onclick="handleSort('proj_finish')" class="py-3 px-3 text-center cursor-pointer hover:text-teal-600">
                                    Proj Fin <span id="sort-icon-proj_finish" class="ml-0.5 text-slate-400"></span>
                                </th>
                                <th onclick="handleSort('prob_top2_pct')" class="py-3 px-3 text-center cursor-pointer hover:text-teal-600">
                                    <span id="col-header-top2">Top 2 %</span> <span id="sort-icon-prob_top2_pct" class="ml-0.5 text-slate-400"></span>
                                </th>
                                <th id="col-header-top4" onclick="handleSort('prob_top4_pct')" class="py-3 px-3 text-center cursor-pointer hover:text-teal-600">
                                    Top 4 % <span id="sort-icon-prob_top4_pct" class="ml-0.5 text-slate-400"></span>
                                </th>
                                <th class="py-3 px-3 text-center">Projected Pool</th>
                                <th class="py-3 px-3 text-center hidden md:table-cell">Pool Odds Split</th>
                                <th onclick="handleSort('mhr_rating')" class="py-3 px-3 text-right cursor-pointer hover:text-teal-600">
                                    MHR <span id="sort-icon-mhr_rating" class="ml-0.5 text-slate-400"></span>
                                </th>
                            </tr>
                        </thead>
                        <tbody id="standings-tbody" class="divide-y divide-teal-100/80 font-medium"></tbody>
                    </table>
                </div>

                <!-- Pool Ranks Breakdown Footer -->
                <div class="px-4 py-2.5 bg-teal-50/50 border-t border-teal-100 text-xs font-mono text-slate-600">
                    <span id="standings-pool-ranks-summary"></span>
                </div>
            </div>
        </section>

        <!-- VIEW 2: DEDICATED PLAYOFF POOLS -->
        <section id="view-pools" class="tab-view hidden space-y-4 sm:space-y-6 animate-fadeIn">
            <div class="border-b border-teal-200/80 pb-3 flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                <div>
                    <h2 id="pools-view-title" class="text-base sm:text-xl font-black uppercase tracking-tight text-teal-950">
                        Playoff Groups Breakdown
                    </h2>
                    <p id="pools-view-subtitle" class="text-xs font-mono text-slate-500 mt-0.5">
                        Postseason groupings based on simulated regular season finish.
                    </p>
                </div>
                <div id="pools-qualification-pill" class="px-3 py-1 rounded-lg text-xs font-mono font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 w-fit">
                    Qualification Rules
                </div>
            </div>

            <!-- Pool Cards Grid -->
            <div id="pool-cards-container" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6"></div>
        </section>

        <!-- VIEW 3: INTERACTIVE WHAT-IF SIMULATOR -->
        <section id="view-simulator" class="tab-view hidden space-y-5 animate-fadeIn">
            <div class="bg-white rounded-2xl p-4 sm:p-5 border border-teal-200 neon-card-glow flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div>
                    <div class="flex items-center gap-2">
                        <span class="text-xl">⚡</span>
                        <h2 class="text-base sm:text-lg font-black uppercase tracking-tight text-teal-950">
                            Interactive What-If Simulator
                        </h2>
                    </div>
                    <p class="text-xs font-mono text-slate-500 mt-0.5">
                        Pick game winners below or leave them as "Simulate". Projections update in real time.
                    </p>
                </div>
                <div class="flex items-center gap-2">
                    <button onclick="resetSimulatorPicks()" class="px-3.5 py-1.5 rounded-lg text-xs font-black uppercase tracking-wider bg-slate-100 hover:bg-rose-50 text-slate-700 hover:text-rose-700 border border-slate-300 hover:border-rose-300 transition-all shadow-xs">
                        Reset All Picks
                    </button>
                    <div id="sim-user-picks-badge" class="px-3 py-1.5 rounded-lg text-xs font-mono font-black bg-teal-100 text-teal-800 border border-teal-300">
                        0 Custom Picks
                    </div>
                </div>
            </div>

            <!-- Simulator Split Grid: Matchup Picker on Left, Live Table on Right -->
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
                
                <!-- Left Column: Scheduled Fixtures Picker -->
                <div class="lg:col-span-5 bg-white rounded-2xl border border-teal-200 neon-card-glow p-4 space-y-3">
                    <div class="flex items-center justify-between pb-2 border-b border-teal-100">
                        <h3 class="font-black uppercase tracking-tight text-teal-950 text-xs sm:text-sm flex items-center gap-1.5">
                            <span>📅</span> Future Schedule Fixtures (<span id="sim-fixtures-count">0</span>)
                        </h3>
                        <select id="sim-team-filter" onchange="renderSimulatorFixtureList()" class="bg-teal-50 border border-teal-200 text-teal-900 text-xs font-bold rounded-lg px-2 py-1 max-w-[140px] truncate cursor-pointer">
                            <option value="">All Teams</option>
                        </select>
                    </div>

                    <div id="sim-fixtures-container" class="space-y-2.5 max-h-[680px] overflow-y-auto pr-1 touch-scroll">
                        <!-- Populated by renderSimulatorFixtureList() -->
                    </div>
                </div>

                <!-- Right Column: Live Recalculated Standings Table -->
                <div class="lg:col-span-7 bg-white rounded-2xl border border-teal-200 neon-card-glow overflow-hidden shadow-sm space-y-0">
                    <div class="p-3.5 sm:p-4 border-b border-teal-100 flex items-center justify-between bg-gradient-to-r from-teal-50/70 to-emerald-50/50">
                        <div>
                            <h3 class="font-black uppercase tracking-tight text-teal-950 text-xs sm:text-sm flex items-center gap-1.5">
                                <span>📊</span> Live Projected Standings Impact
                            </h3>
                            <p class="text-[11px] font-mono text-slate-500">Real-time Monte Carlo execution (1,500 runs per pick change)</p>
                        </div>
                        <span id="sim-calc-spinner" class="hidden text-xs font-mono text-teal-700 animate-pulse font-bold">Recalculating...</span>
                    </div>

                    <div class="overflow-x-auto touch-scroll">
                        <table class="w-full text-left border-collapse whitespace-nowrap text-xs font-sans">
                            <thead>
                                <tr class="bg-teal-50/90 border-b border-teal-200 text-teal-900 text-[10px] sm:text-[11px] font-black uppercase tracking-wider select-none">
                                    <th class="py-2.5 px-3">Team</th>
                                    <th class="py-2.5 px-2 text-center">GP</th>
                                    <th class="py-2.5 px-2.5 text-center bg-teal-100/50 text-teal-950 font-black">Pts</th>
                                    <th class="py-2.5 px-2.5 text-center font-bold">Proj Pts</th>
                                    <th class="py-2.5 px-2 text-center">Proj Fin</th>
                                    <th class="py-2.5 px-2.5 text-center">Top 2 %</th>
                                    <th class="py-2.5 px-3 text-center">Projected Pool</th>
                                </tr>
                            </thead>
                            <tbody id="sim-standings-tbody" class="divide-y divide-teal-100/80 font-medium font-sans">
                                <!-- Populated by renderSimulatorStandings() -->
                            </tbody>
                        </table>
                    </div>
                </div>

            </div>
        </section>

    </main>

    <!-- Global Layout Footer -->
    <footer class="bg-white text-center py-4 text-[10px] sm:text-xs font-mono text-slate-500 border-t border-teal-200 mt-auto uppercase tracking-wider">
        &copy; 2026 Daily Puck Standings & Analytics &bull; Connected to OMHA GameSheet & Team Webcals
    </footer>

    <!-- JavaScript Application Logic -->
    <script>
        let currentCohort = "U11 AA";
        let currentLeague = "Tri-County";
        let currentSearchQuery = "";
        let activeOpenAccordionTeam = null;

        // Default Sort State: Current Points Descending
        let currentSortColumn = "current_pts";
        let currentSortDirection = "desc";

        // Simulator State: Map of game_id -> 'home' | 'tie' | 'away' (or null if auto)
        let userGamePicks = {};

        // Official Expected Regular Season Game Counts by League
        const EXPECTED_GAMES_BY_LEAGUE = {
            "Tri-County": 26,
            "York-Simcoe": 26,
            "Lakeshore": 27
        };

        // Date Boundary Validator: October 1 to January 24 inclusive
        function isRegularSeasonDate(dateStr) {
            if (!dateStr || dateStr === '-' || dateStr === 'TBD') return false;
            const s = String(dateStr).trim();
            let month = 0, day = 0;
            const m1 = s.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})/);
            if (m1) {
                month = parseInt(m1[2], 10);
                day = parseInt(m1[3], 10);
            } else {
                const m2 = s.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{4})/);
                if (m2) {
                    month = parseInt(m2[1], 10);
                    day = parseInt(m2[2], 10);
                } else {
                    const months = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12 };
                    const m3 = s.match(/^([a-zA-Z]{3,9})\s+(\d{1,2}),?\s+(\d{4})/);
                    if (m3) {
                        month = months[m3[1].substring(0, 3).toLowerCase()] || 0;
                        day = parseInt(m3[2], 10);
                    }
                }
            }
            if (month >= 10 && month <= 12) return true;
            if (month === 1 && day >= 1 && day <= 24) return true;
            return false;
        }

        // Normalizes dates from any input format to standard YYYY-MM-DD
        function formatGameDate(dateStr) {
            if (!dateStr || dateStr === '-' || dateStr === 'TBD') return '-';
            const s = String(dateStr).trim();
            const m1 = s.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})/);
            if (m1) {
                return `${m1[1]}-${m1[2].padStart(2, '0')}-${m1[3].padStart(2, '0')}`;
            }
            const m2 = s.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{4})/);
            if (m2) {
                return `${m2[3]}-${m2[1].padStart(2, '0')}-${m2[2].padStart(2, '0')}`;
            }
            const months = { jan: '01', feb: '02', mar: '03', apr: '04', may: '05', jun: '06', jul: '07', aug: '08', sep: '09', oct: '10', nov: '11', dec: '12' };
            const m3 = s.match(/^([a-zA-Z]{3,9})\s+(\d{1,2}),?\s+(\d{4})/);
            if (m3) {
                const mon = months[m3[1].substring(0, 3).toLowerCase()] || '01';
                return `${m3[3]}-${mon}-${m3[2].padStart(2, '0')}`;
            }
            return s;
        }

        // Preloaded Fallback Simulation Baseline (with sample game logs)
        let simulationDatabase = {
            "U11 AA": {
                "Tri-County": [
                    { team_name: "Garden City Minor Falcons", mhr_rating: 89.7, current_gp: 7, current_w: 6, current_l: 1, current_t: 0, current_pts: 12, proj_pts_avg: 47.7, proj_finish: 1.0, prob_top2_pct: 99.8, prob_top4_pct: 100.0, pool_probs: { "Group A": 99.6, "Group B": 0.4, "Group C": 0.0 }, completed_games: [{ date: "2026-10-25", opponent: "Burlington Eagles", is_home: true, team_goals: 5, opp_goals: 2, result: "W", location: "Jack Gatecliff Arena" }], upcoming_games: [{ date: "2026-11-14", time: "14:00", opponent: "Centre Wellington Fusion", is_home: false, location: "CW Sportsplex" }] },
                    { team_name: "Centre Wellington Fusion", mhr_rating: 88.7, current_gp: 8, current_w: 5, current_l: 3, current_t: 0, current_pts: 10, proj_pts_avg: 38.1, proj_finish: 3.0, prob_top2_pct: 46.4, prob_top4_pct: 85.0, pool_probs: { "Group A": 19.6, "Group B": 36.9, "Group C": 43.5 }, completed_games: [], upcoming_games: [{ date: "2026-11-14", time: "14:00", opponent: "Garden City Minor Falcons", is_home: true, location: "CW Sportsplex" }] },
                    { team_name: "Burlington Eagles", mhr_rating: 87.9, current_gp: 8, current_w: 5, current_l: 2, current_t: 1, current_pts: 11, proj_pts_avg: 36.6, proj_finish: 3.8, prob_top2_pct: 20.7, prob_top4_pct: 75.0, pool_probs: { "Group A": 0.5, "Group B": 73.5, "Group C": 26.0 }, completed_games: [{ date: "2026-10-25", opponent: "Garden City Minor Falcons", is_home: false, team_goals: 2, opp_goals: 5, result: "L", location: "Jack Gatecliff Arena" }], upcoming_games: [{ date: "2026-11-08", time: "18:00", opponent: "Stoney Creek Warriors", is_home: true, location: "Central Arena" }] },
                    { team_name: "Norfolk Knights", mhr_rating: 87.8, current_gp: 8, current_w: 5, current_l: 3, current_t: 0, current_pts: 10, proj_pts_avg: 36.6, proj_finish: 3.7, prob_top2_pct: 22.5, prob_top4_pct: 76.0, pool_probs: { "Group A": 37.4, "Group B": 46.3, "Group C": 16.3 }, completed_games: [], upcoming_games: [] },
                    { team_name: "Guelph Gryphons", mhr_rating: 87.3, current_gp: 6, current_w: 4, current_l: 1, current_t: 1, current_pts: 9, proj_pts_avg: 34.0, proj_finish: 5.0, prob_top2_pct: 6.7, prob_top4_pct: 55.0, pool_probs: { "Group A": 1.2, "Group B": 28.7, "Group C": 70.1 }, completed_games: [], upcoming_games: [] },
                    { team_name: "Stoney Creek Warriors", mhr_rating: 87.3, current_gp: 9, current_w: 5, current_l: 2, current_t: 2, current_pts: 12, proj_pts_avg: 32.5, proj_finish: 5.7, prob_top2_pct: 2.6, prob_top4_pct: 35.0, pool_probs: { "Group A": 26.6, "Group B": 30.0, "Group C": 43.4 }, completed_games: [], upcoming_games: [{ date: "2026-11-08", time: "18:00", opponent: "Burlington Eagles", is_home: false, location: "Central Arena" }] },
                    { team_name: "Oakville Rangers", mhr_rating: 87.3, current_gp: 7, current_w: 4, current_l: 3, current_t: 0, current_pts: 8, proj_pts_avg: 31.3, proj_finish: 6.1, prob_top2_pct: 1.3, prob_top4_pct: 28.0, pool_probs: { "Group A": 27.0, "Group B": 41.2, "Group C": 31.8 }, completed_games: [], upcoming_games: [] },
                    { team_name: "Flamborough Sabres", mhr_rating: 86.3, current_gp: 6, current_w: 3, current_l: 3, current_t: 0, current_pts: 6, proj_pts_avg: 24.5, proj_finish: 8.8, prob_top2_pct: 0.0, prob_top4_pct: 2.0, pool_probs: { "Group A": 30.9, "Group B": 1.3, "Group C": 67.8 }, completed_games: [], upcoming_games: [] },
                    { team_name: "West Niagara Flying Aces", mhr_rating: 86.2, current_gp: 6, current_w: 2, current_l: 4, current_t: 0, current_pts: 4, proj_pts_avg: 23.6, proj_finish: 9.1, prob_top2_pct: 0.0, prob_top4_pct: 1.0, pool_probs: { "Group A": 26.8, "Group B": 41.5, "Group C": 31.7 }, completed_games: [], upcoming_games: [] },
                    { team_name: "Halton Hills Thunder", mhr_rating: 86.2, current_gp: 8, current_w: 2, current_l: 6, current_t: 0, current_pts: 4, proj_pts_avg: 22.0, proj_finish: 9.7, prob_top2_pct: 0.0, prob_top4_pct: 0.5, pool_probs: { "Group A": 47.7, "Group B": 36.7, "Group C": 15.6 }, completed_games: [], upcoming_games: [] },
                    { team_name: "Niagara Falls Canucks", mhr_rating: 85.6, current_gp: 7, current_w: 2, current_l: 5, current_t: 0, current_pts: 4, proj_pts_avg: 19.0, proj_finish: 11.0, prob_top2_pct: 0.0, prob_top4_pct: 0.0, pool_probs: { "Group A": 75.4, "Group B": 15.0, "Group C": 9.6 }, completed_games: [], upcoming_games: [] },
                    { team_name: "Glancaster Bombers", mhr_rating: 85.2, current_gp: 8, current_w: 4, current_l: 4, current_t: 0, current_pts: 8, proj_pts_avg: 17.7, proj_finish: 11.5, prob_top2_pct: 0.0, prob_top4_pct: 0.0, pool_probs: { "Group A": 76.0, "Group B": 14.0, "Group C": 10.0 }, completed_games: [], upcoming_games: [] },
                    { team_name: "Milton Winterhawks", mhr_rating: 85.0, current_gp: 6, current_w: 1, current_l: 3, current_t: 2, current_pts: 4, proj_pts_avg: 14.7, proj_finish: 12.6, prob_top2_pct: 0.0, prob_top4_pct: 0.0, pool_probs: { "Group A": 24.0, "Group B": 39.1, "Group C": 36.9 }, completed_games: [], upcoming_games: [] },
                    { team_name: "Brampton 45s", mhr_rating: 83.6, current_gp: 7, current_w: 1, current_l: 5, current_t: 1, current_pts: 3, proj_pts_avg: 8.6, proj_finish: 14.1, prob_top2_pct: 0.0, prob_top4_pct: 0.0, pool_probs: { "Group A": 0.0, "Group B": 98.3, "Group C": 1.7 }, completed_games: [], upcoming_games: [] },
                    { team_name: "Hamilton Steel", mhr_rating: 83.0, current_gp: 5, current_w: 0, current_l: 4, current_t: 1, current_pts: 1, proj_pts_avg: 5.0, proj_finish: 14.8, prob_top2_pct: 0.0, prob_top4_pct: 0.0, pool_probs: { "Group A": 6.3, "Group B": 1.7, "Group C": 92.0 }, completed_games: [], upcoming_games: [] }
                ]
            }
        };

        const POOL_DEFINITIONS = {
            "Tri-County": {
                "U11 AA": {
                    "Group A": { seeds: [1, 6, 10, 11, 12], desc: "Seeds 1, 6, 10, 11, 12" },
                    "Group B": { seeds: [2, 5, 8, 9, 15], desc: "Seeds 2, 5, 8, 9, 15" },
                    "Group C": { seeds: [3, 4, 7, 13, 14], desc: "Seeds 3, 4, 7, 13, 14" }
                },
                "U14 AA": {
                    "Group A": { seeds: [1, 6, 7, 12, 13], desc: "Double Round Robin (8 Games)" },
                    "Group B": { seeds: [2, 5, 9, 10], desc: "Triple Round Robin (9 Games)" },
                    "Group C": { seeds: [3, 4, 8, 11], desc: "Triple Round Robin (9 Games)" }
                }
            },
            "York-Simcoe": {
                "U11 AA": {
                    "Pool A": { seeds: [1, 11, 12], desc: "Seeds 1, 11, 12 (1st to Semis)" },
                    "Pool B": { seeds: [2, 9, 10], desc: "Seeds 2, 9, 10 (1st to Semis)" },
                    "Pool C": { seeds: [3, 7, 8], desc: "Seeds 3, 7, 8 (1st to Semis)" },
                    "Pool D": { seeds: [4, 5, 6], desc: "Seeds 4, 5, 6 (1st to Semis)" }
                },
                "U14 AA": {
                    "Pool A": { seeds: [1, 11, 12], desc: "Seeds 1, 11, 12 (1st to Semis)" },
                    "Pool B": { seeds: [2, 9, 10], desc: "Seeds 2, 9, 10 (1st to Semis)" },
                    "Pool C": { seeds: [3, 7, 8], desc: "Seeds 3, 7, 8 (1st to Semis)" },
                    "Pool D": { seeds: [4, 5, 6], desc: "Seeds 4, 5, 6 (1st to Semis)" }
                }
            },
            "Lakeshore": {
                "U11 AA": {
                    "Pool A": { seeds: [1, 4, 6, 8, 10], desc: "5-Team Round Robin (Top 2 to Semis)" },
                    "Pool B": { seeds: [2, 3, 5, 7, 9], desc: "5-Team Round Robin (Top 2 to Semis)" }
                },
                "U14 AA": {
                    "Pool A": { seeds: [1, 4, 6, 8, 10], desc: "5-Team Round Robin (Top 2 to Semis)" },
                    "Pool B": { seeds: [2, 3, 5, 7, 9], desc: "5-Team Round Robin (Top 2 to Semis)" }
                }
            }
        };

        function switchMainTab(tabId) {
            document.querySelectorAll('.tab-view').forEach(el => el.classList.add('hidden'));
            const target = document.getElementById('view-' + tabId);
            if (target) target.classList.remove('hidden');

            const btnStandings = document.getElementById('tab-standings');
            const btnPools = document.getElementById('tab-pools');
            const btnSim = document.getElementById('tab-simulator');

            [btnStandings, btnPools, btnSim].forEach(b => {
                b.className = "flex-1 sm:flex-initial text-center px-3.5 sm:px-5 py-1.5 rounded-lg text-xs sm:text-sm font-black uppercase tracking-wider text-slate-600 hover:text-teal-700 transition-all";
            });

            const activeBtn = document.getElementById('tab-' + tabId);
            activeBtn.className = "flex-1 sm:flex-initial text-center px-3.5 sm:px-5 py-1.5 rounded-lg text-xs sm:text-sm font-black uppercase tracking-wider transition-all bg-teal-600 text-white shadow-sm neon-pill-active";

            if (tabId === 'standings') renderStandingsTable();
            else if (tabId === 'pools') renderPoolCards();
            else if (tabId === 'simulator') renderSimulatorTab();
        }

        function setCohort(cohort) {
            currentCohort = cohort;
            document.getElementById('cohort-btn-u11').className = cohort === 'U11 AA' 
                ? "px-3 py-1 rounded-md text-xs font-black uppercase tracking-wider bg-teal-600 text-white shadow-sm"
                : "px-3 py-1 rounded-md text-xs font-black uppercase tracking-wider text-teal-900 hover:text-teal-700";
            document.getElementById('cohort-btn-u14').className = cohort === 'U14 AA' 
                ? "px-3 py-1 rounded-md text-xs font-black uppercase tracking-wider bg-teal-600 text-white shadow-sm"
                : "px-3 py-1 rounded-md text-xs font-black uppercase tracking-wider text-teal-900 hover:text-teal-700";

            activeOpenAccordionTeam = null;
            userGamePicks = {};
            renderCurrentView();
        }

        function onLeagueChange() {
            currentLeague = document.getElementById('league-select').value;
            activeOpenAccordionTeam = null;
            userGamePicks = {};
            renderCurrentView();
        }

        function onSearchInput() {
            currentSearchQuery = document.getElementById('team-search-filter').value.trim().toLowerCase();
            renderCurrentView();
        }

        function renderCurrentView() {
            if (!document.getElementById('view-standings').classList.contains('hidden')) {
                renderStandingsTable();
            } else if (!document.getElementById('view-pools').classList.contains('hidden')) {
                renderPoolCards();
            } else {
                renderSimulatorTab();
            }
        }

        function handleSort(column) {
            if (currentSortColumn === column) {
                currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                currentSortColumn = column;
                currentSortDirection = (column === 'team_name' || column === 'proj_finish') ? 'asc' : 'desc';
            }
            renderStandingsTable();
        }

        function toggleTeamAccordion(teamName) {
            if (activeOpenAccordionTeam === teamName) {
                activeOpenAccordionTeam = null;
            } else {
                activeOpenAccordionTeam = teamName;
            }
            renderStandingsTable();
        }

        function getActiveTeams() {
            const cohortData = simulationDatabase[currentCohort] || {};
            let teams = cohortData[currentLeague] || [];
            if (currentSearchQuery) {
                teams = teams.filter(t => t.team_name.toLowerCase().includes(currentSearchQuery));
            }

            // Dynamically ensure self-healing regular season GP and Point Percentages
            teams.forEach(t => {
                const comp = (t.completed_games || []).filter(g => isRegularSeasonDate(g.date));
                const effectiveGp = (t.completed_games && t.completed_games.length > 0) ? comp.length : (t.current_gp || 0);
                let effectivePts = t.current_pts || 0;
                if (t.completed_games && t.completed_games.length > 0 && comp.length !== t.completed_games.length) {
                    const w = comp.filter(g => g.result === 'W').length;
                    const ti = comp.filter(g => g.result === 'T').length;
                    effectivePts = (w * 2) + ti;
                }
                t.effective_gp = effectiveGp;
                t.effective_pts = effectivePts;
                t.pt_pct = effectiveGp > 0 ? ((effectivePts / (effectiveGp * 2)) * 100) : 0.0;
            });

            return [...teams].sort((a, b) => {
                let valA = a[currentSortColumn];
                let valB = b[currentSortColumn];
                if (currentSortColumn === 'current_pts') {
                    valA = a.effective_pts;
                    valB = b.effective_pts;
                } else if (currentSortColumn === 'current_gp') {
                    valA = a.effective_gp;
                    valB = b.effective_gp;
                }
                if (typeof valA === 'string') {
                    return currentSortDirection === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
                }
                return currentSortDirection === 'asc' ? valA - valB : valB - valA;
            });
        }

        function getProjectedPoolAssignment(team, cohort, league, projRank) {
            if (team && team.pool_probs && Object.keys(team.pool_probs).length > 0) {
                const bestPool = Object.entries(team.pool_probs).sort((a, b) => b[1] - a[1])[0];
                if (bestPool && bestPool[1] > 0) return bestPool[0];
            }
            const leaguePools = POOL_DEFINITIONS[league]?.[cohort] || {};
            for (const [poolName, data] of Object.entries(leaguePools)) {
                if (data.seeds.includes(projRank)) return poolName;
            }
            return "-";
        }

        function renderStandingsTable() {
            const tbody = document.getElementById('standings-tbody');
            const teams = getActiveTeams();
            const isYorkSimcoe = currentLeague === "York-Simcoe";
            const expectedGames = EXPECTED_GAMES_BY_LEAGUE[currentLeague] || 26;

            document.getElementById('standings-table-title').innerHTML = `<span>🏒</span> [${currentCohort}] ${currentLeague} Standings Matrix`;
            document.getElementById('standings-count-badge').innerText = `${teams.length} Teams`;

            const top4Header = document.getElementById('col-header-top4');
            if (top4Header) {
                if (isYorkSimcoe) top4Header.classList.remove('hidden');
                else top4Header.classList.add('hidden');
            }

            const top2Header = document.getElementById('col-header-top2');
            if (top2Header) {
                top2Header.innerText = currentLeague === 'Tri-County' ? 'Top 2 % (Bye)' : 'Top 2 %';
            }

            ['team_name', 'current_gp', 'current_pts', 'pt_pct', 'proj_pts_avg', 'proj_finish', 'prob_top2_pct', 'prob_top4_pct', 'mhr_rating'].forEach(col => {
                const iconEl = document.getElementById('sort-icon-' + col);
                if (iconEl) {
                    if (currentSortColumn === col) {
                        iconEl.innerText = currentSortDirection === 'asc' ? '▲' : '▼';
                        iconEl.className = "ml-0.5 text-teal-600 font-black";
                    } else {
                        iconEl.innerText = '';
                    }
                }
            });

            tbody.innerHTML = '';
            if (teams.length === 0) {
                tbody.innerHTML = `<tr><td colspan="12" class="py-8 text-center text-slate-400 font-mono text-xs uppercase">No teams found.</td></tr>`;
                return;
            }

            teams.forEach((t) => {
                const isOpen = activeOpenAccordionTeam === t.team_name;
                const projectedSeed = Math.round(t.proj_finish) || 1;
                const assignedPool = getProjectedPoolAssignment(t, currentCohort, currentLeague, projectedSeed);

                // Filter games strictly to regular season window (Oct 1 - Jan 24)
                const filteredComp = (t.completed_games || []).filter(g => isRegularSeasonDate(g.date));
                const filteredUp = (t.upcoming_games || []).filter(g => isRegularSeasonDate(g.date));

                // Self-healing regular season tallies
                let effectiveGp = (t.completed_games && t.completed_games.length > 0) ? filteredComp.length : (t.current_gp || 0);
                let effectivePts = t.current_pts || 0;
                let effectiveW = t.current_w || 0;
                let effectiveL = t.current_l || 0;
                let effectiveT = t.current_t || 0;

                if (t.completed_games && t.completed_games.length > 0 && filteredComp.length !== t.completed_games.length) {
                    effectiveW = filteredComp.filter(g => g.result === 'W').length;
                    effectiveL = filteredComp.filter(g => g.result === 'L').length;
                    effectiveT = filteredComp.filter(g => g.result === 'T').length;
                    effectivePts = (effectiveW * 2) + effectiveT;
                }

                const recStr = `${effectiveW}-${effectiveL}-${effectiveT}`;
                const ptPct = effectiveGp > 0 ? ((effectivePts / (effectiveGp * 2)) * 100) : 0.0;

                // Anomaly check: Add hazard icon if total regular season games != expected
                const totalRegularSeasonGames = effectiveGp + filteredUp.length;
                const hasScheduleDiscrepancy = totalRegularSeasonGames !== expectedGames;
                const hazardBadge = hasScheduleDiscrepancy 
                    ? `<span title="Schedule Discrepancy: ${totalRegularSeasonGames} of ${expectedGames} regular season games recorded (Oct 1 - Jan 24)" class="ml-1.5 cursor-help text-amber-500 font-bold select-none text-xs">⚠️</span>`
                    : '';

                let poolOddsStr = "";
                if (t.pool_probs) {
                    poolOddsStr = Object.entries(t.pool_probs).map(([k, v]) => `${k.replace('Group ', 'G').replace('Pool ', 'P')}: ${v.toFixed(0)}%`).join(' &bull; ');
                }

                const top4Cell = isYorkSimcoe ? `<td class="py-3 px-3 text-center font-mono font-bold text-slate-800">${t.prob_top4_pct.toFixed(1)}%</td>` : '';
                const escapeName = t.team_name.replace(/'/g, "\\'");

                const rowHtml = `
                    <tr onclick="toggleTeamAccordion('${escapeName}')" class="hover:bg-teal-50/70 transition-colors border-b border-teal-100/60 cursor-pointer ${isOpen ? 'bg-teal-50/90' : ''}">
                        <td class="py-3 px-3 sm:px-4 font-black uppercase text-teal-950 flex items-center justify-between">
                            <span class="flex items-center">
                                ${t.team_name}
                                ${hazardBadge}
                            </span>
                            <span class="text-[10px] font-mono text-teal-600 ml-2">${isOpen ? '▲' : '▼'}</span>
                        </td>
                        <td class="py-3 px-2 text-center font-mono text-slate-600">${effectiveGp}</td>
                        <td class="py-3 px-2 text-center font-mono text-slate-700">${recStr}</td>
                        <td class="py-3 px-3 text-center font-mono font-black text-teal-900 bg-teal-50/50">${effectivePts}</td>
                        <td class="py-3 px-2.5 text-center font-mono font-bold text-slate-700">${ptPct.toFixed(1)}%</td>
                        <td class="py-3 px-3 text-center font-mono font-black text-cyan-700">${t.proj_pts_avg.toFixed(1)}</td>
                        <td class="py-3 px-3 text-center font-mono font-black text-slate-900">#${t.proj_finish.toFixed(1)}</td>
                        <td class="py-3 px-3 text-center font-mono font-bold text-slate-800">${t.prob_top2_pct.toFixed(1)}%</td>
                        ${top4Cell}
                        <td class="py-3 px-3 text-center font-mono font-black text-teal-900">${assignedPool}</td>
                        <td class="py-3 px-3 text-center font-mono text-[11px] text-slate-500 hidden md:table-cell">${poolOddsStr}</td>
                        <td class="py-3 px-3 text-right font-mono font-bold text-slate-700">${t.mhr_rating ? t.mhr_rating.toFixed(1) : '-'}</td>
                    </tr>
                `;

                let drawerHtml = "";
                if (isOpen) {
                    // Show completed games in chronological order (earliest to latest) filtered to regular season
                    const compGames = [...filteredComp].sort((a, b) => {
                        const da = formatGameDate(a.date) || a.date || '';
                        const db = formatGameDate(b.date) || b.date || '';
                        return da.localeCompare(db);
                    });

                    // Show upcoming games in chronological order filtered to regular season
                    const upGames = [...filteredUp].sort((a, b) => {
                        const da = formatGameDate(a.date) || a.date || '';
                        const db = formatGameDate(b.date) || b.date || '';
                        return da.localeCompare(db);
                    });

                    let compRows = compGames.map(g => {
                        const resBadge = g.result === 'W' 
                            ? '<span class="px-1.5 py-0.5 rounded text-[10px] font-black bg-emerald-100 text-emerald-800 border border-emerald-300">W</span>'
                            : (g.result === 'L' ? '<span class="px-1.5 py-0.5 rounded text-[10px] font-black bg-rose-100 text-rose-800 border border-rose-300">L</span>'
                            : '<span class="px-1.5 py-0.5 rounded text-[10px] font-black bg-amber-100 text-amber-800 border border-amber-300">T</span>');

                        return `
                            <tr class="border-b border-teal-100/60 text-xs font-mono">
                                <td class="py-1.5 px-2 text-slate-500 whitespace-nowrap">${formatGameDate(g.date)}</td>
                                <td class="py-1.5 px-2 text-slate-800 font-sans font-bold">
                                    <span class="text-slate-400 font-normal mr-1">${g.is_home ? 'vs' : '@'}</span>${g.opponent}
                                </td>
                                <td class="py-1.5 px-2 text-center">${resBadge}</td>
                                <td class="py-1.5 px-2 text-center font-black text-slate-900">${g.team_goals} - ${g.opp_goals}</td>
                                <td class="py-1.5 px-2 text-slate-500 truncate max-w-[120px]">${g.location || 'Local Arena'}</td>
                            </tr>
                        `;
                    }).join('');

                    if (compGames.length === 0) {
                        compRows = `<tr><td colspan="5" class="py-4 text-center text-xs font-mono text-slate-400">No completed regular season games recorded yet.</td></tr>`;
                    }

                    // Upcoming games without game time column
                    let upRows = upGames.map(g => {
                        return `
                            <tr class="border-b border-teal-100/60 text-xs font-mono">
                                <td class="py-1.5 px-2 text-slate-500 whitespace-nowrap">${formatGameDate(g.date)}</td>
                                <td class="py-1.5 px-2 text-slate-800 font-sans font-bold">
                                    <span class="text-slate-400 font-normal mr-1">${g.is_home ? 'vs' : '@'}</span>${g.opponent}
                                </td>
                                <td class="py-1.5 px-2 text-slate-500 truncate max-w-[140px]">${g.location || 'Home/Away Arena'}</td>
                            </tr>
                        `;
                    }).join('');

                    if (upGames.length === 0) {
                        upRows = `<tr><td colspan="3" class="py-4 text-center text-xs font-mono text-slate-400">No remaining regular season games scheduled on calendar.</td></tr>`;
                    }

                    drawerHtml = `
                        <tr class="bg-teal-50/40 border-b border-teal-200 animate-fadeIn">
                            <td colspan="12" class="p-3 sm:p-5">
                                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                    <!-- Completed Box Scores -->
                                    <div class="bg-white rounded-xl border border-teal-200 p-3 shadow-sm">
                                        <div class="flex items-center justify-between pb-2 mb-2 border-b border-teal-100">
                                            <span class="text-xs font-black uppercase tracking-wider text-teal-900 flex items-center gap-1.5">
                                                <span>🏁</span> Completed Results (${compGames.length})
                                            </span>
                                            <span class="text-[10px] font-mono text-slate-400 uppercase">GameSheet Verified</span>
                                        </div>
                                        <div class="overflow-x-auto touch-scroll max-h-56 overflow-y-auto">
                                            <table class="w-full text-left">
                                                <thead>
                                                    <tr class="text-[10px] font-mono text-slate-400 uppercase border-b border-teal-100">
                                                        <th class="py-1 px-2">Date</th>
                                                        <th class="py-1 px-2">Opponent</th>
                                                        <th class="py-1 px-2 text-center">Res</th>
                                                        <th class="py-1 px-2 text-center">Score</th>
                                                        <th class="py-1 px-2">Venue</th>
                                                    </tr>
                                                </thead>
                                                <tbody>${compRows}</tbody>
                                            </table>
                                        </div>
                                    </div>

                                    <!-- Upcoming Schedule -->
                                    <div class="bg-white rounded-xl border border-teal-200 p-3 shadow-sm">
                                        <div class="flex items-center justify-between pb-2 mb-2 border-b border-teal-100">
                                            <span class="text-xs font-black uppercase tracking-wider text-teal-900 flex items-center gap-1.5">
                                                <span>📅</span> Upcoming Games (${upGames.length})
                                            </span>
                                            <span class="text-[10px] font-mono text-slate-400 uppercase">Regular Season (through Jan 24)</span>
                                        </div>
                                        <div class="overflow-x-auto touch-scroll max-h-56 overflow-y-auto">
                                            <table class="w-full text-left">
                                                <thead>
                                                    <tr class="text-[10px] font-mono text-slate-400 uppercase border-b border-teal-100">
                                                        <th class="py-1 px-2">Date</th>
                                                        <th class="py-1 px-2">Opponent</th>
                                                        <th class="py-1 px-2">Venue</th>
                                                    </tr>
                                                </thead>
                                                <tbody>${upRows}</tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </td>
                        </tr>
                    `;
                }

                tbody.innerHTML += rowHtml + drawerHtml;
            });

            // Update Pool Ranks Summary Text Below Standings Table
            const poolSummaryEl = document.getElementById('standings-pool-ranks-summary');
            if (poolSummaryEl) {
                const leaguePools = POOL_DEFINITIONS[currentLeague]?.[currentCohort] || {};
                const parts = Object.entries(leaguePools).map(([pName, pData]) => `<strong>${pName}:</strong> Ranks ${pData.seeds.join(', ')}`);
                poolSummaryEl.innerHTML = `<span class="text-teal-900 font-bold uppercase tracking-wider text-[11px]">Pool Placement by Rank:</span> ${parts.join(' &nbsp; &bull; &nbsp; ')}`;
            }
        }

        function renderPoolCards() {
            const container = document.getElementById('pool-cards-container');
            const cohortData = simulationDatabase[currentCohort] || {};
            const teams = cohortData[currentLeague] || [];

            document.getElementById('pools-view-title').innerText = `🏒 [${currentCohort}] ${currentLeague} Projected Playoff Pools`;
            
            const pillEl = document.getElementById('pools-qualification-pill');
            if (currentLeague === 'Tri-County') {
                pillEl.innerText = "Top 2 in each pool advance to Semifinals (Seeds 1 & 2 receive round-robin byes)";
            } else if (currentLeague === 'York-Simcoe') {
                pillEl.innerText = "1st Place in each pool moves on to YMSHL Semifinals";
            } else {
                pillEl.innerText = "Top 2 teams in each pool advance to Crossover Semifinals";
            }

            const leaguePools = POOL_DEFINITIONS[currentLeague]?.[currentCohort] || {};
            container.innerHTML = '';

            const sortedByProj = [...teams].sort((a, b) => a.proj_finish - b.proj_finish);

            Object.entries(leaguePools).forEach(([poolName, data]) => {
                let teamRowsHtml = '';

                data.seeds.forEach(s => {
                    if (s <= sortedByProj.length) {
                        const t = sortedByProj[s - 1];
                        const oddsVal = t.pool_probs?.[poolName] || 0.0;

                        teamRowsHtml += `
                            <div class="flex items-center justify-between p-2 rounded-lg bg-teal-50/60 border border-teal-100">
                                <div class="flex items-center space-x-2 truncate">
                                    <span class="w-6 h-6 rounded-md bg-teal-600 text-white font-mono font-black text-xs flex items-center justify-center flex-shrink-0">#${s}</span>
                                    <span class="font-bold text-xs uppercase text-slate-800 truncate">${t.team_name}</span>
                                </div>
                                <div class="text-right flex-shrink-0 font-mono text-xs">
                                    <span class="font-black text-teal-800">${oddsVal.toFixed(0)}%</span>
                                </div>
                            </div>
                        `;
                    }
                });

                container.innerHTML += `
                    <div class="bg-white rounded-2xl border border-teal-200 neon-card-glow p-4 space-y-3">
                        <div class="flex items-center justify-between pb-2 border-b border-teal-100">
                            <div>
                                <h3 class="font-black uppercase text-teal-950 text-sm tracking-tight">${poolName}</h3>
                                <p class="text-[10px] font-mono text-slate-400 mt-0.5">${data.desc}</p>
                            </div>
                            <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-teal-100 text-teal-800">${data.seeds.length} Teams</span>
                        </div>
                        <div class="space-y-1.5">${teamRowsHtml}</div>
                    </div>
                `;
            });
        }

        // =========================================================================
        // ⚡ REAL-TIME INTERACTIVE WHAT-IF SIMULATOR ENGINE
        // =========================================================================

        function extractMasterScheduledFixtures(cohort, league) {
            const cohortData = simulationDatabase[cohort] || {};
            const teams = cohortData[league] || [];
            const fixturesMap = new Map();

            teams.forEach(t => {
                (t.upcoming_games || []).forEach(g => {
                    // Strictly exclude games outside regular season window (Oct 1 - Jan 24)
                    if (!isRegularSeasonDate(g.date)) return;

                    const homeTeam = g.is_home ? t.team_name : g.opponent;
                    const awayTeam = g.is_home ? g.opponent : t.team_name;
                    const gameDate = formatGameDate(g.date);
                    const key = `${gameDate}_${homeTeam}_${awayTeam}`;

                    if (!fixturesMap.has(key)) {
                        fixturesMap.set(key, {
                            id: key,
                            date: gameDate,
                            time: g.time || 'TBD',
                            home: homeTeam,
                            away: awayTeam,
                            location: g.location || 'Local Rink'
                        });
                    }
                });
            });

            return Array.from(fixturesMap.values()).sort((a, b) => {
                const dateCmp = (a.date || '').localeCompare(b.date || '');
                return dateCmp !== 0 ? dateCmp : (a.time || '').localeCompare(b.time || '');
            });
        }

        function renderSimulatorTab() {
            populateSimulatorTeamFilter();
            renderSimulatorFixtureList();
            runClientSideSimulation();
        }

        function populateSimulatorTeamFilter() {
            const selectEl = document.getElementById('sim-team-filter');
            const cohortData = simulationDatabase[currentCohort] || {};
            const teams = (cohortData[currentLeague] || []).map(t => t.team_name).sort();

            const curVal = selectEl.value;
            selectEl.innerHTML = '<option value="">All Teams</option>';
            teams.forEach(t => {
                const opt = document.createElement('option');
                opt.value = t;
                opt.textContent = t;
                selectEl.appendChild(opt);
            });
            selectEl.value = teams.includes(curVal) ? curVal : '';
        }

        function setSimulatorPick(gameId, pickResult) {
            if (pickResult === 'auto') {
                delete userGamePicks[gameId];
            } else {
                userGamePicks[gameId] = pickResult;
            }
            renderSimulatorFixtureList();
            runClientSideSimulation();
        }

        function resetSimulatorPicks() {
            userGamePicks = {};
            renderSimulatorFixtureList();
            runClientSideSimulation();
        }

        function renderSimulatorFixtureList() {
            const container = document.getElementById('sim-fixtures-container');
            const filterTeam = document.getElementById('sim-team-filter').value;
            let fixtures = extractMasterScheduledFixtures(currentCohort, currentLeague);

            document.getElementById('sim-fixtures-count').innerText = fixtures.length;
            const customPicksCount = Object.keys(userGamePicks).length;
            document.getElementById('sim-user-picks-badge').innerText = `${customPicksCount} Custom Pick${customPicksCount === 1 ? '' : 's'}`;

            if (filterTeam) {
                fixtures = fixtures.filter(f => f.home === filterTeam || f.away === filterTeam);
            }

            if (fixtures.length === 0) {
                container.innerHTML = `<div class="py-8 text-center text-xs font-mono text-slate-400">No scheduled regular season fixtures found.</div>`;
                return;
            }

            container.innerHTML = fixtures.map(f => {
                const curPick = userGamePicks[f.id] || 'auto';

                const btnHomeClass = curPick === 'home' 
                    ? 'bg-emerald-600 text-white font-black border-emerald-600 shadow-sm' 
                    : 'bg-white hover:bg-slate-50 text-slate-700 border-slate-300';
                const btnTieClass = curPick === 'tie' 
                    ? 'bg-amber-500 text-white font-black border-amber-500 shadow-sm' 
                    : 'bg-white hover:bg-slate-50 text-slate-700 border-slate-300';
                const btnAwayClass = curPick === 'away' 
                    ? 'bg-emerald-600 text-white font-black border-emerald-600 shadow-sm' 
                    : 'bg-white hover:bg-slate-50 text-slate-700 border-slate-300';
                const btnAutoClass = curPick === 'auto' 
                    ? 'bg-teal-700 text-white font-black border-teal-700 shadow-sm' 
                    : 'bg-white hover:bg-slate-50 text-slate-500 border-slate-200';

                return `
                    <div class="p-2.5 rounded-xl border border-teal-100 bg-white/90 space-y-2 text-xs shadow-xs">
                        <div class="flex items-center justify-between text-[11px] font-mono text-slate-400 border-b border-teal-50 pb-1">
                            <span>${f.date}</span>
                            <span class="truncate max-w-[140px]">${f.location}</span>
                        </div>
                        <div class="flex items-center justify-between font-bold text-slate-900">
                            <span class="truncate text-left flex-1">${f.home}</span>
                            <span class="text-slate-400 font-mono text-[10px] px-2 font-normal">vs</span>
                            <span class="truncate text-right flex-1">${f.away}</span>
                        </div>
                        <!-- Result Pick Toggles -->
                        <div class="grid grid-cols-4 gap-1 text-[11px] font-mono pt-1">
                            <button onclick="setSimulatorPick('${f.id}', 'home')" class="py-1 px-1 rounded-md border text-center font-bold transition ${btnHomeClass}">
                                Home Win
                            </button>
                            <button onclick="setSimulatorPick('${f.id}', 'tie')" class="py-1 px-1 rounded-md border text-center font-bold transition ${btnTieClass}">
                                Tie
                            </button>
                            <button onclick="setSimulatorPick('${f.id}', 'away')" class="py-1 px-1 rounded-md border text-center font-bold transition ${btnAwayClass}">
                                Away Win
                            </button>
                            <button onclick="setSimulatorPick('${f.id}', 'auto')" class="py-1 px-1 rounded-md border text-center font-semibold transition ${btnAutoClass}">
                                Auto Sim
                            </button>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // Fast Client-Side Poisson Sample Generator
        function samplePoisson(lambda) {
            const L = Math.exp(-lambda);
            let k = 0;
            let p = 1.0;
            do {
                k++;
                p *= Math.random();
            } while (p > L);
            return k - 1;
        }

        function runClientSideSimulation() {
            const spinner = document.getElementById('sim-calc-spinner');
            if (spinner) spinner.classList.remove('hidden');

            setTimeout(() => {
                const cohortData = simulationDatabase[currentCohort] || {};
                const teams = cohortData[currentLeague] || [];
                const fixtures = extractMasterScheduledFixtures(currentCohort, currentLeague);

                // Calculate added points and GP based on user-picked games
                const addedPts = {};
                const addedGp = {};
                teams.forEach(t => {
                    addedPts[t.team_name] = 0;
                    addedGp[t.team_name] = 0;
                });

                fixtures.forEach(f => {
                    const pick = userGamePicks[f.id];
                    if (pick && pick !== 'auto') {
                        addedGp[f.home] = (addedGp[f.home] || 0) + 1;
                        addedGp[f.away] = (addedGp[f.away] || 0) + 1;
                        if (pick === 'home') {
                            addedPts[f.home] = (addedPts[f.home] || 0) + 2;
                        } else if (pick === 'away') {
                            addedPts[f.away] = (addedPts[f.away] || 0) + 2;
                        } else if (pick === 'tie') {
                            addedPts[f.home] = (addedPts[f.home] || 0) + 1;
                            addedPts[f.away] = (addedPts[f.away] || 0) + 1;
                        }
                    }
                });

                const teamRatings = {};
                teams.forEach(t => {
                    teamRatings[t.team_name] = t.effective_rating || t.mhr_rating || 82.0;
                });

                const SIM_RUNS = 1500;
                const pointTotals = {};
                const rankCounts = {};
                teams.forEach(t => {
                    pointTotals[t.team_name] = [];
                    rankCounts[t.team_name] = {};
                });

                for (let r = 0; r < SIM_RUNS; r++) {
                    const currentPts = {};
                    teams.forEach(t => { 
                        const basePts = t.effective_pts !== undefined ? t.effective_pts : (t.current_pts || 0);
                        currentPts[t.team_name] = basePts + (addedPts[t.team_name] || 0); 
                    });

                    fixtures.forEach(f => {
                        const userPick = userGamePicks[f.id];
                        // Only simulate outcomes for unpicked matches
                        if (!userPick || userPick === 'auto') {
                            const rHome = teamRatings[f.home] || 82.0;
                            const rAway = teamRatings[f.away] || 82.0;
                            const delta = (rHome + 0.35) - rAway;
                            const margin = delta * 0.70;
                            const lamHome = Math.max(0.5, 3.2 + margin / 2.0);
                            const lamAway = Math.max(0.5, 3.2 - margin / 2.0);
                            const gHome = samplePoisson(lamHome);
                            const gAway = samplePoisson(lamAway);

                            if (gHome > gAway) {
                                currentPts[f.home] = (currentPts[f.home] || 0) + 2;
                            } else if (gAway > gHome) {
                                currentPts[f.away] = (currentPts[f.away] || 0) + 2;
                            } else {
                                currentPts[f.home] = (currentPts[f.home] || 0) + 1;
                                currentPts[f.away] = (currentPts[f.away] || 0) + 1;
                            }
                        }
                    });

                    // Sort order for this run
                    const ranked = [...teams].sort((a, b) => {
                        const pA = currentPts[a.team_name];
                        const pB = currentPts[b.team_name];
                        return pB !== pA ? pB - pA : (Math.random() - 0.5);
                    });

                    ranked.forEach((t, idx) => {
                        const rank = idx + 1;
                        pointTotals[t.team_name].push(currentPts[t.team_name]);
                        rankCounts[t.team_name][rank] = (rankCounts[t.team_name][rank] || 0) + 1;
                    });
                }

                // Compile Simulated Projections with updated GP, Points, and ranking by Points
                const simResults = teams.map(t => {
                    const ptsList = pointTotals[t.team_name] || [];
                    const avgPts = ptsList.reduce((acc, v) => acc + v, 0) / (ptsList.length || 1);
                    const rCounts = rankCounts[t.team_name] || {};
                    let expFinish = 0;
                    Object.entries(rCounts).forEach(([rk, cnt]) => {
                        expFinish += Number(rk) * cnt;
                    });
                    expFinish = expFinish / SIM_RUNS;
                    const top2 = (((rCounts[1] || 0) + (rCounts[2] || 0)) / SIM_RUNS) * 100.0;

                    const baseGp = t.effective_gp !== undefined ? t.effective_gp : (t.current_gp || 0);
                    const basePts = t.effective_pts !== undefined ? t.effective_pts : (t.current_pts || 0);
                    const updatedGp = baseGp + (addedGp[t.team_name] || 0);
                    const updatedPts = basePts + (addedPts[t.team_name] || 0);

                    return {
                        team_name: t.team_name,
                        current_gp: updatedGp,
                        current_pts: updatedPts,
                        proj_pts: avgPts,
                        proj_fin: expFinish,
                        top2_pct: top2,
                        proj_pool: getProjectedPoolAssignment(t, currentCohort, currentLeague, Math.round(expFinish) || 1)
                    };
                }).sort((a, b) => {
                    // Ranked primarily by updated Points descending, tiebreaker by Proj Pts
                    if (b.current_pts !== a.current_pts) {
                        return b.current_pts - a.current_pts;
                    }
                    return b.proj_pts - a.proj_pts;
                });

                renderSimulatorStandingsTable(simResults);
                if (spinner) spinner.classList.add('hidden');
            }, 30);
        }

        function renderSimulatorStandingsTable(simResults) {
            const tbody = document.getElementById('sim-standings-tbody');
            if (!tbody) return;

            tbody.innerHTML = simResults.map((t) => {
                return `
                    <tr class="hover:bg-teal-50/60 border-b border-teal-100/60">
                        <td class="py-2.5 px-3 font-black uppercase text-teal-950 truncate max-w-[150px] sm:max-w-xs">
                            ${t.team_name}
                        </td>
                        <td class="py-2.5 px-2 text-center font-mono text-slate-500">${t.current_gp}</td>
                        <td class="py-2.5 px-2.5 text-center font-mono font-black text-teal-900 bg-teal-50/70">${t.current_pts}</td>
                        <td class="py-2.5 px-2.5 text-center font-mono font-black text-cyan-700">${t.proj_pts.toFixed(1)}</td>
                        <td class="py-2.5 px-2 text-center font-mono font-bold text-slate-800">#${t.proj_fin.toFixed(1)}</td>
                        <td class="py-2.5 px-2.5 text-center font-mono font-black text-slate-900">${t.top2_pct.toFixed(1)}%</td>
                        <td class="py-2.5 px-3 text-center font-mono font-black text-teal-900">${t.proj_pool}</td>
                    </tr>
                `;
            }).join('');
        }

        async function syncLiveSimulationResults() {
            try {
                const res = await fetch('./simulation_results.json?v=' + Date.now());
                if (!res.ok) return;
                const data = await res.json();
                if (data && data.results) {
                    simulationDatabase = data.results;
                    renderCurrentView();
                }
            } catch (err) {
                console.log("Using baseline simulation data.");
            }
        }

        document.addEventListener('DOMContentLoaded', () => {
            renderStandingsTable();
            syncLiveSimulationResults();
        });
    </script>
</body>
</html>

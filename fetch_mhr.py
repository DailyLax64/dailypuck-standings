import os
import re
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY", "").strip()

# Target MHR ranking URLs
MHR_DIVISIONS = {
    "U11 AA": "https://myhockeyrankings.com/rank.php?y=2026&v=142",
    "U14 AA": "https://myhockeyrankings.com/rank.php?y=2026&v=145"
}

class MHRTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_row = False
        self.in_cell = False
        self.current_row = []
        self.current_text = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.in_row = True
            self.current_row = []
        elif tag in ["td", "th"] and self.in_row:
            self.in_cell = True
            self.current_text = []

    def handle_endtag(self, tag):
        if tag == "tr" and self.in_row:
            self.in_row = False
            if self.current_row:
                self.rows.append(self.current_row)
        elif tag in ["td", "th"] and self.in_cell:
            self.in_cell = False
            text = " ".join("".join(self.current_text).split())
            self.current_row.append(text)

    def handle_data(self, data):
        if self.in_cell:
            self.current_text.append(data)

def clean_team_name(name):
    cleaned = re.sub(r'\s*U\d{1,2}\s+(?:AA|A|AAA|BB)\s+\(ON\)', '', name, flags=re.IGNORECASE).strip()
    return ' '.join(cleaned.split())

def norm_key(s):
    return re.sub(r'[^A-Z0-9]', '', str(s or '').upper())

def find_canonical_team(cleaned_name, cohort, master_db):
    cohort_dict = master_db.get(cohort, {})
    if cleaned_name in cohort_dict:
        return cleaned_name
    
    c_upper = cleaned_name.upper()
    for can in cohort_dict:
        if can.upper() == c_upper:
            return can

    for can, data in cohort_dict.items():
        for alias in data.get("aliases", []):
            if alias.upper() == c_upper:
                return can

    c_norm = norm_key(cleaned_name)
    for can, data in cohort_dict.items():
        if norm_key(can) == c_norm:
            return can
        for alias in data.get("aliases", []):
            if norm_key(alias) == c_norm:
                return can

    return None

def fetch_html(target_url, api_key):
    if not api_key:
        print("   ⚠️ SCRAPER_API_KEY secret not found. Attempting direct connection...", flush=True)
        req_url = target_url
    else:
        params = urllib.parse.urlencode({
            "api_key": api_key,
            "url": target_url,
            "render": "true",
            "premium": "true",
            "country_code": "ca"
        })
        req_url = f"https://api.scraperapi.com?{params}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    req = urllib.request.Request(req_url, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", errors="ignore")

def parse_mhr_table(html_content):
    parser = MHRTableParser()
    parser.feed(html_content)
    
    col_map = {}
    records = []
    
    for row in parser.rows:
        if not row:
            continue
        
        joined = " ".join(row).lower()
        if "team" in joined and ("rating" in joined or "record" in joined):
            col_map = {}
            for i, h in enumerate(row):
                hl = h.lower()
                if "rank" in hl and "rank" not in col_map: col_map["rank"] = i
                elif "team" in hl and "team" not in col_map: col_map["team"] = i
                elif "record" in hl and "record" not in col_map: col_map["record"] = i
                elif "rating" in hl and "rating" not in col_map: col_map["rating"] = i
                elif "agd" in hl and "agd" not in col_map: col_map["agd"] = i
                elif "sched" in hl and "sched" not in col_map: col_map["sched"] = i
            continue

        if "team" in col_map and len(row) > col_map["team"]:
            team_raw = row[col_map["team"]]
            if not

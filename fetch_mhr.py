import os
import re
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY", "").strip()

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
        print("   ⚠️ SCRAPER_API

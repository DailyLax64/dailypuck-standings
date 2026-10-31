import json
import os

fixes = {
    "Garden City Minor Falcons": ["St. Catharines Falcons", "St Catharines Falcons"],
    "King Rebellion U11AA": ["King Rebellion"],
    "Collingwood Jr. Blues 11 AA": ["Collingwood Jr Blues", "Collingwood Jr. Blues"],
    "Orangeville Flyer U11 AA": ["Orangeville Flyers"],
    "Collingwood Jr. Blues 14 AA": ["Collingwood Jr Blues", "Collingwood Jr. Blues"],
    
    "NORTH DURHAM AA U11": ["North Durham Warriors"],
    "BELLEVILLE AA U11": ["Belleville Bulls"],
    "OSHAWA AA U11": ["Oshawa Generals"],
    "WHITBY AA U11": ["Whitby Wildcats"],
    "AJAX-PICKERING AA U11": ["Ajax Pickering Raiders", "Ajax-Pickering Raiders"],
    "PETERBOROUGH AA U11": ["Peterborough Petes"],
    "QUINTE WEST AA U11": ["Quinte West Golden Hawks"],
    "KINGSTON AREA AA U11": ["Kingston Canadians"],
    "CLARINGTON AA U11": ["Clarington Toros"],
    "NORTHUMBERLAND AA U11": ["Northumberland Nighthawks"],
    
    "NORTH DURHAM AA U14": ["North Durham Warriors"],
    "BELLEVILLE AA U14": ["Belleville Bulls"],
    "OSHAWA AA U14": ["Oshawa Generals"],
    "WHITBY AA U14": ["Whitby Wildcats"],
    "AJAX-PICKERING AA U14": ["Ajax Pickering Raiders", "Ajax-Pickering Raiders"],
    "PETERBOROUGH AA U14": ["Peterborough Petes"],
    "QUINTE WEST AA U14": ["Quinte West Golden Hawks"],
    "KINGSTON AREA AA U14": ["Kingston Canadians"],
    "CLARINGTON AA U14": ["Clarington Toros"],
    "NORTHUMBERLAND AA U14": ["Northumberland Nighthawks"]
}

def apply_aliases():
    master_path = "master_teams.json"
    if not os.path.exists(master_path):
        print(f"Error: {master_path} not found.")
        return

    with open(master_path, "r", encoding="utf-8") as f:
        master_db = json.load(f)

    for cohort in master_db:
        for team, obj in master_db[cohort].items():
            if team in fixes:
                for alias in fixes[team]:
                    if alias not in obj.get("aliases", []):
                        obj.setdefault("aliases", []).append(alias)

    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(master_db, f, indent=2)

    print("✅ Aliases injected successfully!")

if __name__ == "__main__":
    apply_aliases()

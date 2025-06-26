import os
import json
import argparse
import csv
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def init_empty_day_dict():
    return {
        "walking": 0,
        "in bus": 0,
        "in train": 0,
        "in passenger vehicle": 0,
        "running": 0,
        "cycling": 0
    }

def analyze_file_per_day(file_path, start_date, end_date):
    data = load_json(file_path)
    daily_stats = {}

    if isinstance(data, dict) and "semanticSegments" in data:
        entries = data["semanticSegments"]
    elif isinstance(data, list):
        entries = data
    else:
        raise ValueError("Formato JSON non riconosciuto.")

    for entry in entries:
        try:
            if isinstance(entry, dict) and 'startTime' in entry:
                start_time = isoparse(entry['startTime'])
            else:
                continue
        except Exception:
            continue

        if not (start_date <= start_time <= end_date):
            continue

        activity = entry.get("activity")
        if not activity or "topCandidate" not in activity:
            continue

        activity_type = activity["topCandidate"]["type"].lower().replace("_", " ")
        distance_km = float(activity.get("distanceMeters", 0)) / 1000

        day = start_time.date().isoformat()
        if day not in daily_stats:
            daily_stats[day] = init_empty_day_dict()

        if activity_type in daily_stats[day]:
            daily_stats[day][activity_type] += distance_km

    return daily_stats

def save_combined_csv(all_data, output_path):
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ["user_id", "date", "walking", "in bus", "in train", "in passenger vehicle", "running", "cycling", "total", "sustainable", "percent_sustainable"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in all_data:
            writer.writerow(row)

def main():
    parser = argparse.ArgumentParser(description="Calcola statistiche giornaliere di mobilità e le salva in un unico CSV.")
    parser.add_argument("--uploads", default="uploads", help="Cartella contenente i file degli utenti.")
    parser.add_argument("--output", default="mobilita.csv", help="Percorso file CSV in output.")
    args = parser.parse_args()

    start_date = datetime(2025, 4, 1, tzinfo=timezone.utc)
    end_date = datetime.now(timezone.utc)

    all_results = []

    for user_id in os.listdir(args.uploads):
        user_folder = os.path.join(args.uploads, user_id)
        if not os.path.isdir(user_folder):
            continue

        file_path = None
        for fname in ["location-history.json", "Spostamenti.json"]:
            candidate = os.path.join(user_folder, fname)
            if os.path.exists(candidate):
                file_path = candidate
                break

        if not file_path:
            print(f"⚠️  Nessun file per user {user_id}")
            continue

        try:
            daily_stats = analyze_file_per_day(file_path, start_date, end_date)
            for date_str in sorted(daily_stats.keys()):
                d = daily_stats[date_str]
                total = sum(d.values())
                sustainable = d["walking"] + d["cycling"] + d["in bus"] + d["in train"] + d["running"]
                percent = sustainable / total * 100 if total > 0 else 0

                all_results.append({
                    "user_id": user_id,
                    "date": date_str,
                    **d,
                    "total": round(total, 3),
                    "sustainable": round(sustainable, 3),
                    "percent_sustainable": round(percent, 2)
                })

            print(f"✅ Elaborato user {user_id} ({len(daily_stats)} giorni)")
        except Exception as e:
            print(f"❌ Errore con user {user_id}: {e}")

    save_combined_csv(all_results, args.output)
    print(f"\n📁 File salvato: {args.output} ({len(all_results)} righe)")

if __name__ == "__main__":
    main()

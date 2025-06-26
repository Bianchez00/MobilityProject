import os
import json
import argparse
import csv
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse

def load_json(file_path):
    print(f"Loading JSON file: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def init_empty_week_dict():
    return {
        "walking": 0,
        "in bus": 0,
        "in train": 0,
        "in passenger vehicle": 0,
        "running": 0,
        "cycling": 0
    }

def get_week_key(date_obj):
    return f"{date_obj.isocalendar()[0]}-W{date_obj.isocalendar()[1]:02d}"

def get_week_range(date_obj):
    start = date_obj - timedelta(days=date_obj.weekday())
    end = start + timedelta(days=6)
    return start.date(), end.date()

def analyze_file_per_week(file_path, start_date, end_date):
    data = load_json(file_path)
    weekly_stats = {}

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

        week_key = get_week_key(start_time)
        if week_key not in weekly_stats:
            weekly_stats[week_key] = {
                "start": get_week_range(start_time)[0],
                "end": get_week_range(start_time)[1],
                "data": init_empty_week_dict()
            }

        if activity_type in weekly_stats[week_key]["data"]:
            weekly_stats[week_key]["data"][activity_type] += distance_km

    return weekly_stats

def save_combined_weekly_csv(all_data, output_path):
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ["user_id", "week_start", "week_end", "week_number", "walking", "in bus", "in train", "in passenger vehicle", "running", "cycling", "total", "sustainable", "percent_sustainable"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_data:
            writer.writerow(row)

def main():
    print("Starting script...")
    parser = argparse.ArgumentParser(description="Calcola statistiche settimanali di mobilità in un unico CSV.")
    parser.add_argument("--uploads", default="uploads", help="Cartella contenente i file degli utenti.")
    parser.add_argument("--output", default="mobilita_settimanale.csv", help="Percorso file CSV di output.")
    args = parser.parse_args()

    print(f"Using uploads directory: {args.uploads}")
    print(f"Output will be saved to: {args.output}")

    start_date = datetime(2025, 4, 1, tzinfo=timezone.utc)
    end_date = datetime.now(timezone.utc)
    print(f"Analyzing data from {start_date} to {end_date}")

    all_results = []

    user_dirs = os.listdir(args.uploads)
    print(f"Found {len(user_dirs)} user directories")

    for user_id in user_dirs:
        print(f"\nProcessing user: {user_id}")
        user_folder = os.path.join(args.uploads, user_id)
        if not os.path.isdir(user_folder):
            print(f"Skipping {user_id} - not a directory")
            continue

        file_path = None
        for fname in ["location-history.json", "Spostamenti.json"]:
            candidate = os.path.join(user_folder, fname)
            if os.path.exists(candidate):
                file_path = candidate
                print(f"Found file: {fname}")
                break

        if not file_path:
            print(f"⚠️  Nessun file per user {user_id}")
            continue

        try:
            print(f"Analyzing file: {file_path}")
            weekly_stats = analyze_file_per_week(file_path, start_date, end_date)
            print(f"Found {len(weekly_stats)} weeks of data")
            
            for week_key in sorted(weekly_stats.keys()):
                week = weekly_stats[week_key]
                d = week["data"]
                total = sum(d.values())
                sustainable = d["walking"] + d["cycling"] + d["in bus"] + d["in train"] + d["running"]
                percent = sustainable / total * 100 if total > 0 else 0

                all_results.append({
                    "user_id": user_id,
                    "week_start": week["start"],
                    "week_end": week["end"],
                    "week_number": week_key,
                    **d,
                    "total": round(total, 3),
                    "sustainable": round(sustainable, 3),
                    "percent_sustainable": round(percent, 2)
                })

            print(f"✅ Elaborato user {user_id} ({len(weekly_stats)} settimane)")
        except Exception as e:
            print(f"❌ Errore con user {user_id}: {str(e)}")
            import traceback
            print(traceback.format_exc())

    print(f"\nSaving results to {args.output}")
    save_combined_weekly_csv(all_results, args.output)
    print(f"\n📁 File settimanale salvato: {args.output} ({len(all_results)} righe)")

if __name__ == "__main__":
    main()

import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

def fetch_neo_feed(date=None):
    # Read secret from environment (injected by Docker or host)
    api_key = os.environ.get("NASA_API_KEY")
    if not api_key:
        return None

    params = {"api_key": api_key}
    if date:
        params.update({"start_date": date, "end_date": date})

    try:
        resp = requests.get("https://api.nasa.gov/neo/rest/v1/feed", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None

def normalize_asteroid_data(raw_data):
    normalized_list = []
    if not raw_data or "near_earth_objects" not in raw_data:
        return normalized_list

    for date_key, asteroids in raw_data.get('near_earth_objects', {}).items():
        for asteroid in asteroids:
            try:
                miss_km = None
                cad = asteroid.get('close_approach_data') or []
                if cad:
                    miss = cad[0].get('miss_distance', {}).get('kilometers')
                    miss_km = float(miss) if miss is not None else None

                diameter_km = None
                diam = asteroid.get('estimated_diameter', {}).get('kilometers', {})
                if diam:
                    diameter_km = diam.get('estimated_diameter_max') or diam.get('estimated_diameter_min')

                clean_asteroid = {
                    "id": asteroid.get('id'),
                    "name": asteroid.get('name'),
                    "diameter_km": diameter_km,
                    "miss_distance_km": miss_km,
                    "is_hazardous": asteroid.get('is_potentially_hazardous_asteroid', False),
                    "close_approach_date": cad[0].get('close_approach_date') if cad else None
                }
                normalized_list.append(clean_asteroid)
            except Exception:
                # skip malformed entries rather than failing the whole response
                continue
    return normalized_list

@app.route('/asteroids', methods=['GET'])
def get_asteroids():
    date = request.args.get("date")  # optional YYYY-MM-DD
    raw_json = fetch_neo_feed(date=date)
    if not raw_json:
        return jsonify({"error": "NASA API unreachable or NASA_API_KEY not set"}), 502

    clean_data = normalize_asteroid_data(raw_json)
    return jsonify(clean_data)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "asteroid-data-service"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
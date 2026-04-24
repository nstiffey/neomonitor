import os
import requests
import logging
from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Service Discovery
ASTEROID_SERVICE = os.environ.get('ASTEROID_SERVICE_URL', 'http://asteroid-service:5001')

@app.route('/risk', methods=['GET'])
def analyze_risk():
    """
    Analyzes NEO risk based on a global threshold.
    Query params:
      - threshold: distance threshold in km (default: 1000000.0)
    """
    try:
        # Determine risk threshold from explicit query param or default
        threshold = request.args.get('threshold')
        threshold = float(threshold) if threshold is not None else 1000000.0

        # 1. Get Asteroid Data
        neo_resp = requests.get(f"{ASTEROID_SERVICE}/feed")
        if neo_resp.status_code != 200:
            return jsonify({'error': 'Failed to fetch NASA data'}), 500
        neo_data = neo_resp.json()

        # 2. Analyze Risks
        processed_asteroids = []
        dangerous_count = 0

        asteroids = neo_data.get('asteroids', [])

        for asteroid in asteroids:
            name = asteroid['name']
            diameter_km = asteroid['diameter_km']
            close_approaches = asteroid.get('close_approaches', [])
            if not close_approaches:
                continue
            miss_km = close_approaches[0]['miss_distance_km']

            is_risky = miss_km < threshold
            if is_risky:
                dangerous_count += 1

            processed_asteroids.append({
                'name': name,
                'diameter_meters': diameter_km * 1000,  # Convert back to meters for consistency
                'miss_distance_km': miss_km,
                'is_risky': is_risky,
                'close_approach_date': close_approaches[0]['date']
            })

        # 3. Return Risk Analysis as JSON
        return jsonify({
            'threshold': threshold,
            'asteroids': processed_asteroids,
            'dangerous_count': dangerous_count
        }), 200

    except Exception as e:
        logger.error(f"Risk analysis failed: {e}")
        return jsonify({'error': 'Internal analysis error', 'details': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)
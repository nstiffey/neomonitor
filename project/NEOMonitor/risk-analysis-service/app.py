import os
import requests
import logging
from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Service Discovery
ASTEROID_SERVICE = os.environ.get('ASTEROID_SERVICE_URL', 'http://asteroid-service:5001')
USER_SERVICE = os.environ.get('USER_SERVICE_URL', 'http://user-service:5002')

@app.route('/risk', methods=['GET'])
def analyze_risk():
    """
    Analyzes NEO risk based on threshold.
    Query params:
      - threshold: distance threshold in km (default: 1000000.0)
      - user_id: optional user ID to pull threshold from profile
    """
    try:
        # Determine risk threshold from user profile or explicit query param
        user_id = request.args.get('user_id')
        threshold = request.args.get('threshold')

        if user_id:
            user_resp = requests.get(f"{USER_SERVICE}/users/{user_id}")
            if user_resp.status_code != 200:
                return jsonify({'error': 'Unable to resolve user profile', 'details': user_resp.json()}), 404
            user_profile = user_resp.json()
            threshold = float(user_profile.get('risk_threshold_km', 1000000.0))
        else:
            threshold = float(threshold) if threshold is not None else 1000000.0

        # 1. Get Asteroid Data
        neo_resp = requests.get(f"{ASTEROID_SERVICE}/feed")
        if neo_resp.status_code != 200:
            return jsonify({'error': 'Failed to fetch NASA data'}), 500
        neo_data = neo_resp.json()

        # 2. Analyze Risks
        processed_asteroids = []
        dangerous_count = 0

        near_earth_objects = neo_data.get('near_earth_objects', {})

        for date, objects in near_earth_objects.items():
            for obj in objects:
                name = obj['name']
                diameter = obj['estimated_diameter']['meters']['estimated_diameter_max']
                close_approach = obj['close_approach_data'][0]
                miss_km = float(close_approach['miss_distance']['kilometers'])

                is_risky = miss_km < threshold
                if is_risky:
                    dangerous_count += 1

                processed_asteroids.append({
                    'name': name,
                    'diameter_meters': diameter,
                    'miss_distance_km': miss_km,
                    'is_risky': is_risky,
                    'close_approach_date': close_approach.get('close_approach_date')
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
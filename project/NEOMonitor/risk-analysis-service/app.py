import os
import requests
import logging
from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Service Discovery
ASTEROID_SERVICE = os.environ.get('ASTEROID_SERVICE_URL', 'http://asteroid-service:5001')

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "service": "risk-analysis-service",
        "description": "Analyzes asteroid risk based on proximity",
        "endpoints": {
            "/risk": "Analyze asteroid risks",
            "/health": "Health check"
        }
    }), 200

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

        # Determine whether we should return only potentially hazardous objects
        hazardous_only = request.args.get('hazardous', 'false').lower() in ['1', 'true', 'yes', 'on']

        # 2. Analyze Risks
        processed_asteroids = []
        dangerous_count = 0

        asteroids = neo_data.get('asteroids', [])

        for asteroid in asteroids:
            name = asteroid.get('name')
            diameter_data = asteroid.get('diameter_meters', {})
            diameter_meters = None
            if isinstance(diameter_data, dict):
                min_d = diameter_data.get('min')
                max_d = diameter_data.get('max')
                if min_d is not None and max_d is not None:
                    diameter_meters = (float(min_d) + float(max_d)) / 2.0
            if diameter_meters is None:
                diameter_meters = float(asteroid.get('diameter_meters', 0))

            close_approaches = asteroid.get('close_approaches', [])
            if not close_approaches:
                continue
            miss_km = float(close_approaches[0].get('miss_distance_km', 0.0))
            approach_date = close_approaches[0].get('date')

            is_risky = miss_km < threshold
            if is_risky:
                dangerous_count += 1

            asteroid_record = {
                'name': name,
                'diameter_meters': diameter_meters,
                'miss_distance_km': miss_km,
                'is_risky': is_risky,
                'close_approach_date': approach_date
            }

            if not hazardous_only or is_risky:
                processed_asteroids.append(asteroid_record)

        # 3. Return Risk Analysis as JSON
        return jsonify({
            'threshold': threshold,
            'asteroids': processed_asteroids,
            'dangerous_count': dangerous_count
        }), 200

    except Exception as e:
        logger.error(f"Risk analysis failed: {e}")
        return jsonify({'error': 'Internal analysis error', 'details': str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "service": "risk-analysis-service",
        "status": "healthy",
        "endpoints": {
            "risk": "/risk",
            "health": "/health"
        }
    }), 200


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)
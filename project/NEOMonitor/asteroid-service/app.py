import os
import requests
import redis
import json
import logging
from flask import Flask, jsonify, request
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
NASA_API_KEY = os.environ.get('NASA_API_KEY', 'DEMO_KEY')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/1')

# Redis Connection
try:
    cache = redis.from_url(REDIS_URL)
    logger.info("Connected to Redis cache")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    cache = None

def normalize_nasa_response(nasa_data, start_date, end_date):
    """Normalize NASA's complex JSON into a clean, consistent format"""
    normalized = {
        "date_range": {
            "start_date": start_date,
            "end_date": end_date,
            "total_asteroids": nasa_data.get('element_count', 0)
        },
        "asteroids": []
    }
    
    near_earth_objects = nasa_data.get('near_earth_objects', {})
    
    for date, objects in near_earth_objects.items():
        for obj in objects:
            # Extract and validate key data
            asteroid = {
                "id": obj.get('id'),
                "name": obj.get('name'),
                "nasa_jpl_url": obj.get('nasa_jpl_url'),
                "absolute_magnitude": obj.get('absolute_magnitude_h'),
                "diameter_meters": {
                    "min": obj['estimated_diameter']['meters']['estimated_diameter_min'],
                    "max": obj['estimated_diameter']['meters']['estimated_diameter_max']
                },
                "is_potentially_hazardous": obj.get('is_potentially_hazardous_asteroid', False),
                "close_approaches": []
            }
            
            # Normalize close approach data
            for approach in obj.get('close_approach_data', []):
                normalized_approach = {
                    "date": approach.get('close_approach_date'),
                    "date_full": approach.get('close_approach_date_full'),
                    "epoch_timestamp": approach.get('epoch_date_close_approach'),
                    "velocity_kmh": float(approach['relative_velocity']['kilometers_per_hour']),
                    "miss_distance_km": float(approach['miss_distance']['kilometers']),
                    "miss_distance_au": float(approach['miss_distance']['astronomical']),
                    "orbiting_body": approach.get('orbiting_body')
                }
                asteroid['close_approaches'].append(normalized_approach)
            
            normalized['asteroids'].append(asteroid)
    
    return normalized

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "service": "asteroid-service",
        "description": "Provides asteroid data from NASA NEO API",
        "endpoints": {
            "/feed": "Get asteroid feed data",
            "/health": "Health check"
        }
    }), 200

@app.route('/feed', methods=['GET'])
def get_feed():
    # Default to today if no date provided
    today = datetime.now().strftime('%Y-%m-%d')
    start_date = request.args.get('start_date', today)
    end_date = request.args.get('end_date', start_date)
    
    cache_key = f"nasa_feed_{start_date}_{end_date}"
    
    # 1. Check Cache
    if cache:
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache HIT for {start_date} to {end_date}")
            return jsonify(json.loads(cached_data))

    # 2. Fetch from NASA (Cache Miss)
    logger.info(f"Cache MISS. Fetching from NASA for {start_date} to {end_date}...")
    url = "https://api.nasa.gov/neo/rest/v1/feed"
    params = {
        'start_date': start_date,
        'end_date': end_date,
        'api_key': NASA_API_KEY
    }
    
    try:
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            return jsonify({"error": "NASA API Error", "details": resp.text}), resp.status_code
        
        nasa_data = resp.json()
        
        # 3. Normalize the data
        normalized_data = normalize_nasa_response(nasa_data, start_date, end_date)
        
        # 4. Save to Cache (Expires in 1 hour = 3600 seconds)
        if cache:
            cache.setex(cache_key, 3600, json.dumps(normalized_data))
            
        return jsonify(normalized_data)
        
    except Exception as e:
        logger.error(f"Error fetching NASA data: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
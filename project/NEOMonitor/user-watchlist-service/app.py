import os
import logging
from flask import Flask, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# The Database configuration and Models (User, Watchlist) have been removed.
# All CRUD operations and tracking logic have been removed.

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "service": "user-watchlist-service",
<<<<<<< HEAD
        "status": "healthy",
        "endpoints": {
            "health": "/health"
        }
    }), 200


=======
        "description": "User watchlist management (placeholder)",
        "endpoints": {
            "/health": "Health check"
        }
    }), 200

>>>>>>> 7b40c7d483ceec83e60ffd9840ef57ae1b08deff
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    # Default port remains 5002 for consistency in the service mesh
    app.run(host='0.0.0.0', port=5002)
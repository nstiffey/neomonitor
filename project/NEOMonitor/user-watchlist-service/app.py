import os
import logging
from flask import Flask, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# The Database configuration and Models (User, Watchlist) have been removed.
# All CRUD operations and tracking logic have been removed.

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    # Default port remains 5002 for consistency in the service mesh
    app.run(host='0.0.0.0', port=5002)
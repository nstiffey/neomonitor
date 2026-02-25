import os
import requests
import logging
from flask import Flask, request, jsonify, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

ASTEROID_SERVICE_URL = os.environ.get('ASTEROID_SERVICE_URL', 'http://asteroid-service:5001')
USER_SERVICE_URL = os.environ.get('USER_SERVICE_URL', 'http://user-service:5002')
RISK_SERVICE_URL = os.environ.get('RISK_SERVICE_URL', 'http://risk-service:5003')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')

limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=REDIS_URL,
    default_limits=["50 per hour"]
)

logging.basicConfig(level=logging.INFO)

def read_secret(path):
    try:
        with open(path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

DB_PASSWORD = os.environ.get('DB_PASSWORD') or read_secret(os.environ.get('DB_PASSWORD_FILE', '/run/secrets/db_password'))
API_KEY = os.environ.get('NSASA_API_KEY') or read_secret(os.environ.get('API_KEY_FILE', '/run/secrets/api_key'))


def proxy_requests(target_url, endpoint):
    try:
        response = requests.request(
            method=request.method,
            url=target_url,
            headers={key: value for key, value in request.headers if key.lower() != 'host'},
            data=request.get_data(),
            cookies=request.cookies,
            params=request.args,
            allow_redirects=False
        )
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
         
         #strip gateway header stuff
        excluded = {'content-encoding', 'content-length', 'transfer-encoding', 'connection'}
        headers = [(name, value) for (name, value) in response.raw.headers.items() if name.lower() not in excluded]

        return Response(response.content, response.status_code, headers)
    except requests.exceptions.RequestException as e:
        logging.error(f"Error proxying request to {target_url}: {e}")
        return jsonify({'error': 'Failed to connect to the target service'}), 502
    
@app.route('/asteroids', methods=['GET'])
def get_asteroids():
    target_url = 'http://asteroid-service:5001/asteroids'
    return proxy_requests(target_url, '/asteroids')

@app.route('/users', methods=['POST'])
@app.route('/users/<user_id>', methods=['GET', 'PUT', 'DELETE']) 
def manage_users():
    url = os.environ.get('USER_SERVICE_URL', 'http://user-service:5002/users')
    return proxy_requests(url, '/users')
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)

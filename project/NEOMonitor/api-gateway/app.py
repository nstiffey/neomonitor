import os
import requests
import logging
import time
import uuid
import json
import threading
from flask import Flask, request, jsonify, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import httpx

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CircuitBreaker:
    def __init__(self, failure_threshold=5):
        self.failures = 0
        self.failure_threshold = failure_threshold
        self.last_failure = None
        self.is_open = False
    
    def record_success(self):
        self.failures = 0
        self.is_open = False
    
    def record_failure(self):
        self.failures += 1
        self.last_failure = time.time()
        if self.failures >= self.failure_threshold:
            self.is_open = True
    
    def is_available(self):
        if not self.is_open:
            return True
        # Half-open: retry after 30s
        if time.time() - self.last_failure > 30:
            return True
        return False

class RequestContext:
    def __init__(self):
        self.request_id = str(uuid.uuid4())
        self.start_time = time.time()
        self.service_called = None

context = RequestContext()

class ServiceHealth:
    def __init__(self, service_name, check_url):
        self.service_name = service_name
        self.check_url = check_url
        self.is_healthy = True
        self.start_monitoring()
    
    def start_monitoring(self):
        def check_periodically():
            while True:
                try:
                    resp = requests.get(self.check_url, timeout=2.0)
                    self.is_healthy = resp.status_code == 200
                except:
                    self.is_healthy = False
                time.sleep(5)  # Check every 5 seconds
        
        thread = threading.Thread(target=check_periodically, daemon=True)
        thread.start()

app = Flask(__name__)

# Load Configuration
ASTEROID_SERVICE_URL = os.environ.get('ASTEROID_SERVICE_URL', 'http://asteroid-service:5001')
USER_SERVICE_URL = os.environ.get('USER_SERVICE_URL', 'http://user-service:5002')
RISK_SERVICE_URL = os.environ.get('RISK_SERVICE_URL', 'http://risk-service:5003')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')

# Initialize circuit breakers and health checks
asteroid_breaker = CircuitBreaker()
user_breaker = CircuitBreaker()
risk_breaker = CircuitBreaker()

asteroid_health = ServiceHealth('asteroid-service', f"{ASTEROID_SERVICE_URL}/health")
user_health = ServiceHealth('user-service', f"{USER_SERVICE_URL}/health")
risk_health = ServiceHealth('risk-service', f"{RISK_SERVICE_URL}/health")

# Setup Rate Limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=REDIS_URL,
    default_limits=["50 per hour"]
)

def proxy_request(service_url, endpoint, breaker, health):
    context.service_called = service_url.split('/')[-1]
    
    if not health.is_healthy:
        return jsonify({
            "error": f"{health.service_name} is unavailable",
            "status": "unhealthy"
        }), 503
    
    if not breaker.is_available():
        return jsonify({
            "error": f"{health.service_name} temporarily unavailable",
            "service": health.service_name,
            "retry_after": 30
        }), 503
    
    try:
        logger.info(json.dumps({
            "event": "service_call_start",
            "request_id": context.request_id,
            "service": context.service_called
        }))
        
        with httpx.Client(timeout=httpx.Timeout(5.0, connect=2.0)) as client:
            resp = client.request(
                method=request.method,
                url=f"{service_url}/{endpoint}",
                headers={key: value for (key, value) in request.headers.items() if key.lower() not in ['host', 'content-length']},
                content=request.get_data(),
                params=request.args
            )
        
        logger.info(json.dumps({
            "event": "service_call_end",
            "request_id": context.request_id,
            "service": context.service_called,
            "status": resp.status_code
        }))
        
        if resp.status_code < 500:
            breaker.record_success()
        else:
            breaker.record_failure()
        
        # Return the response
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.headers.items()
                   if name.lower() not in excluded_headers]
        
        return Response(resp.content, resp.status_code, headers)
    
    except httpx.TimeoutException:
        breaker.record_failure()
        logger.error(json.dumps({
            "event": "service_call_error",
            "request_id": context.request_id,
            "service": context.service_called,
            "error": "timeout"
        }))
        return jsonify({
            "error": f"{health.service_name} timeout",
            "service": health.service_name,
            "timeout": 5.0
        }), 504
    
    except httpx.ConnectError:
        breaker.record_failure()
        logger.error(json.dumps({
            "event": "service_call_error",
            "request_id": context.request_id,
            "service": context.service_called,
            "error": "connection_error"
        }))
        return jsonify({
            "error": f"{health.service_name} unreachable",
            "service": health.service_name
        }), 502
    
    except Exception as e:
        logger.error(json.dumps({
            "event": "service_call_error",
            "request_id": context.request_id,
            "service": context.service_called,
            "error": str(e)
        }))
        return jsonify({
            "error": "gateway error",
            "details": str(e)
        }), 500

@app.before_request
def setup_request_context():
    context.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
    context.start_time = time.time()
    logger.info(json.dumps({
        "event": "request_start",
        "request_id": context.request_id,
        "method": request.method,
        "path": request.path,
        "client_ip": get_remote_address()
    }))

@app.after_request
def log_request_end(response):
    duration = time.time() - context.start_time
    logger.info(json.dumps({
        "event": "request_end",
        "request_id": context.request_id,
        "status": response.status_code,
        "duration_ms": int(duration * 1000),
        "service": context.service_called
    }))
    return response

# --- Routes ---

@app.route('/')
def index():
    return jsonify({
        "name": "NEOMonitor API Gateway",
        "status": "operational",
        "endpoints": {
            "asteroids": "/neo/feed",
            "dashboard": "/dashboard/<user_id>",
            "user": "/user/<user_id>"
        }
    })

@app.route('/neo/<path:path>', methods=['GET', 'POST'])
def asteroid_proxy(path):
    return proxy_request(ASTEROID_SERVICE_URL, path, asteroid_breaker, asteroid_health)

@app.route('/user/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def user_proxy(path):
    return proxy_request(USER_SERVICE_URL, path, user_breaker, user_health)

@app.route('/dashboard/<path:path>', methods=['GET'])
def risk_proxy(path):
    return proxy_request(RISK_SERVICE_URL, path, risk_breaker, risk_health)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
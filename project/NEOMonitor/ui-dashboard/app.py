import os
import requests
import logging
from flask import Flask, jsonify, request, render_template_string

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Service Discovery
RISK_SERVICE = os.environ.get('RISK_SERVICE_URL', 'http://risk-service:5003')
USER_SERVICE = os.environ.get('USER_SERVICE_URL', 'http://user-service:5002')

# HTML Template
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>NEOMonitor Dashboard</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background: #f0f2f5; }
        .card { background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .danger { color: #d32f2f; font-weight: bold; }
        .safe { color: #388e3c; }
        h1 { color: #1a237e; }
        table { width: 100%; border-collapse: collapse; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; }
    </style>
</head>
<body>
    <h1>🛰️ NEOMonitor Risk Analysis</h1>
    
    <div class="card">
        <h2>Risk Assessment</h2>
        <p><strong>Alert Threshold:</strong> {{ "{:,.0f}".format(threshold) }} km</p>
        <p><strong>Status:</strong> 
            {% if risk_stats.dangerous_count > 0 %}
                <span class="danger">⚠️ {{ risk_stats.dangerous_count }} Threats Detected</span>
            {% else %}
                <span class="safe">✅ No Immediate Threats</span>
            {% endif %}
        </p>
    </div>

    <div class="card">
        <h3>Asteroid Approaches (Today)</h3>
        <table>
            <tr>
                <th>Asteroid Name</th>
                <th>Diameter (Est)</th>
                <th>Miss Distance</th>
                <th>Risk Status</th>
            </tr>
            {% for ast in asteroids %}
            <tr>
                <td>{{ ast.name }}</td>
                <td>{{ "{:.2f}".format(ast.diameter_meters) }} m</td>
                <td>{{ "{:,.0f}".format(ast.miss_distance_km) }} km</td>
                <td>
                    {% if ast.is_risky %}
                        <span class="danger">TOO CLOSE</span>
                    {% else %}
                        <span class="safe">Safe</span>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

@app.route('/')
def get_dashboard():
    try:
        # Determine risk threshold from user profile or explicit query param
        user_id = request.args.get('user_id')
        threshold = request.args.get('threshold')
        user_name = 'Anonymous'

        if user_id:
            user_resp = requests.get(f"{USER_SERVICE}/users/{user_id}")
            if user_resp.status_code != 200:
                return jsonify({'error': 'Unable to resolve user profile', 'details': user_resp.json()}), 404
            user_profile = user_resp.json()
            user_name = user_profile.get('name', user_name)
            threshold = float(user_profile.get('risk_threshold_km', 1000000.0))
        else:
            threshold = float(threshold) if threshold is not None else 1000000.0

        # Call Risk Analysis API
        risk_resp = requests.get(f"{RISK_SERVICE}/risk?threshold={threshold}")
        if risk_resp.status_code != 200:
            return "Failed to fetch risk analysis", 500
        
        risk_data = risk_resp.json()
        asteroids = risk_data.get('asteroids', [])
        dangerous_count = risk_data.get('dangerous_count', 0)

        # Render Dashboard
        return render_template_string(
            DASHBOARD_TEMPLATE,
            title=f"NEOMonitor Risk Analysis for {user_name}",
            threshold=threshold,
            asteroids=asteroids,
            risk_stats={'dangerous_count': dangerous_count}
        )

    except Exception as e:
        logger.error(f"Dashboard rendering failed: {e}")
        return f"Internal System Error: {e}", 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004)

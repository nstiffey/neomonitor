import os
import requests
import logging
from flask import Flask, request, jsonify, render_template_string

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Service Discovery
GATEWAY_URL = os.environ.get('GATEWAY_URL', 'http://api-gateway:8000')

@app.route('/')
def index():
    """
    Renders the NEO-Sentinel Global Dashboard.
    Uses client-side JavaScript Fetch API to call /risk endpoint.
    """
    html = """
    <html>
        <head>
            <title>NEO-Sentinel Global Dashboard</title>
            <script>
                async function updateRiskReport() {
                    const threshold = document.getElementById('threshold').value;
                    const response = await fetch(`/risk?threshold=${threshold}`);
                    const data = await response.json();
                    
                    const report = {
                        threshold_km: data.threshold,
                        summary: `Detected ${data.dangerous_count} potential risks in the current window.`,
                        objects: data.asteroids.map(ast => ({
                            name: ast.name,
                            miss_distance_km: ast.miss_distance_km,
                            diameter_km: (ast.diameter_meters / 1000).toFixed(4),
                            is_hazardous: ast.is_risky
                        }))
                    };
                    
                    // Update threshold display
                    document.getElementById('threshold-display').textContent = report.threshold_km.toLocaleString();
                    
                    // Update summary
                    document.getElementById('summary').textContent = report.summary;
                    
                    // Update objects list
                    const objectsList = document.getElementById('objects-list');
                    objectsList.innerHTML = '';
                    
                    if (report.objects.length === 0) {
                        objectsList.innerHTML = '<p>No immediate threats found within the global threshold.</p>';
                    } else {
                        report.objects.forEach(obj => {
                            const li = document.createElement('li');
                            li.style.background = '#fff';
                            li.style.marginBottom = '10px';
                            li.style.padding = '10px';
                            li.style.borderRadius = '4px';
                            li.style.borderLeft = `5px solid ${obj.is_hazardous ? 'red' : '#ccc'}`;
                            li.innerHTML = `
                                <strong>${obj.name}</strong><br>
                                Distance: ${obj.miss_distance_km.toLocaleString()} km | 
                                Diameter: ${obj.diameter_km} km 
                                ${obj.is_hazardous ? '<span style="color: red; font-weight: bold;"> [POTENTIALLY HAZARDOUS]</span>' : ''}
                            `;
                            objectsList.appendChild(li);
                        });
                    }
                }
                
                // Load initial data on page load
                window.onload = updateRiskReport;
            </script>
        </head>
        <body style="font-family: sans-serif; padding: 20px; background: #f9f9f9;">
            <h1>NEO-Sentinel Global Risk Report</h1>
            <p>
                <label for="threshold">Global Threshold (km):</label>
                <input type="number" id="threshold" value="1000000" onchange="updateRiskReport()">
                <strong>Current Threshold:</strong> <span id="threshold-display">1,000,000</span> km
            </p>
            <div style="background: #ffffff; padding: 15px; border-radius: 5px; border: 1px solid #ddd;">
                <h3 id="summary">Loading...</h3>
            </div>
            <hr>
            <ul id="objects-list" style="list-style-type: none; padding: 0;">
                <li>Loading asteroid data...</li>
            </ul>
        </body>
    </html>
    """
    return html

@app.route('/risk', methods=['GET'])
def risk_proxy():
    """
    Proxy to gateway /risk for client-side fetch.
    """
    try:
        threshold = request.args.get('threshold', '1000000')
        response = requests.get(f"{GATEWAY_URL}/risk", params={'threshold': threshold})
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        return jsonify({'error': 'Proxy failed'}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "ui-dashboard"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
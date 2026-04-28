import os
import requests
import logging
from flask import Flask, request, jsonify, render_template_string, Response

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Service Discovery
GATEWAY_URL = os.environ.get('GATEWAY_URL', 'http://api-gateway:8000')

@app.route('/')
def index():
    """
    Renders the NEOMonitor Global Dashboard.
    Uses client-side JavaScript Fetch API to call /risk endpoint.
    """
    html = """
    <html>
        <head>
            <title>NEOMonitor Global Dashboard</title>
            <script>
                let currentSortField = 'miss_distance_km';
                let currentSortOrder = 'desc';

                function toggleSort(field) {
                    if (currentSortField === field) {
                        currentSortOrder = currentSortOrder === 'desc' ? 'asc' : 'desc';
                    } else {
                        currentSortField = field;
                        currentSortOrder = 'desc';
                    }
                    updateRiskReport();
                }

                function sortAsteroids(objects) {
                    return objects.sort((a, b) => {
                        const aVal = Number(a[currentSortField]);
                        const bVal = Number(b[currentSortField]);
                        if (aVal === bVal) return 0;
                        const direction = currentSortOrder === 'asc' ? 1 : -1;
                        return aVal > bVal ? direction : -direction;
                    });
                }

                async function updateRiskReport(event) {
                    if (event) {
                        event.preventDefault();
                    }
                    try {
                        const thresholdElement = document.getElementById('threshold');
                        const hazardousOnly = document.getElementById('filter-hazardous').checked;
                        const threshold = thresholdElement.value || '1000000';
                        const response = await fetch(`/risk?threshold=${encodeURIComponent(threshold)}&hazardous=${hazardousOnly}`);
                        if (!response.ok) {
                            const error = await response.text();
                            throw new Error(`Request failed: ${response.status} ${error}`);
                        }
                        const data = await response.json();
                        let objects = data.asteroids
                            .map(ast => ({
                                name: ast.name,
                                miss_distance_km: ast.miss_distance_km,
                                diameter_km: Number((ast.diameter_meters / 1000).toFixed(4)),
                                is_hazardous: ast.is_risky
                            }))
                            .filter(ast => !hazardousOnly || ast.is_hazardous);

                        const summaryParts = [
                            `Detected ${data.dangerous_count} potential risks in the current window.`,
                            hazardousOnly ? 'Showing only potentially hazardous objects.' : 'Showing all objects under the threshold.'
                        ];

                        document.getElementById('threshold-display').textContent = parseFloat(data.threshold).toLocaleString();
                        document.getElementById('filter-status').textContent = hazardousOnly ? 'Hazardous-only mode active' : 'Full risk report';
                        document.getElementById('summary').textContent = summaryParts.join(' ');

                        const objectsContainer = document.getElementById('objects-container');
                        objectsContainer.innerHTML = '';

                        if (objects.length === 0) {
                            objectsContainer.innerHTML = '<p>No matching asteroid objects found for the selected filter.</p>';
                            return;
                        }

                        objects = sortAsteroids(objects);

                        const table = document.createElement('table');
                        table.style.width = '100%';
                        table.style.borderCollapse = 'collapse';
                        table.style.background = '#fff';
                        table.style.boxShadow = '0 0 8px rgba(0,0,0,0.05)';

                        const thead = document.createElement('thead');
                        thead.innerHTML = `
                            <tr style="background: #f1f5f9; text-align: left;">
                                <th style="padding: 12px; border-bottom: 2px solid #ddd;">Name</th>
                                <th style="padding: 12px; border-bottom: 2px solid #ddd; cursor: pointer;">Distance (km) ${currentSortField === 'miss_distance_km' ? (currentSortOrder === 'desc' ? '↓' : '↑') : ''}</th>
                                <th style="padding: 12px; border-bottom: 2px solid #ddd; cursor: pointer;">Diameter (km) ${currentSortField === 'diameter_km' ? (currentSortOrder === 'desc' ? '↓' : '↑') : ''}</th>
                                <th style="padding: 12px; border-bottom: 2px solid #ddd;">Status</th>
                            </tr>
                        `;

                        const distanceHeader = thead.querySelector('th:nth-child(2)');
                        const diameterHeader = thead.querySelector('th:nth-child(3)');
                        distanceHeader.addEventListener('click', () => toggleSort('miss_distance_km'));
                        diameterHeader.addEventListener('click', () => toggleSort('diameter_km'));

                        const tbody = document.createElement('tbody');
                        objects.forEach(obj => {
                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td style="padding: 12px; border-bottom: 1px solid #eee;">${obj.name}</td>
                                <td style="padding: 12px; border-bottom: 1px solid #eee;">${obj.miss_distance_km.toLocaleString()}</td>
                                <td style="padding: 12px; border-bottom: 1px solid #eee;">${obj.diameter_km.toLocaleString()}</td>
                                <td style="padding: 12px; border-bottom: 1px solid #eee; color: ${obj.is_hazardous ? 'red' : '#333'}; font-weight: ${obj.is_hazardous ? '700' : '400'};">${obj.is_hazardous ? 'Potentially Hazardous' : 'Normal'}</td>
                            `;
                            tbody.appendChild(row);
                        });

                        table.appendChild(thead);
                        table.appendChild(tbody);
                        objectsContainer.appendChild(table);
                    } catch (err) {
                        document.getElementById('summary').textContent = `Unable to load asteroid risk data: ${err.message}`;
                        document.getElementById('objects-container').innerHTML = `<p style="color: red;">${err.message}</p>`;
                    }
                }

                window.onload = updateRiskReport;
            </script>
        </head>
        <body style="font-family: sans-serif; padding: 20px; background: #f9f9f9;">
            <h1>NEO-Sentinel Global Risk Report</h1>
            <form id="controls-form" onsubmit="updateRiskReport(event)">
                <p>
                    <label for="threshold">Global Threshold (km):</label>
                    <input type="number" id="threshold" value="1000000" step="1000" placeholder="Enter threshold in km" style="width: 180px; margin-left: 10px;">
                    <button type="submit" style="margin-left: 10px;">Apply</button>
                </p>
                <p>
                    <label>
                        <input type="checkbox" id="filter-hazardous">
                        Show only potentially hazardous objects
                    </label>
                </p>
            </form>
            <p>
                <strong>Current Threshold:</strong> <span id="threshold-display">1,000,000</span> km<br>
                <em id="filter-status">Full risk report</em>
            </p>
            <div style="background: #ffffff; padding: 15px; border-radius: 5px; border: 1px solid #ddd;">
                <h3 id="summary">Loading...</h3>
            </div>
            <hr>
            <div id="objects-container">
                <p>Loading asteroid data...</p>
            </div>
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
        return Response(response.content, status=response.status_code, content_type=response.headers.get('Content-Type', 'application/json'))
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        return jsonify({'error': 'Proxy failed', 'details': str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "ui-dashboard"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
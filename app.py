import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)

NODE_COORDS = {
    'Hub': [14.6819, 77.6006],
    'Node-A (Main St)': [14.6890, 77.6100],
    'Node-B (West End)': [14.6750, 77.5900],
    'Node-C (South Ave)': [14.6700, 77.5800],
    'Node-D (North Zone)': [14.6950, 77.6200],
    'Node-E (East Wing)': [14.6890, 77.6100],
    'Node-F (Central Hospital)': [14.7000, 77.6300]
}

ROAD_NETWORK = {
    'Hub': {'Node-A (Main St)': 2, 'Node-B (West End)': 5, 'Node-C (South Ave)': 4},
    'Node-A (Main St)': {'Hub': 2, 'Node-D (North Zone)': 3, 'Node-E (East Wing)': 7},
    'Node-B (West End)': {'Hub': 5, 'Node-C (South Ave)': 1},
    'Node-C (South Ave)': {'Hub': 4, 'Node-B (West End)': 1, 'Node-F (Central Hospital)': 4},
    'Node-D (North Zone)': {'Node-A (Main St)': 3, 'Node-E (East Wing)': 2},
    'Node-E (East Wing)': {'Node-A (Main St)': 7, 'Node-D (North Zone)': 2, 'Node-F (Central Hospital)': 3},
    'Node-F (Central Hospital)': {'Node-C (South Ave)': 4, 'Node-E (East Wing)': 3}
}

def find_optimal_route(start, target):
    queue = [(0, start, [start])]
    visited = set()
    while queue:
        queue.sort(key=lambda x: x[0])
        cost, current, path = queue.pop(0)
        if current == target:
            return path, cost
        if current not in visited:
            visited.add(current)
            for neighbor, weight in ROAD_NETWORK.get(current, {}).items():
                if neighbor not in visited:
                    queue.append((cost + weight, neighbor, path + [neighbor]))
    return [start, target], 3

def init_db():
    conn = sqlite3.connect('ambulance.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            emergency_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            optimal_route TEXT,
            total_distance TEXT,
            assigned_ambulance TEXT,
            status TEXT DEFAULT 'En Route',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

SIDEBAR_TEMPLATE = """
    <div class="sidebar d-none d-lg-block">
        <div class="brand">
            <i class="fa-solid fa-truck-medical text-danger fa-lg"></i> AmbuTrack
        </div>
        <div class="text-muted small mb-3 text-uppercase fw-bold" style="font-size: 0.75rem;">Ambulance Dispatch System</div>
        <ul class="nav flex-column">
            <li class="nav-item"><a class="nav-link active" href="/"><i class="fa-solid fa-chart-pie"></i> Dashboard</a></li>
            <li class="nav-item"><a class="nav-link" href="/map"><i class="fa-solid fa-map-location-dot"></i> Live Map</a></li>
            <li class="nav-item"><a class="nav-link" href="/fleet"><i class="fa-solid fa-truck"></i> Ambulance Fleet</a></li>
            <li class="nav-item"><a class="nav-link" href="/incidents"><i class="fa-solid fa-list-check"></i> Incidents</a></li>
            <li class="nav-item"><a class="nav-link" href="/analytics"><i class="fa-solid fa-chart-line"></i> Analytics</a></li>
            <li class="nav-item"><a class="nav-link" href="/hospitals"><i class="fa-solid fa-hospital"></i> Hospitals</a></li>
            <li class="nav-item"><a class="nav-link" href="/users"><i class="fa-solid fa-users"></i> Users</a></li>
            <li class="nav-item"><a class="nav-link" href="/settings"><i class="fa-solid fa-gear"></i> Settings</a></li>
        </ul>
        <div class="mt-4 p-3 bg-dark rounded-3 border border-secondary text-white small">
            <div class="text-danger fw-bold mb-1"><i class="fa-solid fa-phone"></i> Emergency Helpline</div>
            <div class="fs-4 fw-bold">108</div>
            <div class="text-muted" style="font-size: 0.7rem;">Always Here for You</div>
        </div>
    </div>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AmbuTrack - Ambulance Dispatch System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <!-- Leaflet Routing Machine CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet-routing-machine@latest/dist/leaflet-routing-machine.css" />
    <style>
        body { background-color: #f4f7f6; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .sidebar { width: 260px; background-color: #0f172a; min-height: 100vh; position: fixed; color: #94a3b8; padding: 20px; z-index: 1000; }
        .sidebar .brand { color: #ffffff; font-weight: bold; font-size: 1.2rem; display: flex; align-items: center; gap: 10px; margin-bottom: 30px; }
        .sidebar .nav-link { color: #94a3b8; padding: 12px 15px; border-radius: 8px; margin-bottom: 5px; display: flex; align-items: center; gap: 12px; font-size: 0.95rem; }
        .sidebar .nav-link:hover, .sidebar .nav-link.active { background-color: #1e293b; color: #ffffff; }
        .main-content { margin-left: 260px; padding: 25px; }
        .top-navbar { background: #ffffff; padding: 12px 25px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; }
        .stat-card { background: #ffffff; border-radius: 10px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); border: none; }
        .card-custom { background: #ffffff; border-radius: 10px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); border: none; margin-bottom: 20px; }
        #map { height: 350px; width: 100%; border-radius: 8px; }
        .badge-high { background-color: #fee2e2; color: #dc2626; font-weight: 600; }
        .badge-medium { background-color: #fef3c7; color: #d97706; font-weight: 600; }
        .badge-low { background-color: #d1fae5; color: #059669; font-weight: 600; }
    </style>
</head>
<body>

    """ + SIDEBAR_TEMPLATE + """

    <div class="main-content">
        <div class="top-navbar">
            <div class="input-group" style="max-width: 350px;">
                <span class="input-group-text bg-light border-0"><i class="fa-solid fa-search text-muted"></i></span>
                <input type="text" class="form-control bg-light border-0" placeholder="Search location, incident or ambulance...">
            </div>
            <div class="d-flex align-items: center gap-4">
                <div class="d-flex align-items: center gap-2 text-success small fw-bold">
                    <span class="badge bg-success rounded-circle p-1"></span> System Online
                </div>
                <div>
                    <span><strong>Irfan<br><small class="text-muted" style="font-size: 0.75rem;">Admin</small></span>
                </div>
            </div>
        </div>

        <div class="d-flex justify-content-between align-items-center mb-4">
            <div>
                <h3 class="fw-bold mb-0">Ambulance Dispatch & Route Optimizer</h3>
                <p class="text-muted small mb-0">Smart Response. Safer Communities.</p>
            </div>
            <div class="text-end text-danger fw-bold d-flex align-items: center gap-2">
                <i class="fa-solid fa-heart-pulse fa-lg"></i> Every Second Counts
            </div>
        </div>

        <div class="row g-3 mb-4">
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="text-muted small">Total Requests Today</div>
                    <div class="d-flex justify-content-between align-items-end mt-2">
                        <h3 class="fw-bold mb-0">{{ total_count }}</h3>
                        <span class="text-success small fw-bold"><i class="fa-solid fa-arrow-up"></i> 12%</span>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="text-muted small">Active Dispatches</div>
                    <div class="d-flex justify-content-between align-items-end mt-2">
                        <h3 class="fw-bold mb-0">3</h3>
                        <span class="text-success small fw-bold"><i class="fa-solid fa-arrow-up"></i> 50%</span>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="text-muted small">Available Fleet</div>
                    <div class="d-flex justify-content-between align-items-end mt-2">
                        <h3 class="fw-bold mb-0">8</h3>
                        <span class="text-success small fw-bold"><i class="fa-solid fa-check"></i></span>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card border-start border-danger border-4">
                    <div class="text-muted small">Critical Incidents</div>
                    <div class="d-flex justify-content-between align-items-end mt-2">
                        <h3 class="fw-bold mb-0 text-danger">1</h3>
                        <span class="badge bg-danger">Alert</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="row g-3">
            <div class="col-lg-4">
                <div class="card-custom">
                    <h5 class="fw-bold mb-3"><i class="fa-solid fa-triangle-exclamation text-danger me-2"></i>Report Emergency Incident</h5>
                    <form action="/submit" method="POST">
                        <div class="mb-3">
                            <label class="form-label small fw-bold text-muted">Incident Location (Node / Landmark)</label>
                            <select class="form-select" name="location" required>
                                <option value="Node-A (Main St)">Node-A (Main St)</option>
                                <option value="Node-B (West End)">Node-B (West End)</option>
                                <option value="Node-C (South Ave)">Node-C (South Ave)</option>
                                <option value="Node-D (North Zone)">Node-D (North Zone)</option>
                                <option value="Node-E (East Wing)">Node-E (East Wing)</option>
                                <option value="Node-F (Central Hospital)">Node-F (Central Hospital)</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label small fw-bold text-muted">Emergency Type</label>
                            <select class="form-select" name="type" required>
                                <option value="Medical Emergency">Medical Emergency</option>
                                <option value="Road Accident">Road Accident</option>
                                <option value="Cardiac Arrest">Cardiac Arrest</option>
                                <option value="Fire Incident">Fire Incident</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label small fw-bold text-muted">Severity Level</label>
                            <select class="form-select" name="severity">
                                <option value="High">High</option>
                                <option value="Medium">Medium</option>
                                <option value="Low">Low</option>
                            </select>
                        </div>
                        <button type="submit" class="btn btn-primary w-100 py-2 fw-bold"><i class="fa-solid fa-paper-plane me-2"></i>Dispatch Optimized Ambulance</button>
                    </form>
                </div>
            </div>

            <div class="col-lg-5">
                <div class="card-custom">
                    <h5 class="fw-bold mb-2"><i class="fa-solid fa-map-location text-primary me-2"></i>Live GIS Route Map</h5>
                    <div id="map" class="mb-3"></div>
                </div>
            </div>

            <div class="col-lg-3">
                <div class="card-custom">
                    <h6 class="fw-bold mb-3"><i class="fa-solid fa-truck-medical text-success me-2"></i>Ambulance Fleet</h6>
                    <div class="d-flex flex-column gap-3">
                        <div class="d-flex justify-content-between align-items-center border-bottom pb-2">
                            <div><strong class="small d-block">AMB-01</strong><span class="text-muted" style="font-size: 0.75rem;">City Center</span></div>
                            <span class="badge bg-success bg-opacity-10 text-success small">Available</span>
                        </div>
                        <div class="d-flex justify-content-between align-items-center border-bottom pb-2">
                            <div><strong class="small d-block">AMB-02</strong><span class="text-muted" style="font-size: 0.75rem;">East Wing</span></div>
                            <span class="badge bg-success bg-opacity-10 text-success small">Available</span>
                        </div>
                        <div class="d-flex justify-content-between align-items-center border-bottom pb-2">
                            <div><strong class="small d-block">AMB-03</strong><span class="text-muted" style="font-size: 0.75rem;">To Node-A</span></div>
                            <span class="badge bg-danger bg-opacity-10 text-danger small">En Route</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card-custom">
            <h5 class="fw-bold mb-3"><i class="fa-solid fa-list-check text-primary me-2"></i>Recent Incidents & Dispatch Status</h5>
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>Incident ID</th>
                            <th>Location Node</th>
                            <th>Type</th>
                            <th>Severity</th>
                            <th>Assigned Ambulance</th>
                            <th>Status</th>
                            <th class="text-end">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for row in incidents %}
                        <tr>
                            <td><strong>#INC-{{ 1040 + row[0] }}</strong></td>
                            <td>{{ row[1] }}</td>
                            <td>{{ row[2] }}</td>
                            <td><span class="badge {% if row[3] == 'High' %}badge-high{% elif row[3] == 'Medium' %}badge-medium{% else %}badge-low{% endif %}">{{ row[3] }}</span></td>
                            <td>{{ row[6] }}</td>
                            <td><span class="badge bg-primary bg-opacity-15 text-primary">{{ row[7] }}</span></td>
                            <td class="text-end">
                                <a href="/resolve/{{ row[0] }}" class="btn btn-sm btn-light text-success" title="Mark Resolved"><i class="fa-solid fa-check"></i></a>
                            </td>
                        </tr>
                        {% else %}
                        <tr><td colspan="7" class="text-center text-muted py-4">No recent incidents logged yet.</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <!-- Leaflet Routing Machine JS -->
    <script src="https://unpkg.com/leaflet-routing-machine@latest/dist/leaflet-routing-machine.js"></script>
    <script>
        const map = L.map('map').setView([14.6819, 77.6006], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);

        const nodeCoords = {{ coords | safe }};

        {% if latest_path %}
            const waypointsList = [
                {% for node in latest_path %}
                    L.latLng(nodeCoords["{{ node }}"][0], nodeCoords["{{ node }}"][1]),
                {% endfor %}
            ];

            if (waypointsList.length > 1) {
                L.Routing.control({
                    waypoints: waypointsList,
                    routeWhileDragging: false,
                    addWaypoints: false,
                    draggableWaypoints: false,
                    fitSelectedRoutes: true,
                    show: false
                }).addTo(map);
            }
        {% else %}
            L.marker(nodeCoords['Hub']).addTo(map).bindPopup('<b>Ambulance Fleet Hub</b>').openPopup();
        {% endif %}
    </script>
</body>
</html>
"""

def render_subpage(title, active_tab, content_html):
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>AmbuTrack - {title}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            body {{ background-color: #f4f7f6; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
            .sidebar {{ width: 260px; background-color: #0f172a; min-height: 100vh; position: fixed; color: #94a3b8; padding: 20px; z-index: 1000; }}
            .sidebar .brand {{ color: #ffffff; font-weight: bold; font-size: 1.2rem; display: flex; align-items: center; gap: 10px; margin-bottom: 30px; }}
            .sidebar .nav-link {{ color: #94a3b8; padding: 12px 15px; border-radius: 8px; margin-bottom: 5px; display: flex; align-items: center; gap: 12px; font-size: 0.95rem; }}
            .sidebar .nav-link:hover, .sidebar .nav-link.active {{ background-color: #1e293b; color: #ffffff; }}
            .main-content {{ margin-left: 260px; padding: 25px; }}
            .card-custom {{ background: #ffffff; border-radius: 10px; padding: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); border: none; }}
        </style>
    </head>
    <body>
        {SIDEBAR_TEMPLATE}
        <div class="main-content">
            <h2 class="fw-bold mb-4">{title}</h2>
            <div class="card-custom">
                {content_html}
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/')
def home():
    conn = sqlite3.connect('ambulance.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, location, emergency_type, severity, optimal_route, total_distance, assigned_ambulance, status FROM incidents ORDER BY id DESC')
    incidents = cursor.fetchall()
    
    latest_path = []
    if incidents:
        loc = incidents[0][1]
        path, _ = find_optimal_route('Hub', loc)
        latest_path = path

    cursor.execute('SELECT COUNT(*) FROM incidents')
    total_count = cursor.fetchone()[0]
    conn.close()
    return render_template_string(DASHBOARD_HTML, incidents=incidents, coords=str(NODE_COORDS), latest_path=latest_path, total_count=total_count)

@app.route('/map')
def live_map():
    return render_subpage("Live GIS Tracking Map", "map", "<p class='text-muted'>Full-screen interactive tracking matrix loaded. Real-time fleet tracking active.</p>")

@app.route('/fleet')
def fleet():
    return render_subpage("Ambulance Fleet Management", "fleet", "<h5>Registered Units</h5><ul class='list-group mt-3'><li class='list-group-item'>AMB-01 - City Center (Available)</li></ul>")

@app.route('/incidents')
def incidents_page():
    conn = sqlite3.connect('ambulance.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, location, emergency_type, severity, status, timestamp FROM incidents ORDER BY id DESC')
    data = cursor.fetchall()
    conn.close()
    rows = "".join([f"<tr><td>#INC-{1040+r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td><td>{r[5]}</td></tr>" for r in data])
    table = f"<table class='table'><thead><tr><th>ID</th><th>Location</th><th>Type</th><th>Severity</th><th>Status</th><th>Timestamp</th></tr></thead><tbody>{rows if rows else '<tr><td colspan=\"6\" class=\"text-center\">No incidents logged</td></tr>'}</tbody></table>"
    return render_subpage("All Incidents Log", "incidents", table)

@app.route('/analytics')
def analytics():
    return render_subpage("System Analytics & Reports", "analytics", "<p class='text-muted'>Average response time: <strong>4.2 minutes</strong>.</p>")

@app.route('/hospitals')
def hospitals():
    return render_subpage("Connected Hospitals Directory", "hospitals", "<ul><li><strong>Central Hospital</strong> - Node-F</li></ul>")

@app.route('/users')
def users():
    return render_subpage("System Operators & Users", "users", "<p>Logged in as: <strong>Durgam Kasim (Admin)</strong></p>")

@app.route('/settings')
def settings():
    return render_subpage("Application Settings", "settings", "<p>Network Binding: <code>0.0.0.0:8000</code></p>")

@app.route('/submit', methods=['POST'])
def submit():
    location = request.form.get('location')
    etype = request.form.get('type')
    severity = request.form.get('severity')
    
    path, distance = find_optimal_route('Hub', location)
    route_str = " ➔ ".join(path)
    
    conn = sqlite3.connect('ambulance.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO incidents (location, emergency_type, severity, optimal_route, total_distance, assigned_ambulance, status) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                   (location, etype, severity, route_str, f"{distance} km", "AMB-03", 'En Route'))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route('/resolve/<int:id>')
def resolve(id):
    conn = sqlite3.connect('ambulance.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE incidents SET status = 'Completed' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
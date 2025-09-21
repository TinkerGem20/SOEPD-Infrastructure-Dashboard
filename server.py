from flask import Flask, jsonify, request, send_from_directory, Response
import json
import os
import queue  # 👈 needed for SSE

app = Flask(__name__)

PROJECTS_FILE = "projects.json"
subscribers = []  # 👈 to keep track of clients connected via SSE

# ------------------------
# 🔹 Helper Functions
# ------------------------

def load_projects():
    if not os.path.exists(PROJECTS_FILE):
        return []
    with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_projects(projects):
    with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(projects, f, indent=2)

def notify_clients():
    """Push new update to all connected SSE clients."""
    dead = []
    data = json.dumps(load_projects())
    for sub in subscribers:
        try:
            sub.put(data, block=False)
        except:
            dead.append(sub)
    for d in dead:
        subscribers.remove(d)

# ------------------------
# 🔹 API ROUTES
# ------------------------

@app.route("/projects", methods=["GET"])
def get_projects():
    """Return all projects"""
    return jsonify(load_projects())

@app.route("/projects.json", methods=["GET"])
def get_projects_json():
    """Serve the raw projects.json file (for project.html fetch)"""
    return send_from_directory(".", "projects.json")

@app.route("/project/<pr>", methods=["GET"])
def get_project(pr):
    """Return a single project by PR number"""
    projects = load_projects()
    for p in projects:
        if p["pr"] == pr:
            return jsonify(p)
    return jsonify({"error": "Project not found"}), 404

@app.route("/project/<pr>/notes", methods=["POST"])
def add_note(pr):
    """
    Add a new project update (note).
    Body can include either:
    - { "date": "2025-09-21", "update": "..." }
    - or { "dateStart": "2025-09-20", "dateEnd": "2025-09-25", "update": "..." }
    """
    projects = load_projects()
    for p in projects:
        if p["pr"] == pr:
            note = request.json
            if "notes" not in p:
                p["notes"] = []
            p["notes"].append(note)
            save_projects(projects)
            notify_clients()
            return jsonify({"message": "Note added", "project": p}), 201
    return jsonify({"error": "Project not found"}), 404

# ------------------------
# 🔹 SSE for Live Updates
# ------------------------

@app.route("/events")
def events():
    """Clients connect here for live updates via Server-Sent Events."""
    def gen():
        q = queue.Queue()
        subscribers.append(q)
        try:
            while True:
                data = q.get()
                yield f"data: {data}\n\n"
        except GeneratorExit:
            subscribers.remove(q)

    return Response(gen(), mimetype="text/event-stream")

# ------------------------
# 🔹 FRONTEND ROUTES
# ------------------------

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/project.html")
def project_page():
    return send_from_directory(".", "project.html")

if __name__ == "__main__":
    app.run(debug=True, threaded=True)

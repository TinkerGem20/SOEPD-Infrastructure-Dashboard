from flask import Flask, jsonify, request, send_from_directory, Response, make_response
import json
import os
import queue  # 👈 needed for SSE
import datetime
import csv
import io

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

def to_date(d):
    return datetime.datetime.strptime(d, "%Y-%m-%d").date()

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
# 🔹 Summary & CSV Export
# ------------------------

@app.route("/project/<pr>/updates/summary", methods=["GET"])
def get_updates_summary(pr):
    """Return JSON summary of updates within a date range"""
    start_date = request.args.get("start")
    end_date = request.args.get("end")

    projects = load_projects()
    project = next((p for p in projects if p["pr"] == pr), None)
    if not project or "notes" not in project:
        return jsonify({"error": "No updates found"}), 404

    filtered_notes = []
    for note in project["notes"]:
        if "date" in note:
            d = to_date(note["date"])
            if start_date and d < to_date(start_date):
                continue
            if end_date and d > to_date(end_date):
                continue
            filtered_notes.append(note)
        elif "dateStart" in note and "dateEnd" in note:
            ds, de = to_date(note["dateStart"]), to_date(note["dateEnd"])
            if start_date and de < to_date(start_date):
                continue
            if end_date and ds > to_date(end_date):
                continue
            filtered_notes.append(note)

    return jsonify({
        "project": project["title"],
        "pr": project["pr"],
        "updates": filtered_notes
    })

@app.route("/project/<pr>/updates/export", methods=["GET"])
def export_updates_csv(pr):
    """Export updates as CSV (Excel-readable)."""
    start_date = request.args.get("start")
    end_date = request.args.get("end")

    projects = load_projects()
    project = next((p for p in projects if p["pr"] == pr), None)
    if not project or "notes" not in project:
        return jsonify({"error": "No updates found"}), 404

    filtered_notes = []
    for note in project["notes"]:
        if "date" in note:
            d = to_date(note["date"])
            if start_date and d < to_date(start_date):
                continue
            if end_date and d > to_date(end_date):
                continue
            filtered_notes.append(note)
        elif "dateStart" in note and "dateEnd" in note:
            ds, de = to_date(note["dateStart"]), to_date(note["dateEnd"])
            if start_date and de < to_date(start_date):
                continue
            if end_date and ds > to_date(end_date):
                continue
            filtered_notes.append(note)

    # Generate CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Project", "PR", "Date/Start", "End", "Update"])
    for n in filtered_notes:
        writer.writerow([
            project["title"],
            project["pr"],
            n.get("date", n.get("dateStart", "")),
            n.get("dateEnd", ""),
            n.get("update", "")
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={project['pr']}_updates.csv"
    response.headers["Content-Type"] = "text/csv"
    return response


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

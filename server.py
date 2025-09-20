from flask import Flask, jsonify, request, send_from_directory
import json
import os

app = Flask(__name__)

PROJECTS_FILE = "projects.json"

# ✅ Load projects from JSON file
def load_projects():
    if not os.path.exists(PROJECTS_FILE):
        return []
    with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# ✅ Save projects back to JSON file
def save_projects(projects):
    with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(projects, f, indent=2)

# ------------------------
# 🔹 ROUTES
# ------------------------

@app.route("/projects", methods=["GET"])
def get_projects():
    """Return all projects"""
    return jsonify(load_projects())

@app.route("/project/<pr>", methods=["GET"])
def get_project(pr):
    """Return one project by PR number"""
    projects = load_projects()
    project = next((p for p in projects if p["pr"] == pr), None)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    return jsonify(project)

@app.route("/project/<pr>/notes", methods=["POST"])
def add_note(pr):
    """
    Add a new project update (note).
    Body must include: { "date": "...", "update": "...", "status": "..." }
    """
    projects = load_projects()
    for p in projects:
        if p["pr"] == pr:
            note = request.json
            if "notes" not in p:
                p["notes"] = []
            p["notes"].append(note)
            save_projects(projects)
            return jsonify({"message": "Note added", "project": p}), 201
    return jsonify({"error": "Project not found"}), 404

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
    app.run(debug=True)

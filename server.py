from flask import Flask, jsonify, request, send_from_directory
import json
import os

app = Flask(__name__, static_folder=".", static_url_path="")

PROJECTS_FILE = "projects.json"

# Load projects from file
def load_projects():
    if not os.path.exists(PROJECTS_FILE):
        return []
    with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

# Save projects to file
def save_projects(projects):
    with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(projects, f, indent=2, ensure_ascii=False)

# Serve index.html at root URL
@app.route("/")
def index():
    return send_from_directory(".", "index.html")

# API to get all projects
@app.route("/projects", methods=["GET"])
def get_projects():
    return jsonify(load_projects())

# API to add a new project
@app.route("/add_project", methods=["POST"])
def add_project():
    projects = load_projects()
    data = request.get_json()

    if not data.get("pr") or not data.get("title"):
        return jsonify({"error": "Missing required fields"}), 400

    projects.append(data)
    save_projects(projects)

    return jsonify({"message": "Project added successfully"}), 201

if __name__ == "__main__":
    app.run(debug=True)

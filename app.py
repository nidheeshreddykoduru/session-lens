import json
import os
import uuid
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS

USERS_FILE = "users.json"
SESSIONS_DIR = "sessions"
PROJECTS_FILE = "projects.json"


def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def load_projects():
    if not os.path.exists(PROJECTS_FILE):
        return []
    with open(PROJECTS_FILE, "r") as f:
        return json.load(f)


def save_projects(projects):
    with open(PROJECTS_FILE, "w") as f:
        json.dump(projects, f, indent=2)


def user_projects():
    owner = session["username"]
    return [p for p in load_projects() if p.get("owner") == owner]


def owned_project(project_id):
    return next((p for p in user_projects() if p["id"] == project_id), None)


def count_sessions(project_id):
    path = os.path.join(SESSIONS_DIR, project_id)
    if not os.path.isdir(path):
        return 0
    return len([f for f in os.listdir(path) if f.endswith(".json")])


def session_has_errors(events):
    for e in events:
        if e.get("type") == 6:
            payload = e.get("data", {}).get("payload", {})
            if isinstance(payload, dict) and payload.get("level") == "error":
                return True
    return False


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-before-deploying")
CORS(app)
os.makedirs(SESSIONS_DIR, exist_ok=True)

if not os.path.exists(USERS_FILE):
    save_users([])


# ── Auth ──────────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("username"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        users = load_users()
        user = next((u for u in users if u["username"] == username), None)
        if not user or user["password"] != password:
            return jsonify({"error": "Invalid username or password."}), 401
        session["username"] = username
        return jsonify({"ok": True})
    return render_template("login.html")


@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm", "")
    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400
    if password != confirm:
        return jsonify({"error": "Passwords do not match."}), 400
    users = load_users()
    if any(u["username"] == username for u in users):
        return jsonify({"error": "Username already taken."}), 409
    users.append({"username": username, "password": password, "created_at": datetime.now().isoformat()})
    save_users(users)
    session["username"] = username
    return jsonify({"ok": True})


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Public: recording endpoint ────────────────────────────────────────────────

@app.route("/record", methods=["POST"])
def record():
    data = request.get_json()
    if not data:
        return jsonify({"error": "no data"}), 400

    project_id = data.get("projectId")
    session_id = data.get("sessionId") or ("sess_" + uuid.uuid4().hex[:8])
    events = data.get("events", [])

    if project_id:
        session_dir = os.path.join(SESSIONS_DIR, project_id)
        os.makedirs(session_dir, exist_ok=True)
        filepath = os.path.join(session_dir, f"{session_id}.json")
    else:
        filepath = os.path.join(SESSIONS_DIR, f"{session_id}.json")

    existing = []
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            existing = json.load(f)
    existing.extend(events)
    with open(filepath, "w") as f:
        json.dump(existing, f)

    label = f"project:{project_id} | " if project_id else ""
    print(f"[{label}session:{session_id}] +{len(events)} events (total {len(existing)})")
    return jsonify({"sessionId": session_id, "received": len(events), "total": len(existing)})


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
@login_required
def dashboard():
    projects = user_projects()
    for p in projects:
        p["session_count"] = count_sessions(p["id"])
    return render_template("dashboard.html", projects=projects, username=session["username"])


@app.route("/projects/new", methods=["POST"])
@login_required
def new_project():
    name = request.form.get("name", "").strip()
    if not name:
        return redirect(url_for("dashboard"))
    all_projects = load_projects()
    project_id = "proj_" + uuid.uuid4().hex[:8]
    all_projects.append({
        "id": project_id,
        "name": name,
        "owner": session["username"],
        "created_at": datetime.now().isoformat(),
    })
    save_projects(all_projects)
    return redirect(url_for("project_view", project_id=project_id))


# ── Project ───────────────────────────────────────────────────────────────────

@app.route("/project/<project_id>")
@login_required
def project_view(project_id):
    proj = owned_project(project_id)
    if not proj:
        return "Project not found", 404

    project_dir = os.path.join(SESSIONS_DIR, project_id)
    sessions = []
    if os.path.isdir(project_dir):
        for filename in os.listdir(project_dir):
            if not filename.endswith(".json"):
                continue
            sid = filename[:-5]
            with open(os.path.join(project_dir, filename), "r") as f:
                events = json.load(f)
            first_ts = events[0]["timestamp"] if events else 0
            recorded_at = datetime.fromtimestamp(first_ts / 1000).strftime("%Y-%m-%d %H:%M:%S") if first_ts else "—"
            sessions.append({"id": sid, "events": len(events), "recorded_at": recorded_at, "ts": first_ts, "has_errors": session_has_errors(events)})
    sessions.sort(key=lambda s: s["ts"], reverse=True)
    return render_template("project.html", project=proj, sessions=sessions)


# ── Replay ────────────────────────────────────────────────────────────────────

@app.route("/replay/<project_id>/<session_id>")
@login_required
def replay(project_id, session_id):
    proj = owned_project(project_id)
    if not proj:
        return "Project not found", 404
    filepath = os.path.join(SESSIONS_DIR, project_id, f"{session_id}.json")
    if not os.path.exists(filepath):
        return "Session not found", 404
    return render_template("replay.html", project=proj, session_id=session_id)


@app.route("/sessions/<project_id>/<session_id>")
@login_required
def session_data(project_id, session_id):
    if not owned_project(project_id):
        return jsonify({"error": "not found"}), 404
    filepath = os.path.join(SESSIONS_DIR, project_id, f"{session_id}.json")
    if not os.path.exists(filepath):
        return jsonify({"error": "session not found"}), 404
    with open(filepath, "r") as f:
        return app.response_class(f.read(), mimetype="application/json")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

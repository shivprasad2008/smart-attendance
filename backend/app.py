"""
SmartAttend — Python Flask Backend
No database. In-memory storage only.
Admin: shiv / 1234
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid, random, string, time
from functools import wraps

app = Flask(__name__)
CORS(app)

# ══════════════════════════════════════
# IN-MEMORY STORAGE
# ══════════════════════════════════════

users = [
    {
        "id": "admin-001",
        "name": "Shiv",
        "username": "shiv",
        "password": "1234",
        "role": "admin"
    }
]

sessions = []     # { id, teacher_id, teacher_name, subject, code, status, created_at, ended_at }
attendance = []   # { id, student_id, student_name, session_id, subject, timestamp }

# Simple token store: token -> user_id
tokens = {}

# ══════════════════════════════════════
# HELPERS
# ══════════════════════════════════════

def find_user_by_id(uid):
    return next((u for u in users if u["id"] == uid), None)

def find_user_by_username(username):
    return next((u for u in users if u["username"].lower() == username.lower()), None)

def gen_code():
    """Generate ATT-XXXX style code"""
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(random.choices(chars, k=4))
    return f"ATT-{suffix}"

def get_current_user():
    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if not token or token not in tokens:
        return None
    uid = tokens[token]
    return find_user_by_id(uid)

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        request.current_user = user
        return f(*args, **kwargs)
    return decorated

def require_role(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"error": "Unauthorized"}), 401
            if user["role"] not in roles:
                return jsonify({"error": "Forbidden"}), 403
            request.current_user = user
            return f(*args, **kwargs)
        return decorated
    return decorator

def safe_user(u):
    return {"id": u["id"], "name": u["name"], "username": u["username"], "role": u["role"]}

# ══════════════════════════════════════
# AUTH ROUTES
# ══════════════════════════════════════

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    user = find_user_by_username(username)
    if not user or user["password"] != password:
        return jsonify({"error": "Invalid credentials"}), 401

    token = str(uuid.uuid4())
    tokens[token] = user["id"]

    return jsonify({"token": token, "user": safe_user(user)})


@app.route("/api/me", methods=["GET"])
@require_auth
def me():
    return jsonify({"user": safe_user(request.current_user)})


@app.route("/api/logout", methods=["POST"])
@require_auth
def logout():
    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    tokens.pop(token, None)
    return jsonify({"message": "Logged out"})

# ══════════════════════════════════════
# USER MANAGEMENT (Admin only)
# ══════════════════════════════════════

@app.route("/api/users", methods=["GET"])
@require_role("admin")
def get_users():
    role_filter = request.args.get("role")
    result = [safe_user(u) for u in users if u["role"] != "admin"]
    if role_filter:
        result = [u for u in result if u["role"] == role_filter]
    return jsonify({"users": result, "total": len(result)})


@app.route("/api/users", methods=["POST"])
@require_role("admin")
def create_user():
    data = request.json or {}
    name     = data.get("name", "").strip()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    role     = data.get("role", "student").strip()

    if not name or not username or not password:
        return jsonify({"error": "Name, username, and password required"}), 400
    if role not in ("student", "teacher"):
        return jsonify({"error": "Role must be student or teacher"}), 400
    if find_user_by_username(username):
        return jsonify({"error": "Username already taken"}), 409

    new_user = {
        "id": str(uuid.uuid4()),
        "name": name,
        "username": username,
        "password": password,
        "role": role
    }
    users.append(new_user)
    return jsonify({"user": safe_user(new_user)}), 201


@app.route("/api/users/<uid>", methods=["DELETE"])
@require_role("admin")
def delete_user(uid):
    global users
    user = find_user_by_id(uid)
    if not user or user["role"] == "admin":
        return jsonify({"error": "User not found"}), 404
    users = [u for u in users if u["id"] != uid]
    return jsonify({"message": "User deleted"})

# ══════════════════════════════════════
# SESSION ROUTES (Teacher)
# ══════════════════════════════════════

@app.route("/api/sessions/start", methods=["POST"])
@require_role("teacher")
def start_session():
    data    = request.json or {}
    subject = data.get("subject", "").strip()
    if not subject:
        return jsonify({"error": "Subject is required"}), 400

    # Check if teacher already has an active session
    existing = next((s for s in sessions if s["teacher_id"] == request.current_user["id"] and s["status"] == "ACTIVE"), None)
    if existing:
        return jsonify({"error": "You already have an active session. End it first."}), 400

    code = gen_code()
    # Ensure uniqueness
    while any(s["code"] == code and s["status"] == "ACTIVE" for s in sessions):
        code = gen_code()

    session = {
        "id": str(uuid.uuid4()),
        "teacher_id": request.current_user["id"],
        "teacher_name": request.current_user["name"],
        "subject": subject,
        "code": code,
        "status": "ACTIVE",
        "created_at": time.time(),
        "ended_at": None
    }
    sessions.append(session)
    return jsonify({"session": session, "code": code}), 201


@app.route("/api/sessions/end", methods=["POST"])
@require_role("teacher")
def end_session():
    active = next((s for s in sessions if s["teacher_id"] == request.current_user["id"] and s["status"] == "ACTIVE"), None)
    if not active:
        return jsonify({"error": "No active session found"}), 404
    active["status"] = "CLOSED"
    active["ended_at"] = time.time()
    count = sum(1 for a in attendance if a["session_id"] == active["id"])
    return jsonify({"session": active, "total_present": count})


@app.route("/api/sessions", methods=["GET"])
@require_role("teacher", "admin")
def get_sessions():
    uid = request.current_user["id"]
    role = request.current_user["role"]
    result = sessions if role == "admin" else [s for s in sessions if s["teacher_id"] == uid]
    # Attach present count
    enriched = []
    for s in reversed(result):
        count = sum(1 for a in attendance if a["session_id"] == s["id"])
        enriched.append({**s, "present_count": count})
    return jsonify({"sessions": enriched})


@app.route("/api/sessions/active", methods=["GET"])
@require_role("teacher")
def get_active_session():
    active = next((s for s in sessions if s["teacher_id"] == request.current_user["id"] and s["status"] == "ACTIVE"), None)
    if not active:
        return jsonify({"session": None})
    count = sum(1 for a in attendance if a["session_id"] == active["id"])
    return jsonify({"session": {**active, "present_count": count}})

# ══════════════════════════════════════
# ATTENDANCE ROUTES (Student)
# ══════════════════════════════════════

@app.route("/api/attendance/mark", methods=["POST"])
@require_role("student")
def mark_attendance():
    data = request.json or {}
    code = data.get("code", "").strip().upper()

    if not code:
        return jsonify({"error": "Attendance code is required"}), 400

    # Find active session with this code
    session = next((s for s in sessions if s["code"] == code and s["status"] == "ACTIVE"), None)
    if not session:
        return jsonify({"error": "Invalid or expired code. Check with your teacher."}), 404

    # Check duplicate
    already = next((a for a in attendance if a["student_id"] == request.current_user["id"] and a["session_id"] == session["id"]), None)
    if already:
        return jsonify({"error": "You have already marked attendance for this session."}), 409

    record = {
        "id": str(uuid.uuid4()),
        "student_id": request.current_user["id"],
        "student_name": request.current_user["name"],
        "session_id": session["id"],
        "subject": session["subject"],
        "teacher_name": session["teacher_name"],
        "timestamp": time.time()
    }
    attendance.append(record)
    return jsonify({"message": f"Attendance marked for {session['subject']}!", "record": record}), 201


@app.route("/api/attendance/my", methods=["GET"])
@require_role("student")
def my_attendance():
    uid = request.current_user["id"]
    my_records = [a for a in attendance if a["student_id"] == uid]

    # Calculate per-subject stats
    subject_map = {}
    for r in my_records:
        s = r["subject"]
        if s not in subject_map:
            subject_map[s] = 0
        subject_map[s] += 1

    # Total closed sessions per subject (to calculate %)
    closed_sessions = [s for s in sessions if s["status"] == "CLOSED"]
    subject_totals = {}
    for s in closed_sessions:
        sub = s["subject"]
        subject_totals[sub] = subject_totals.get(sub, 0) + 1

    # Also count active sessions
    for s in sessions:
        sub = s["subject"]
        if sub not in subject_totals:
            subject_totals[sub] = 0

    subject_stats = []
    for sub, attended in subject_map.items():
        total = subject_totals.get(sub, attended)
        pct = round((attended / total * 100) if total > 0 else 100)
        subject_stats.append({
            "subject": sub,
            "attended": attended,
            "total": total,
            "percentage": pct,
            "warning": pct < 75
        })

    total_attended = len(my_records)
    total_sessions = len(closed_sessions)
    overall_pct = round((total_attended / total_sessions * 100) if total_sessions > 0 else 0)

    return jsonify({
        "records": my_records,
        "subject_stats": subject_stats,
        "overall_percentage": overall_pct,
        "total_attended": total_attended,
        "total_sessions": total_sessions,
        "total_missed": total_sessions - total_attended
    })


@app.route("/api/attendance/session/<session_id>", methods=["GET"])
@require_role("teacher", "admin")
def session_attendance(session_id):
    records = [a for a in attendance if a["session_id"] == session_id]
    return jsonify({"records": records, "count": len(records)})

# ══════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════

@app.route("/api/analytics/teacher", methods=["GET"])
@require_role("teacher")
def teacher_analytics():
    uid = request.current_user["id"]
    my_sessions = [s for s in sessions if s["teacher_id"] == uid]
    closed = [s for s in my_sessions if s["status"] == "CLOSED"]

    total_sessions = len(my_sessions)
    total_attendance = sum(1 for a in attendance if any(s["id"] == a["session_id"] and s["teacher_id"] == uid for s in sessions))

    avg_present = round(total_attendance / len(closed)) if closed else 0

    # Per-session data for history
    history = []
    for s in reversed(my_sessions[-10:]):
        count = sum(1 for a in attendance if a["session_id"] == s["id"])
        history.append({
            "session_id": s["id"],
            "subject": s["subject"],
            "code": s["code"],
            "status": s["status"],
            "created_at": s["created_at"],
            "present_count": count
        })

    return jsonify({
        "total_sessions": total_sessions,
        "closed_sessions": len(closed),
        "avg_present": avg_present,
        "total_attendance_records": total_attendance,
        "history": history
    })

# ══════════════════════════════════════
# HEALTH
# ══════════════════════════════════════

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "users": len(users),
        "sessions": len(sessions),
        "attendance": len(attendance)
    })


if __name__ == "__main__":
    print("\n🚀 SmartAttend Python Backend running on http://localhost:5000")
    print("👤 Default Admin: username=shiv | password=1234\n")
    app.run(debug=True, port=5000)

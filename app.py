"""
Event Manager Web Application
Flask backend with MySQL database, session-based authentication,
and role-based access control (Admin / User).
"""

import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error

# ──────────────────────────────────────────────
# App configuration
# ──────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "event-manager-secret-key-change-me")

# ──────────────────────────────────────────────
# Database configuration (Railway-compatible)
# ──────────────────────────────────────────────
DB_CONFIG = {
    "host": os.environ.get("MYSQLHOST", "localhost"),
    "user": os.environ.get("MYSQLUSER", "root"),
    "password": os.environ.get("MYSQLPASSWORD", ""),
    "database": os.environ.get("MYSQLDATABASE", "event_manager"),
    "port": int(os.environ.get("MYSQLPORT", 3306)),
}


def get_db():
    """Return a fresh MySQL connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Database connection error: {e}")
        return None


# ──────────────────────────────────────────────
# Database initialisation
# ──────────────────────────────────────────────
def init_db():
    """Create tables and seed a default admin account if needed."""
    conn = get_db()
    if conn is None:
        print("[WARNING] Could not connect to MySQL. Check your credentials.")
        return
    cursor = conn.cursor()

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            role ENUM('admin', 'user') DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create events table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            event_date DATE NOT NULL,
            event_time TIME NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Seed default admin (admin / admin123) if no admin exists
    cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
    if cursor.fetchone() is None:
        hashed = generate_password_hash("admin123")
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (%s, %s, 'admin')",
            ("admin", hashed),
        )
        print("[OK] Default admin created -> username: admin | password: admin123")

    conn.commit()
    cursor.close()
    conn.close()


# ──────────────────────────────────────────────
# Decorators for access control
# ──────────────────────────────────────────────
def login_required(f):
    """Redirect to login if the user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Restrict access to admin-only routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Access denied. Admin privileges required.", "danger")
            return redirect(url_for("user_dashboard"))
        return f(*args, **kwargs)
    return decorated


# ──────────────────────────────────────────────
# Routes — Authentication
# ──────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def login():
    """Login page – authenticates and redirects by role."""
    if "user_id" in session:
        return redirect(url_for("admin_dashboard") if session["role"] == "admin" else url_for("user_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        if conn is None:
            flash("Database connection failed.", "danger")
            return render_template("login.html")

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['username']}!", "success")
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("user_dashboard"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Clear session and redirect to login."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ──────────────────────────────────────────────
# Routes — Admin dashboard
# ──────────────────────────────────────────────
@app.route("/admin")
@admin_required
def admin_dashboard():
    """Admin dashboard – full CRUD on events, user management."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM events ORDER BY event_date ASC, event_time ASC")
    events = cursor.fetchall()

    cursor.execute("SELECT id, username, role, created_at FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("admin_dashboard.html", events=events, users=users)


# ──────────────────────────────────────────────
# Routes — Event CRUD (admin only)
# ──────────────────────────────────────────────
@app.route("/add_event", methods=["POST"])
@admin_required
def add_event():
    """Create a new event."""
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    event_date = request.form.get("event_date")
    event_time = request.form.get("event_time")

    if not title or not event_date or not event_time:
        flash("Title, date, and time are required.", "warning")
        return redirect(url_for("admin_dashboard"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO events (title, description, event_date, event_time) VALUES (%s, %s, %s, %s)",
        (title, description, event_date, event_time),
    )
    conn.commit()
    cursor.close()
    conn.close()
    flash("Event created successfully!", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/edit_event/<int:event_id>", methods=["POST"])
@admin_required
def edit_event(event_id):
    """Update an existing event."""
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    event_date = request.form.get("event_date")
    event_time = request.form.get("event_time")

    if not title or not event_date or not event_time:
        flash("Title, date, and time are required.", "warning")
        return redirect(url_for("admin_dashboard"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE events SET title=%s, description=%s, event_date=%s, event_time=%s WHERE id=%s",
        (title, description, event_date, event_time, event_id),
    )
    conn.commit()
    cursor.close()
    conn.close()
    flash("Event updated successfully!", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/delete_event/<int:event_id>")
@admin_required
def delete_event(event_id):
    """Delete an event by ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Event deleted.", "info")
    return redirect(url_for("admin_dashboard"))


# ──────────────────────────────────────────────
# Routes — User management (admin only)
# ──────────────────────────────────────────────
@app.route("/create_user", methods=["POST"])
@admin_required
def create_user():
    """Admin creates a new user account."""
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "user")

    if not username or not password:
        flash("Username and password are required.", "warning")
        return redirect(url_for("admin_dashboard"))

    if role not in ("admin", "user"):
        role = "user"

    conn = get_db()
    cursor = conn.cursor()
    try:
        hashed = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
            (username, hashed, role),
        )
        conn.commit()
        flash(f"User '{username}' created as {role}.", "success")
    except mysql.connector.IntegrityError:
        flash(f"Username '{username}' already exists.", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/delete_user/<int:user_id>")
@admin_required
def delete_user(user_id):
    """Delete a user (cannot delete yourself)."""
    if user_id == session.get("user_id"):
        flash("You cannot delete your own account.", "warning")
        return redirect(url_for("admin_dashboard"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("User deleted.", "info")
    return redirect(url_for("admin_dashboard"))


# ──────────────────────────────────────────────
# Routes — User dashboard (read-only)
# ──────────────────────────────────────────────
@app.route("/user")
@login_required
def user_dashboard():
    """User dashboard – view-only list of events."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM events ORDER BY event_date ASC, event_time ASC")
    events = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("user_dashboard.html", events=events)


# ──────────────────────────────────────────────
# API — Events as JSON (for FullCalendar)
# ──────────────────────────────────────────────
@app.route("/api/events")
@login_required
def api_events():
    """Return events in JSON format for calendar integration."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM events ORDER BY event_date ASC")
    events = cursor.fetchall()
    cursor.close()
    conn.close()

    data = []
    for e in events:
        data.append({
            "id": e["id"],
            "title": e["title"],
            "start": f"{e['event_date']}T{e['event_time']}",
            "description": e["description"],
        })
    return jsonify(data)


# ──────────────────────────────────────────────
# Start the application
# ──────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)

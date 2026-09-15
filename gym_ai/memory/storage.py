"""
SQLite persistent storage engine for Gym AI.
Tracks conversation threads, messages, personal records (PRs),
logged meals, and body weight history across sessions.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from common.paths import DATA_ROOT

logger = logging.getLogger("gym_ai.memory.storage")

DB_PATH = os.path.join(DATA_ROOT, "data", "fitpath_memory.db")


def _get_connection() -> sqlite3.Connection:
    """Create and configure SQLite database connection."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database schema if not already present."""
    with _get_connection() as conn:
        cursor = conn.cursor()

        # 1. Conversations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                title TEXT,
                summary TEXT
            )
        """)

        # 2. Messages
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata_json TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)

        # 3. Personal Records (PRs)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personal_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                exercise_name TEXT NOT NULL,
                weight_kg REAL NOT NULL,
                reps INTEGER NOT NULL,
                estimated_1rm REAL NOT NULL,
                achieved_at TEXT NOT NULL,
                notes TEXT
            )
        """)

        # 4. Meal Logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meal_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                meal_name TEXT NOT NULL,
                calories REAL NOT NULL,
                protein_g REAL NOT NULL,
                carbs_g REAL NOT NULL,
                fat_g REAL NOT NULL,
                logged_at TEXT NOT NULL,
                details_json TEXT
            )
        """)

        # 5. Body Weight Logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weight_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                weight_kg REAL NOT NULL,
                logged_at TEXT NOT NULL,
                notes TEXT
            )
        """)

        # 6. Users & Authentication
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                salt TEXT NOT NULL,
                full_name TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # 7. Workout Sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workout_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                exercise_id TEXT NOT NULL,
                duration_sec INTEGER NOT NULL,
                total_reps INTEGER NOT NULL,
                form_accuracy_pct REAL,
                avg_cadence_sec REAL,
                fatigue_velocity_loss_pct REAL,
                faults_json TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()


# Ensure DB is initialized at import
try:
    init_db()
except Exception as e:
    logger.warning(f"Could not initialize memory DB: {e}")


def save_chat_message(
    role: str,
    content: str,
    conversation_id: str = "default",
    metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """Save a user or assistant message to persistent conversation history."""
    init_db()
    now_iso = datetime.now().isoformat(timespec="seconds")
    with _get_connection() as conn:
        cursor = conn.cursor()
        # Upsert conversation header
        cursor.execute(
            """
            INSERT INTO conversations (id, created_at, updated_at, title)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET updated_at = excluded.updated_at
            """,
            (conversation_id, now_iso, now_iso, "Athlete Coaching Thread"),
        )
        # Insert message
        cursor.execute(
            """
            INSERT INTO messages (conversation_id, role, content, timestamp, metadata_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, role, content, now_iso, json.dumps(metadata or {})),
        )
        conn.commit()
        return cursor.lastrowid


def get_recent_messages(
    conversation_id: str = "default",
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Retrieve recent chat messages ordered chronologically."""
    init_db()
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT role, content, timestamp, metadata_json
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (conversation_id, limit),
        )
        rows = cursor.fetchall()
        messages = []
        for r in reversed(rows):
            messages.append({
                "role": r["role"],
                "content": r["content"],
                "timestamp": r["timestamp"],
            })
        return messages


def log_personal_record(
    exercise_name: str,
    weight_kg: float,
    reps: int,
    notes: str = "",
    user_id: str = "default",
) -> Dict[str, Any]:
    """
    Log a strength personal record (PR), compute 1RM via Epley formula,
    and persist into the SQLite database.
    """
    init_db()
    from gym_ai.memory.pr_tracker import calculate_epley_1rm
    clean_name = exercise_name.strip().title()
    estimated_1rm = calculate_epley_1rm(weight_kg, reps)
    now_iso = datetime.now().isoformat(timespec="seconds")

    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO personal_records (user_id, exercise_name, weight_kg, reps, estimated_1rm, achieved_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, clean_name, weight_kg, reps, estimated_1rm, now_iso, notes),
        )
        record_id = cursor.lastrowid
        conn.commit()

    return {
        "id": record_id,
        "exercise": clean_name,
        "weight_kg": weight_kg,
        "reps": reps,
        "estimated_1rm": estimated_1rm,
        "achieved_at": now_iso,
        "notes": notes,
    }


def get_all_personal_records(
    exercise_name: Optional[str] = None,
    user_id: str = "default",
) -> List[Dict[str, Any]]:
    """Retrieve all personal records, optionally filtered by exercise."""
    init_db()
    with _get_connection() as conn:
        cursor = conn.cursor()
        if exercise_name:
            cursor.execute(
                """
                SELECT id, exercise_name, weight_kg, reps, estimated_1rm, achieved_at, notes
                FROM personal_records
                WHERE user_id = ? AND LOWER(exercise_name) = LOWER(?)
                ORDER BY estimated_1rm DESC, weight_kg DESC
                """,
                (user_id, exercise_name.strip()),
            )
        else:
            cursor.execute(
                """
                SELECT id, exercise_name, weight_kg, reps, estimated_1rm, achieved_at, notes
                FROM personal_records
                WHERE user_id = ?
                ORDER BY exercise_name ASC, estimated_1rm DESC
                """,
                (user_id,),
            )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_best_pr(
    exercise_name: str,
    user_id: str = "default",
) -> Optional[Dict[str, Any]]:
    """Retrieve the highest estimated 1RM PR for an exercise."""
    prs = get_all_personal_records(exercise_name, user_id=user_id)
    return prs[0] if prs else None


def log_meal_record(
    meal_name: str,
    calories: float,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
    details: Optional[Dict[str, Any]] = None,
    user_id: str = "default",
) -> int:
    """Store a logged meal entry in SQLite memory."""
    init_db()
    now_iso = datetime.now().isoformat(timespec="seconds")
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO meal_logs (user_id, meal_name, calories, protein_g, carbs_g, fat_g, logged_at, details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                meal_name,
                calories,
                protein_g,
                carbs_g,
                fat_g,
                now_iso,
                json.dumps(details or {}),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def log_weight_entry(
    weight_kg: float,
    notes: str = "",
    user_id: str = "default",
) -> int:
    """Log an athlete body weight tracking data point."""
    init_db()
    now_iso = datetime.now().isoformat(timespec="seconds")
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO weight_logs (user_id, weight_kg, logged_at, notes)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, weight_kg, now_iso, notes),
        )
        conn.commit()
        return cursor.lastrowid


def build_memory_context_prompt(user_id: str = "default") -> str:
    """Format active PRs, recent weight entries, and logged meals for prompt injection."""
    prs = get_all_personal_records(user_id=user_id)
    # Deduplicate to best PR per exercise
    best_prs: Dict[str, Dict[str, Any]] = {}
    for pr in prs:
        ex = pr["exercise_name"]
        if ex not in best_prs or pr["estimated_1rm"] > best_prs[ex]["estimated_1rm"]:
            best_prs[ex] = pr

    lines = []
    if best_prs:
        lines.append("ATHLETE STRENGTH PERSONAL RECORDS (PRs):")
        for ex, pr in best_prs.items():
            lines.append(
                f"- {ex}: {pr['weight_kg']} kg x {pr['reps']} reps (Estimated 1RM: {pr['estimated_1rm']} kg)"
            )

    return "\n".join(lines)


# ==========================================
# User Account & Auth Storage
# ==========================================

def create_user(
    user_id: str,
    email: str,
    username: str,
    hashed_password: str,
    salt: str,
    full_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new user account in SQLite."""
    init_db()
    now_iso = datetime.now().isoformat(timespec="seconds")
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (id, email, username, hashed_password, salt, full_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, email.lower().strip(), username.strip(), hashed_password, salt, full_name or username, now_iso),
        )
        conn.commit()
    return {
        "id": user_id,
        "email": email.lower().strip(),
        "username": username.strip(),
        "full_name": full_name or username,
        "created_at": now_iso,
    }


def get_user_by_email_or_username(identifier: str) -> Optional[Dict[str, Any]]:
    """Look up a user record by email or username."""
    init_db()
    clean_id = identifier.strip().lower()
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM users
            WHERE lower(email) = ? OR lower(username) = ?
            LIMIT 1
            """,
            (clean_id, clean_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Look up a user record by primary key user_id."""
    init_db()
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ? LIMIT 1", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


# ==========================================
# Workout Session History Storage
# ==========================================

def log_workout_session(
    session_id: str,
    user_id: str,
    exercise_id: str,
    duration_sec: int,
    total_reps: int,
    form_accuracy_pct: float = 100.0,
    avg_cadence_sec: float = 2.0,
    fatigue_velocity_loss_pct: float = 0.0,
    faults: Optional[List[str]] = None,
    notes: str = "",
) -> Dict[str, Any]:
    """Store completed mobile or CV workout session."""
    init_db()
    now_iso = datetime.now().isoformat(timespec="seconds")
    faults_list = faults or []
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO workout_sessions (
                id, user_id, exercise_id, duration_sec, total_reps,
                form_accuracy_pct, avg_cadence_sec, fatigue_velocity_loss_pct,
                faults_json, notes, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                user_id,
                exercise_id,
                int(duration_sec),
                int(total_reps),
                float(form_accuracy_pct),
                float(avg_cadence_sec),
                float(fatigue_velocity_loss_pct),
                json.dumps(faults_list),
                notes,
                now_iso,
            ),
        )
        conn.commit()
    return {
        "session_id": session_id,
        "user_id": user_id,
        "exercise_id": exercise_id,
        "duration_sec": duration_sec,
        "total_reps": total_reps,
        "form_accuracy_pct": form_accuracy_pct,
        "avg_cadence_sec": avg_cadence_sec,
        "fatigue_velocity_loss_pct": fatigue_velocity_loss_pct,
        "faults": faults_list,
        "notes": notes,
        "created_at": now_iso,
    }


def get_workout_sessions(
    user_id: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Retrieve recent workout sessions ordered by newest first."""
    init_db()
    with _get_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute(
                """
                SELECT * FROM workout_sessions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM workout_sessions
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
        rows = cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            try:
                d["faults"] = json.loads(d.get("faults_json") or "[]")
            except Exception:
                d["faults"] = []
            results.append(d)
        return results


"""SQLite persistence layer for patient records."""
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "patients.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name    TEXT    NOT NULL,
    dob          TEXT    NOT NULL,              -- stored as ISO yyyy-mm-dd
    email        TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    glucose      REAL    NOT NULL,
    haemoglobin  REAL    NOT NULL,
    cholesterol  REAL    NOT NULL,
    remarks      TEXT    NOT NULL DEFAULT '',
    created_at   TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def list_patients():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM patients ORDER BY id")]


def get_patient(patient_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
        return dict(row) if row else None


def find_duplicate(email, full_name, dob, exclude_id=None):
    """Return an existing record with the same email, or the same name + DOB."""
    with get_conn() as conn:
        row = conn.execute(
            """SELECT * FROM patients
               WHERE (email = ? OR (LOWER(full_name) = LOWER(?) AND dob = ?))
                 AND id != ?""",
            (email, full_name, dob, exclude_id or -1),
        ).fetchone()
        return dict(row) if row else None


def create_patient(p):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO patients (full_name, dob, email, glucose, haemoglobin, cholesterol, remarks)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (p["full_name"], p["dob"], p["email"], p["glucose"],
             p["haemoglobin"], p["cholesterol"], p.get("remarks", "")),
        )
        return cur.lastrowid


def update_patient(patient_id, p):
    with get_conn() as conn:
        conn.execute(
            """UPDATE patients SET full_name=?, dob=?, email=?, glucose=?,
                      haemoglobin=?, cholesterol=?, remarks=? WHERE id=?""",
            (p["full_name"], p["dob"], p["email"], p["glucose"],
             p["haemoglobin"], p["cholesterol"], p.get("remarks", ""), patient_id),
        )


def update_remarks(patient_id, remarks):
    with get_conn() as conn:
        conn.execute("UPDATE patients SET remarks=? WHERE id=?", (remarks, patient_id))


def delete_patient(patient_id):
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        return cur.rowcount > 0

"""Flask backend: REST API + single-page frontend for the Health Prediction app."""
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

import ai_service  # noqa: E402  (after load_dotenv so env vars are available)
import database as db  # noqa: E402
from validators import iso_to_display, validate_patient  # noqa: E402

app = Flask(__name__)
db.init_db()

PENDING_REMARKS = "Prediction unavailable - use Regenerate to retry"


def to_api(record):
    """Convert a DB row to the JSON shape used by the frontend."""
    out = dict(record)
    out["dob"] = iso_to_display(record["dob"])
    return out


def error(message, status, errors=None):
    body = {"message": message}
    if errors:
        body["errors"] = errors
    return jsonify(body), status


def predict(record):
    """Return (remarks, warning). Never raises; AI failure becomes a warning."""
    try:
        return ai_service.get_remarks(record), None
    except ai_service.AIServiceError as exc:
        return PENDING_REMARKS, f"Record saved, but AI prediction failed: {exc}"


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/patients")
def list_patients():
    return jsonify([to_api(p) for p in db.list_patients()])


@app.post("/api/patients")
def create_patient():
    clean, errors = validate_patient(request.get_json(silent=True) or {})
    if errors:
        return error("Validation failed", 422, errors)

    dup = db.find_duplicate(clean["email"], clean["full_name"], clean["dob"])
    if dup:
        return error(
            f"Duplicate record: {dup['full_name']} ({dup['email']}) already exists", 409,
            {"email": "A record with this email or name and date of birth already exists"},
        )

    clean["remarks"], warning = predict(clean)
    new_id = db.create_patient(clean)
    return jsonify({"patient": to_api(db.get_patient(new_id)), "warning": warning}), 201


@app.put("/api/patients/<int:patient_id>")
def update_patient(patient_id):
    existing = db.get_patient(patient_id)
    if not existing:
        return error("Record not found", 404)

    clean, errors = validate_patient(request.get_json(silent=True) or {})
    if errors:
        return error("Validation failed", 422, errors)

    if db.find_duplicate(clean["email"], clean["full_name"], clean["dob"], exclude_id=patient_id):
        return error("Duplicate record", 409,
                     {"email": "Another record with this email or name and date of birth exists"})

    warning = None
    inputs_changed = any(clean[k] != existing[k] for k in ("dob", "glucose", "haemoglobin", "cholesterol"))
    if inputs_changed or existing["remarks"] == PENDING_REMARKS:
        clean["remarks"], warning = predict(clean)
    else:
        clean["remarks"] = existing["remarks"]

    db.update_patient(patient_id, clean)
    return jsonify({"patient": to_api(db.get_patient(patient_id)), "warning": warning})


@app.post("/api/patients/<int:patient_id>/remarks")
def regenerate_remarks(patient_id):
    record = db.get_patient(patient_id)
    if not record:
        return error("Record not found", 404)
    try:
        remarks = ai_service.get_remarks(record)
    except ai_service.AIServiceError as exc:
        return error(f"AI prediction failed: {exc}", 502)
    db.update_remarks(patient_id, remarks)
    return jsonify({"patient": to_api(db.get_patient(patient_id))})


@app.delete("/api/patients/<int:patient_id>")
def delete_patient(patient_id):
    if not db.delete_patient(patient_id):
        return error("Record not found", 404)
    return jsonify({"message": "Record deleted"})


if __name__ == "__main__":
    app.run(debug=True)

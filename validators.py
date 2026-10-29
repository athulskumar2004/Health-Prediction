"""Input validation for patient records.

Dates are accepted as dd/mm/yyyy. The separators '.' and '-' are also accepted
and normalised to '/', because the supplied test data uses dd.mm.yyyy.
"""
import math
import re
from datetime import date, datetime

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,99}$")
DATE_RE = re.compile(r"^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})$")

# Plausibility limits (reject typos, not clinically abnormal values)
LIMITS = {
    "glucose":     ("Glucose", "mg/dL", 20, 1000),
    "haemoglobin": ("Haemoglobin", "g/dL", 3, 25),
    "cholesterol": ("Cholesterol", "mg/dL", 50, 1000),
}


def parse_dob(text):
    """Return (date, error). Error is None when the date is valid."""
    m = DATE_RE.match(text)
    if not m:
        return None, "Date of birth must be in dd/mm/yyyy format"
    day, month, year = (int(g) for g in m.groups())
    try:
        dob = date(year, month, day)
    except ValueError:
        return None, f"{day:02d}/{month:02d}/{year} is not a real calendar date"
    if dob > date.today():
        return None, "Date of birth cannot be in the future"
    if year < 1900:
        return None, "Date of birth must be 1900 or later"
    return dob, None


def validate_patient(data):
    """Validate raw input. Returns (clean_dict, errors_dict)."""
    errors, clean = {}, {}

    name = " ".join(str(data.get("full_name", "")).split())
    if not name:
        errors["full_name"] = "Full name is required"
    elif not NAME_RE.match(name):
        errors["full_name"] = "Full name may contain only letters, spaces, . ' -"
    else:
        clean["full_name"] = name

    dob_text = str(data.get("dob", "")).strip()
    if not dob_text:
        errors["dob"] = "Date of birth is required"
    else:
        dob, err = parse_dob(dob_text)
        if err:
            errors["dob"] = err
        else:
            clean["dob"] = dob.isoformat()

    email = str(data.get("email", "")).strip().lower()
    if not email:
        errors["email"] = "Email is required"
    elif not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address (e.g. name@example.com)"
    else:
        clean["email"] = email

    for field, (label, unit, low, high) in LIMITS.items():
        raw = str(data.get(field, "")).strip()
        if not raw:
            errors[field] = f"{label} is required"
            continue
        try:
            value = float(raw)
        except ValueError:
            errors[field] = f"{label} must be a number"
            continue
        if math.isnan(value) or math.isinf(value):
            errors[field] = f"{label} must be a number"
        elif not low <= value <= high:
            errors[field] = f"{label} must be between {low} and {high} {unit}"
        else:
            clean[field] = value

    return clean, errors


def iso_to_display(iso):
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")

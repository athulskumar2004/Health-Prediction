# Health Prediction Records

A Flask + SQLite web app for managing patient blood-test records. When a valid record is saved,
the values are sent to an external AI API (Google Gemini) and the predicted health risk is
stored in the **Remarks** column.

## Features
- Create, Read, Update, Delete patient records
- Validation on both name, date of birth (dd/mm/yyyy, real date, not in the future), email format,
  and numeric blood values within plausible ranges
- Duplicate detection (same email, or same name + date of birth)
- SQLite persistent storage
- AI remarks generated on create, and on update when DOB or blood values change
- If the AI API is unavailable the record is still saved; use **Regenerate** to retry

## Project structure
```
app.py            Flask routes (REST API) and app wiring
validators.py     Input validation rules
database.py      SQLite data access
ai_service.py    Gemini API integration and prompt
templates/       index.html (Bootstrap 5 UI)
static/          app.js (fetch-based frontend), style.css
tests/           End-to-end test using the assignment data (AI call mocked)
```

## Setup
```bash
python -m venv venv
venv\Scripts\activate            # Windows  (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env           # macOS/Linux: cp .env.example .env
# edit .env and add your own GEMINI_API_KEY (free key: https://aistudio.google.com/apikey)
python app.py
```
Open http://127.0.0.1:5000

## API
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /api/patients | List all records |
| POST | /api/patients | Create (validate, de-duplicate, call AI) |
| PUT | /api/patients/<id> | Update |
| DELETE | /api/patients/<id> | Delete |
| POST | /api/patients/<id>/remarks | Re-run AI prediction |

Status codes: 201 created, 422 validation error, 409 duplicate, 404 not found, 502 AI failure.

## Notes
- Dates are entered as dd/mm/yyyy; `.` and `-` separators are also accepted and normalised.
- Predictions are a screening aid, not a medical diagnosis.

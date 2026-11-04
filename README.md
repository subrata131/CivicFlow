# CivicFlow – Municipal Waterlogging Complaint Tracker

This version keeps the original CivicFlow HTML/CSS layout and frontend interactions. The fixes are focused on API validation, authentication/authorization, complaint ownership, photo uploads, assignment/status history consistency, and database selection.

## Included project structure

```text
Municipal-Waterlogging-Tracker-Fixed/
├── backend/
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── auth.py
│   ├── database.py
│   └── seed.py
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   ├── js/app.js
│   └── uploads/
├── database/schema.sql
├── waterlogging_tracker.db
├── requirements.txt
└── .env.example
```

## Run on Windows (PowerShell)

1. Extract this ZIP.
2. Open the extracted project folder in VS Code.
3. Open a terminal in the project root and create the environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env`. The included SQLite database is used automatically when `DATABASE_URL` is not set.
5. Start the API from the backend folder:

```powershell
cd backend
uvicorn main:app --reload
```

6. Open the application at http://127.0.0.1:8000 and API docs at http://127.0.0.1:8000/docs.

## Demo officer login

- Username: `admin`
- Password: `Admin@12345`

Citizen users can register from the application. The included SQLite database contains the existing project records; back it up before experimenting.

## Complaint API

`POST /api/complaints` accepts `multipart/form-data`:

- `location` – required
- `description` – required (minimum 10 characters)
- `priority` – Low, Medium, or High (default Medium)
- `photo` – optional image, maximum 10 MB

In Swagger, authorize using a citizen token before executing this endpoint. The browser frontend sends the token automatically after citizen login.

## Data and photo storage

- The default database is `waterlogging_tracker.db` in the project root.
- Complaint photos are stored in `frontend/uploads/` and retain the existing `/static/uploads/<filename>` URL format.
- The database stores the relative photo URL in `complaints.photo_path`.
- Existing complaint records and IDs are preserved in the included database copy.

## MySQL option

Install the MySQL driver if you want to use MySQL:

```powershell
pip install pymysql
```

Then set `DATABASE_URL` in `.env`, for example:

```env
DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/waterlogging_tracker
```

Create the database first and ensure its tables match `backend/models.py`. `Base.metadata.create_all()` creates missing tables but does not migrate or alter existing tables. Back up data and use a migration before changing an existing schema.

## Main bug fixes

- Swagger now displays the complaint form fields because the endpoint declares `Form()` and `File()` parameters.
- Missing/invalid tokens are rejected; the old implicit admin fallback is removed.
- Admin-only routes require an admin token.
- Citizens can only list, view, or inspect the history of their own complaints.
- Complaint submission no longer assigns reports to the first citizen when authentication fails.
- Photo reads are capped at 10 MB plus one byte; failed DB writes remove the newly saved file.
- Repeating the current status does not create duplicate history rows.
- Reassigning the same worker consecutively is rejected; assigning a different worker creates a new assignment record.
- Dashboard worker display returns the latest assignment and the frontend selects that worker in the assignment control.
- Logout removes only CivicFlow session keys rather than clearing unrelated local storage.

## Notes

This is a local academic project starter, not a production-hardened municipal service. Before public deployment, replace the demo secret, change the demo officer password, validate actual image contents, add rate limiting/CSRF protections as appropriate, and use database migrations and backups.

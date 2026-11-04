import logging
import uuid
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from database import Base, engine, get_db, SessionLocal
from models import Citizen, Admin, Department, Worker, Complaint, Assignment, ComplaintStatusHistory
from schemas import RegisterIn, LoginIn, StatusIn, AssignmentIn, WorkerIn, DepartmentIn
from auth import hash_password, verify_password, create_token, current_user, require_admin, require_citizen

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
UPLOADS_DIR = FRONTEND_DIR / "uploads"  # Keeps existing /static/uploads URLs working.
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Municipal Waterlogging Complaint Tracker", version="1.1.0")
Base.metadata.create_all(bind=engine)


def init_db():
    db = SessionLocal()
    try:
        if not db.query(Admin).filter_by(username="admin").first():
            db.add(Admin(username="admin", password_hash=hash_password("Admin@12345")))
        defaults = [
            ("Drainage Department", "Drain cleaning and maintenance"),
            ("Sanitation Department", "Waste and garbage management"),
            ("Road Maintenance", "Road repair and maintenance"),
        ]
        for name, desc in defaults:
            if not db.query(Department).filter_by(department_name=name).first():
                db.add(Department(department_name=name, description=desc))
        db.commit()
        drainage = db.query(Department).filter_by(department_name="Drainage Department").first()
        if drainage and not db.query(Worker).first():
            db.add_all([
                Worker(worker_name="Rahul Das", phone="9876543210", department_id=drainage.department_id),
                Worker(worker_name="Amit Roy", phone="9876501234", department_id=drainage.department_id),
            ])
            db.commit()
    except Exception:
        db.rollback()
        logger.exception("Database initialization failed")
        raise
    finally:
        db.close()


init_db()
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled application error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "message": "Waterlogging Tracker API is running"}


@app.post("/api/register")
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    if db.query(Citizen).filter(func.lower(Citizen.email) == email).first():
        raise HTTPException(409, "Email is already registered")
    citizen = Citizen(full_name=data.full_name.strip(), email=email, phone=data.phone.strip(),
                      password_hash=hash_password(data.password), address=data.address)
    try:
        db.add(citizen)
        db.commit()
        db.refresh(citizen)
    except Exception:
        db.rollback()
        logger.exception("Citizen registration failed")
        raise HTTPException(500, "Could not register citizen")
    return {"token": create_token(citizen.email, "citizen", citizen.citizen_id),
            "role": "citizen", "name": citizen.full_name}


@app.post("/api/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    role = (data.role or "").lower().strip()
    if role in ("officer", "admin"):
        admin = db.query(Admin).filter(Admin.username == data.email.strip()).first()
        if admin and verify_password(data.password, admin.password_hash):
            return {"token": create_token(admin.username, "admin", admin.admin_id),
                    "role": "admin", "name": admin.username}
        if db.query(Citizen).filter(func.lower(Citizen.email) == data.email.strip().lower()).first():
            raise HTTPException(401, "This is a Citizen account. Please toggle to 'Citizen' above.")
        raise HTTPException(401, "Incorrect officer username or password")

    citizen = db.query(Citizen).filter(func.lower(Citizen.email) == data.email.strip().lower()).first()
    if citizen and verify_password(data.password, citizen.password_hash):
        return {"token": create_token(citizen.email, "citizen", citizen.citizen_id),
                "role": "citizen", "name": citizen.full_name}
    if role == "citizen" and db.query(Admin).filter(Admin.username == data.email.strip()).first():
        raise HTTPException(401, "This is an Officer account. Please toggle to 'Department Officer' above.")
    if role == "citizen":
        raise HTTPException(401, "Incorrect citizen email or password")
    admin = db.query(Admin).filter(Admin.username == data.email.strip()).first()
    if admin and verify_password(data.password, admin.password_hash):
        return {"token": create_token(admin.username, "admin", admin.admin_id),
                "role": "admin", "name": admin.username}
    raise HTTPException(401, "Incorrect login details")


@app.post("/api/complaints")
async def create_complaint(
    location: str = Form(...),
    description: str = Form(...),
    priority: str = Form("Medium"),
    photo: UploadFile | None = File(default=None),
    user=Depends(require_citizen),
    db: Session = Depends(get_db),
):
    """Create a complaint from multipart/form-data; Swagger shows all four fields."""
    location, description = location.strip(), description.strip()
    if len(location) < 3 or len(location) > 255:
        raise HTTPException(422, "Problem location must be between 3 and 255 characters")
    if len(description) < 10:
        raise HTTPException(422, "Description must be at least 10 characters")
    if priority not in ("Low", "Medium", "High"):
        raise HTTPException(422, "Priority must be Low, Medium, or High")

    citizen = db.query(Citizen).filter(Citizen.citizen_id == user["user_id"]).first()
    if not citizen:
        raise HTTPException(401, "Citizen account not found. Please log in again.")

    saved_file = None
    photo_rel_path = None
    try:
        if photo and photo.filename:
            ext = Path(photo.filename).suffix.lower()
            if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}:
                raise HTTPException(400, "Unsupported image format. Allowed: JPG, PNG, WEBP, GIF, BMP.")
            data = await photo.read(10 * 1024 * 1024 + 1)
            if len(data) > 10 * 1024 * 1024:
                raise HTTPException(400, "Image size exceeds 10MB limit")
            if data:
                filename = f"{uuid.uuid4().hex}{ext}"
                saved_file = UPLOADS_DIR / filename
                saved_file.write_bytes(data)
                photo_rel_path = f"/static/uploads/{filename}"

        complaint = Complaint(citizen_id=citizen.citizen_id, location=location,
                              description=description, priority=priority,
                              status="Pending", photo_path=photo_rel_path)
        db.add(complaint)
        db.flush()
        db.add(ComplaintStatusHistory(complaint_id=complaint.complaint_id,
                                      old_status=None, new_status="Pending", changed_by=user["sub"]))
        db.commit()
        db.refresh(complaint)
        return {"message": "Complaint submitted successfully",
                "complaint_id": complaint.complaint_id, "photo_path": photo_rel_path}
    except HTTPException:
        db.rollback()
        if saved_file and saved_file.exists():
            saved_file.unlink()
        raise
    except Exception:
        db.rollback()
        if saved_file and saved_file.exists():
            saved_file.unlink()
        logger.exception("Complaint creation failed")
        raise HTTPException(500, "Failed to save complaint")
    finally:
        if photo:
            await photo.close()


def complaint_query(db: Session):
    return db.query(Complaint).options(
        joinedload(Complaint.citizen),
        joinedload(Complaint.assignments).joinedload(Assignment.worker),
    )


def complaint_dict(c):
    # Order by assignment timestamp/id so the newest assignment is displayed.
    latest = max(c.assignments, key=lambda a: (a.assigned_date or datetime.min, a.assignment_id), default=None)
    return {
        "complaint_id": c.complaint_id,
        "citizen_name": c.citizen.full_name if c.citizen else "",
        "citizen_email": c.citizen.email if c.citizen else "",
        "location": c.location, "description": c.description,
        "priority": c.priority, "status": c.status,
        "complaint_date": c.complaint_date.isoformat() if c.complaint_date else None,
        "worker_name": latest.worker.worker_name if latest and latest.worker else None,
        "photo_path": c.photo_path,
    }


@app.get("/api/complaints/my")
def my_complaints(user=Depends(require_citizen), db: Session = Depends(get_db)):
    rows = complaint_query(db).filter(Complaint.citizen_id == user["user_id"]).order_by(
        Complaint.complaint_date.desc()).all()
    return [complaint_dict(c) for c in rows]


@app.get("/api/complaints")
def all_complaints(user=Depends(require_admin), db: Session = Depends(get_db)):
    rows = complaint_query(db).order_by(Complaint.complaint_date.desc()).all()
    return [complaint_dict(c) for c in rows]


@app.get("/api/complaints/{complaint_id}")
def complaint_detail(complaint_id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    c = complaint_query(db).filter(Complaint.complaint_id == complaint_id).first()
    if not c:
        raise HTTPException(404, "Complaint not found")
    if user["role"] == "citizen" and c.citizen_id != user["user_id"]:
        raise HTTPException(403, "You cannot view this complaint")
    if user["role"] not in ("citizen", "admin"):
        raise HTTPException(403, "Access denied")
    return complaint_dict(c)


@app.get("/api/dashboard")
def dashboard(user=Depends(require_admin), db: Session = Depends(get_db)):
    total = db.query(func.count(Complaint.complaint_id)).scalar() or 0
    counts = {s: db.query(func.count(Complaint.complaint_id)).filter(Complaint.status == s).scalar() or 0
              for s in ("Pending", "In Progress", "Resolved")}
    return {"total": total, **counts}


@app.put("/api/complaints/{complaint_id}/status")
def update_status(complaint_id: int, data: StatusIn, user=Depends(require_admin), db: Session = Depends(get_db)):
    c = db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()
    if not c:
        raise HTTPException(404, "Complaint not found")
    old = c.status
    if old == data.status:
        return {"message": "Complaint already has this status", "status": c.status}
    c.status = data.status
    if data.status == "Resolved":
        assignment = db.query(Assignment).filter(Assignment.complaint_id == complaint_id).order_by(
            Assignment.assigned_date.desc(), Assignment.assignment_id.desc()).first()
        if assignment and not assignment.completion_date:
            assignment.completion_date = datetime.now()
    db.add(ComplaintStatusHistory(complaint_id=complaint_id, old_status=old,
                                  new_status=data.status, changed_by=user["sub"]))
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Status update failed")
        raise HTTPException(500, "Could not update complaint status")
    return {"message": "Status updated", "status": c.status}


@app.post("/api/assignments")
def assign_worker(data: AssignmentIn, user=Depends(require_admin), db: Session = Depends(get_db)):
    c = db.query(Complaint).filter(Complaint.complaint_id == data.complaint_id).first()
    w = db.query(Worker).filter(Worker.worker_id == data.worker_id).first()
    if not c or not w:
        raise HTTPException(404, "Complaint or worker not found")
    if c.status == "Resolved":
        raise HTTPException(409, "A resolved complaint cannot be assigned")
    latest = db.query(Assignment).filter(Assignment.complaint_id == c.complaint_id).order_by(
        Assignment.assigned_date.desc(), Assignment.assignment_id.desc()).first()
    if latest and latest.worker_id == w.worker_id:
        raise HTTPException(409, "This worker is already assigned to the complaint")
    db.add(Assignment(complaint_id=c.complaint_id, worker_id=w.worker_id))
    if c.status == "Pending":
        old = c.status
        c.status = "In Progress"
        db.add(ComplaintStatusHistory(complaint_id=c.complaint_id, old_status=old,
                                      new_status=c.status, changed_by=user["sub"]))
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Worker assignment failed")
        raise HTTPException(500, "Could not assign worker")
    return {"message": "Worker assigned successfully"}


@app.get("/api/workers")
def get_workers(user=Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(Worker).options(joinedload(Worker.department)).order_by(Worker.worker_name).all()
    return [{"worker_id": w.worker_id, "worker_name": w.worker_name, "phone": w.phone,
             "department": w.department.department_name if w.department else None} for w in rows]


@app.post("/api/workers")
def add_worker(data: WorkerIn, user=Depends(require_admin), db: Session = Depends(get_db)):
    if not db.query(Department).filter(Department.department_id == data.department_id).first():
        raise HTTPException(404, "Department not found")
    worker = Worker(**data.model_dump())
    try:
        db.add(worker); db.commit(); db.refresh(worker)
    except Exception:
        db.rollback(); logger.exception("Worker creation failed")
        raise HTTPException(500, "Could not add worker")
    return {"message": "Worker added", "worker_id": worker.worker_id}


@app.get("/api/departments")
def get_departments(user=Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(Department).order_by(Department.department_name).all()
    return [{"department_id": d.department_id, "department_name": d.department_name} for d in rows]


@app.post("/api/departments")
def add_department(data: DepartmentIn, user=Depends(require_admin), db: Session = Depends(get_db)):
    if db.query(Department).filter(Department.department_name == data.department_name).first():
        raise HTTPException(409, "Department already exists")
    d = Department(**data.model_dump())
    try:
        db.add(d); db.commit(); db.refresh(d)
    except Exception:
        db.rollback(); logger.exception("Department creation failed")
        raise HTTPException(500, "Could not add department")
    return {"message": "Department added", "department_id": d.department_id}


@app.get("/api/complaints/{complaint_id}/history")
def complaint_history(complaint_id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    c = db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()
    if not c:
        raise HTTPException(404, "Complaint not found")
    if user["role"] == "citizen" and c.citizen_id != user["user_id"]:
        raise HTTPException(403, "You cannot view this complaint history")
    if user["role"] not in ("citizen", "admin"):
        raise HTTPException(403, "Access denied")
    rows = db.query(ComplaintStatusHistory).filter(
        ComplaintStatusHistory.complaint_id == complaint_id).order_by(
        ComplaintStatusHistory.changed_at.asc(), ComplaintStatusHistory.history_id.asc()).all()
    return [{"old_status": h.old_status, "new_status": h.new_status,
             "changed_by": h.changed_by,
             "changed_at": h.changed_at.isoformat() if h.changed_at else None} for h in rows]

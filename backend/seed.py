from database import SessionLocal, Base, engine
from models import Admin, Department, Worker
from auth import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    if not db.query(Admin).filter_by(username="admin").first():
        db.add(Admin(username="admin", password_hash=hash_password("Admin@12345")))
    departments = [
        ("Drainage Department", "Drain cleaning and maintenance"),
        ("Sanitation Department", "Waste and garbage management"),
        ("Road Maintenance", "Road repair and maintenance"),
    ]
    for name, desc in departments:
        if not db.query(Department).filter_by(department_name=name).first():
            db.add(Department(department_name=name, description=desc))
    db.commit()
    drainage = db.query(Department).filter_by(department_name="Drainage Department").first()
    if not db.query(Worker).first():
        db.add_all([
            Worker(worker_name="Rahul Das", phone="9876543210", department_id=drainage.department_id),
            Worker(worker_name="Amit Roy", phone="9876501234", department_id=drainage.department_id),
        ])
    db.commit()
    print("Seed complete. Admin username: admin | password: Admin@12345")
finally:
    db.close()

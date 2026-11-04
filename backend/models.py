from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import relationship
from database import Base

class Citizen(Base):
    __tablename__ = "citizens"
    citizen_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    phone = Column(String(15), nullable=False)
    password_hash = Column(String(255), nullable=False)
    address = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    complaints = relationship("Complaint", back_populates="citizen")

class Admin(Base):
    __tablename__ = "admins"
    admin_id = Column(Integer, primary_key=True)
    username = Column(String(60), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

class Department(Base):
    __tablename__ = "departments"
    department_id = Column(Integer, primary_key=True)
    department_name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255))
    workers = relationship("Worker", back_populates="department")

class Worker(Base):
    __tablename__ = "workers"
    worker_id = Column(Integer, primary_key=True)
    worker_name = Column(String(100), nullable=False)
    phone = Column(String(15), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.department_id"))
    department = relationship("Department", back_populates="workers")
    assignments = relationship("Assignment", back_populates="worker")

class Complaint(Base):
    __tablename__ = "complaints"
    complaint_id = Column(Integer, primary_key=True, index=True)
    citizen_id = Column(Integer, ForeignKey("citizens.citizen_id"), nullable=False)
    location = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(Enum("Low", "Medium", "High"), default="Medium", nullable=False)
    status = Column(Enum("Pending", "In Progress", "Resolved"), default="Pending", nullable=False)
    photo_path = Column(String(255))
    complaint_date = Column(DateTime, server_default=func.now())
    citizen = relationship("Citizen", back_populates="complaints")
    assignments = relationship("Assignment", back_populates="complaint", cascade="all, delete-orphan")
    history = relationship("ComplaintStatusHistory", back_populates="complaint", cascade="all, delete-orphan")

class Assignment(Base):
    __tablename__ = "assignments"
    assignment_id = Column(Integer, primary_key=True)
    complaint_id = Column(Integer, ForeignKey("complaints.complaint_id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("workers.worker_id"), nullable=False)
    assigned_date = Column(DateTime, server_default=func.now())
    completion_date = Column(DateTime)
    complaint = relationship("Complaint", back_populates="assignments")
    worker = relationship("Worker", back_populates="assignments")

class ComplaintStatusHistory(Base):
    __tablename__ = "complaint_status_history"
    history_id = Column(Integer, primary_key=True)
    complaint_id = Column(Integer, ForeignKey("complaints.complaint_id"), nullable=False)
    old_status = Column(String(30))
    new_status = Column(String(30), nullable=False)
    changed_by = Column(String(60), nullable=False)
    changed_at = Column(DateTime, server_default=func.now())
    complaint = relationship("Complaint", back_populates="history")

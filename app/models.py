from sqlalchemy import Column, Integer, String, Float,DateTime,Boolean
from datetime import datetime
from .database import Base


class User(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String)

    roll_number = Column(String)
    department = Column(String)
    year = Column(String)


class Assignment(Base):

    __tablename__ = "assignments"
    is_training = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer)

    image_path = Column(String)

    is_reference = Column(Integer)

    similarity_score = Column(Float)

    submission_date = Column(DateTime, default=datetime.utcnow)
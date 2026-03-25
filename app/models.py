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


from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    image_path = Column(String)
    is_reference = Column(Integer, default=0)
    is_training = Column(Boolean, default=False)
    
    # Add these to match your Neon changes:
    status = Column(String, default="pending")
    similarity_score = Column(Float, default=0.0)
    feedback = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    # ------------------------------

    # Relationship to the User model (if you have one)
    student = relationship("User", back_populates="assignments")
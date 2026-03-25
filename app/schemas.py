from pydantic import BaseModel, ConfigDict
from typing import Optional

# -----------------------------
# USER SCHEMAS
# -----------------------------

from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    name: str
    username: str      # This can be their email or a unique ID
    roll_number: str
    password: str
    department: str          # Department
    role: str          # 'student', 'teacher', or 'admin'

class UserLogin(BaseModel):
    username: str
    password: str
    role: str          # Added as per your plan

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    roll_number: Optional[str] = None
    department: Optional[str] = None
    year: Optional[str] = None

    # Modern Pydantic v2 way to handle SQLAlchemy models
    model_config = ConfigDict(from_attributes=True)
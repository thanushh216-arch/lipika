from pydantic import BaseModel, ConfigDict
from typing import Optional

# -----------------------------
# USER SCHEMAS
# -----------------------------

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str
    
    # Optional fields for Teachers/Admins
    roll_number: Optional[str] = None
    department: Optional[str] = None
    year: Optional[str] = None

    # 🔥 FIX: Tell Pydantic to ignore extra fields from Lovable
    model_config = ConfigDict(extra="ignore")

class UserLogin(BaseModel):
    email: str
    password: str
    
    # Also ignore extra fields here
    model_config = ConfigDict(extra="ignore")

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
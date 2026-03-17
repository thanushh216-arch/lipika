from pydantic import BaseModel
from typing import Optional # <--- Add this import

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str
    
    # Make these optional so teachers can skip them
    roll_number: Optional[str] = None
    department: Optional[str] = None
    year: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    # These can also be optional in the output
    roll_number: Optional[str]
    department: Optional[str]
    year: Optional[str]

    class Config:
        from_attributes = True
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

# Relative imports from your package
from . import models, schemas
from .database import SessionLocal

# -----------------------------
# CONFIG
# -----------------------------
# 💡 Pro-tip: Use an environment variable for the secret key if possible
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this") 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# -----------------------------
# PASSWORD HASHING FIX
# -----------------------------
# Added 'bcrypt__truncate_error=True' to fix the version mismatch crash
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__truncate_error=True 
)

security = HTTPBearer()

# -----------------------------
# DATABASE SESSION (Helper)
# -----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------------
# PASSWORD FUNCTIONS
# -----------------------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

# -----------------------------
# CREATE USER
# -----------------------------
def create_user(db: Session, user: schemas.UserCreate):
    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed_pass = hash_password(user.password)
    
    db_user = models.User(
        name=user.name,
        email=user.email,
        password=hashed_pass,
        role=user.role,
        roll_number=user.roll_number,
        department=user.department,
        year=user.year
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# -----------------------------
# AUTHENTICATE USER
# -----------------------------
def authenticate_user(db: Session, username: str, password: str, role: str):
    # Search for a user where (email OR roll_number) matches AND the role matches
    user = db.query(models.User).filter(
        ((models.User.email == username) | (models.User.roll_number == username)),
        (models.User.role == role)
    ).first()
    
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user

# -----------------------------
# CREATE JWT TOKEN
# -----------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# -----------------------------
# GET CURRENT USER (TOKEN → USER)
# -----------------------------
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception

    # Query the user by ID
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="User no longer exists"
        )
        
    return user
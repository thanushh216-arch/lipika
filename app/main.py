import os
import shutil
import uuid
from typing import List

from fastapi import FastAPI, Depends, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from gradio_client import Client, handle_file

# Internal project imports
from .database import engine, SessionLocal
from . import models, schemas, auth
from .dependencies import require_role

# Initialize database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Lipika Backend API")

# -----------------------------
# CORS SETTINGS (The Connection Bridge)
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows Lovable and local testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# STATIC FILES SETUP
# -----------------------------
# Creating folders if they don't exist
UPLOAD_DIR = "uploads"
TRAIN_DIR = "training_data"

for folder in [UPLOAD_DIR, TRAIN_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/training_data", StaticFiles(directory=TRAIN_DIR), name="training_data")

# -----------------------------
# DATABASE SESSION
# -----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------------
# AUTHENTICATION
# -----------------------------
@app.get("/")
def read_root():
    return {"message": "Lipika Backend is active and running", "status": "online"}

@app.post("/signup", response_model=schemas.UserOut)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Ensure role is set; default to student if not provided
    return auth.create_user(db, user)

@app.post("/login")
def login(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    # Lovable sends email/password; we verify against Neon
    db_user = auth.authenticate_user(db, login_data.email, login_data.password)

    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = auth.create_access_token(
        data={"sub": str(db_user.id), "role": db_user.role}
    )

    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "role": db_user.role,
        "user": {
            "id": db_user.id,
            "name": db_user.name,
            "email": db_user.email
        }
    }

# -----------------------------
# UTILITIES
# -----------------------------
def get_match_type(score: float):
    if score >= 85: # Tightened thresholds for better accuracy
        return "Strong Match"
    elif score >= 60:
        return "Moderate Match"
    return "Weak Match"

def save_upload_file(upload_file: UploadFile, destination_folder: str) -> str:
    unique_filename = f"{uuid.uuid4()}_{upload_file.filename}"
    file_path = os.path.join(destination_folder, unique_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return file_path

# -----------------------------
# STUDENT: UPLOAD ASSIGNMENT
# -----------------------------
@app.post("/upload-assignment")
async def upload_assignment(
    file: UploadFile = File(...),
    assignment_id: str = Form(None), # Added as optional for Lovable compatibility
    db: Session = Depends(get_db),
    current_user = Depends(require_role("student"))
):
    file_path = save_upload_file(file, UPLOAD_DIR)

    # Check for existing reference
    reference = db.query(models.Assignment).filter(
        models.Assignment.student_id == current_user.id,
        models.Assignment.is_reference == 1
    ).first()

    # If first time, this becomes the master reference
    if reference is None:
        new_assignment = models.Assignment(
            student_id=current_user.id,
            image_path=file_path,
            is_reference=1,
            is_training=True,
            similarity_score=100.0
        )
        db.add(new_assignment)
        db.commit()
        return {
            "message": "First submission: Reference handwriting saved.",
            "similarity_score": 100.0,
            "match_type": "Reference"
        }

    # Compare against reference using Hugging Face
    try:
        client = Client("thanoxz/ml-api")
        result = client.predict(
            handle_file(reference.image_path),
            handle_file(file_path),
            api_name="/compare_handwriting"
        )
        similarity = float(result) if not isinstance(result, list) else float(result[0])
    except Exception as e:
        print(f"ML API Error: {e}")
        similarity = 0.0

    new_assignment = models.Assignment(
        student_id=current_user.id,
        image_path=file_path,
        is_reference=0,
        is_training=False,
        similarity_score=similarity
    )

    db.add(new_assignment)
    db.commit()

    return {
        "message": "Handwriting verification complete",
        "similarity_score": similarity,
        "match_type": get_match_type(similarity)
    }

# -----------------------------
# TEACHER DASHBOARD
# -----------------------------
@app.get("/teacher/assignments")
def get_assignments(
    db: Session = Depends(get_db),
    current_user = Depends(require_role("teacher"))
):
    # Join assignments with user data to show names in the dashboard
    query_result = db.query(models.Assignment, models.User).join(
        models.User, models.Assignment.student_id == models.User.id
    ).filter(models.Assignment.is_reference == 0).all()

    data_list = []
    for assignment, student in query_result:
        data_list.append({
            "id": assignment.id,
            "student_name": student.name,
            "roll_number": student.roll_number,
            "similarity": round(assignment.similarity_score, 2),
            "match_type": get_match_type(assignment.similarity_score),
            "date": assignment.created_at.strftime("%Y-%m-%d %H:%M"),
            "image_url": f"https://thxanozz.onrender.com/{assignment.image_path}" # Full URL for Lovable
        })

    return {"data": data_list}

# -----------------------------
# ADMIN: UPLOAD TRAINING DATA
# -----------------------------
@app.post("/admin/upload-training-by-roll/{roll_number}")
def upload_training_by_roll(
    roll_number: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin"))
):
    student = db.query(models.User).filter(
        models.User.roll_number == roll_number,
        models.User.role == "student"
    ).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student roll number not found")

    folder = os.path.join(TRAIN_DIR, f"student_{student.id}")
    file_path = save_upload_file(file, folder)

    new_training = models.Assignment(
        student_id=student.id,
        image_path=file_path,
        is_reference=0,
        is_training=True,
        similarity_score=100.0
    )
    
    db.add(new_training)
    db.commit()

    return {"message": f"Training data added for {student.name}", "path": file_path}
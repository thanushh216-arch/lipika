import os
import shutil
import uuid
from datetime import timedelta
from typing import List

from fastapi import FastAPI, Depends, File, UploadFile, HTTPException
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
# CORS SETTINGS
# -----------------------------
# This allows your frontend (React, Vue, etc.) to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# STATIC FILES
# -----------------------------
# This makes images in these folders viewable in the browser
# Example: http://127.0.0.1:8000/uploads/your_image.png
if not os.path.exists("uploads"):
    os.makedirs("uploads")
if not os.path.exists("training_data"):
    os.makedirs("training_data")

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/training_data", StaticFiles(directory="training_data"), name="training_data")


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
# ROOT API
# -----------------------------
@app.get("/")
def read_root():
    return {"message": "Lipika Backend is active and running"}

# -----------------------------
# AUTHENTICATION
# -----------------------------
@app.post("/signup", response_model=schemas.UserOut)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return auth.create_user(db, user)

@app.post("/login")
def login(
    login_data: schemas.UserLogin,
    db: Session = Depends(get_db)
):
    db_user = auth.authenticate_user(db, login_data.email, login_data.password)

    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = auth.create_access_token(
        data={"sub": str(db_user.id), "role": db_user.role}
    )

    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "role": db_user.role
    }

# -----------------------------
# UTILITIES
# -----------------------------
def get_match_type(score: float):
    if score >= 75:
        return "Strong Match"
    elif score >= 50:
        return "Moderate Match"
    return "Weak Match"

def save_upload_file(upload_file: UploadFile, destination_folder: str) -> str:
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)
    
    unique_filename = f"{uuid.uuid4()}_{upload_file.filename}"
    file_path = os.path.join(destination_folder, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return file_path

# -----------------------------
# STUDENT: UPLOAD ASSIGNMENT
# -----------------------------
@app.post("/upload-assignment")
def upload_assignment(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(require_role("student"))
):
    file_path = save_upload_file(file, "uploads")

    reference = db.query(models.Assignment).filter(
        models.Assignment.student_id == current_user.id,
        models.Assignment.is_reference == 1
    ).first()

    if reference is None:
        similarity = 100.0
        new_assignment = models.Assignment(
            student_id=current_user.id,
            image_path=file_path,
            is_reference=1,
            is_training=True,
            similarity_score=similarity
        )
        db.add(new_assignment)
        db.commit()

        return {
            "message": "Reference handwriting saved successfully.",
            "similarity_score": similarity,
            "match_type": "Reference"
        }

    try:
        client = Client("thanoxz/ml-api")
        result = client.predict(
            handle_file(reference.image_path),
            handle_file(file_path),
            api_name="/compare_handwriting"
        )
        similarity = float(result)
    except Exception as e:
        print(f"ML Model Error: {e}")
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
        "message": "Assignment verified against reference.",
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
    query_result = db.query(models.Assignment, models.User).join(
        models.User, models.Assignment.student_id == models.User.id
    ).filter(models.Assignment.is_reference == 0).all()

    stats = {"Strong Match": 0, "Moderate Match": 0, "Weak Match": 0}
    data_list = []

    for assignment, student in query_result:
        m_type = get_match_type(assignment.similarity_score)
        stats[m_type] += 1
        
        data_list.append({
            "student_id": assignment.student_id,
            "student_name": student.name,
            "roll_number": student.roll_number,
            "similarity": assignment.similarity_score,
            "match_type": m_type,
            "date": assignment.created_at,
            "image_url": f"/{assignment.image_path}" # Added leading slash for frontend routing
        })

    return {
        "total": len(query_result),
        "summary": stats,
        "data": data_list
    }

# -----------------------------
# ADMIN: MANAGE STUDENTS & DATA
# -----------------------------

@app.get("/admin/students", response_model=List[schemas.UserOut])
def list_students(
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin"))
):
    students = db.query(models.User).filter(models.User.role == "student").all()
    return students

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
        raise HTTPException(
            status_code=404, 
            detail=f"Student with Roll Number '{roll_number}' not found."
        )

    student_id = student.id
    folder = os.path.join("training_data", f"student_{student_id}")
    
    try:
        file_path = save_upload_file(file, folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File save error: {str(e)}")

    new_training = models.Assignment(
        student_id=student_id,
        image_path=file_path,
        is_reference=0,
        is_training=True,
        similarity_score=100.0
    )
    
    db.add(new_training)
    db.commit()
    db.refresh(new_training)

    return {
        "status": "success",
        "message": f"Training data uploaded for {student.name}",
        "roll_number": student.roll_number,
        "file_id": new_training.id,
        "saved_path": f"/{file_path}"
    }
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Get URL from environment (Render/Neon) or fallback to local SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lipika.db")

# 2. Fix for PostgreSQL URL format (SQLAlchemy requires 'postgresql://')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 3. Handle specific arguments for SQLite vs PostgreSQL
# SQLite needs 'check_same_thread: False', but PostgreSQL will crash if it sees it.
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# 4. Create the engine with the dynamic arguments
engine = create_engine(
    DATABASE_URL, 
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
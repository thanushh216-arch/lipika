import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Define the variable FIRST
# This pulls the 'DATABASE_URL' you set in Render's Environment Variables
DATABASE_URL = os.getenv("DATABASE_URL")

# 2. Fix for SQLAlchemy 2.0 (converts postgres:// to postgresql://)
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    SQLALCHEMY_DATABASE_URL = DATABASE_URL

# 3. Now use it in create_engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"sslmode": "require"}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
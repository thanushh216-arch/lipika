import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. GET THE URL FROM RENDER ENVIRONMENT VARIABLES
# This matches the "DATABASE_URL" you set in Render's dashboard
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# 2. FIX FOR POSTGRES DIALECT (Render/Neon specific)
# Neon URLs start with 'postgres://', but SQLAlchemy 2.0 needs 'postgresql://'
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 3. CREATE THE ENGINE
# (Make sure SQLALCHEMY_DATABASE_URL is passed inside here)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"sslmode": "require"}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
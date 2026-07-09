import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database URL configuration (using local SQLite database file erp.db)
DATABASE_URL = "sqlite:///./erp.db"

# Create Database Engine
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Required for SQLite to allow multiple threads
)

# Create Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base for models
Base = declarative_base()

# Database Session Dependency (Generator for route dependency injection)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

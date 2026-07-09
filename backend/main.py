import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

# Import backend modules
from backend.database import engine, Base, get_db
from backend.models import User, Vendor, Invoice, InvoiceItem, AuditLog
from backend.security import get_password_hash
from backend.routes import auth, invoices, vendors, analytics, logs, settings
from backend.routes.invoices import SYSTEM_SETTINGS
from backend.security import get_current_user
from backend.routes.auth import check_admin_user
from backend.schemas import SettingsOut, SettingsUpdate

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ConstructAI ERP Backend Gateway",
    description="REST API core for AI-powered ERP invoice automation platform",
    version="1.0.0"
)

# Configure CORS to allow frontend calls (especially local file execution)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(invoices.router)
app.include_router(vendors.router)
app.include_router(analytics.router)
app.include_router(logs.router)
app.include_router(settings.router)

def save_to_env(key: str, value: str):
    BASE_DIR = Path(__file__).resolve().parent.parent
    env_path = BASE_DIR / ".env"
    
    lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
    key_found = False
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            key_found = True
        else:
            new_lines.append(line)
            
    if not key_found:
        new_lines.append(f"{key}={value}\n")
        
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

# --- SETTINGS ENDPOINTS ---
@app.get("/api/settings", response_model=SettingsOut, tags=["Settings"])
def get_settings(current_user: User = Depends(get_current_user)):
    """
    Retrieves system configuration status (Gemini active state).
    """
    return {
        "has_key": bool(SYSTEM_SETTINGS["gemini_api_key"]),
        "gemini_model": SYSTEM_SETTINGS.get("gemini_model", "gemini-2.0-flash-lite")
    }

@app.put("/api/settings", response_model=SettingsOut, tags=["Settings"])
def update_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(check_admin_user)
):
    """
    Modifies configuration parameters (e.g. keying Gemini API token). ADMIN ONLY.
    """
    if payload.gemini_api_key is not None:
        key = payload.gemini_api_key.strip()
        if key and not (key.startswith("AIza") or key.startswith("AQ")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Gemini API key: must start with 'AIza' or 'AQ'."
            )
        SYSTEM_SETTINGS["gemini_api_key"] = key
        save_to_env("GEMINI_API_KEY", key)
        
    if payload.gemini_model is not None:
        model = payload.gemini_model.strip()
        if not model:
            model = "gemini-2.0-flash-lite"
        SYSTEM_SETTINGS["gemini_model"] = model
        save_to_env("GEMINI_MODEL", model)
        
    # Reload environment
    BASE_DIR = Path(__file__).resolve().parent.parent
    env_path = BASE_DIR / ".env"
    load_dotenv(dotenv_path=env_path, override=True)
    
    # Audit log
    audit = AuditLog(
        user=admin_user.username,
        action="Settings Update",
        details=f"Updated ERP configurations. API key updated: {payload.gemini_api_key is not None}. Model updated: {payload.gemini_model is not None}."
    )
    db.add(audit)
    db.commit()
    
    return {
        "has_key": bool(SYSTEM_SETTINGS["gemini_api_key"]),
        "gemini_model": SYSTEM_SETTINGS.get("gemini_model", "gemini-2.0-flash-lite")
    }

# --- DATABASE SEEDING ON STARTUP & ENVIRONMENT SETUP ---
@app.on_event("startup")
def seed_database():
    # Set Gemini Key dynamically
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key:
        SYSTEM_SETTINGS["gemini_api_key"] = gemini_key
    else:
        SYSTEM_SETTINGS["gemini_api_key"] = ""
        
    SYSTEM_SETTINGS["gemini_model"] = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")

    # 2. Seed default users
    db = next(get_db())
    try:
        if db.query(User).count() == 0:
            admin = User(
                username="admin",
                email="admin@constructai.com",
                password_hash=get_password_hash("admin123"),
                role="ADMIN"
            )
            employee = User(
                username="user",
                email="user@constructai.com",
                password_hash=get_password_hash("user"),
                role="EMPLOYEE"
            )
            db.add(admin)
            db.add(employee)
            db.commit()
            
            # Seed audit log
            db.add(AuditLog(user="system", action="DB Init", details="Created default user login: 'admin' (password: admin123) with role ADMIN."))
            db.add(AuditLog(user="system", action="DB Init", details="Created default employee login: 'user' (password: user) with role EMPLOYEE."))
            db.commit()
    finally:
        db.close()

# Mount frontend files (Must be placed after endpoints definitions to avoid masking routes)
if os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
elif os.path.exists("ConstructAI/frontend"):
    app.mount("/", StaticFiles(directory="ConstructAI/frontend", html=True), name="static")

import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from backend.security import get_current_user
from backend.models import User

router = APIRouter(prefix="/api/settings", tags=["Settings"])

class GeminiKeyPayload(BaseModel):
    api_key: str

@router.get("/gemini")
def get_gemini_key(current_user: User = Depends(get_current_user)):
    # Reload environment to check key
    BASE_DIR = Path(__file__).resolve().parents[2]
    env_path = BASE_DIR / ".env"
    load_dotenv(dotenv_path=env_path, override=True)
    
    key = os.getenv("GEMINI_API_KEY", "")
    # Return masked key or whether it exists
    return {
        "has_key": bool(key),
        "api_key": key[:6] + "x" * (len(key) - 6) if len(key) > 6 else key
    }

@router.post("/gemini")
def save_gemini_key(payload: GeminiKeyPayload, current_user: User = Depends(get_current_user)):
    key = payload.api_key.strip()
    
    # Validation: Key must start with AIza or AQ
    if not (key.startswith("AIza") or key.startswith("AQ")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Gemini API key: must start with 'AIza' or 'AQ'."
        )
        
    # Find .env path
    BASE_DIR = Path(__file__).resolve().parents[2]
    env_path = BASE_DIR / ".env"
    
    # Read existing .env lines
    lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
    # Check if GEMINI_API_KEY exists, replace or append
    key_found = False
    new_lines = []
    for line in lines:
        if line.strip().startswith("GEMINI_API_KEY"):
            new_lines.append(f"GEMINI_API_KEY={key}\n")
            key_found = True
        else:
            new_lines.append(line)
            
    if not key_found:
        new_lines.append(f"GEMINI_API_KEY={key}\n")
        
    # Write back to .env
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
        
    # Force reload environment variables
    load_dotenv(dotenv_path=env_path, override=True)
    
    # Also reload in backend/routes/invoices.py's SYSTEM_SETTINGS
    from backend.routes.invoices import SYSTEM_SETTINGS
    SYSTEM_SETTINGS["gemini_api_key"] = key
    
    return {
        "success": True,
        "message": "Gemini API Key Saved Successfully"
    }

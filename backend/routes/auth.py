from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, AuditLog
from backend.schemas import UserCreate, UserOut, Token
from backend.security import get_password_hash, verify_password, create_access_token, SECRET_KEY, ALGORITHM, get_current_user, oauth2_scheme

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def check_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to ensure the current authenticated user is an ADMIN.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin access required."
        )
    return current_user

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Registers a new user in the system.
    """
    # Check if username or email already exists
    existing_user = db.query(User).filter(
        (User.username == user_in.username) | (User.email == user_in.email)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or Email already registered."
        )
        
    hashed_pwd = get_password_hash(user_in.password)
    new_user = User(
        username=user_in.username,
        email=user_in.email,
        password_hash=hashed_pwd,
        role=user_in.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Log registration in audits
    audit = AuditLog(
        user=new_user.username,
        action="User Register",
        details=f"Account created successfully for email '{new_user.email}' with role '{new_user.role}'."
    )
    db.add(audit)
    db.commit()
    
    return new_user

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordBearer = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Note: Using custom JSON payload instead of OAuth2 password request form for clean SPA JSON requests
    pass

# We will implement a custom JSON login endpoint alongside the standard one for frontend ease-of-use
from pydantic import BaseModel
class LoginPayload(BaseModel):
    username: str
    password: str

@router.post("/login/json", response_model=Token)
def login_json(payload: LoginPayload, db: Session = Depends(get_db)):
    """
    JSON endpoint for user login. Returns access token.
    """
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password."
        )
        
    # Update audits
    audit = AuditLog(
        user=user.username,
        action="User Login",
        details=f"User login successful from frontend API. Role: {user.role}."
    )
    db.add(audit)
    db.commit()
    
    access_token = create_access_token(subject=user.username)
    return {"access_token": access_token, "token_type": "bearer"}

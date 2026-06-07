from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database.session import get_db
from models.user import User
from schemas import UserCreate, TokenOut, UserOut
from core.security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=TokenOut)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    exists = db.query(User).filter(User.email == email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(name=payload.name, email=email, password_hash=hash_password(payload.password), role="user")
    db.add(user); db.commit(); db.refresh(user)
    return {"access_token": create_access_token(user.email), "user": user}


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    email = form.username.strip().lower()
    print(f"[DEBUG AUTH] Login attempt email: '{email}', password: '{form.password}'")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        print(f"[DEBUG AUTH] User not found for email: '{email}'")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong email or password")
    
    password_ok = verify_password(form.password, user.password_hash)
    print(f"[DEBUG AUTH] User found. Password match result: {password_ok}")
    
    if not password_ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong email or password")
    return {"access_token": create_access_token(user.email), "user": user}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user

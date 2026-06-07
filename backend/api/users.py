from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.session import get_db
from core.security import get_current_user
from models.user import User
from schemas import UserOut

router = APIRouter(prefix="/users", tags=["users"])

@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return db.query(User).all()

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from database.session import get_db
from models.user import User
from models.model_version import ModelVersion
from core.security import get_current_user
from schemas import ModelVersionOut

router = APIRouter(prefix="/admin/model-versions", tags=["model_versions"])

def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user

@router.get("", response_model=list[ModelVersionOut])
def get_model_versions(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return db.query(ModelVersion).all()

@router.post("/{id}/deploy", response_model=ModelVersionOut)
def deploy_model_version(id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    mv = db.query(ModelVersion).filter(ModelVersion.id == id).first()
    if not mv:
        raise HTTPException(status_code=404, detail="Model version not found")
        
    # Archive any currently deployed model versions
    currently_deployed = db.query(ModelVersion).filter(ModelVersion.status == "current").all()
    for current in currently_deployed:
        current.status = "archived"
        
    mv.status = "current"
    mv.deployed_at = datetime.utcnow()
    db.commit()
    db.refresh(mv)
    return mv

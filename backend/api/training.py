from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
import time
import json
from datetime import datetime
from database.session import get_db
from models.user import User
from models.training_job import TrainingJob
from models.training_dataset import TrainingDataset
from models.model_version import ModelVersion
from core.security import get_current_user
from schemas import TrainingJobOut, TrainingJobCreate

router = APIRouter(prefix="/admin/training", tags=["training"])

def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user

@router.get("/jobs", response_model=list[TrainingJobOut])
def get_jobs(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return db.query(TrainingJob).all()

@router.post("/jobs", response_model=TrainingJobOut)
def create_job(payload: TrainingJobCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    dataset_size = db.query(TrainingDataset).filter(TrainingDataset.status == "active").count()
    job = TrainingJob(
        model_name=payload.model_name,
        status="pending",
        dataset_size=dataset_size,
        config_json=payload.config_json or json.dumps({"learning_rate": 0.001, "epochs": 5, "batch_size": 16}),
        created_by=admin.id
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

# Background simulation function
def simulate_training_run(job_id: int):
    # We open a new session in the background thread
    from database.session import SessionLocal
    db = SessionLocal()
    try:
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if not job:
            return
            
        # Simulate running state
        job.status = "running"
        db.commit()
        time.sleep(10)
        
        # Simulate evaluating state
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        job.status = "evaluating"
        db.commit()
        time.sleep(5)
        
        # Simulate completion
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        job.status = "completed"
        metrics = {
            "bleu_4": 0.42 + (time.time() % 10) / 100.0,
            "cider": 0.85 + (time.time() % 10) / 100.0,
            "loss": 0.12 - (time.time() % 10) / 200.0
        }
        job.result_metrics_json = json.dumps(metrics)
        
        # Also create a new model version candidate
        new_version_num = f"v1.0.{job_id}"
        mv = ModelVersion(
            version=new_version_num,
            checkpoint_path=f"/models/checkpoints/{job.model_name}_{new_version_num}",
            metrics_json=json.dumps(metrics),
            status="candidate"
        )
        db.add(mv)
        db.commit()
    except Exception as e:
        print(f"Error in training simulation: {e}")
        db.rollback()
    finally:
        db.close()

@router.post("/jobs/{id}/start", response_model=TrainingJobOut)
def start_job(id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    job = db.query(TrainingJob).filter(TrainingJob.id == id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    if job.status != "pending":
        raise HTTPException(status_code=400, detail=f"Job cannot be started. Current status: {job.status}")
        
    job.status = "running"
    db.commit()
    
    # Run the simulation in background task
    background_tasks.add_task(simulate_training_run, job.id)
    
    db.refresh(job)
    return job

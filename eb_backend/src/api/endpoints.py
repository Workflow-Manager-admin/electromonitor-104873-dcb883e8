from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import List, Optional
import os

from . import models, schemas, database

# JWT config
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "supersecretjwtkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hrs

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/api", tags=["api-v1"])

# Utility functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(db, user_id)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_officer(current_user: models.User = Depends(get_current_active_user)):
    # officer role has name == 'officer'
    if current_user.role is None or current_user.role.name.lower() != "officer":
        raise HTTPException(status_code=403, detail="Only officers allowed")
    return current_user

async def get_current_customer(current_user: models.User = Depends(get_current_active_user)):
    # customer role has name == 'customer'
    if current_user.role is None or current_user.role.name.lower() != "customer":
        raise HTTPException(status_code=403, detail="Only customers allowed")
    return current_user

# PUBLIC_INTERFACE
@router.post("/register", response_model=schemas.User, summary="Register new user", tags=["auth"])
def register_user(user_in: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """
    Register a new user (customer or officer).
    """
    if get_user_by_username(db, user_in.username):
        raise HTTPException(status_code=400, detail="Username already registered.")
    if get_user_by_email(db, user_in.email):
        raise HTTPException(status_code=400, detail="Email already registered.")

    hashed_pw = get_password_hash(user_in.password)
    new_user = models.User(
        username=user_in.username,
        full_name=user_in.full_name,
        email=user_in.email,
        hashed_password=hashed_pw,
        role_id=user_in.role_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# PUBLIC_INTERFACE
@router.post("/login", summary="Login (get access token)", tags=["auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    """
    Authenticate user and return JWT access token.
    """
    user = get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

# PUBLIC_INTERFACE
@router.get("/me", response_model=schemas.User, summary="Get current user", tags=["users"])
def get_me(current_user: models.User = Depends(get_current_active_user)):
    """
    Retrieve authenticated user's information.
    """
    return current_user

# --- CRUD: Users (Officers: manage all, Customers: self) ---
# PUBLIC_INTERFACE
@router.get("/users/", response_model=List[schemas.User], summary="List all users [officer only]", tags=["users"])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db), officer: models.User = Depends(get_current_officer)):
    """
    Officer: list all users.
    """
    return db.query(models.User).offset(skip).limit(limit).all()

@router.get("/users/{user_id}", response_model=schemas.User, summary="Get single user [officer only]", tags=["users"])
def read_user(user_id: int, db: Session = Depends(database.get_db), officer: models.User = Depends(get_current_officer)):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/users/{user_id}", response_model=schemas.User, summary="Update user [officer only]", tags=["users"])
def update_user(user_id: int, data: schemas.UserBase, db: Session = Depends(database.get_db), officer: models.User = Depends(get_current_officer)):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.username = data.username
    user.full_name = data.full_name
    user.email = data.email
    db.commit()
    db.refresh(user)
    return user

@router.delete("/users/{user_id}", summary="Delete user [officer only]", tags=["users"])
def delete_user(user_id: int, db: Session = Depends(database.get_db), officer: models.User = Depends(get_current_officer)):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"detail": f"User {user_id} deleted."}

# --- CRUD: Usage readings ---
# PUBLIC_INTERFACE
@router.post("/usage/", response_model=schemas.Usage, summary="Add usage (reading)", tags=["usage"])
def add_usage(usage: schemas.UsageCreate, db: Session = Depends(database.get_db), officer: models.User = Depends(get_current_officer)):
    new_usage = models.Usage(**usage.dict())
    db.add(new_usage)
    db.commit()
    db.refresh(new_usage)
    return new_usage

@router.get("/usage/", response_model=List[schemas.Usage], summary="List all usage [officer only]", tags=["usage"])
def list_usage(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db), officer: models.User = Depends(get_current_officer)):
    return db.query(models.Usage).offset(skip).limit(limit).all()

@router.get("/usage/customer", response_model=List[schemas.Usage], summary="Get my usage readings [customer]", tags=["usage"])
def get_customer_usage(current_user: models.User = Depends(get_current_customer), db: Session = Depends(database.get_db)):
    return db.query(models.Usage).filter(models.Usage.user_id == current_user.id).all()

# --- CRUD: Bills ---
# PUBLIC_INTERFACE
@router.post("/bills/", response_model=schemas.Bill, summary="Create bill [officer only]", tags=["bills"])
def create_bill(data: schemas.BillCreate, db: Session = Depends(database.get_db), officer: models.User = Depends(get_current_officer)):
    new_bill = models.Bill(**data.dict())
    db.add(new_bill)
    db.commit()
    db.refresh(new_bill)
    return new_bill

@router.get("/bills/", response_model=List[schemas.Bill], summary="List all bills [officer only]", tags=["bills"])
def list_bills(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db), officer: models.User = Depends(get_current_officer)):
    return db.query(models.Bill).offset(skip).limit(limit).all()

@router.get("/bills/customer", response_model=List[schemas.Bill], summary="Get my bills [customer]", tags=["bills"])
def get_customer_bills(current_user: models.User = Depends(get_current_customer), db: Session = Depends(database.get_db)):
    return db.query(models.Bill).filter(models.Bill.user_id == current_user.id).all()

@router.put("/bills/{bill_id}", response_model=schemas.Bill, summary="Officer updates bill status", tags=["bills"])
def update_bill(bill_id: int, status: Optional[str] = None, db: Session = Depends(database.get_db), officer: models.User = Depends(get_current_officer)):
    bill = db.query(models.Bill).filter(models.Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    if status:
        bill.status = status
        db.commit()
        db.refresh(bill)
    return bill

# --- CRUD: Notifications ---
# PUBLIC_INTERFACE
@router.post("/notifications/", response_model=schemas.Notification, summary="Create notification [officer only]", tags=["notifications"])
def create_notification(payload: schemas.NotificationCreate, db: Session = Depends(database.get_db), officer: models.User = Depends(get_current_officer)):
    notification = models.Notification(**payload.dict())
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification

@router.get("/notifications/", response_model=List[schemas.Notification], summary="List notifications [officer only]", tags=["notifications"])
def list_all_notifications(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db), officer: models.User = Depends(get_current_officer)):
    return db.query(models.Notification).offset(skip).limit(limit).all()

@router.get("/notifications/customer", response_model=List[schemas.Notification], summary="Get my notifications [customer]", tags=["notifications"])
def get_customer_notifications(current_user: models.User = Depends(get_current_customer), db: Session = Depends(database.get_db)):
    return db.query(models.Notification).filter(models.Notification.user_id == current_user.id).all()

@router.put("/notifications/{notification_id}", response_model=schemas.Notification, summary="Mark as read (customer only)", tags=["notifications"])
def mark_notification_as_read(notification_id: int, current_user: models.User = Depends(get_current_customer), db: Session = Depends(database.get_db)):
    notif = db.query(models.Notification).filter(models.Notification.id == notification_id, models.Notification.user_id == current_user.id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif

# --- Analytics Endpoints ---
# PUBLIC_INTERFACE
@router.get("/analytics/usage-summary", summary="Usage summary stats (officer only)", tags=["analytics"])
def usage_summary(db: Session = Depends(database.get_db), officer: models.User = Depends(get_current_officer)):
    """
    Get usage total/average per customer for dashboard charts.
    """
    from sqlalchemy import func
    results = db.query(
        models.User.id,
        models.User.username,
        func.count(models.Usage.id),
        func.sum(models.Usage.reading_value),
        func.avg(models.Usage.reading_value)
    ).outerjoin(models.Usage, models.User.id == models.Usage.user_id).group_by(models.User.id).all()
    return [
        {
            "user_id": user_id,
            "username": username,
            "usage_count": usage_count,
            "total_usage": float(total or 0),
            "average_usage": float(avg or 0)
        }
        for user_id, username, usage_count, total, avg in results
    ]

@router.get("/analytics/bill-stats", summary="Bill stats - paid/overdue (officer only)", tags=["analytics"])
def bill_stats(db: Session = Depends(database.get_db), officer: models.User = Depends(get_current_officer)):
    """
    Dashboard bill status stats.
    """
    from sqlalchemy import func
    status_counts = db.query(
        models.Bill.status, func.count(models.Bill.id)
    ).group_by(models.Bill.status).all()
    return {k: v for k, v in status_counts}

# Officer/Customer dashboard direct endpoints
@router.get("/officer/dashboard", summary="Officer dashboard quick stats", tags=["dashboards"])
def officer_dashboard(db: Session = Depends(database.get_db), officer: models.User = Depends(get_current_officer)):
    """
    Stats: total users, total readings, unpaid bills, total notifications pending.
    """
    n_users = db.query(models.User).count()
    n_usage = db.query(models.Usage).count()
    n_unpaid = db.query(models.Bill).filter(models.Bill.status == "pending").count()
    n_notif = db.query(models.Notification).filter(models.Notification.is_read == False).count()
    return {
        "total_users": n_users,
        "total_usage_records": n_usage,
        "unpaid_bills": n_unpaid,
        "pending_notifications": n_notif,
    }

@router.get("/customer/dashboard", summary="Customer dashboard quick stats", tags=["dashboards"])
def customer_dashboard(current_user: models.User = Depends(get_current_customer), db: Session = Depends(database.get_db)):
    """
    My usage count, unpaid bills, unread notifications.
    """
    n_usage = db.query(models.Usage).filter(models.Usage.user_id == current_user.id).count()
    n_unpaid = db.query(models.Bill).filter(models.Bill.user_id == current_user.id, models.Bill.status == "pending").count()
    n_unread = db.query(models.Notification).filter(models.Notification.user_id == current_user.id, models.Notification.is_read == False).count()
    return {
        "my_usage_records": n_usage,
        "unpaid_bills": n_unpaid,
        "unread_notifications": n_unread,
    }

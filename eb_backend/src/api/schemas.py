from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# PUBLIC_INTERFACE
class RoleBase(BaseModel):
    """Base schema for Role."""
    name: str = Field(..., description="Name of the role (officer/customer)")

class RoleCreate(RoleBase):
    pass

class Role(RoleBase):
    id: int

    class Config:
        orm_mode = True

# PUBLIC_INTERFACE
class UserBase(BaseModel):
    """Base schema for User info."""
    username: str = Field(..., description="Username")
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Account password")
    role_id: int

class User(UserBase):
    id: int
    is_active: bool
    role: Optional[Role] = None

    class Config:
        orm_mode = True

# PUBLIC_INTERFACE
class UsageBase(BaseModel):
    """Base schema for usage reading."""
    reading_value: float = Field(..., description="Electricity usage value")
    timestamp: Optional[datetime]
    description: Optional[str] = None

class UsageCreate(UsageBase):
    user_id: int

class Usage(UsageBase):
    id: int
    user_id: int

    class Config:
        orm_mode = True

# PUBLIC_INTERFACE
class BillBase(BaseModel):
    """Base schema for Bill."""
    amount: float
    due_date: datetime
    status: Optional[str]
    generated_at: Optional[datetime]

class BillCreate(BillBase):
    user_id: int
    usage_id: int

class Bill(BillBase):
    id: int
    user_id: int
    usage_id: int

    class Config:
        orm_mode = True

# PUBLIC_INTERFACE
class NotificationBase(BaseModel):
    """Base schema for Notifications."""
    content: str
    sent_at: Optional[datetime]
    is_read: Optional[bool] = False

class NotificationCreate(NotificationBase):
    user_id: int
    bill_id: Optional[int] = None

class Notification(NotificationBase):
    id: int
    user_id: int
    bill_id: Optional[int] = None

    class Config:
        orm_mode = True
